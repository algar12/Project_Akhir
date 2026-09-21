"""
rule_engine.py — Unified Network Guard: Detection
==================================================
Engine deteksi berbasis aturan (rule-based / threshold-based) yang
beroperasi secara real-time terhadap data traffic jaringan.

Serangan yang dideteksi:
  1. PORT SCAN      — banyak port berbeda dari satu source dalam window pendek
  2. SYN FLOOD      — banjir paket SYN ke satu target
  3. ICMP FLOOD     — banjir paket ICMP echo ke subnet IoT
  4. TRAFFIC SPIKE  — lonjakan bytes/detik dari satu source
  5. MQTT RATE ABUSE— jumlah pesan MQTT sangat tinggi dari satu client

Prinsip kerja:
  - Masing-masing rule memiliki sliding-window time bucket sendiri.
  - Setiap record traffic dari DB (atau langsung dari collector) dievaluasi.
  - Jika threshold terlampaui → buat Alert dan kirim ke AlertManager.
  - RuleEngine berjalan di thread terpisah, polling DB setiap N detik
    untuk menganalisis traffic yang baru masuk.

Desain sliding window:
  - Menggunakan collections.deque per (source_ip) dengan maxlen implisit
    dari window waktu (time-based eviction).
  - Lebih ringan dari time-series DB query untuk use-case real-time.
"""

import ipaddress
import logging
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool

from detection.config import (
    DATABASE_URL,
    IOT_SUBNET,
    PORTSCAN_PKT_THRESHOLD,
    PORTSCAN_WINDOW_SECONDS,
    SYNFLOOD_PKT_THRESHOLD,
    SYNFLOOD_WINDOW_SECONDS,
    ICMPFLOOD_PKT_THRESHOLD,
    ICMPFLOOD_WINDOW_SECONDS,
    TRAFFIC_SPIKE_BPS,
    TRAFFIC_SPIKE_WINDOW,
    MQTT_RATE_THRESHOLD,
    MQTT_RATE_WINDOW,
)
from detection.alert_manager import Alert, AlertManager, map_severity

logger = logging.getLogger(__name__)

# Interval polling DB (detik) — seberapa sering engine ambil data traffic baru
RULE_ENGINE_POLL_INTERVAL: int = 3


# ─── Sliding Window Helper ────────────────────────────────────────────────────
class TimeWindow:
    """
    Struktur data ringan untuk sliding window berbasis waktu.

    Menyimpan timestamp + value (misal bytes atau port) dalam deque.
    Setiap kali count() dipanggil, entri yang lebih lama dari `window_seconds`
    secara otomatis dievict.
    """

    def __init__(self, window_seconds: int) -> None:
        self.window_seconds = window_seconds
        # Setiap entri: (timestamp: datetime, value: Any)
        self._data: deque[tuple[datetime, Any]] = deque()

    def add(self, value: Any = 1, ts: datetime | None = None) -> None:
        self._data.append((ts or datetime.now(timezone.utc).replace(tzinfo=None), value))

    def _evict(self) -> None:
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=self.window_seconds)
        while self._data and self._data[0][0] < cutoff:
            self._data.popleft()

    def count(self) -> int:
        """Jumlah entri dalam window aktif."""
        self._evict()
        return len(self._data)

    def sum(self) -> float:
        """Jumlah nilai (value) dalam window aktif."""
        self._evict()
        return sum(v for _, v in self._data)

    def unique_values(self) -> set:
        """Jumlah nilai unik dalam window (untuk hitung unique port)."""
        self._evict()
        return {v for _, v in self._data}


# ─── Rule Engine ─────────────────────────────────────────────────────────────
def _is_private_ip(ip: str) -> bool:
    """
    True jika IP termasuk LAN privat (RFC1918 / loopback / link-local).
    Digunakan untuk menolak source publik (mis. IP Google) yang sempat
    memicu false positive PORT_SCAN / TRAFFIC_SPIKE pada demo.
    """
    if not ip:
        return False
    try:
        addr = ipaddress.ip_address(ip)
        return bool(addr.is_private or addr.is_loopback or addr.is_link_local)
    except ValueError:
        return False


def _get_local_ip() -> str:
    """
    IP lokal host pemantau (via route default, tanpa mengirim paket nyata).
    Dipakai untuk mengecualikan traffic host sendiri dari analisis serangan.
    """
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 80))   # hanya pilih route — tidak mengirim data
            return s.getsockname()[0]
        finally:
            s.close()
    except Exception:  # noqa: BLE001
        return ''


class RuleEngine:
    """
    Mesin deteksi berbasis aturan yang memantau traffic jaringan secara
    real-time dengan polling database periodik.

    Usage:
        mgr = AlertManager()
        engine = RuleEngine(alert_manager=mgr)
        engine.start()
        ...
        engine.stop()
    """

    def __init__(self, alert_manager: AlertManager) -> None:
        self.alert_manager = alert_manager
        self._stop_event   = threading.Event()
        self._thread: threading.Thread | None = None

        # IP host pemantau sendiri — traffic host (mis. browsing/download besar)
        # TIDAK diatribusikan sebagai serangan dari host (host = pengamat, bukan
        # entitas yang dipantau). Diisi dinamis via route default.
        self._local_host_ip = _get_local_ip()
        if self._local_host_ip:
            logger.info("[RuleEngine] IP host lokal (tidak dianalisis): %s", self._local_host_ip)

        # Sliding windows per source IP
        # format: {source_ip: TimeWindow}
        self._portscan_windows:  dict[str, TimeWindow] = defaultdict(
            lambda: TimeWindow(PORTSCAN_WINDOW_SECONDS)
        )
        self._synflood_windows:  dict[str, TimeWindow] = defaultdict(
            lambda: TimeWindow(SYNFLOOD_WINDOW_SECONDS)
        )
        self._icmpflood_windows: dict[str, TimeWindow] = defaultdict(
            lambda: TimeWindow(ICMPFLOOD_WINDOW_SECONDS)
        )
        self._spike_windows:     dict[str, TimeWindow] = defaultdict(
            lambda: TimeWindow(TRAFFIC_SPIKE_WINDOW)
        )
        self._mqtt_rate_windows: dict[str, TimeWindow] = defaultdict(
            lambda: TimeWindow(MQTT_RATE_WINDOW)
        )

        # Checkpoint berbasis ID (bukan timestamp) — baris dengan timestamp identik
        # tidak pernah terlewat, dan data >2000 per polling diproses pada
        # iterasi berikutnya (tidak dibuang). Dimulai dari ID terbaru saat start
        # agar tidak mengulang analisis seluruh histori (hindari banjir alert lama).
        self._last_analyzed_id: int = 0
        try:
            with create_engine(
                DATABASE_URL,
                poolclass=QueuePool,
                pool_size=2,
                max_overflow=2,
                pool_pre_ping=True,
                echo=False,
            ).connect() as conn:
                self._last_analyzed_id = int(
                    conn.execute(
                        text("SELECT COALESCE(MAX(id), 0) FROM network_traffic")
                    ).scalar_one()
                )
            logger.info(
                "[RuleEngine] Checkpoint awal = id %d (histori tidak diulang)",
                self._last_analyzed_id,
            )
        except Exception as exc:
            logger.warning(
                "[RuleEngine] Gagal ambil MAX(id) awal: %s — mulai dari 0.", exc
            )

        # DB engine
        self._engine = create_engine(
            DATABASE_URL,
            poolclass=QueuePool,
            pool_size=3,
            max_overflow=5,
            pool_pre_ping=True,
            echo=False,
        )

        self._total_analyzed   = 0
        self._total_alerts_gen = 0

    # ─── Internal: Ambil Traffic Baru dari DB ────────────────────────────────
    def _fetch_new_traffic(self) -> list[dict[str, Any]]:
        """
        Mengambil record traffic_jaringan yang belum dianalisis
        (id > _last_analyzed_id) dari database.
        """
        sql = text("""
            SELECT
                id, timestamp, source_ip, destination_ip, protocol,
                source_port, destination_port, packet_count, bytes,
                is_syn, icmp_type
            FROM network_traffic
            WHERE id > :last_id
            ORDER BY id ASC
            LIMIT 2000
        """)
        try:
            with self._engine.connect() as conn:
                rows = conn.execute(sql, {'last_id': self._last_analyzed_id})
                return [dict(r._mapping) for r in rows]
        except Exception as exc:
            logger.error("[RuleEngine] Gagal fetch traffic: %s", exc)
            return []

    # ─── Internal: Analisis Satu Record ──────────────────────────────────────
    def _analyze_record(self, rec: dict[str, Any]) -> None:
        """Evaluasi satu record traffic terhadap semua aturan."""
        src   = rec.get('source_ip', '')
        dst   = rec.get('destination_ip', '')
        proto = rec.get('protocol', '').upper()
        sport = rec.get('source_port')
        dport = rec.get('destination_port')
        nbytes= rec.get('bytes', 0) or 0
        ts    = rec.get('timestamp', datetime.now(timezone.utc).replace(tzinfo=None))

        # ── Guard: hanya analisis sumber dari LAN privat (RFC1918) ────────────
        # Mencegah false positive dari IP publik (mis. 172.217.x — Google)
        # yang muncul sebagai source saat akses internet dari subnet IoT.
        if not _is_private_ip(src):
            return

        # ── Guard: kecualikan traffic host pemantau sendiri ──────────────────
        # Host (browsing/download besar) adalah pengamat, bukan entitas yang
        # dipantau — traffic-nya tidak diatribusikan sebagai serangan.
        if self._local_host_ip and src == self._local_host_ip:
            return

        # ── Rule 1: Port Scan ─────────────────────────────────────────────────
        # HANYA paket TCP SYN murni (is_syn=true): satu source mencoba banyak
        # destination_port berbeda — bukan seluruh volume TCP (klien normal
        # yang berkomunikasi ke banyak port tidak memicu false positive).
        if proto == 'TCP' and dport is not None and rec.get('is_syn'):
            win = self._portscan_windows[src]
            win.add(value=dport, ts=ts)
            unique_ports = win.unique_values()
            if len(unique_ports) >= PORTSCAN_PKT_THRESHOLD:
                self._emit_alert(Alert(
                    source_ip=src,
                    target_ip=dst,
                    attack_type='PORT_SCAN',
                    severity='MEDIUM',
                    confidence=0.85,
                    description=(
                        f"Terdeteksi {len(unique_ports)} port unik "
                        f"dipindai dari {src} dalam {PORTSCAN_WINDOW_SECONDS}s "
                        f"(threshold: {PORTSCAN_PKT_THRESHOLD})"
                    ),
                    timestamp=ts,
                ))

        # ── Rule 2: SYN Flood ─────────────────────────────────────────────────
        # HANYA menghitung paket TCP dengan flag SYN murni (is_syn=true),
        # bukan seluruh volume TCP — sehingga HTTPS/browsing normal
        # (data payload TCP biasa) tidak lagi memicu SYN flood palsu.
        if proto == 'TCP' and rec.get('is_syn'):
            win = self._synflood_windows[f"{src}->{dst}"]
            win.add(ts=ts)
            if win.count() >= SYNFLOOD_PKT_THRESHOLD:
                self._emit_alert(Alert(
                    source_ip=src,
                    target_ip=dst,
                    attack_type='SYN_FLOOD',
                    severity='HIGH',
                    confidence=0.80,
                    description=(
                        f"SYN Flood: {win.count()} paket SYN dari {src} "
                        f"ke {dst} dalam {SYNFLOOD_WINDOW_SECONDS}s "
                        f"(threshold: {SYNFLOOD_PKT_THRESHOLD})"
                    ),
                    timestamp=ts,
                ))

        # ── Rule 3: ICMP Flood ────────────────────────────────────────────────────
        # HANYA menghitung ICMP Echo Request (type 8) — reply (type 0)
        # dari korban tidak diatribusikan sebagai serangan dari korban.
        if proto == 'ICMP' and rec.get('icmp_type') == 8:
            win = self._icmpflood_windows[src]
            win.add(ts=ts)
            if win.count() >= ICMPFLOOD_PKT_THRESHOLD:
                self._emit_alert(Alert(
                    source_ip=src,
                    target_ip=dst,
                    attack_type='ICMP_FLOOD',
                    severity='HIGH',
                    confidence=0.90,
                    description=(
                        f"ICMP Flood: {win.count()} paket dari {src} "
                        f"ke {dst} dalam {ICMPFLOOD_WINDOW_SECONDS}s "
                        f"(threshold: {ICMPFLOOD_PKT_THRESHOLD})"
                    ),
                    timestamp=ts,
                ))

        # ── Rule 4: Traffic Spike (bytes) ─────────────────────────────────────
        win = self._spike_windows[src]
        win.add(value=nbytes, ts=ts)
        total_bytes = win.sum()
        if total_bytes >= TRAFFIC_SPIKE_BPS:
            self._emit_alert(Alert(
                source_ip=src,
                target_ip=dst,
                attack_type='TRAFFIC_SPIKE',
                severity='MEDIUM',
                confidence=0.70,
                description=(
                    f"Traffic spike: {total_bytes:,} bytes dari {src} "
                    f"dalam {TRAFFIC_SPIKE_WINDOW}s "
                    f"(threshold: {TRAFFIC_SPIKE_BPS:,} bytes / {TRAFFIC_SPIKE_WINDOW}s)"
                ),
                timestamp=ts,
            ))

        # ── Rule 5: MQTT Rate Abuse ───────────────────────────────────────────
        # Terlalu banyak paket ke port 1883 dari satu source
        if dport == 1883:
            win = self._mqtt_rate_windows[src]
            win.add(ts=ts)
            if win.count() >= MQTT_RATE_THRESHOLD:
                self._emit_alert(Alert(
                    source_ip=src,
                    target_ip=dst,
                    attack_type='MQTT_RATE_ABUSE',
                    severity='MEDIUM',
                    confidence=0.75,
                    description=(
                        f"MQTT rate abuse: {win.count()} koneksi/paket "
                        f"dari {src} ke broker dalam {MQTT_RATE_WINDOW}s "
                        f"(threshold: {MQTT_RATE_THRESHOLD})"
                    ),
                    timestamp=ts,
                ))

    # ─── Internal: Emit Alert ─────────────────────────────────────────────────
    def _emit_alert(self, alert: Alert) -> None:
        """Teruskan alert ke AlertManager dan update statistik."""
        inserted = self.alert_manager.process(alert)
        if inserted:
            self._total_alerts_gen += 1

    # ─── Internal: Loop Utama ─────────────────────────────────────────────────
    def _run_loop(self) -> None:
        """Loop polling yang berjalan di thread terpisah."""
        logger.info("[RuleEngine] Mulai. Polling setiap %ds.", RULE_ENGINE_POLL_INTERVAL)
        while not self._stop_event.is_set():
            records = self._fetch_new_traffic()

            if records:
                for rec in records:
                    self._analyze_record(rec)
                    self._total_analyzed += 1

                # Update checkpoint timestamp ke record terakhir
                self._last_analyzed_id = records[-1]['id']

                logger.debug(
                    "[RuleEngine] Dianalisis: %d record | Alert dibuat: %d",
                    len(records), self._total_alerts_gen,
                )

            self._stop_event.wait(timeout=RULE_ENGINE_POLL_INTERVAL)

        logger.info("[RuleEngine] Loop berhenti.")

    # ─── Public API ──────────────────────────────────────────────────────────
    def start(self) -> None:
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            name='rule-engine',
            daemon=True,
        )
        self._thread.start()
        logger.info("[RuleEngine] Thread aktif.")

    def stop(self) -> None:
        logger.info("[RuleEngine] Menghentikan...")
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10)
        logger.info(
            "[RuleEngine] Berhenti. Dianalisis: %d | Alert: %d",
            self._total_analyzed, self._total_alerts_gen,
        )

    @property
    def stats(self) -> dict[str, int]:
        return {
            'total_analyzed':   self._total_analyzed,
            'total_alerts_gen': self._total_alerts_gen,
        }
