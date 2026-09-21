"""
evaluator.py — Unified Network Guard: ML
==========================================
Mengevaluasi performa sistem deteksi menggunakan metrik standar penelitian:
  - Accuracy, Precision, Recall, F1-Score
  - False Positive Rate (FPR)
  - Detection Latency (rata-rata, median, persentil 95)
  - Confusion Matrix

Sumber data evaluasi:
  1. Tabel ml_predictions — hasil prediksi Isolation Forest
  2. Tabel alerts         — semua alert (dari rule engine, Suricata, ML)

Ground Truth:
  Evaluasi membutuhkan ground truth (label aktual) yang didefinisikan
  berdasarkan waktu skenario pengujian. Format:
    [{
        'start': datetime,
        'end': datetime,
        'label': 'port_scan' | 'syn_flood' | 'normal' | ...
        'source_ip': '...' (opsional)
    }]

Cara menjalankan:
  python -m ml.main evaluate --scenarios scenarios.json

Format scenarios.json:
  [
    {"start": "2024-01-15T09:00:00", "end": "2024-01-15T09:05:00",
     "label": "normal"},
    {"start": "2024-01-15T09:05:00", "end": "2024-01-15T09:10:00",
     "label": "port_scan", "source_ip": "192.168.20.10"}
  ]
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool

from ml.config import DATABASE_URL, RF_CLASSES

logger = logging.getLogger(__name__)

# ─── DB Engine ────────────────────────────────────────────────────────────────
_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(
            DATABASE_URL,
            poolclass=QueuePool,
            pool_size=2,
            max_overflow=3,
            pool_pre_ping=True,
            echo=False,
        )
    return _engine


# ─── Ambil Predictions dari DB ────────────────────────────────────────────────
def _load_predictions(since: datetime, until: datetime) -> pd.DataFrame:
    sql = text("""
        SELECT timestamp, source_ip, time_bucket,
               if_score, is_anomaly, attack_class, confidence
        FROM ml_predictions
        WHERE timestamp >= :since
          AND timestamp <  :until
        ORDER BY timestamp ASC
    """)
    try:
        engine = _get_engine()
        with engine.connect() as conn:
            df = pd.read_sql(sql, conn, params={'since': since, 'until': until})
        return df
    except Exception as exc:
        logger.error("[Evaluator] Gagal load predictions: %s", exc)
        return pd.DataFrame()


# ─── Ambil Alerts dari DB ─────────────────────────────────────────────────────
def _load_alerts(since: datetime, until: datetime) -> pd.DataFrame:
    sql = text("""
        SELECT timestamp, source_ip, target_ip,
               attack_type, severity, confidence
        FROM alerts
        WHERE timestamp >= :since
          AND timestamp <  :until
        ORDER BY timestamp ASC
    """)
    try:
        engine = _get_engine()
        with engine.connect() as conn:
            df = pd.read_sql(sql, conn, params={'since': since, 'until': until})
        return df
    except Exception as exc:
        logger.error("[Evaluator] Gagal load alerts: %s", exc)
        return pd.DataFrame()


# ─── Anotasi Ground Truth ─────────────────────────────────────────────────────
def _annotate_ground_truth(
    df: pd.DataFrame,
    scenarios: list[dict],
    ts_col: str = 'timestamp',
) -> pd.DataFrame:
    """
    Tambahkan kolom 'ground_truth' ke DataFrame berdasarkan skenario pengujian.

    Setiap baris yang jatuh dalam rentang waktu skenario mendapat label
    sesuai skenario. Baris di luar semua skenario mendapat label 'normal'.

    Args:
        df        : DataFrame dengan kolom timestamp
        scenarios : List dict {start, end, label, source_ip (opsional)}
        ts_col    : Nama kolom timestamp

    Returns:
        DataFrame dengan kolom tambahan 'ground_truth'
    """
    df = df.copy()
    df['ground_truth'] = 'normal'   # default

    for sc in scenarios:
        start  = pd.Timestamp(sc['start'])
        end    = pd.Timestamp(sc['end'])
        label  = sc.get('label', 'unknown')
        src_ip = sc.get('source_ip')

        mask = (df[ts_col] >= start) & (df[ts_col] < end)
        if src_ip:
            if 'source_ip' in df.columns:
                mask &= (df['source_ip'] == src_ip)

        df.loc[mask, 'ground_truth'] = label

    return df


# ─── Hitung Confusion Matrix per Kelas ───────────────────────────────────────
def _per_class_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    pos_labels: list[str],
) -> dict:
    """
    Hitung TP, TN, FP, FN, dan metrik turunannya.
    pos_labels: semua label yang dianggap 'positif' (bukan 'normal').
    """
    y_true_bin = np.array([0 if t == 'normal' else 1 for t in y_true])
    y_pred_bin = np.array([0 if p == 'normal' else 1 for p in y_pred])

    TP = int(((y_true_bin == 1) & (y_pred_bin == 1)).sum())
    TN = int(((y_true_bin == 0) & (y_pred_bin == 0)).sum())
    FP = int(((y_true_bin == 0) & (y_pred_bin == 1)).sum())
    FN = int(((y_true_bin == 1) & (y_pred_bin == 0)).sum())

    total     = TP + TN + FP + FN
    accuracy  = (TP + TN) / total if total > 0 else 0
    precision = TP / (TP + FP)    if (TP + FP) > 0 else 0
    recall    = TP / (TP + FN)    if (TP + FN) > 0 else 0
    f1        = (2 * precision * recall / (precision + recall)
                 if (precision + recall) > 0 else 0)
    fpr       = FP / (FP + TN)    if (FP + TN) > 0 else 0

    return {
        'TP': TP, 'TN': TN, 'FP': FP, 'FN': FN,
        'accuracy':  round(accuracy,  4),
        'precision': round(precision, 4),
        'recall':    round(recall,    4),
        'f1_score':  round(f1,        4),
        'fpr':       round(fpr,       4),
    }


# ─── Hitung Detection Latency ─────────────────────────────────────────────────
def _calc_detection_latency(
    df_alerts: pd.DataFrame,
    scenarios: list[dict],
) -> dict:
    """
    Menghitung detection latency: selisih antara waktu mulai serangan
    dan waktu alert pertama yang sesuai muncul.

    Returns:
        dict berisi rata-rata, median, p95 latency dalam detik.
    """
    latencies = []
    for sc in scenarios:
        if sc.get('label', 'normal') == 'normal':
            continue

        attack_start = pd.Timestamp(sc['start'])
        attack_label = sc.get('label', '').upper()

        # Cari alert pertama setelah attack_start yang relevan
        relevant = df_alerts[
            (df_alerts['timestamp'] >= attack_start) &
            (df_alerts['timestamp'] < pd.Timestamp(sc['end'])) &
            df_alerts['attack_type'].str.contains(
                attack_label.split('_')[0], case=False, na=False
            )
        ]

        if not relevant.empty:
            first_alert = relevant['timestamp'].min()
            lat = (first_alert - attack_start).total_seconds()
            latencies.append(lat)
            logger.debug(
                "[Evaluator] Latency skenario '%s': %.2fs", attack_label, lat
            )

    if not latencies:
        return {
            'note': 'Tidak ada alert yang berkorelasi dengan skenario serangan.',
            'latencies_sec': [],
        }

    arr = np.array(latencies)
    return {
        'n_detected':     len(latencies),
        'mean_sec':       round(float(arr.mean()), 3),
        'median_sec':     round(float(np.median(arr)), 3),
        'p95_sec':        round(float(np.percentile(arr, 95)), 3),
        'min_sec':        round(float(arr.min()), 3),
        'max_sec':        round(float(arr.max()), 3),
        'latencies_sec':  [round(float(l), 3) for l in latencies],
    }


# ─── Fungsi Evaluasi Utama ────────────────────────────────────────────────────
def evaluate(
    scenarios: list[dict],
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    output_path: Optional[str] = None,
) -> dict:
    """
    Evaluasi lengkap sistem deteksi ML.

    Args:
        scenarios  : List skenario pengujian (lihat format di header file)
        since      : Mulai evaluasi (default: 1 jam sebelum skenario pertama)
        until      : Akhir evaluasi (default: 1 jam setelah skenario terakhir)
        output_path: Jika diisi, simpan laporan JSON ke path ini

    Returns:
        dict laporan lengkap evaluasi.
    """
    logger.info("[Evaluator] Memulai evaluasi...")

    # Tentukan rentang waktu otomatis dari skenario
    if since is None:
        sc_starts = [datetime.fromisoformat(sc['start']) for sc in scenarios]
        since = min(sc_starts) - timedelta(minutes=10)

    if until is None:
        sc_ends = [datetime.fromisoformat(sc['end']) for sc in scenarios]
        until = max(sc_ends) + timedelta(minutes=10)

    logger.info("[Evaluator] Rentang: %s s/d %s", since, until)

    # ── Load data ─────────────────────────────────────────────────────────────
    df_pred   = _load_predictions(since, until)
    df_alerts = _load_alerts(since, until)

    if df_pred.empty:
        logger.warning("[Evaluator] Tidak ada data ml_predictions. "
                       "Pastikan predictor sudah berjalan saat skenario.")
        return {'error': 'Tidak ada data prediksi di database.'}

    logger.info(
        "[Evaluator] Data: %d prediksi | %d alerts",
        len(df_pred), len(df_alerts),
    )

    # ── Anotasi ground truth ──────────────────────────────────────────────────
    df_pred = _annotate_ground_truth(df_pred, scenarios, ts_col='timestamp')

    # ── Buat kolom predicted label ────────────────────────────────────────────
    # Jika is_anomaly=True → pakai attack_class, jika tidak → 'normal'
    df_pred['predicted'] = df_pred.apply(
        lambda r: r['attack_class'] if r['is_anomaly'] else 'normal',
        axis=1,
    )

    # ── Metrik biner (normal vs anomali) ─────────────────────────────────────
    non_normal_labels = [l for l in df_pred['ground_truth'].unique() if l != 'normal']
    binary_metrics = _per_class_metrics(
        y_true=df_pred['ground_truth'].values,
        y_pred=df_pred['predicted'].values,
        pos_labels=non_normal_labels,
    )

    # ── Laporan per kelas (multi-class) ──────────────────────────────────────
    all_labels = sorted(df_pred['ground_truth'].unique().tolist())
    try:
        multi_report = classification_report(
            df_pred['ground_truth'],
            df_pred['predicted'],
            labels=all_labels,
            output_dict=True,
            zero_division=0,
        )
    except Exception:
        multi_report = {}

    # ── Detection Latency ─────────────────────────────────────────────────────
    if not df_alerts.empty:
        df_alerts['timestamp'] = pd.to_datetime(df_alerts['timestamp'])
        latency_report = _calc_detection_latency(df_alerts, scenarios)
    else:
        latency_report = {'note': 'Tidak ada alert di database.'}

    # ── Distribusi Skor IF ────────────────────────────────────────────────────
    score_stats = {
        'mean':   round(float(df_pred['if_score'].mean()), 4),
        'std':    round(float(df_pred['if_score'].std()),  4),
        'min':    round(float(df_pred['if_score'].min()),  4),
        'max':    round(float(df_pred['if_score'].max()),  4),
        'p5':     round(float(df_pred['if_score'].quantile(0.05)), 4),
        'median': round(float(df_pred['if_score'].median()),       4),
    }

    # ── Susun laporan lengkap ─────────────────────────────────────────────────
    report = {
        'evaluated_at':     datetime.now().isoformat(),
        'period':           {'since': str(since), 'until': str(until)},
        'n_predictions':    len(df_pred),
        'n_alerts':         len(df_alerts),
        'n_scenarios':      len(scenarios),
        'binary_metrics':   binary_metrics,
        'multi_class_report': multi_report,
        'detection_latency': latency_report,
        'if_score_stats':   score_stats,
        'label_distribution': df_pred['ground_truth'].value_counts().to_dict(),
        'prediction_distribution': df_pred['predicted'].value_counts().to_dict(),
    }

    # ── Cetak ringkasan di terminal ───────────────────────────────────────────
    _print_summary(report)

    # ── Simpan laporan ────────────────────────────────────────────────────────
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
        logger.info("[Evaluator] Laporan disimpan → %s", output_path)

    return report


def _print_summary(report: dict) -> None:
    """Cetak ringkasan metrik evaluasi ke terminal."""
    bm = report.get('binary_metrics', {})
    lat = report.get('detection_latency', {})

    print("\n" + "=" * 60)
    print("  UNIFIED NETWORK GUARD — LAPORAN EVALUASI")
    print("=" * 60)
    print(f"  Prediksi dianalisis : {report.get('n_predictions', 0):,}")
    print(f"  Alert dievaluasi    : {report.get('n_alerts', 0):,}")
    print()
    print("  ─── Metrik Deteksi Biner (Anomali vs Normal) ───")
    print(f"  Accuracy    : {bm.get('accuracy',  0):.4f}  ({bm.get('accuracy', 0)*100:.2f}%)")
    print(f"  Precision   : {bm.get('precision', 0):.4f}  ({bm.get('precision',0)*100:.2f}%)")
    print(f"  Recall      : {bm.get('recall',    0):.4f}  ({bm.get('recall',   0)*100:.2f}%)")
    print(f"  F1-Score    : {bm.get('f1_score',  0):.4f}  ({bm.get('f1_score', 0)*100:.2f}%)")
    print(f"  FPR         : {bm.get('fpr',       0):.4f}  ({bm.get('fpr',      0)*100:.2f}%)")
    print()
    print(f"  TP={bm.get('TP',0)} | TN={bm.get('TN',0)} | "
          f"FP={bm.get('FP',0)} | FN={bm.get('FN',0)}")
    print()
    print("  ─── Detection Latency ──────────────────────────")
    if 'mean_sec' in lat:
        print(f"  Mean   : {lat.get('mean_sec', '-'):.3f} detik")
        print(f"  Median : {lat.get('median_sec', '-'):.3f} detik")
        print(f"  P95    : {lat.get('p95_sec', '-'):.3f} detik")
    else:
        print(f"  {lat.get('note', '-')}")
    print("=" * 60 + "\n")
