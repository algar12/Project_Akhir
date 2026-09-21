"""
config.py — Unified Network Guard: ML
=======================================
Konfigurasi terpusat untuk seluruh pipeline Machine Learning.
Dibaca dari environment variables (.env) dengan nilai default yang aman.
"""

import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

# ─── Database ─────────────────────────────────────────────────────────────────
DB_HOST: str     = os.getenv('DB_HOST', 'localhost')
DB_PORT: int     = int(os.getenv('DB_PORT', '5432'))
DB_NAME: str     = os.getenv('DB_NAME', 'network_guard')
DB_USER: str     = os.getenv('DB_USER', 'guard_user')
DB_PASSWORD: str = os.getenv('DB_PASSWORD', 'guard_secret')

DATABASE_URL: str = (
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# ─── Path Model & Dataset ─────────────────────────────────────────────────────
_BASE = os.path.dirname(__file__)

MODEL_DIR: str         = os.path.join(_BASE, 'models')
IF_MODEL_PATH: str     = os.path.join(MODEL_DIR, 'isolation_forest.pkl')
RF_MODEL_PATH: str     = os.path.join(MODEL_DIR, 'random_forest.pkl')
SCALER_PATH: str       = os.path.join(MODEL_DIR, 'scaler.pkl')
LABEL_ENCODER_PATH: str= os.path.join(MODEL_DIR, 'label_encoder.pkl')
IF_CALIBRATION_PATH: str = os.path.join(MODEL_DIR, 'if_calibration.json')

# Direktori dataset CSV yang di-generate dari lab
DATASET_DIR: str       = os.path.join(_BASE, 'datasets')

# ─── Feature Engineering ──────────────────────────────────────────────────────
# Window agregasi (detik) — traffic dikelompokkan per IP sumber per window ini
FEATURE_WINDOW_SECONDS: int = int(os.getenv('FEATURE_WINDOW_SECONDS', '10'))

# Nama fitur numerik yang digunakan model (URUTAN INI HARUS KONSISTEN)
FEATURE_COLUMNS: list[str] = [
    'packet_count',         # jumlah total paket dalam window
    'byte_count',           # total bytes dalam window
    'connection_count',     # jumlah baris unik (unique flow approximation)
    'packet_rate',          # packet_count / window_seconds
    'byte_rate',            # byte_count / window_seconds
    'avg_packet_size',      # byte_count / packet_count
    'unique_dst_ports',     # jumlah port tujuan unik
    'unique_dst_ips',       # jumlah IP tujuan unik
    'proto_tcp_ratio',      # proporsi paket TCP (0.0–1.0)
    'proto_udp_ratio',      # proporsi paket UDP (0.0–1.0)
    'proto_icmp_ratio',     # proporsi paket ICMP (0.0–1.0)
    'mqtt_ratio',           # proporsi paket ke/dari port 1883
]

# ─── Isolation Forest Hyperparameter ─────────────────────────────────────────
IF_N_ESTIMATORS: int    = int(os.getenv('IF_N_ESTIMATORS', '200'))
IF_CONTAMINATION: float = float(os.getenv('ANOMALY_CONTAMINATION', '0.05'))
IF_MAX_SAMPLES: str     = os.getenv('IF_MAX_SAMPLES', 'auto')
IF_RANDOM_STATE: int    = 42

# ─── Random Forest Hyperparameter ────────────────────────────────────────────
RF_N_ESTIMATORS: int    = int(os.getenv('RF_N_ESTIMATORS', '150'))
RF_MAX_DEPTH: int       = int(os.getenv('RF_MAX_DEPTH', '15'))
RF_RANDOM_STATE: int    = 42
RF_N_JOBS: int          = -1   # pakai semua core CPU tersedia

# Daftar label kelas untuk Random Forest
RF_CLASSES: list[str] = [
    'normal',
    'port_scan',
    'syn_flood',
    'icmp_flood',
    'traffic_spike',
    'mqtt_anomaly',
]

# ─── Predictor Real-Time ──────────────────────────────────────────────────────
# Seberapa sering predictor poll DB untuk data traffic baru (detik)
PREDICTOR_POLL_INTERVAL: int = int(os.getenv('PREDICTOR_POLL_INTERVAL', '10'))

# Subnet IoT aktual — dipakai sebagai target_ip default pada alert ML
IOT_SUBNET: str = os.getenv('IOT_SUBNET', '192.168.10.0/24')

# Skor anomali Isolation Forest di bawah threshold ini dianggap anomali.
# Default None → pakai threshold hasil kalibrasi saat training (if_calibration.json),
# yang dihitung dari contamination (persentil) pada data normal — akurat & auto.
# Jika di-set angka, akan MENIMPA kalibrasi (untuk tuning manual).
IF_SCORE_THRESHOLD: float | None = (
    float(os.getenv('IF_SCORE_THRESHOLD'))
    if os.getenv('IF_SCORE_THRESHOLD') is not None else None
)

# Confidence alert ML: mapping dari skor anomali ke nilai confidence
IF_CONFIDENCE_BASE: float = 0.70

# ─── Logging ─────────────────────────────────────────────────────────────────
LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
