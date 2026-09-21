"""
main.py — Unified Network Guard: Detection
===========================================
Entry point modul Detection.

Menjalankan tiga komponen secara bersamaan:
  1. AlertManager  — singleton pengelola alert (dipakai bersama)
  2. RuleEngine    — deteksi threshold berbasis polling DB
  3. EveParser     — tail Suricata EVE JSON secara real-time

Cara menjalankan:
    python -m detection.main

    # Hanya rule engine (tanpa Suricata)
    python -m detection.main --no-eve

    # Hanya EVE parser (Suricata sudah jalan, tidak perlu DB traffic)
    python -m detection.main --no-rules

Catatan:
  - Modul ini TIDAK butuh sudo (tidak ada raw socket).
  - Suricata sendiri yang butuh sudo untuk sniff; hasil alertnya
    dibaca dari file /var/log/suricata/eve.json.
"""

import argparse
import logging
import signal
import sys
import threading

from detection.config import LOG_LEVEL
from detection.alert_manager import AlertManager
from detection.rule_engine import RuleEngine
from detection.eve_parser import EveParser

# ─── Setup Logging ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger('detection.main')


# ─── Argumen CLI ─────────────────────────────────────────────────────────────
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Unified Network Guard — Detection Engine',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        '--no-rules',
        action='store_true',
        help='Nonaktifkan Rule Engine (tidak polling DB traffic).',
    )
    parser.add_argument(
        '--no-eve',
        action='store_true',
        help='Nonaktifkan EVE Parser (tidak baca log Suricata).',
    )
    return parser.parse_args()


# ─── Main ─────────────────────────────────────────────────────────────────────
def main() -> None:
    args = parse_args()

    logger.info("=" * 60)
    logger.info("  Unified Network Guard — Detection Engine")
    logger.info("=" * 60)

    # 1. Inisialisasi AlertManager (dipakai bersama oleh semua komponen)
    alert_manager = AlertManager()
    logger.info("[Main] AlertManager siap (suppress=%ds).", alert_manager.suppress_seconds)

    rule_engine: RuleEngine | None = None
    eve_parser:  EveParser  | None = None

    # 2. Inisialisasi komponen sesuai argumen
    if not args.no_rules:
        rule_engine = RuleEngine(alert_manager=alert_manager)

    if not args.no_eve:
        eve_parser = EveParser(alert_manager=alert_manager)

    if not rule_engine and not eve_parser:
        logger.error("[Main] Tidak ada komponen aktif. Gunakan --help.")
        sys.exit(1)

    # 3. Graceful shutdown
    def shutdown(signum, frame) -> None:
        sig_name = signal.Signals(signum).name
        logger.info("\n[Main] Sinyal %s diterima. Menutup semua komponen...", sig_name)
        if rule_engine:
            rule_engine.stop()
        if eve_parser:
            eve_parser.stop()
        # Cetak statistik akhir
        logger.info("[Main] ── Statistik Akhir ──────────────────────────")
        logger.info("[Main] AlertManager : %s", alert_manager.stats)
        if rule_engine:
            logger.info("[Main] RuleEngine   : %s", rule_engine.stats)
        if eve_parser:
            logger.info("[Main] EveParser    : %s", eve_parser.stats)
        logger.info("[Main] Detection engine berhenti.")
        sys.exit(0)

    signal.signal(signal.SIGINT,  shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # 4. Jalankan komponen
    if rule_engine:
        rule_engine.start()

    if eve_parser:
        eve_parser.start()

    # 5. Statistik periodik setiap 60 detik di main thread
    logger.info("[Main] Semua komponen aktif. Tekan Ctrl+C untuk berhenti.")
    while True:
        # Blokir selama 60 detik, cetak statistik
        try:
            shutdown_event = threading.Event()
            shutdown_event.wait(timeout=60)
        except KeyboardInterrupt:
            shutdown(signal.SIGINT, None)

        # Cetak statistik runtime
        logger.info(
            "[Main] ── Statistik Runtime ── "
            "AlertMgr=%s | RuleEngine=%s | EveParser=%s",
            alert_manager.stats,
            rule_engine.stats if rule_engine else 'disabled',
            eve_parser.stats  if eve_parser  else 'disabled',
        )


if __name__ == '__main__':
    main()
