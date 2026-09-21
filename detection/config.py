"""
config.py — Unified Network Guard: Detection
=============================================
Membaca semua konfigurasi modul detection dari environment variables (.env).
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

# ─── Jaringan ─────────────────────────────────────────────────────────────────
IOT_SUBNET: str  = os.getenv('IOT_SUBNET', '192.168.10.0/24')
GATEWAY_IP: str  = os.getenv('GATEWAY_IP', '192.168.10.1')

# ─── Suricata ─────────────────────────────────────────────────────────────────
SURICATA_EVE_PATH: str = os.getenv(
    'SURICATA_EVE_PATH', '/var/log/suricata/eve.json'
)
# Interval (detik) pemeriksaan file EVE ketika tidak ada baris baru
EVE_POLL_INTERVAL: float = float(os.getenv('EVE_POLL_INTERVAL', '1.0'))

# ─── Rule Engine — Threshold ──────────────────────────────────────────────────
# Jumlah paket SYN dalam window waktu yang memicu alert Port Scan
PORTSCAN_PKT_THRESHOLD: int    = int(os.getenv('PORTSCAN_PKT_THRESHOLD', '20'))
PORTSCAN_WINDOW_SECONDS: int   = int(os.getenv('PORTSCAN_WINDOW_SECONDS', '5'))

# SYN Flood: pkt SYN masuk ke satu tujuan
SYNFLOOD_PKT_THRESHOLD: int    = int(os.getenv('SYNFLOOD_PKT_THRESHOLD', '100'))
SYNFLOOD_WINDOW_SECONDS: int   = int(os.getenv('SYNFLOOD_WINDOW_SECONDS', '2'))

# ICMP Ping Flood
ICMPFLOOD_PKT_THRESHOLD: int   = int(os.getenv('ICMPFLOOD_PKT_THRESHOLD', '50'))
ICMPFLOOD_WINDOW_SECONDS: int  = int(os.getenv('ICMPFLOOD_WINDOW_SECONDS', '3'))

# Traffic Spike umum (bytes/detik per source)
TRAFFIC_SPIKE_BPS: int         = int(os.getenv('TRAFFIC_SPIKE_BPS', '5000000'))   # 5 MB/window (≈1 MB/s)
TRAFFIC_SPIKE_WINDOW: int      = int(os.getenv('TRAFFIC_SPIKE_WINDOW', '5'))

# MQTT: jumlah pesan masuk cepat dari satu client dalam 1 detik
MQTT_RATE_THRESHOLD: int       = int(os.getenv('MQTT_RATE_THRESHOLD', '30'))
MQTT_RATE_WINDOW: int          = int(os.getenv('MQTT_RATE_WINDOW', '1'))

# ─── Alert Manager ────────────────────────────────────────────────────────────
# Durasi supression: alert duplikat dari IP + jenis yang sama dalam window ini
# tidak akan di-insert ulang ke DB
ALERT_SUPPRESS_SECONDS: int    = int(os.getenv('ALERT_SUPPRESS_SECONDS', '30'))

# ─── Logging ─────────────────────────────────────────────────────────────────
LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
