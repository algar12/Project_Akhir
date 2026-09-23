"""
config.py — Unified Network Guard: Collector
=============================================
Membaca konfigurasi dari environment variables (.env).
Semua pengaturan terpusat di sini sehingga mudah diubah tanpa
menyentuh kode logika.
"""

import os
from dotenv import load_dotenv

# Muat file .env dari root project (dua level di atas collector/)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))


# ─── Jaringan & Interface ─────────────────────────────────────────────────────
CAPTURE_INTERFACE: str = os.getenv('CAPTURE_INTERFACE', 'eth0')
IOT_SUBNET: str        = os.getenv('IOT_SUBNET', '192.168.20.0/24')
GATEWAY_IP: str        = os.getenv('GATEWAY_IP', '192.168.20.1')

# BPF filter untuk Scapy — tangkap paket dari/ke subnet IoT.
# Prefix diambil dari IOT_SUBNET apa adanya (bukan hardcode /24).
# Contoh: IOT_SUBNET=192.168.20.0/24 → "net 192.168.20.0/24".
CAPTURE_BPF_FILTER: str = f"net {IOT_SUBNET}"


# ─── MQTT Broker ─────────────────────────────────────────────────────────────
MQTT_BROKER_HOST: str = os.getenv('MQTT_BROKER_HOST', 'localhost')
MQTT_BROKER_PORT: int = int(os.getenv('MQTT_BROKER_PORT', '1883'))

# Topic wildcard, contoh: "iot/#" akan subscribe semua sub-topic di bawah "iot/"
MQTT_TOPIC_BASE: str  = os.getenv('MQTT_TOPIC_BASE', 'iot/#')
MQTT_CLIENT_ID: str   = 'ung-collector-mqtt'
MQTT_KEEPALIVE: int   = 60
MQTT_RECONNECT_DELAY: int = 5  # detik sebelum coba reconnect


# ─── Database PostgreSQL ──────────────────────────────────────────────────────
DB_HOST: str     = os.getenv('DB_HOST', 'localhost')
DB_PORT: int     = int(os.getenv('DB_PORT', '5432'))
DB_NAME: str     = os.getenv('DB_NAME', 'network_guard')
DB_USER: str     = os.getenv('DB_USER', 'guard_user')
DB_PASSWORD: str = os.getenv('DB_PASSWORD', 'guard_secret')

# Connection string SQLAlchemy
DATABASE_URL: str = (
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)


# ─── Sniffer ─────────────────────────────────────────────────────────────────
# Jumlah paket yang di-buffer sebelum di-flush ke database sekaligus (batch insert)
TRAFFIC_BATCH_SIZE: int  = int(os.getenv('TRAFFIC_BATCH_SIZE', '50'))
TRAFFIC_FLUSH_INTERVAL: int = int(os.getenv('TRAFFIC_FLUSH_INTERVAL', '5'))   # detik


# ─── Logging ─────────────────────────────────────────────────────────────────
LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
