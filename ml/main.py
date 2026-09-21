"""
main.py — Unified Network Guard: ML
=====================================
Entry point modul ML dengan tiga sub-command:

  train    — Latih model Isolation Forest (+ opsional Random Forest)
  predict  — Jalankan prediksi real-time (mode daemon)
  evaluate — Hitung metrik evaluasi berdasarkan skenario pengujian

Cara penggunaan:
  # Training dari CSV (default: ml/datasets/normal.csv)
  python -m ml.main train

  # Training dari DB langsung (24 jam terakhir)
  python -m ml.main train --from-db --hours 24

  # Training IF + RF sekaligus
  python -m ml.main train --rf

  # Prediksi real-time (tanpa integrasi AlertManager)
  python -m ml.main predict

  # Prediksi real-time + kirim alert ke detection module
  python -m ml.main predict --with-alerts

  # Evaluasi dengan file skenario
  python -m ml.main evaluate --scenarios ml/scenarios_example.json

  # Evaluasi + simpan laporan
  python -m ml.main evaluate --scenarios ml/scenarios_example.json --out report.json
"""

import argparse
import json
import logging
import os
import signal
import sys

from ml.config import LOG_LEVEL, DATASET_DIR, MODEL_DIR

# ─── Setup Logging ─────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger('ml.main')


# ─── Sub-command: Train ────────────────────────────────────────────────────
def cmd_train(args: argparse.Namespace) -> None:
    from ml.trainer import run_training

    report = run_training(
        train_rf    = args.rf,
        from_db     = args.from_db,
        hours_back  = args.hours,
        normal_csv  = args.normal_csv or '',
        labeled_csv = args.labeled_csv or '',
    )

    if 'error' in report:
        logger.error("[Main:train] %s", report['error'])
        sys.exit(1)

    logger.info("[Main:train] Training selesai.")
    if args.rf and 'random_forest' in report:
        rf = report['random_forest']
        if not rf.get('skipped'):
            cv = rf.get('cv_metrics', {})
            logger.info(
                "[Main:train] RF CV → accuracy=%.4f | f1=%.4f",
                cv.get('test_accuracy', 0), cv.get('test_f1_weighted', 0),
            )


# ─── Sub-command: Predict ──────────────────────────────────────────────────
def cmd_predict(args: argparse.Namespace) -> None:
    from ml.predictor import AnomalyPredictor

    alert_manager = None
    if args.with_alerts:
        try:
            from detection.alert_manager import AlertManager
            alert_manager = AlertManager()
            logger.info("[Main:predict] AlertManager aktif — alert akan disimpan ke DB.")
        except ImportError:
            logger.warning("[Main:predict] Modul detection tidak tersedia. "
                           "Prediksi jalan tanpa alert.")

    predictor = AnomalyPredictor(alert_manager=alert_manager)
    ok = predictor.start()
    if not ok:
        logger.error("[Main:predict] Gagal memulai predictor. "
                     "Pastikan model sudah dilatih dengan: python -m ml.main train")
        sys.exit(1)

    def shutdown(signum, frame):
        logger.info("\n[Main:predict] Berhenti...")
        predictor.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT,  shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    logger.info("[Main:predict] Prediksi real-time aktif. Tekan Ctrl+C untuk berhenti.")
    signal.pause()


# ─── Sub-command: Evaluate ────────────────────────────────────────────────
def cmd_evaluate(args: argparse.Namespace) -> None:
    from ml.evaluator import evaluate

    if not args.scenarios:
        logger.error("[Main:evaluate] --scenarios diperlukan.")
        sys.exit(1)

    if not os.path.isfile(args.scenarios):
        logger.error("[Main:evaluate] File tidak ditemukan: %s", args.scenarios)
        sys.exit(1)

    with open(args.scenarios, 'r', encoding='utf-8') as f:
        scenarios = json.load(f)

    logger.info("[Main:evaluate] Memuat %d skenario dari %s", len(scenarios), args.scenarios)

    report = evaluate(
        scenarios=scenarios,
        output_path=args.out or None,
    )

    if 'error' in report:
        logger.error("[Main:evaluate] %s", report['error'])
        sys.exit(1)


# ─── Argument Parser ──────────────────────────────────────────────────────
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Unified Network Guard — ML Pipeline',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    sub = parser.add_subparsers(dest='command', required=True)

    # ── train ──────────────────────────────────────────────────────────────
    p_train = sub.add_parser('train', help='Latih model ML')
    p_train.add_argument('--rf', action='store_true',
                         help='Juga latih Random Forest Classifier')
    p_train.add_argument('--from-db', action='store_true',
                         help='Ambil data training dari database (bukan CSV)')
    p_train.add_argument('--hours', type=int, default=24,
                         help='Jika --from-db: ambil N jam terakhir dari DB')
    p_train.add_argument('--normal-csv', type=str, default='',
                         help=f'Path CSV data normal (default: {DATASET_DIR}/normal.csv)')
    p_train.add_argument('--labeled-csv', type=str, default='',
                         help=f'Path CSV berlabel untuk RF (default: {DATASET_DIR}/labeled.csv)')

    # ── predict ────────────────────────────────────────────────────────────
    p_pred = sub.add_parser('predict', help='Jalankan prediksi anomali real-time')
    p_pred.add_argument('--with-alerts', action='store_true',
                        help='Kirim anomali ke AlertManager (simpan ke tabel alerts)')

    # ── evaluate ───────────────────────────────────────────────────────────
    p_eval = sub.add_parser('evaluate', help='Evaluasi performa deteksi')
    p_eval.add_argument('--scenarios', type=str, required=True,
                        help='Path file JSON skenario pengujian')
    p_eval.add_argument('--out', type=str, default='',
                        help='Path untuk menyimpan laporan JSON evaluasi')

    return parser


# ─── Main ─────────────────────────────────────────────────────────────────
def main() -> None:
    # Pastikan direktori penting ada
    os.makedirs(MODEL_DIR,  exist_ok=True)
    os.makedirs(DATASET_DIR, exist_ok=True)

    parser = build_parser()
    args   = parser.parse_args()

    logger.info("=" * 60)
    logger.info("  Unified Network Guard — ML Module [%s]", args.command.upper())
    logger.info("=" * 60)

    if args.command == 'train':
        cmd_train(args)
    elif args.command == 'predict':
        cmd_predict(args)
    elif args.command == 'evaluate':
        cmd_evaluate(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
