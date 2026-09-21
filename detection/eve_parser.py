"""
eve_parser.py — Unified Network Guard: Detection
=================================================
Parser log Suricata secara real-time menggunakan teknik "tail -f" (inotify-like
polling) terhadap file /var/log/suricata/eve.json.

Format EVE (Event-Based Extensible) JSON adalah format output Suricata modern
yang menggabungkan semua tipe event (alert, flow, dns, http, tls, dll.)
dalam satu file JSONL (JSON Lines — satu event per baris).

Alur kerja:
  1. Buka file EVE dan seek ke EOF (agar tidak memproses log lama saat start).
  2. Polling setiap EVE_POLL_INTERVAL detik untuk baris baru.
  3. Parse JSON setiap baris.
  4. Filter hanya event_type == "alert".
  5. Ekstrak: timestamp, src_ip, dest_ip, proto, classtype, signature, severity.
  6. Buat objek Alert dan kirim ke AlertManager.

Menangani edge case:
  - File belum ada (Suricata belum dimulai) → retry loop.
  - File di-rotate (ukuran file lebih kecil dari posisi terakhir) → reopen.
  - Baris JSON rusak / parsial → skip & log warning.
"""

import json
import logging
import os
import threading
import time
from datetime import datetime, timezone

from detection.config import SURICATA_EVE_PATH, EVE_POLL_INTERVAL
from detection.alert_manager import Alert, AlertManager, map_severity

logger = logging.getLogger(__name__)


# ─── Peta Suricata severity (int) → string ────────────────────────────────────
# Suricata menggunakan angka 1-4: 1=Critical, 2=Major, 3=Minor, 4=Informational
SURICATA_SEVERITY_MAP: dict[int, str] = {
    1: 'CRITICAL',
    2: 'HIGH',
    3: 'MEDIUM',
    4: 'LOW',
}


class EveParser:
    """
    Parser EVE JSON Suricata yang beroperasi secara real-time (tail mode).

    Usage:
        mgr    = AlertManager()
        parser = EveParser(alert_manager=mgr)
        parser.start()
        ...
        parser.stop()
    """

    def __init__(
        self,
        alert_manager: AlertManager,
        eve_path: str          = SURICATA_EVE_PATH,
        poll_interval: float   = EVE_POLL_INTERVAL,
    ) -> None:
        self.alert_manager = alert_manager
        self.eve_path      = eve_path
        self.poll_interval = poll_interval

        self._stop_event  = threading.Event()
        self._thread: threading.Thread | None = None

        self._total_events_read   = 0
        self._total_alerts_parsed = 0
        self._total_alerts_sent   = 0

    # ─── Internal: Parse Satu Baris EVE ──────────────────────────────────────
    def _parse_line(self, line: str) -> Alert | None:
        """
        Mengurai satu baris EVE JSON menjadi objek Alert.

        Returns:
            Alert jika baris adalah event type 'alert', None jika bukan.
        """
        line = line.strip()
        if not line:
            return None

        try:
            evt = json.loads(line)
        except json.JSONDecodeError as exc:
            logger.debug("[EveParser] Baris JSON tidak valid: %s | %.60s", exc, line)
            return None

        self._total_events_read += 1

        # Filter hanya event alert
        if evt.get('event_type') != 'alert':
            return None

        self._total_alerts_parsed += 1

        # ── Ekstrak field ──────────────────────────────────────────────────────
        alert_detail = evt.get('alert', {})
        signature    = alert_detail.get('signature', 'Unknown Suricata Alert')
        classtype    = alert_detail.get('category', 'bad-unknown')
        suri_sev_int = alert_detail.get('severity', 3)          # int 1–4
        sid          = alert_detail.get('signature_id', 0)
        rev          = alert_detail.get('rev', 1)

        src_ip   = evt.get('src_ip',  '0.0.0.0')
        dest_ip  = evt.get('dest_ip', '0.0.0.0')
        src_port = evt.get('src_port')
        dst_port = evt.get('dest_port')
        proto    = evt.get('proto', 'UNKNOWN')

        # Parse timestamp EVE (format: "2024-01-15T10:30:45.123456+0700")
        ts_str = evt.get('timestamp', '')
        try:
            # Normalisasi offset format +0700 → +07:00 untuk fromisoformat
            if ts_str and len(ts_str) > 5 and ts_str[-5] in ('+', '-') and ':' not in ts_str[-5:]:
                ts_str = ts_str[:-2] + ':' + ts_str[-2:]
            ts = datetime.fromisoformat(ts_str) if ts_str else datetime.now(timezone.utc).replace(tzinfo=None)
            # Selalu normalisasi ke UTC naive — konsisten dengan seluruh pipeline.
            # (eve.json menulis offset lokal, mis. +0700; kolom DB & API memakai UTC.)
            if ts.tzinfo is not None:
                ts = ts.astimezone(timezone.utc).replace(tzinfo=None)
        except ValueError:
            ts = datetime.now(timezone.utc).replace(tzinfo=None)

        # Severity: gabungkan classtype-based + Suricata severity int
        classtype_sev = map_severity(classtype)
        suri_sev_str  = SURICATA_SEVERITY_MAP.get(suri_sev_int, 'MEDIUM')

        # Ambil yang lebih tinggi antara keduanya
        SEV_RANK = {'LOW': 0, 'MEDIUM': 1, 'HIGH': 2, 'CRITICAL': 3}
        final_sev = (
            classtype_sev
            if SEV_RANK.get(classtype_sev, 0) >= SEV_RANK.get(suri_sev_str, 0)
            else suri_sev_str
        )

        # Susun deskripsi
        port_info = ''
        if src_port and dst_port:
            port_info = f" | port {src_port}→{dst_port}"
        description = (
            f"[Suricata SID:{sid} rev:{rev}] {signature} | "
            f"proto={proto}{port_info} | classtype={classtype}"
        )

        return Alert(
            source_ip=src_ip,
            target_ip=dest_ip,
            attack_type=self._normalize_attack_type(signature, classtype),
            severity=final_sev,
            confidence=1.0,   # Suricata rule match → confidence penuh
            description=description,
            timestamp=ts,
            source='suricata',
        )

    # ─── Internal: Normalisasi Nama Serangan ─────────────────────────────────
    @staticmethod
    def _normalize_attack_type(signature: str, classtype: str) -> str:
        """
        Mengkonversi signature Suricata menjadi nama attack_type yang konsisten.
        Contoh: "UNG-ALERT: Possible TCP Port Scan..." → "PORT_SCAN"
        """
        sig_upper = signature.upper()
        ct_upper  = classtype.upper().replace('-', '_')

        if 'PORT SCAN' in sig_upper or 'RECON' in sig_upper:
            return 'PORT_SCAN'
        elif 'SYN FLOOD' in sig_upper:
            return 'SYN_FLOOD'
        elif 'ICMP' in sig_upper and ('FLOOD' in sig_upper or 'PING' in sig_upper):
            return 'ICMP_FLOOD'
        elif 'MQTT' in sig_upper and 'UNAUTHORIZED' in sig_upper:
            return 'UNAUTHORIZED_MQTT'
        elif 'MQTT' in sig_upper:
            return 'MQTT_ANOMALY'
        elif 'DENIAL' in ct_upper or 'DOS' in ct_upper:
            return 'DOS_ATTACK'
        elif 'ADMIN' in ct_upper or 'ATTEMPTED_ADMIN' in ct_upper:
            return 'PRIVILEGE_ESCALATION'
        elif 'TROJAN' in ct_upper:
            return 'MALWARE_ACTIVITY'
        else:
            # Fallback: pakai classtype dinormalisasi
            return ct_upper if ct_upper else 'UNKNOWN_IDS_ALERT'

    # ─── Internal: Loop Tail ─────────────────────────────────────────────────
    def _tail_loop(self) -> None:
        """
        Membaca EVE JSON secara berkelanjutan seperti 'tail -f'.

        Strategi:
        - Jika file belum ada, tunggu sampai Suricata membuat file tersebut.
        - Buka file, seek ke EOF (skip log lama saat pertama kali).
        - Loop: baca baris baru, proses, tidur EVE_POLL_INTERVAL detik.
        - Jika file di-rotate (size < posisi terakhir), reopen dari awal.
        """
        logger.info("[EveParser] Memantau: %s", self.eve_path)

        # Tunggu sampai file EVE ada
        while not self._stop_event.is_set():
            if os.path.isfile(self.eve_path):
                break
            logger.warning(
                "[EveParser] File EVE belum ada: %s — coba lagi dalam 10s...",
                self.eve_path,
            )
            self._stop_event.wait(timeout=10)

        if self._stop_event.is_set():
            return

        fh = open(self.eve_path, 'r', encoding='utf-8', errors='replace')
        # Seek ke akhir file — abaikan log lama sebelum collector berjalan
        fh.seek(0, 2)
        last_pos = fh.tell()
        pending = ''   # buffer baris parsial (belum diakhiri newline)

        logger.info("[EveParser] Seek ke EOF (pos=%d). Menunggu alert baru...", last_pos)

        while not self._stop_event.is_set():
            # Deteksi log rotation: file diganti (inode/size mengecil)
            try:
                current_size = os.path.getsize(self.eve_path)
            except OSError:
                current_size = 0

            if current_size < last_pos:
                logger.info("[EveParser] Log rotation terdeteksi. Reopen file...")
                try:
                    fh.close()
                except Exception:  # noqa: BLE001
                    pass
                fh = open(self.eve_path, 'r', encoding='utf-8', errors='replace')
                last_pos = 0
                pending = ''   # file baru → baris parsial lama tidak relevan

            # Baca semua baris baru sejak posisi terakhir
            fh.seek(last_pos)
            raw = fh.read()
            last_pos = fh.tell()

            if raw:
                # Gabungkan dengan sisa baris parsial dari iterasi sebelumnya
                lines = (pending + raw).splitlines(keepends=True)
                # Baris terakhir tanpa '\n' = masih ditulis Suricata → tunda dulu
                if lines and not lines[-1].endswith('\n'):
                    pending = lines.pop()
                else:
                    pending = ''

                for line in lines:
                    alert = self._parse_line(line)
                    if alert:
                        inserted = self.alert_manager.process(alert)
                        if inserted:
                            self._total_alerts_sent += 1

                if lines:
                    logger.debug(
                        "[EveParser] Dibaca: %d baris | Alert dikirim: %d",
                        len(lines), self._total_alerts_sent,
                    )

            self._stop_event.wait(timeout=self.poll_interval)

        fh.close()
        logger.info("[EveParser] Tail loop berhenti.")

    # ─── Public API ──────────────────────────────────────────────────────────
    def start(self) -> None:
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._tail_loop,
            name='eve-parser',
            daemon=True,
        )
        self._thread.start()
        logger.info("[EveParser] Thread aktif.")

    def stop(self) -> None:
        logger.info("[EveParser] Menghentikan...")
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10)
        logger.info(
            "[EveParser] Berhenti. Events: %d | Alerts parsed: %d | Alerts sent: %d",
            self._total_events_read,
            self._total_alerts_parsed,
            self._total_alerts_sent,
        )

    @property
    def stats(self) -> dict[str, int]:
        return {
            'total_events_read':   self._total_events_read,
            'total_alerts_parsed': self._total_alerts_parsed,
            'total_alerts_sent':   self._total_alerts_sent,
        }
