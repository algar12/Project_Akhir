"""
config.py — Unified Network Guard: API
=======================================
Semua konfigurasi API dimuat dari environment variables (.env).
"""

import os
import secrets
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))


# ─── Helpers Waktu (UTC) ───────────────────────────────────────────────────────
def utc_now() -> datetime:
    """Sekarang dalam UTC, naive — konsisten dengan seluruh pipeline (DB, collector)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_naive_utc(dt: datetime | None) -> datetime | None:
    """
    Normalisasi datetime (query param API) ke naive UTC.
    - aware  → konversi ke UTC lalu buang tzinfo (cocok dibandingkan dgn kolom TIMESTAMP)
    - naive  → dianggap sudah UTC
    """
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt

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

# ─── Security ─────────────────────────────────────────────────────────────────
# API Key untuk autentikasi semua endpoint /api/v1/*
# Wajib diisi di .env — jika kosong, generate random sekali pakai (tidak aman untuk prod)
API_KEY: str = os.getenv('API_KEY', '')
if not API_KEY:
    API_KEY = secrets.token_hex(32)
    print(
        f"\n[SECURITY WARNING] API_KEY tidak diset di .env!\n"
        f"Menggunakan kunci sementara (akan berubah setiap restart):\n"
        f"  API_KEY={API_KEY}\n"
        f"Tambahkan ke file .env untuk nilai yang persisten.\n"
    )

# Nama header yang dipakai client untuk mengirim API key
API_KEY_HEADER: str = 'X-API-Key'

# ─── CORS ─────────────────────────────────────────────────────────────────────
# Origin yang diizinkan mengakses API (pisahkan dengan koma di .env)
# Contoh: "http://localhost:3001,http://192.168.20.101:3001"
# Catatan: regex middleware juga mengizinkan seluruh origin localhost/LAN privat.
_cors_raw: str  = os.getenv('CORS_ORIGINS', 'http://localhost:3001')
CORS_ORIGINS: list[str] = [o.strip() for o in _cors_raw.split(',') if o.strip()]

# ─── Rate Limiting ─────────────────────────────────────────────────────────────
# Format slowapi: "N/period" — period: second, minute, hour, day
RATE_LIMIT_DEFAULT:   str = os.getenv('RATE_LIMIT_DEFAULT',   '120/minute')
RATE_LIMIT_HEAVY:     str = os.getenv('RATE_LIMIT_HEAVY',     '30/minute')   # endpoint berat
RATE_LIMIT_WS:        str = os.getenv('RATE_LIMIT_WS',        '10/minute')   # WebSocket connect

# ─── Paginasi ─────────────────────────────────────────────────────────────────
DEFAULT_PAGE_SIZE: int = int(os.getenv('DEFAULT_PAGE_SIZE', '50'))
MAX_PAGE_SIZE:     int = int(os.getenv('MAX_PAGE_SIZE',     '500'))

# ─── API Server ───────────────────────────────────────────────────────────────
API_HOST:   str = os.getenv('API_HOST',   '0.0.0.0')
API_PORT:   int = int(os.getenv('API_PORT',   '8000'))
API_PREFIX: str = '/api/v1'

# ─── WebSocket ────────────────────────────────────────────────────────────────
# Interval (detik) polling alert baru untuk dikirim ke WebSocket client
WS_POLL_INTERVAL: float = float(os.getenv('WS_POLL_INTERVAL', '2.0'))

# ─── Logging ─────────────────────────────────────────────────────────────────
LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
