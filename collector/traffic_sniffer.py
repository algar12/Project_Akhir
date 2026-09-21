"""
traffic_sniffer.py — Unified Network Guard: Collector
======================================================
Menangkap paket jaringan secara real-time menggunakan Scapy,
mengekstrak fitur penting, lalu menyimpannya ke database secara
batch untuk efisiensi I/O.

Fitur yang diekstrak per paket:
  - timestamp, source_ip, destination_ip
  - protocol (TCP / UDP / ICMP / OTHER)
  - source_port, destination_port
  - packet_count (selalu 1 per paket)
  - bytes (panjang paket dalam byte)

Mekanisme batch-insert:
  Paket dikumpulkan ke dalam buffer (list) dahulu, baru di-flush ke
  PostgreSQL setiap TRAFFIC_BATCH_SIZE paket atau TRAFFIC_FLUSH_INTERVAL
  detik, mana yang lebih dulu tercapai — agar tidak terlalu sering I/O.
"""

import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any

from scapy.all import sniff, IP, TCP, UDP, ICMP, Packet

from collector.config import (
    CAPTURE_INTERFACE,
    CAPTURE_BPF_FILTER,
    TRAFFIC_BATCH_SIZE,
    TRAFFIC_FLUSH_INTERVAL,
)
from collector.db import insert_traffic_batch

logger = logging.getLogger(__name__)


class TrafficSniffer:
    """
    Pengumpul paket jaringan berbasis Scapy.

    Usage:
        sniffer = TrafficSniffer()
        sniffer.start()
        ...
        sniffer.stop()
    """

    def __init__(
        self,
        interface: str = CAPTURE_INTERFACE,
        bpf_filter: str = CAPTURE_BPF_FILTER,
        batch_size: int = TRAFFIC_BATCH_SIZE,
        flush_interval: int = TRAFFIC_FLUSH_INTERVAL,
    ) -> None:
        self.interface     = interface
        self.bpf_filter    = bpf_filter
        self.batch_size    = batch_size
        self.flush_interval = flush_interval

        self._buffer: list[dict[str, Any]] = []
        self._lock          = threading.Lock()
        self._stop_event    = threading.Event()
        self._flush_thread: threading.Thread | None = None
        self._sniff_thread: threading.Thread | None = None

        # Statistik runtime
        self._total_captured = 0
        self._total_saved    = 0

    # ─── Internal: Ekstraksi Fitur Paket ─────────────────────────────────────
    def _extract_features(self, pkt: Packet) -> dict[str, Any] | None:
        """
        Mengekstrak field penting dari paket Scapy.

        Mengembalikan None jika paket bukan IP (misal ARP murni, dll.)
        agar record tidak terkontaminasi data non-relevan.
        """
        if not pkt.haslayer(IP):
            return None

        ip_layer  = pkt[IP]
        proto_num = ip_layer.proto

        # Nilai default (dipakai untuk branch yang tidak meng-set field tertentu)
        is_syn = False
        icmp_type = None

        # Tentukan protokol dan port
        if proto_num == 6 and pkt.haslayer(TCP):     # TCP
            tcp = pkt[TCP]
            protocol = 'TCP'
            sport = tcp.sport
            dport = tcp.dport
            # Flag SYN murni (SYN set, ACK tidak) — penanda percobaan koneksi baru.
            # Dipakai RuleEngine untuk deteksi SYN flood yang AKURAT (bukan volume TCP).
            flags = int(tcp.flags)
            is_syn = bool(flags & 0x02) and not bool(flags & 0x10)
        elif proto_num == 17 and pkt.haslayer(UDP):  # UDP
            udp = pkt[UDP]
            protocol = 'UDP'
            sport = udp.sport
            dport = udp.dport
        elif proto_num == 1 and pkt.haslayer(ICMP):  # ICMP
            protocol = 'ICMP'
            sport = None
            dport = None
            # Tipe ICMP disimpan agar rule ICMP_FLOOD hanya menghitung
            # echo request (type 8), bukan echo reply (type 0) dari korban.
            icmp_type = int(pkt[ICMP].type)
        else:
            protocol = f'OTHER({proto_num})'
            sport = None
            dport = None

        return {
            # Timestamp selalu UTC (naive) agar konsisten di seluruh pipeline.
            'timestamp':       datetime.fromtimestamp(
                float(pkt.time), tz=timezone.utc).replace(tzinfo=None),
            'source_ip':       ip_layer.src,
            'destination_ip':  ip_layer.dst,
            'protocol':        protocol,
            'source_port':     sport,
            'destination_port': dport,
            'packet_count':    1,
            'bytes':           len(pkt),
            'is_syn':          is_syn,
            'icmp_type':       icmp_type,
        }

    # ─── Internal: Callback Scapy ─────────────────────────────────────────────
    def _packet_callback(self, pkt: Packet) -> None:
        """
        Dipanggil oleh Scapy untuk setiap paket yang tertangkap.
        Fitur diekstrak lalu dimasukkan ke buffer thread-safe.
        """
        record = self._extract_features(pkt)
        if record is None:
            return

        batch: list[dict[str, Any]] | None = None
        with self._lock:
            self._total_captured += 1
            self._buffer.append(record)

            # Flush segera jika buffer penuh (ambil batch, I/O dilakukan di luar lock)
            if len(self._buffer) >= self.batch_size:
                batch = self._buffer.copy()
                self._buffer.clear()

        # I/O DB dilakukan di LUAR lock agar callback Scapy tidak tersumbat
        if batch:
            self._flush_batch(batch)

        # Log setiap 100 paket agar terminal tidak banjir
        if self._total_captured % 100 == 0:
            logger.info(
                "[Sniffer] Tertangkap: %d pkt | Tersimpan: %d pkt",
                self._total_captured, self._total_saved,
            )

    # ─── Internal: Insert Batch ke DB (tanpa memegang lock) ───────────────────
    def _flush_batch(self, batch: list[dict[str, Any]]) -> None:
        """Insert batch ke database tanpa memegang lock apa pun."""
        try:
            saved = insert_traffic_batch(batch)
        except Exception as exc:  # noqa: BLE001 — jangan biarkan sniffer mati
            logger.error("[Sniffer] Gagal insert batch: %s", exc)
            saved = 0
        with self._lock:
            self._total_saved += saved

    # ─── Internal: Flush Berkala (Timer Thread) ───────────────────────────────
    def _periodic_flush(self) -> None:
        """Thread yang mem-flush buffer setiap TRAFFIC_FLUSH_INTERVAL detik."""
        while not self._stop_event.is_set():
            time.sleep(self.flush_interval)
            with self._lock:
                if not self._buffer:
                    continue
                batch = self._buffer.copy()
                self._buffer.clear()
            self._flush_batch(batch)

    # ─── Internal: Sniff Loop ────────────────────────────────────────────────
    def _sniff_loop(self) -> None:
        """
        Loop sniffing yang berjalan di thread terpisah.
        Menggunakan store=False agar paket tidak di-simpan di RAM oleh Scapy.
        """
        logger.info(
            "[Sniffer] Memulai capture di interface '%s' dengan filter: '%s'",
            self.interface, self.bpf_filter,
        )
        sniff(
            iface=self.interface,
            filter=self.bpf_filter,
            prn=self._packet_callback,
            store=False,
            stop_filter=lambda _: self._stop_event.is_set(),
        )
        logger.info("[Sniffer] Sniff loop berhenti.")

    # ─── Public API ──────────────────────────────────────────────────────────
    def start(self) -> None:
        """Memulai dua thread: sniffer paket dan periodic flush."""
        self._stop_event.clear()

        self._flush_thread = threading.Thread(
            target=self._periodic_flush,
            name='sniffer-flush',
            daemon=True,
        )
        self._flush_thread.start()

        self._sniff_thread = threading.Thread(
            target=self._sniff_loop,
            name='sniffer-capture',
            daemon=True,
        )
        self._sniff_thread.start()

        logger.info("[Sniffer] Pengumpul traffic aktif.")

    def stop(self) -> None:
        """Menghentikan sniffing dan flush sisa buffer."""
        logger.info("[Sniffer] Menghentikan sniffer...")
        self._stop_event.set()

        # Tunggu thread selesai
        if self._sniff_thread and self._sniff_thread.is_alive():
            self._sniff_thread.join(timeout=5)
        if self._flush_thread and self._flush_thread.is_alive():
            self._flush_thread.join(timeout=5)

        # Flush sisa buffer terakhir
        with self._lock:
            self._flush()

        logger.info(
            "[Sniffer] Dihentikan. Total: %d ditangkap, %d disimpan.",
            self._total_captured, self._total_saved,
        )

    @property
    def stats(self) -> dict[str, int]:
        """Mengembalikan statistik runtime sniffer."""
        return {
            'total_captured': self._total_captured,
            'total_saved':    self._total_saved,
            'buffer_size':    len(self._buffer),
        }
