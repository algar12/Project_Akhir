"""
trainer.py — Unified Network Guard: ML
========================================
Melatih dua model Machine Learning:

  Model 1 — Isolation Forest (Unsupervised Anomaly Detection)
  ─────────────────────────────────────────────────────────────
  Algoritma utama sesuai dokumen penelitian.
  Dilatih hanya dengan data NORMAL (unsupervised).
  Menghasilkan anomaly score per sampel:
    - Score mendekati +1 → normal
    - Score mendekati -1 → anomali / outlier

  Model 2 — Random Forest Classifier (Supervised Attack Classifier)
  ──────────────────────────────────────────────────────────────────
  Algoritma opsional untuk mengklasifikasikan jenis serangan.
  Membutuhkan dataset berlabel (normal, port_scan, syn_flood, dst.).
  Dilatih jika flag --train-rf diaktifkan atau dataset berlabel tersedia.

Pipeline pelatihan:
  1. Muat dataset dari CSV (ml/datasets/) atau DB
  2. Preprocessing: StandardScaler (wajib untuk IF yang baik)
  3. Train + simpan model (.pkl) dan scaler
  4. Evaluasi silang (cross-validation) untuk RF
  5. Simpan laporan metrik ke ml/models/training_report.json

Cara menjalankan:
  python -m ml.main train
  python -m ml.main train --rf         # termasuk Random Forest
  python -m ml.main train --from-db    # ambil data langsung dari DB
"""

import json
import logging
import os
from datetime import datetime, timedelta

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import classification_report

from ml.config import (
    MODEL_DIR,
    IF_MODEL_PATH,
    RF_MODEL_PATH,
    SCALER_PATH,
    LABEL_ENCODER_PATH,
    DATASET_DIR,
    FEATURE_COLUMNS,
    IF_N_ESTIMATORS,
    IF_CONTAMINATION,
    IF_MAX_SAMPLES,
    IF_RANDOM_STATE,
    RF_N_ESTIMATORS,
    RF_MAX_DEPTH,
    RF_RANDOM_STATE,
    RF_N_JOBS,
    RF_CLASSES,
)
from ml.feature_extractor import (
    extract_from_db,
    load_dataset_csv,
    get_feature_matrix,
)

logger = logging.getLogger(__name__)


# ─── Pastikan direktori model ada ────────────────────────────────────────────
os.makedirs(MODEL_DIR, exist_ok=True)


# ─── Trainer Isolation Forest ────────────────────────────────────────────────
class IsolationForestTrainer:
    """
    Melatih dan menyimpan model Isolation Forest.

    Isolation Forest dilatih hanya dengan data normal (unsupervised).
    Tidak perlu label — cukup pastikan dataset training adalah traffic normal.
    """

    def __init__(
        self,
        n_estimators: int   = IF_N_ESTIMATORS,
        contamination: float= IF_CONTAMINATION,
        max_samples         = IF_MAX_SAMPLES,
        random_state: int   = IF_RANDOM_STATE,
    ) -> None:
        self.n_estimators  = n_estimators
        self.contamination = contamination
        self.max_samples   = max_samples
        self.random_state  = random_state
        self.scaler        = StandardScaler()
        self.model         = IsolationForest(
            n_estimators=n_estimators,
            contamination=contamination,
            max_samples=max_samples,
            random_state=random_state,
            n_jobs=-1,
        )

    def train(self, df: pd.DataFrame) -> dict:
        """
        Melatih model pada DataFrame fitur.

        Args:
            df: DataFrame yang mengandung FEATURE_COLUMNS.
                Untuk IF, HANYA gunakan data normal (label='normal' atau tanpa label).

        Returns:
            dict berisi metrik training.
        """
        logger.info("[IFTrainer] Memulai training Isolation Forest...")
        logger.info("[IFTrainer] Dataset: %d sampel × %d fitur", len(df), len(FEATURE_COLUMNS))

        X = get_feature_matrix(df)

        if len(X) < 10:
            raise ValueError(f"Dataset terlalu kecil: {len(X)} sampel. Minimal 10.")

        # Scaling — IF bekerja lebih baik dengan data yang sudah di-scale
        logger.info("[IFTrainer] Fitting StandardScaler...")
        X_scaled = self.scaler.fit_transform(X)

        # Training
        logger.info(
            "[IFTrainer] Training IF (n_estimators=%d, contamination=%.3f)...",
            self.n_estimators, self.contamination,
        )
        self.model.fit(X_scaled)

        # Evaluasi sederhana: berapa % data yang dianggap anomali oleh model sendiri
        scores = self.model.score_samples(X_scaled)
        predictions = self.model.predict(X_scaled)   # +1=normal, -1=anomali
        n_anomalies = (predictions == -1).sum()
        anomaly_pct = n_anomalies / len(predictions) * 100

        # Kalibrasi keputusan: threshold = boundary IF (offset_), serta rentang
        # skor data training. Dipakai predictor agar keputusan anomali &
        # confidence TIDAK bergantung pada hardcoded threshold (IF_SCORE_THRESHOLD).
        self._calibration = {
            'threshold': float(self.model.offset_),
            'score_min': float(scores.min()),
            'score_max': float(scores.max()),
        }

        metrics = {
            'model':              'IsolationForest',
            'n_samples':          len(X),
            'n_features':         len(FEATURE_COLUMNS),
            'n_estimators':       self.n_estimators,
            'contamination':      self.contamination,
            'n_marked_anomaly':   int(n_anomalies),
            'anomaly_pct':        round(float(anomaly_pct), 2),
            'score_mean':         round(float(scores.mean()), 4),
            'score_std':          round(float(scores.std()), 4),
            'score_min':          round(float(scores.min()), 4),
            'score_max':          round(float(scores.max()), 4),
            'trained_at':         datetime.now().isoformat(),
        }

        logger.info(
            "[IFTrainer] Selesai. Ditandai anomali: %d/%d (%.1f%%) | "
            "Score: mean=%.4f std=%.4f",
            n_anomalies, len(X), anomaly_pct,
            scores.mean(), scores.std(),
        )
        return metrics

    def save(self) -> None:
        """Simpan model, scaler, dan kalibrasi keputusan ke disk."""
        joblib.dump(self.model,  IF_MODEL_PATH)
        joblib.dump(self.scaler, SCALER_PATH)
        # Kalibrasi (threshold + rentang skor) — dipakai predictor di inferensi
        if getattr(self, '_calibration', None):
            with open(IF_CALIBRATION_PATH, 'w') as f:
                json.dump(self._calibration, f, indent=2)
            logger.info(
                "[IFTrainer] Kalibrasi tersimpan → %s "
                "(threshold=%.4f, min=%.4f, max=%.4f)",
                IF_CALIBRATION_PATH,
                self._calibration['threshold'],
                self._calibration['score_min'],
                self._calibration['score_max'],
            )
        logger.info("[IFTrainer] Model tersimpan → %s", IF_MODEL_PATH)
        logger.info("[IFTrainer] Scaler tersimpan → %s", SCALER_PATH)

    @classmethod
    def load(cls) -> 'IsolationForestTrainer':
        """Load model dan scaler yang sudah tersimpan."""
        trainer = cls.__new__(cls)
        trainer.model  = joblib.load(IF_MODEL_PATH)
        trainer.scaler = joblib.load(SCALER_PATH)
        logger.info("[IFTrainer] Model dimuat dari %s", IF_MODEL_PATH)
        return trainer


# ─── Trainer Random Forest ────────────────────────────────────────────────────
class RandomForestTrainer:
    """
    Melatih dan menyimpan model Random Forest Classifier.

    Random Forest dilatih dengan data berlabel untuk mengklasifikasikan
    jenis serangan. Membutuhkan kolom 'label' di dataset.
    """

    def __init__(
        self,
        n_estimators: int = RF_N_ESTIMATORS,
        max_depth: int    = RF_MAX_DEPTH,
        random_state: int = RF_RANDOM_STATE,
        n_jobs: int       = RF_N_JOBS,
    ) -> None:
        self.n_estimators = n_estimators
        self.max_depth    = max_depth
        self.random_state = random_state
        self.n_jobs       = n_jobs
        self.label_encoder = LabelEncoder()
        self.model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=random_state,
            n_jobs=n_jobs,
            class_weight='balanced',    # handle imbalanced dataset
        )

    def train(self, df: pd.DataFrame, label_col: str = 'label') -> dict:
        """
        Melatih Random Forest dengan dataset berlabel.

        Args:
            df        : DataFrame berisi FEATURE_COLUMNS + kolom label
            label_col : Nama kolom label ('normal', 'port_scan', dst.)

        Returns:
            dict berisi metrik training dan cross-validation.
        """
        if label_col not in df.columns:
            raise ValueError(
                f"Kolom label '{label_col}' tidak ditemukan. "
                f"Kolom tersedia: {list(df.columns)}"
            )

        logger.info("[RFTrainer] Memulai training Random Forest Classifier...")

        X = get_feature_matrix(df)
        y_raw = df[label_col].astype(str).values

        # Encode label → integer
        y = self.label_encoder.fit_transform(y_raw)
        classes = list(self.label_encoder.classes_)
        logger.info("[RFTrainer] Kelas ditemukan: %s", classes)
        logger.info("[RFTrainer] Distribusi label:\n%s",
                    pd.Series(y_raw).value_counts().to_string())

        # Cross-validation 5-fold sebelum fit final
        logger.info("[RFTrainer] Cross-validation 5-fold...")
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=self.random_state)
        cv_results = cross_validate(
            self.model, X, y,
            cv=cv,
            scoring=['accuracy', 'f1_weighted', 'precision_weighted', 'recall_weighted'],
            return_train_score=True,
        )

        cv_metrics = {
            k: round(float(v.mean()), 4)
            for k, v in cv_results.items()
            if k.startswith('test_')
        }
        logger.info("[RFTrainer] CV Results: %s", cv_metrics)

        # Training final pada seluruh dataset
        self.model.fit(X, y)

        # Laporan klasifikasi pada data training
        y_pred = self.model.predict(X)
        report = classification_report(
            y, y_pred,
            target_names=classes,
            output_dict=True,
            zero_division=0,
        )

        # Feature importance
        importance = dict(zip(FEATURE_COLUMNS, self.model.feature_importances_))
        top5 = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:5]
        logger.info("[RFTrainer] Top-5 Feature Importance: %s",
                    [(k, f'{v:.4f}') for k, v in top5])

        metrics = {
            'model':              'RandomForest',
            'n_samples':          len(X),
            'n_features':         len(FEATURE_COLUMNS),
            'n_estimators':       self.n_estimators,
            'max_depth':          self.max_depth,
            'classes':            classes,
            'cv_metrics':         cv_metrics,
            'train_report':       report,
            'feature_importance': {k: round(float(v), 6) for k, v in importance.items()},
            'trained_at':         datetime.now().isoformat(),
        }

        logger.info(
            "[RFTrainer] Selesai. Train accuracy=%.4f | CV accuracy=%.4f",
            report.get('accuracy', 0),
            cv_metrics.get('test_accuracy', 0),
        )
        return metrics

    def save(self) -> None:
        """Simpan model dan label encoder ke disk."""
        joblib.dump(self.model,         RF_MODEL_PATH)
        joblib.dump(self.label_encoder, LABEL_ENCODER_PATH)
        logger.info("[RFTrainer] Model tersimpan → %s", RF_MODEL_PATH)

    @classmethod
    def load(cls) -> 'RandomForestTrainer':
        """Load model dan label encoder yang sudah tersimpan."""
        trainer = cls.__new__(cls)
        trainer.model         = joblib.load(RF_MODEL_PATH)
        trainer.label_encoder = joblib.load(LABEL_ENCODER_PATH)
        logger.info("[RFTrainer] Model dimuat dari %s", RF_MODEL_PATH)
        return trainer


# ─── Fungsi Training Utama ────────────────────────────────────────────────────
def run_training(
    train_rf: bool      = False,
    from_db: bool       = False,
    hours_back: int     = 24,
    normal_csv: str     = '',
    labeled_csv: str    = '',
) -> dict:
    """
    Fungsi training lengkap: muat data → latih → simpan → laporan.

    Args:
        train_rf    : Apakah juga melatih Random Forest
        from_db     : Ambil data dari DB (bukan CSV)
        hours_back  : Jika from_db=True, ambil dari N jam terakhir
        normal_csv  : Path CSV traffic normal (untuk IF)
        labeled_csv : Path CSV berlabel (untuk RF)

    Returns:
        dict laporan lengkap training.
    """
    report = {}

    # ── Training Isolation Forest ─────────────────────────────────────────────
    logger.info("=" * 55)
    logger.info("  TAHAP 1: Training Isolation Forest")
    logger.info("=" * 55)

    if from_db:
        logger.info("[Train] Mengambil data normal dari DB (%d jam terakhir)...", hours_back)
        until = datetime.now()
        since = until - timedelta(hours=hours_back)
        df_normal = extract_from_db(since=since, until=until)

        if df_normal.empty:
            logger.error("[Train] Tidak ada data di DB. Pastikan collector sudah berjalan.")
            return {'error': 'Tidak ada data traffic di database.'}
    else:
        # Cari file CSV normal
        csv_path = normal_csv or os.path.join(DATASET_DIR, 'normal.csv')
        if not os.path.isfile(csv_path):
            logger.error("[Train] File tidak ditemukan: %s", csv_path)
            return {'error': f'File tidak ditemukan: {csv_path}'}
        df_normal = load_dataset_csv(csv_path)
        # Filter hanya label normal jika kolom ada
        if 'label' in df_normal.columns:
            df_normal = df_normal[df_normal['label'] == 'normal']

    if df_normal.empty:
        return {'error': 'Dataset normal kosong setelah filter.'}

    if_trainer = IsolationForestTrainer()
    if_metrics = if_trainer.train(df_normal)
    if_trainer.save()
    report['isolation_forest'] = if_metrics

    # ── Training Random Forest (opsional) ─────────────────────────────────────
    if train_rf:
        logger.info("=" * 55)
        logger.info("  TAHAP 2: Training Random Forest")
        logger.info("=" * 55)

        csv_path = labeled_csv or os.path.join(DATASET_DIR, 'labeled.csv')
        if not os.path.isfile(csv_path):
            logger.warning(
                "[Train] File labeled CSV tidak ditemukan: %s. "
                "Random Forest dilewati.", csv_path,
            )
            report['random_forest'] = {'skipped': True, 'reason': 'File tidak ditemukan'}
        else:
            df_labeled = load_dataset_csv(csv_path)
            if 'label' not in df_labeled.columns:
                logger.warning("[Train] Kolom 'label' tidak ada. RF dilewati.")
                report['random_forest'] = {'skipped': True, 'reason': 'Kolom label tidak ada'}
            else:
                rf_trainer = RandomForestTrainer()
                rf_metrics = rf_trainer.train(df_labeled)
                rf_trainer.save()
                report['random_forest'] = rf_metrics

    # ── Simpan laporan JSON ───────────────────────────────────────────────────
    report_path = os.path.join(MODEL_DIR, 'training_report.json')
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, default=str)
    logger.info("[Train] Laporan training disimpan → %s", report_path)

    return report
