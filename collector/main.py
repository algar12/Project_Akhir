"""
main.py — Unified Network Guard: Collector
===========================================
Entry point utama modul Collector.
Menjalankan dua komponen secara bersamaan:
  1. TrafficSniffer  — capture & simpan paket jaringan via Scapy
  2. MQTTSubscriber  — subscribe & simpan telemetri ESP32 via MQTT

Cara menjalankan:
    sudo venv/bin/python -m collector.main

  (sudo diperlukan oleh Scapy untuk raw socket capture)

Untuk menjalankan HANYA subscriber MQTT (tanpa capture traffic, tanpa sudo):
    python -m collector.main --no-sniffer
"""

import argparse
import logging
import signal
import sys
import threading

from collector.config import LOG_LEVEL
from collector.db import ensure_schema
from collector.traffic_sniffer import TrafficSniffer
from collector.mqtt_subscriber import MQTTSubscriber

# ─── Setup Logging ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger('collector.main')


# ─── Argumen CLI ─────────────────────────────────────────────────────────────
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Unified Network Guard — Data Collector',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        '--no-sniffer',
        action='store_true',
        help='Jalankan hanya MQTT subscriber, tanpa traffic sniffer (tidak butuh sudo).',
    )
    parser.add_argument(
        '--no-mqtt',
        action='store_true',
        help='Jalankan hanya traffic sniffer, tanpa MQTT subscriber.',
    )
    return parser.parse_args()


# ─── Main ─────────────────────────────────────────────────────────────────────
def main() -> None:
    args = parse_args()

    logger.info("=" * 60)
    logger.info("  Unified Network Guard — Collector Module")
    logger.info("=" * 60)

    # 1. Pastikan skema database sudah lengkap
    try:
        ensure_schema()
    except Exception as exc:
        logger.critical("[Main] Gagal konek database: %s", exc)
        logger.critical("[Main] Pastikan PostgreSQL berjalan dan .env sudah dikonfigurasi.")
        sys.exit(1)

    sniffer: TrafficSniffer | None = None
    subscriber: MQTTSubscriber | None = None

    # 2. Inisialisasi komponen sesuai argumen
    if not args.no_sniffer:
        sniffer = TrafficSniffer()

    if not args.no_mqtt:
        subscriber = MQTTSubscriber()

    # 3. Graceful shutdown via SIGINT / SIGTERM
    def shutdown(signum, frame) -> None:
        logger.info("\n[Main] Sinyal berhenti diterima (%s). Menutup...", signal.Signals(signum).name)
        if sniffer:
            sniffer.stop()
        if subscriber:
            subscriber.stop()
        logger.info("[Main] Collector berhenti.")
        sys.exit(0)

    signal.signal(signal.SIGINT,  shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # 4. Jalankan traffic sniffer di thread background
    if sniffer:
        sniffer.start()

    # 5. Jalankan MQTT subscriber
    if subscriber:
        if sniffer:
            # Sniffer sudah jalan di thread-nya sendiri;
            # jalankan MQTT subscriber di thread terpisah agar main thread bisa menunggu
            mqtt_thread = threading.Thread(
                target=lambda: subscriber.start(blocking=True),
                name='mqtt-subscriber',
                daemon=True,
            )
            mqtt_thread.start()
            mqtt_thread.join()  # Blokir di sini sampai MQTT selesai / Ctrl+C
        else:
            # Hanya MQTT, jalankan blocking di main thread
            subscriber.start(blocking=True)
    elif sniffer:
        # Hanya sniffer, buat main thread menunggu
        logger.info("[Main] Hanya traffic sniffer aktif. Tekan Ctrl+C untuk berhenti.")
        try:
            signal.pause()
        except AttributeError:
            # signal.pause() tidak tersedia di Windows
            import time
            while True:
                time.sleep(1)
    else:
        logger.error("[Main] Tidak ada komponen aktif. Gunakan --help untuk info lebih lanjut.")
        sys.exit(1)


if __name__ == '__main__':
    main()
