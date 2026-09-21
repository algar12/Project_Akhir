"""
predictor.py — Unified Network Guard: ML
==========================================
Modul inferensi real-time: menggunakan model yang sudah dilatih untuk
mendeteksi anomali traffic secara berkelanjutan.

Alur kerja:
  1. Muat Isolation Forest + scaler (wajib)
  2. Muat Random Forest + label encoder (opsional, jika tersedia)
  3. Polling DB setiap PREDICTOR_POLL_INTERVAL detik
  4. Ekstrak fitur dari traffic terbaru
  5. Prediksi:
       a. IF: hitung anomaly score → jika < IF_SCORE_THRESHOLD → ANOMALI
       b. RF (jika ada): klasifikasikan jenis serangan
  6. Untuk setiap anomali → buat Alert → kirim ke AlertManager
  7. Simpan hasil prediksi ke tabel ml_predictions

Schema tabel ml_predictions (dibuat otomatis):
  id, timestamp, source_ip, time_bucket,
  if_score, is_anomaly, attack_class, confidence, features (JSONB)

Mapping anomaly score → confidence:
  Skor IF berkisar -1 (sangat anomali) sampai +0.5 (sangat normal).
  Confidence = clamp((threshold - score) / threshold * base_confidence, 0, 1)
  Sehingga makin jauh dari threshold makin tinggi confidence.
"""

import json
import logging
import os
import threading
import time
from datetime import datetime, timedelta, timezone

import joblib
import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool

from ml.config import (
    DATABASE_URL,
    IF_MODEL_PATH,
    RF_MODEL_PATH,
    SCALER_PATH,
    LABEL_ENCODER_PATH,
    IF_CALIBRATION_PATH,
    FEATURE_COLUMNS,
    PREDICTOR_POLL_INTERVAL,
    IF_SCORE_THRESHOLD,
    IF_CONFIDENCE_BASE,
    FEATURE_WINDOW_SECONDS,
    IOT_SUBNET,
)
from ml.feature_extractor import extract_recent, get_feature_matrix

logger = logging.getLogger(__name__)

# ─── DB Engine ────────────────────────────────────────────────────────────────
_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(
            DATABASE_URL,
            poolclass=QueuePool,
            pool_size=3,
            max_overflow=5,
            pool_pre_ping=True,
            echo=False,
        )
    return _engine


def _ensure_predictions_table() -> None:
    """Buat tabel ml_predictions jika belum ada (idempotent)."""
    sql_create = text("""
        CREATE TABLE IF NOT EXISTS ml_predictions (
            id           SERIAL PRIMARY KEY,
            timestamp    TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
            source_ip    VARCHAR(45)   NOT NULL,
            time_bucket  TIMESTAMP,
            if_score     FLOAT,
            is_anomaly   BOOLEAN       DEFAULT FALSE,
            attack_class VARCHAR(50),
            confidence   FLOAT         DEFAULT 0.0,
            features     JSONB
        );
        CREATE INDEX IF NOT EXISTS idx_mlpred_timestamp
            ON ml_predictions (timestamp DESC);
        CREATE INDEX IF NOT EXISTS idx_mlpred_anomaly
            ON ml_predictions (is_anomaly, timestamp DESC);
    """)
    try:
        engine = _get_engine()
        with engine.connect() as conn:
            conn.execute(sql_create)
            conn.commit()
    except Exception as exc:
        logger.error("[Predictor] Gagal buat tabel ml_predictions: %s", exc)


def _insert_predictions(rows: list[dict]) -> None:
    """Batch insert hasil prediksi ke tabel ml_predictions."""
    if not rows:
        return
    sql = text("""
        INSERT INTO ml_predictions
            (timestamp, source_ip, time_bucket, if_score,
             is_anomaly, attack_class, confidence, features)
        VALUES
            (:timestamp, :source_ip, :time_bucket, :if_score,
             :is_anomaly, :attack_class, :confidence, :features)
    """)
    try:
        engine = _get_engine()
        with engine.connect() as conn:
            conn.execute(sql, rows)
            conn.commit()
    except Exception as exc:
        logger.error("[Predictor] Gagal insert ml_predictions: %s", exc)


# ─── Score → Confidence ───────────────────────────────────────────────────────
def _score_to_confidence(score: float, threshold: float, score_min: float) -> float:
    """
    Konversi anomaly score Isolation Forest ke nilai confidence [0.5, 0.99].

    Kalibrasi terhadap rentang skor data training (score_min) dan threshold
    keputusan — sehingga confidence tidak jenuh 0.99 untuk hampir semua kasus.
    - score > threshold (normal) → 0.0
    - score == threshold (borderline) → 0.5
    - score == score_min (paling anomali) → 0.99
    """
    if score > threshold:
        return 0.0
    span = max(threshold - score_min, 1e-6)
    conf = 0.5 + (threshold - score) / span * 0.49
    return round(min(float(conf), 0.99), 4)


# ─── Predictor ────────────────────────────────────────────────────────────────
class AnomalyPredictor:
    """
    Menjalankan inferensi real-time menggunakan model yang telah dilatih.

    Usage:
        from detection.alert_manager import AlertManager
        mgr = AlertManager()
        pred = AnomalyPredictor(alert_manager=mgr)
        pred.start()
        ...
        pred.stop()
    """

    def __init__(self, alert_manager=None) -> None:
        """
        Args:
            alert_manager: Instance AlertManager dari modul detection.
                           Jika None, alert hanya di-log tanpa disimpan ke DB alerts.
        """
        self.alert_manager   = alert_manager
        self._stop_event     = threading.Event()
        self._thread: threading.Thread | None = None

        # Model & preprocessor (dimuat di start())
        self._if_model       = None
        self._if_scaler      = None
        self._rf_model       = None
        self._label_encoder  = None
        self._has_rf         = False

        # Kalibrasi keputusan IF (dibaca dari if_calibration.json saat start):
        #   _decision_threshold — skor <= threshold → anomali (default: offset_ model)
        #   _score_min         — skor paling anomali pada data training (untuk confidence)
        self._calibration       = None
        self._decision_threshold: float | None = None
        self._score_min: float | None = None

        # Tracking: (source_ip, time_bucket) yang sudah diprediksi → waktu terakhir.
        # Menggantikan _last_bucket_ts: menangani baris yang masuk ke bucket lama
        # setelah bucket tsb pertama kali diproses (race condition), sekaligus
        # mencegah duplikasi prediksi pada (ip, bucket) yang sama.
        self._seen_buckets: dict[tuple[str, datetime], datetime] = {}

        # Statistik
        self._total_batches    = 0
        self._total_rows       = 0
        self._total_anomalies  = 0
        self._total_alerts_gen = 0

    # ─── Load Model ──────────────────────────────────────────────────────────
    def _load_models(self) -> bool:
        """
        Memuat model dari disk. Mengembalikan True jika minimal IF berhasil dimuat.
        """
        # Isolation Forest (wajib)
        if not os.path.isfile(IF_MODEL_PATH) or not os.path.isfile(SCALER_PATH):
            logger.error(
                "[Predictor] Model Isolation Forest tidak ditemukan.\n"
                "  Jalankan: python -m ml.main train"
            )
            return False

        self._if_model  = joblib.load(IF_MODEL_PATH)
        self._if_scaler = joblib.load(SCALER_PATH)
        logger.info("[Predictor] Isolation Forest dimuat dari %s", IF_MODEL_PATH)

        # ── Kalibrasi keputusan anomali ──────────────────────────────────────
        # Prioritas threshold: IF_SCORE_THRESHOLD (env, tuning manual) >
        # if_calibration.json (hasil training) > offset_ bawaan model.
        self._calibration = None
        if os.path.isfile(IF_CALIBRATION_PATH):
            try:
                with open(IF_CALIBRATION_PATH) as f:
                    self._calibration = json.load(f)
                logger.info(
                    "[Predictor] Kalibrasi dimuat → threshold=%.4f score_min=%.4f",
                    float(self._calibration.get('threshold', 0)),
                    float(self._calibration.get('score_min', 0)),
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("[Predictor] Gagal baca kalibrasi: %s", exc)
                self._calibration = None

        if IF_SCORE_THRESHOLD is not None:
            self._decision_threshold = float(IF_SCORE_THRESHOLD)
            logger.info(
                "[Predictor] IF_SCORE_THRESHOLD di-set dari env → %.4f",
                self._decision_threshold,
            )
        elif self._calibration and self._calibration.get('threshold') is not None:
            self._decision_threshold = float(self._calibration['threshold'])
        else:
            self._decision_threshold = float(
                getattr(self._if_model, 'offset_', -0.05)
            )
        self._score_min = (
            float(self._calibration['score_min'])
            if self._calibration and self._calibration.get('score_min') is not None
            else None
        )

        # Random Forest (opsional)
        if os.path.isfile(RF_MODEL_PATH) and os.path.isfile(LABEL_ENCODER_PATH):
            self._rf_model      = joblib.load(RF_MODEL_PATH)
            self._label_encoder = joblib.load(LABEL_ENCODER_PATH)
            self._has_rf        = True
            logger.info("[Predictor] Random Forest dimuat dari %s", RF_MODEL_PATH)
        else:
            logger.info("[Predictor] Random Forest tidak tersedia (opsional).")

        return True

    # ─── Prediksi Satu Batch ──────────────────────────────────────────────────
    def _predict_batch(self, df: pd.DataFrame) -> list[dict]:
        """
        Menjalankan prediksi pada DataFrame fitur.

        Returns:
            List dict berisi hasil prediksi per baris:
            {source_ip, time_bucket, if_score, is_anomaly, attack_class, confidence, features}
        """
        X = get_feature_matrix(df)
        X_scaled = self._if_scaler.transform(X)

        # Isolation Forest
        if_scores  = self._if_model.score_samples(X_scaled)   # float array
        if_preds   = self._if_model.predict(X_scaled)          # +1 / -1

        # Random Forest (opsional)
        rf_classes = None
        if self._has_rf:
            try:
                rf_preds   = self._rf_model.predict(X)
                rf_classes = self._label_encoder.inverse_transform(rf_preds)
            except Exception as exc:
                logger.warning("[Predictor] RF predict gagal: %s", exc)

        results = []
        threshold = self._decision_threshold
        score_min = self._score_min
        for i, (_, row) in enumerate(df.iterrows()):
            score      = float(if_scores[i])

            # Keputusan anomali: skor <= threshold (kalibrasi/env) — bukan lagi
            # semata predict()==-1 yang bergantung contamination training.
            if threshold is not None:
                is_anomaly = bool(score <= threshold)
            else:
                is_anomaly = bool(if_preds[i] == -1)

            if is_anomaly and score_min is not None:
                confidence = _score_to_confidence(score, threshold, score_min)
            else:
                confidence = 0.0

            attack_class = 'normal'
            if is_anomaly:
                if rf_classes is not None:
                    attack_class = str(rf_classes[i])
                else:
                    # Heuristik sederhana berdasarkan fitur jika RF tidak ada
                    attack_class = self._heuristic_classify(row)

            results.append({
                'source_ip':    row.get('source_ip', 'unknown'),
                'time_bucket':  row.get('time_bucket', datetime.now()),
                'if_score':     round(score, 6),
                'is_anomaly':   is_anomaly,
                'attack_class': attack_class,
                'confidence':   confidence,
                'features':     json.dumps({
                    col: round(float(row[col]), 4) for col in FEATURE_COLUMNS
                }),
            })
        return results

    # ─── Heuristik Klasifikasi Tanpa RF ───────────────────────────────────────
    @staticmethod
    def _heuristic_classify(row: pd.Series) -> str:
        """
        Klasifikasi kasar berdasarkan nilai fitur ketika RF tidak tersedia.
        Berguna sebagai fallback untuk penamaan serangan di alert.

        Urutan prioritas dibuat dari penanda paling spesifik → umum, dan
        label yang benar secara semantik:
          - byte_rate TINGGI + paket kecil & banyak → bukan 'syn_flood'
            (SYN flood = paket kecil tanpa payload, tapi volume rata-rata
            per paket kecil). Traffic spike murni = byte_rate tinggi.
        """
        pkt_rate     = row.get('packet_rate', 0)
        icmp_r       = row.get('proto_icmp_ratio', 0)
        dst_ports    = row.get('unique_dst_ports', 0)
        byte_rate    = row.get('byte_rate', 0)
        mqtt_r       = row.get('mqtt_ratio', 0)
        tcp_r        = row.get('proto_tcp_ratio', 0)
        avg_pkt      = (byte_rate / pkt_rate) if pkt_rate > 0 else 0

        if icmp_r > 0.5 and pkt_rate > 30:
            return 'icmp_flood'
        elif mqtt_r > 0.5 and pkt_rate > 20:
            return 'mqtt_anomaly'
        elif dst_ports > 15 and pkt_rate > 10:
            return 'port_scan'
        elif (pkt_rate > 60 and tcp_r > 0.8 and avg_pkt < 200):
            # Banjir paket TCP kecil (SYN flood khas: SYN tanpa payload/ACK)
            return 'syn_flood'
        else:
            # Lonjakan bytes tinggi / pola lain → traffic spike (bukan syn_flood)
            return 'traffic_spike'

    # ─── Emit Alert ──────────────────────────────────────────────────────────
    def _emit_alerts(self, anomaly_results: list[dict]) -> None:
        """
        Mengkonversi hasil prediksi anomali menjadi Alert dan mengirimnya
        ke AlertManager (jika tersedia).
        """
        if not self.alert_manager:
            return

        # Import di sini untuk hindari circular import antara ml dan detection
        from detection.alert_manager import Alert, map_severity

        for res in anomaly_results:
            attack_class = res['attack_class']

            # Filter false positive: IF menandai anomali tapi RF menganggap normal.
            # (Contamination 0.05 membuat IF selalu menandai ~5% data normal sebagai
            # anomali; RF yang dilatih pada data normal akan membenarkan label tsb.)
            if attack_class.lower() == 'normal':
                logger.info(
                    "[Predictor] Anomali IF tapi RF=normal → dilewati (false positive): %s",
                    res['source_ip'],
                )
                continue

            severity     = map_severity(attack_class)
            confidence   = res['confidence']
            score        = res['if_score']

            alert = Alert(
                source_ip=res['source_ip'],
                target_ip=IOT_SUBNET,   # subnet IoT aktual (dari env) sebagai target umum
                attack_type=attack_class.upper(),
                severity=severity,
                confidence=confidence,
                description=(
                    f"[ML/Isolation Forest] Anomali terdeteksi dari {res['source_ip']} | "
                    f"IF score={score:.4f} | class={attack_class} | "
                    f"confidence={confidence:.2f}"
                ),
                timestamp=res['time_bucket'] if isinstance(res['time_bucket'], datetime)
                          else datetime.now(timezone.utc).replace(tzinfo=None),
                source='ml',
            )

            inserted = self.alert_manager.process(alert)
            if inserted:
                self._total_alerts_gen += 1

    # ─── Loop Utama ──────────────────────────────────────────────────────────
    def _run_loop(self) -> None:
        """Loop polling utama yang berjalan di thread terpisah."""
        logger.info(
            "[Predictor] Mulai. Polling setiap %ds | IF threshold=%.4f",
            PREDICTOR_POLL_INTERVAL,
            self._decision_threshold if self._decision_threshold is not None else 0.0,
        )

        while not self._stop_event.is_set():
            # Ekstrak fitur dari traffic terbaru
            df = extract_recent(
                window_seconds=PREDICTOR_POLL_INTERVAL * 2
            )

            if df.empty:
                logger.debug("[Predictor] Tidak ada data baru. Menunggu...")
                self._stop_event.wait(timeout=PREDICTOR_POLL_INTERVAL)
                continue

            # Filter baris yang sudah pernah diprediksi (dedup per source_ip + time_bucket).
            # Menggunakan dedup berbasis bucket (bukan timestamp cutoff) agar baris
            # yang masuk ke bucket lama setelah bucket tsb pertama diproses tetap
            # terdeteksi tanpa membuat prediksi duplikat.
            if 'time_bucket' in df.columns:
                keep_mask = [
                    (row['source_ip'], row['time_bucket']) not in self._seen_buckets
                    for _, row in df.iterrows()
                ]
                df = df[keep_mask]

            if df.empty:
                self._stop_event.wait(timeout=PREDICTOR_POLL_INTERVAL)
                continue

            # Prediksi
            results = self._predict_batch(df)
            self._total_batches += 1
            self._total_rows    += len(results)

            # Pisahkan anomali dari normal
            anomalies = [r for r in results if r['is_anomaly']]
            self._total_anomalies += len(anomalies)

            # Simpan semua hasil ke DB (timestamp UTC naive — konsisten seluruh pipeline)
            db_rows = [{
                **r,
                'timestamp': datetime.now(timezone.utc).replace(tzinfo=None),
            } for r in results]
            _insert_predictions(db_rows)

            # Tandai (ip, bucket) yang sudah diprediksi agar tidak diproses ulang
            if 'time_bucket' in df.columns:
                now = datetime.now(timezone.utc).replace(tzinfo=None)
                for _, row in df.iterrows():
                    self._seen_buckets[(row['source_ip'], row['time_bucket'])] = now

            # Prune cache dedup agar tidak membesar tanpa batas
            if len(self._seen_buckets) > 20_000:
                cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=5)
                stale = [k for k, v in self._seen_buckets.items() if v < cutoff]
                for k in stale:
                    del self._seen_buckets[k]
                logger.debug("[Predictor] Cache dedup diprun: %d entri dihapus.", len(stale))

            if anomalies:
                logger.warning(
                    "[Predictor] ⚠️  %d/%d anomali terdeteksi pada batch ini!",
                    len(anomalies), len(results),
                )
                for a in anomalies:
                    logger.warning(
                        "  → [%s] %s | score=%.4f | class=%s | conf=%.2f",
                        a['source_ip'], a['time_bucket'],
                        a['if_score'], a['attack_class'], a['confidence'],
                    )
                self._emit_alerts(anomalies)
            else:
                logger.debug(
                    "[Predictor] Batch #%d: %d baris, semua normal.",
                    self._total_batches, len(results),
                )

            self._stop_event.wait(timeout=PREDICTOR_POLL_INTERVAL)

        logger.info("[Predictor] Loop berhenti.")

    # ─── Public API ──────────────────────────────────────────────────────────
    def start(self) -> bool:
        """
        Muat model lalu mulai thread prediksi.

        Returns:
            True jika berhasil dimulai, False jika model tidak ditemukan.
        """
        _ensure_predictions_table()

        if not self._load_models():
            return False

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            name='ml-predictor',
            daemon=True,
        )
        self._thread.start()
        logger.info("[Predictor] Thread aktif.")
        return True

    def stop(self) -> None:
        logger.info("[Predictor] Menghentikan...")
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=15)
        logger.info(
            "[Predictor] Berhenti. Batch=%d | Rows=%d | Anomali=%d | Alerts=%d",
            self._total_batches, self._total_rows,
            self._total_anomalies, self._total_alerts_gen,
        )

    @property
    def stats(self) -> dict:
        return {
            'total_batches':    self._total_batches,
            'total_rows':       self._total_rows,
            'total_anomalies':  self._total_anomalies,
            'total_alerts_gen': self._total_alerts_gen,
            'has_rf':           self._has_rf,
        }
