"""
feature_extractor.py — Unified Network Guard: ML
=================================================
Mengekstrak dan mengagregasi fitur traffic jaringan dari database
menjadi feature vector yang siap dimasukkan ke model ML.

Konsep Agregasi (Time-Window Aggregation):
  Raw traffic (per paket) → Agregat per (source_ip, window) →
  Feature vector 12 dimensi per baris

Mengapa agregasi, bukan per-paket?
  - Model ML sulit mendeteksi anomali dari satu paket saja.
  - Pola serangan (flood, scan) terlihat dari volume dalam window waktu.
  - Window 10 detik adalah trade-off antara responsivitas dan akurasi.

Fitur yang diekstrak:
  1.  packet_count       — total paket
  2.  byte_count         — total bytes
  3.  connection_count   — jumlah entri unik (proxy flow count)
  4.  packet_rate        — packet_count / window
  5.  byte_rate          — byte_count / window
  6.  avg_packet_size    — byte_count / max(packet_count, 1)
  7.  unique_dst_ports   — jumlah port tujuan berbeda
  8.  unique_dst_ips     — jumlah IP tujuan berbeda
  9.  proto_tcp_ratio    — fraksi TCP
  10. proto_udp_ratio    — fraksi UDP
  11. proto_icmp_ratio   — fraksi ICMP
  12. mqtt_ratio         — fraksi ke/dari port 1883

Dua mode penggunaan:
  A. Batch: extract_from_db(since, until) → DataFrame (untuk training)
  B. Real-time: extract_recent(window_sec) → DataFrame (untuk prediksi)
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool

from ml.config import (
    DATABASE_URL,
    FEATURE_COLUMNS,
    FEATURE_WINDOW_SECONDS,
)

logger = logging.getLogger(__name__)

# ─── DB Engine (singleton) ────────────────────────────────────────────────────
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


# ─── Query Agregasi SQL ───────────────────────────────────────────────────────
def _build_aggregation_query(since: datetime, until: datetime) -> text:
    """
    Query SQL untuk mengagregasi traffic per (source_ip, time_bucket).
    Menggunakan date_trunc dengan FEATURE_WINDOW_SECONDS untuk bucket.
    """
    # PostgreSQL: buat time bucket manual karena date_trunc tidak support detik arbitrer
    bucket_sql = f"""
        (EXTRACT(EPOCH FROM timestamp)::BIGINT / {FEATURE_WINDOW_SECONDS})
        * {FEATURE_WINDOW_SECONDS}
    """
    return text(f"""
        SELECT
            source_ip,
            TO_TIMESTAMP({bucket_sql}) AS time_bucket,
            COUNT(*)                                AS packet_count,
            COALESCE(SUM(bytes), 0)                 AS byte_count,
            COUNT(*)                                AS connection_count,
            COUNT(*) / {FEATURE_WINDOW_SECONDS}.0  AS packet_rate,
            COALESCE(SUM(bytes), 0)
                / {FEATURE_WINDOW_SECONDS}.0        AS byte_rate,
            CASE
                WHEN COUNT(*) > 0
                THEN COALESCE(SUM(bytes), 0)::FLOAT / COUNT(*)
                ELSE 0
            END                                     AS avg_packet_size,
            COUNT(DISTINCT destination_port)        AS unique_dst_ports,
            COUNT(DISTINCT destination_ip)          AS unique_dst_ips,
            -- Rasio per protokol
            SUM(CASE WHEN protocol = 'TCP'  THEN 1 ELSE 0 END)::FLOAT
                / NULLIF(COUNT(*), 0)               AS proto_tcp_ratio,
            SUM(CASE WHEN protocol = 'UDP'  THEN 1 ELSE 0 END)::FLOAT
                / NULLIF(COUNT(*), 0)               AS proto_udp_ratio,
            SUM(CASE WHEN protocol = 'ICMP' THEN 1 ELSE 0 END)::FLOAT
                / NULLIF(COUNT(*), 0)               AS proto_icmp_ratio,
            -- Rasio traffic MQTT (port 1883)
            SUM(CASE
                WHEN destination_port = 1883
                  OR source_port = 1883 THEN 1 ELSE 0
            END)::FLOAT / NULLIF(COUNT(*), 0)       AS mqtt_ratio
        FROM network_traffic
        WHERE timestamp >= :since
          AND timestamp <  :until
        GROUP BY source_ip, time_bucket
        ORDER BY time_bucket ASC, source_ip ASC
    """)


# ─── Fungsi Ekstraksi ─────────────────────────────────────────────────────────
def extract_from_db(
    since: datetime,
    until: datetime,
    source_ip_filter: Optional[str] = None,
) -> pd.DataFrame:
    """
    Ekstraksi fitur batch dari rentang waktu tertentu (untuk training/evaluasi).

    Args:
        since             : Mulai dari waktu ini (inklusif)
        until             : Sampai waktu ini (eksklusif)
        source_ip_filter  : Jika diisi, hanya ambil traffic dari IP ini

    Returns:
        DataFrame dengan kolom: source_ip, time_bucket, + FEATURE_COLUMNS
        DataFrame kosong jika tidak ada data.
    """
    sql = _build_aggregation_query(since, until)
    try:
        engine = _get_engine()
        with engine.connect() as conn:
            df = pd.read_sql(sql, conn, params={'since': since, 'until': until})
    except Exception as exc:
        logger.error("[FeatExtract] Gagal query DB: %s", exc)
        return pd.DataFrame(columns=['source_ip', 'time_bucket'] + FEATURE_COLUMNS)

    if df.empty:
        logger.debug("[FeatExtract] Tidak ada data antara %s dan %s.", since, until)
        return df

    # Filter per IP jika diminta
    if source_ip_filter:
        df = df[df['source_ip'] == source_ip_filter]

    # Isi NaN dengan 0 (null ratio menjadi 0 = tidak ada traffic jenis itu)
    df[FEATURE_COLUMNS] = df[FEATURE_COLUMNS].fillna(0.0)

    logger.debug(
        "[FeatExtract] Diekstrak: %d baris | %s s/d %s",
        len(df), since.strftime('%H:%M:%S'), until.strftime('%H:%M:%S'),
    )
    return df


def extract_recent(
    window_seconds: int = FEATURE_WINDOW_SECONDS * 6,
) -> pd.DataFrame:
    """
    Ekstraksi fitur dari N detik terakhir (untuk prediksi real-time).

    Hanya bucket yang sudah SELESAI yang diambil: `until` dipotong ke awal
    bucket yang masih terbuka, sehingga fitur tidak undercount dari bucket
    parsial (record yang masih masuk ke bucket aktif). Ini menyamakan
    semantik dengan data training (bucket penuh 10 detik).

    Args:
        window_seconds: Berapa detik ke belakang dari sekarang yang diekstrak.
                        Default: 6 × FEATURE_WINDOW_SECONDS (misal 60 detik).

    Returns:
        DataFrame fitur, atau DataFrame kosong jika tidak ada data.
    """
    # Timestamp UTC — hitung epoch dari datetime AWARE (jangan strip tzinfo dulu,
    # karena .timestamp() pada datetime naive dianggap waktu lokal WIB → epoch salah
    # → jendela query bergeser 7 jam dan extract_recent selalu kosong).
    now_utc = datetime.now(timezone.utc)                    # aware (UTC)
    epoch = int(now_utc.timestamp())                        # epoch UTC yang benar
    bucket_start = epoch - (epoch % FEATURE_WINDOW_SECONDS)
    until = datetime.fromtimestamp(bucket_start, tz=timezone.utc).replace(tzinfo=None)
    since = until - timedelta(seconds=window_seconds)
    return extract_from_db(since=since, until=until)


def load_dataset_csv(filepath: str, label_col: str = 'label') -> pd.DataFrame:
    """
    Memuat dataset CSV dari direktori ml/datasets/.

    CSV harus mengandung semua FEATURE_COLUMNS + kolom label.
    Kolom label (misal 'label') berisi: 'normal', 'port_scan', 'syn_flood', dll.

    Args:
        filepath  : Path absolut ke file CSV
        label_col : Nama kolom label

    Returns:
        DataFrame yang sudah divalidasi dan dibersihkan.
    """
    logger.info("[FeatExtract] Memuat dataset: %s", filepath)
    try:
        df = pd.read_csv(filepath)
    except Exception as exc:
        logger.error("[FeatExtract] Gagal baca CSV: %s", exc)
        return pd.DataFrame()

    # Validasi kolom fitur
    missing = [c for c in FEATURE_COLUMNS if c not in df.columns]
    if missing:
        logger.warning("[FeatExtract] Kolom hilang di CSV: %s", missing)
        for col in missing:
            df[col] = 0.0

    # Isi NaN
    df[FEATURE_COLUMNS] = df[FEATURE_COLUMNS].fillna(0.0)

    if label_col in df.columns:
        logger.info(
            "[FeatExtract] Dataset dimuat: %d baris | distribusi label:\n%s",
            len(df), df[label_col].value_counts().to_string(),
        )
    else:
        logger.info("[FeatExtract] Dataset dimuat: %d baris (tanpa kolom label).", len(df))

    return df


# ─── Utilitas ─────────────────────────────────────────────────────────────────
def get_feature_matrix(df: pd.DataFrame) -> np.ndarray:
    """
    Mengambil kolom FEATURE_COLUMNS dari DataFrame sebagai NumPy array.
    Memastikan urutan kolom konsisten dengan urutan yang dilatih model.

    Args:
        df: DataFrame yang mengandung FEATURE_COLUMNS

    Returns:
        2D NumPy array shape (n_samples, n_features)
    """
    return df[FEATURE_COLUMNS].values.astype(np.float64)
