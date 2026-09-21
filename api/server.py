"""
server.py — Unified Network Guard: API
========================================
Aplikasi FastAPI utama:
  - Konfigurasi CORS whitelist + regex origin LAN privat
  - Security headers middleware
  - Rate limiting per IP (REST + WebSocket) — tanpa dependency eksternal
  - Trusted Host middleware (cegah Host header injection)
  - Router mounting semua endpoint
  - WebSocket /ws/alerts — stream alert real-time ke dashboard
  - Endpoint /api/v1/system/status — health check + statistik DB
  - Root GET / — health check publik (tanpa auth)

Cara menjalankan:
  venv/bin/uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload
  atau via:
  python -m api.server
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from api.config import (
    API_PREFIX, CORS_ORIGINS,
    WS_POLL_INTERVAL, LOG_LEVEL,
    utc_now, to_naive_utc,
)
from api.deps import get_db, verify_api_key, verify_ws_token, SessionLocal
from api.schemas import SystemStatus, MessageResponse, NetworkInfo
from api.network_info import get_network_info, suricata_is_running
from api.rate_limit import check_rate_limit, rate_limit_for_path, WS_LIMIT, WS_WINDOW
from api.routes import devices, traffic, alerts, predictions

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('api.server')


# ─── Lifespan: Startup & Shutdown ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Eksekusi saat aplikasi FastAPI mulai dan berhenti.
    Saat mulai, reset status perangkat dangling/stale ke 'offline'.
    """
    try:
        db = SessionLocal()
        # Migrasi kolom mitigated (aman dijalankan berulang — idempotent)
        db.execute(text("""
            ALTER TABLE alerts
                ADD COLUMN IF NOT EXISTS mitigated BOOLEAN NOT NULL DEFAULT false
        """))
        db.execute(text("""
            ALTER TABLE alerts
                ADD COLUMN IF NOT EXISTS mitigated_at TIMESTAMP
        """))
        db.execute(text("""
            UPDATE devices 
            SET status = 'offline' 
            WHERE status = 'online' 
              AND (last_seen IS NULL OR last_seen < (CURRENT_TIMESTAMP - INTERVAL '10 seconds'))
        """))
        db.commit()
        db.close()
        logger.info("[Startup] Status perangkat disinkronkan — node online kadaluarsa diubah ke offline.")
    except Exception as exc:
        logger.warning("[Startup] Gagal mereset status perangkat pada startup: %s", exc)
    
    yield
    logger.info("[Shutdown] API Server dimatikan.")


# ─── Aplikasi FastAPI ─────────────────────────────────────────────────────────
app = FastAPI(
    title='Unified Network Guard API',
    description=(
        '## REST API untuk Platform Monitoring Keamanan IoT\n\n'
        'Semua endpoint `/api/v1/*` membutuhkan header **`X-API-Key`**.\n\n'
        'WebSocket `/ws/alerts` membutuhkan query param **`?token=<api_key>`**.'
    ),
    version='1.0.0',
    docs_url='/docs',          # Swagger UI
    redoc_url='/redoc',        # ReDoc UI
    openapi_url='/openapi.json',
    lifespan=lifespan,
)


# ─── Middleware: CORS ─────────────────────────────────────────────────────────
# Whitelist origin localhost + seluruh subnet LAN privat (192.168.x, 10.x,
# 172.16-31.x) via regex — sehingga dashboard bisa diakses dari perangkat lain
# pada jaringan lokal tanpa perlu menebak IP di .env.
_LAN_ORIGIN_RE = (
    r'^https?://'
    r'(localhost|127\.0\.0\.1'
    r'|10\.\d+\.\d+\.\d+'
    r'|192\.168\.\d+\.\d+'
    r'|172\.(1[6-9]|2\d|3[01])\.\d+\.\d+)'
    r'(:\d+)?$'
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,          # WHITELIST — bukan '*'
    allow_origin_regex=_LAN_ORIGIN_RE,   # origin LAN privat (dinamis per jaringan)
    allow_credentials=True,
    allow_methods=['GET', 'POST', 'OPTIONS'],
    allow_headers=['X-API-Key', 'Content-Type', 'Authorization'],
    max_age=600,                         # preflight cache 10 menit
)


# ─── Middleware: Trusted Host ─────────────────────────────────────────────────
# Mencegah Host header injection. Starlette TrustedHostMiddleware tidak
# mendukung wildcard IP, jadi dipakai middleware kustom berbasis ipaddress:
# izinkan localhost + seluruh IP LAN privat (RFC1918), tolak hostname/domain lain.
import ipaddress as _ipaddr


def _host_allowed(host: str) -> bool:
    host = host.split(':')[0].strip().lower()
    if host in ('', 'localhost', '127.0.0.1', '::1'):
        return True
    if host.endswith('.local'):
        return True
    try:
        ip = _ipaddr.ip_address(host)
        return bool(ip.is_private or ip.is_loopback or ip.is_link_local)
    except ValueError:
        return False  # hostname tak dikenal → tolak


@app.middleware('http')
async def trusted_host_middleware(request: Request, call_next):
    host = request.headers.get('host', '')
    if not _host_allowed(host):
        return JSONResponse(status_code=400, content={'detail': 'Host tidak diizinkan.'})
    return await call_next(request)


# ─── Middleware: Rate Limiting (REST) ─────────────────────────────────────────
@app.middleware('http')
async def rate_limit_middleware(request: Request, call_next):
    """Terapkan batas request per IP untuk endpoint /api/v1/*."""
    if request.url.path.startswith('/api/v1'):
        client_ip = request.client.host if request.client else 'unknown'
        limit, window = rate_limit_for_path(request.url.path)
        if not check_rate_limit(f'{client_ip}:{request.url.path}', limit, window):
            return JSONResponse(
                status_code=429,
                content={
                    'detail': 'Terlalu banyak permintaan. Coba lagi nanti.',
                    'retry_after': int(window),
                },
            )
    return await call_next(request)


# ─── Middleware: Secure HTTP Headers ─────────────────────────────────────────
@app.middleware('http')
async def add_security_headers(request: Request, call_next):
    """
    Tambahkan security headers ke setiap response.
    Headers ini penting meski API-only (konsumsi dari dashboard/browser).
    """
    response: Response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options']        = 'DENY'
    response.headers['X-XSS-Protection']       = '1; mode=block'
    response.headers['Referrer-Policy']         = 'strict-origin-when-cross-origin'
    response.headers['Cache-Control']           = 'no-store'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    # Hapus header yang membocorkan info server
    if 'Server' in response.headers:
        del response.headers['Server']
    return response


# ─── Middleware: Request Logging ──────────────────────────────────────────────
@app.middleware('http')
async def log_requests(request: Request, call_next):
    """Log setiap request: method, path, client IP, status code."""
    client_ip = request.client.host if request.client else 'unknown'
    response  = await call_next(request)
    logger.info(
        '%s %s %s → %d',
        client_ip, request.method, request.url.path, response.status_code,
    )
    return response


# ─── Global Exception Handler ─────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Tangkap semua exception yang tidak terduga.
    Kembalikan 500 generik — TIDAK bocorkan stack trace ke client.
    """
    logger.error('Unhandled exception pada %s %s: %s',
                 request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={'detail': 'Internal server error. Periksa log server.'},
    )


# ─── Router Mounting ──────────────────────────────────────────────────────────
app.include_router(devices.router,     prefix=API_PREFIX)
app.include_router(traffic.router,     prefix=API_PREFIX)
app.include_router(alerts.router,      prefix=API_PREFIX)
app.include_router(predictions.router, prefix=API_PREFIX)


# ─── Root: Health Check Publik ────────────────────────────────────────────────
@app.get(
    '/',
    response_model=MessageResponse,
    tags=['Health'],
    summary='Health check publik (tanpa auth)',
)
def root():
    """Endpoint publik untuk cek apakah API server berjalan."""
    return MessageResponse(
        message='Unified Network Guard API v1.0.0 — aktif.',
        success=True,
    )


# ─── System Status ────────────────────────────────────────────────────────────
@app.get(
    f'{API_PREFIX}/system/status',
    response_model=SystemStatus,
    tags=['System'],
    summary='Status sistem dan statistik database',
)
def system_status(
    _: str = Depends(verify_api_key),
):
    """
    Mengembalikan statistik keseluruhan sistem:
    jumlah device, alert, traffic record, dan anomali.
    """
    db = SessionLocal()
    try:
        def count(table: str, where: str = '') -> int:
            sql = text(f"SELECT COUNT(*) FROM {table} {where}")
            return db.execute(sql).scalar_one()

        return SystemStatus(
            timestamp=utc_now(),
            database='connected',
            total_devices=count('devices'),
            total_alerts=count('alerts'),
            total_traffic=count('network_traffic'),
            total_anomalies=count('ml_predictions', 'WHERE is_anomaly = TRUE'),
            suricata_online=suricata_is_running(),
        )
    except Exception as exc:
        logger.error('[Status] DB error: %s', exc)
        return SystemStatus(
            timestamp=utc_now(),
            database='error',
            total_devices=0,
            total_alerts=0,
            total_traffic=0,
            total_anomalies=0,
            suricata_online=suricata_is_running(),
        )
    finally:
        db.close()


# ─── System Network (dinamis) ─────────────────────────────────────────────────
@app.get(
    f'{API_PREFIX}/system/network',
    response_model=NetworkInfo,
    tags=['System'],
    summary='Informasi jaringan yang sedang tersambung (dinamis)',
)
def system_network(
    _: str = Depends(verify_api_key),
):
    """
    Mengembalikan informasi jaringan aktif saat ini:
    interface, subnet, IP lokal (edge), dan gateway.
    Berubah otomatis mengikuti jaringan yang tersambung (WiFi/LAN).
    """
    return NetworkInfo(**get_network_info())


# ─── WebSocket: Real-Time Alert Stream ────────────────────────────────────────
class ConnectionManager:
    """
    Mengelola daftar koneksi WebSocket aktif.
    Thread-safe untuk penggunaan dengan asyncio event loop.
    """
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.active.append(ws)
        logger.info('[WS] Client terhubung. Total: %d', len(self.active))

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self.active:
            self.active.remove(ws)
        logger.info('[WS] Client terputus. Total: %d', len(self.active))

    async def broadcast(self, data: dict) -> None:
        """Kirim pesan ke semua client aktif. Hapus yang sudah disconnect."""
        dead: list[WebSocket] = []
        for ws in self.active:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


_ws_manager = ConnectionManager()


@app.websocket('/ws/alerts')
async def ws_alert_stream(websocket: WebSocket, token: str | None = None):
    """
    WebSocket endpoint: stream alert baru ke dashboard secara real-time.

    Auth: query param ?token=<api_key>
    Rate limit: RATE_LIMIT_WS (10/menit) per IP — cegah koneksi spam.
    Polling DB setiap WS_POLL_INTERVAL detik, kirim alert baru ke semua client.

    Setiap koneksi memakai checkpoint ID sendiri (per-connection `last_id`),
    sehingga client yang baru connect mendapat alert dari posisinya sendiri
    dan antar-client tidak saling menimpa posisi.
    """
    # ── Rate limit connect (per IP) ───────────────────────────────────────────
    client_ip = websocket.client[0] if websocket.client else 'unknown'
    if not check_rate_limit(f'ws:{client_ip}', WS_LIMIT, WS_WINDOW):
        await websocket.close(
            code=1008, reason='Rate limit tercapai. Coba lagi nanti.'
        )
        logger.warning('[WS] Rate limit koneksi terlampaui dari %s', client_ip)
        return

    # ── Autentikasi ───────────────────────────────────────────────────────────
    if not verify_ws_token(token):
        await websocket.close(code=4001, reason='Unauthorized: token tidak valid.')
        logger.warning('[WS] Koneksi ditolak — token tidak valid.')
        return

    await _ws_manager.connect(websocket)

    # Kirim pesan selamat datang (timestamp UTC aware → +00:00)
    await websocket.send_json({
        'event':   'connected',
        'message': 'Unified Network Guard — Alert Stream aktif.',
        'timestamp': datetime.now(timezone.utc).isoformat(),
    })

    db = SessionLocal()
    # Checkpoint per-koneksi: mulai dari alert terbaru saat koneksi dibuka
    last_id = 0
    try:
        row = db.execute(text("SELECT COALESCE(MAX(id), 0) FROM alerts")).scalar_one()
        last_id = int(row or 0)

        while True:
            # Cek alert baru sejak last_id (per-koneksi)
            sql = text("""
                SELECT id, timestamp, source_ip, target_ip,
                       attack_type, severity, confidence, description
                FROM alerts
                WHERE id > :last_id
                ORDER BY id ASC
                LIMIT 20
            """)
            new_alerts = db.execute(sql, {'last_id': last_id}).mappings().all()

            if new_alerts:
                for row in new_alerts:
                    payload = {
                        'event':      'new_alert',
                        'id':         row['id'],
                        # DB menyimpan naive UTC → beri suffix agar JS parse sebagai UTC
                        'timestamp':  row['timestamp'].isoformat() + '+00:00',
                        'source_ip':  row['source_ip'],
                        'target_ip':  row['target_ip'],
                        'attack_type': row['attack_type'],
                        'severity':   row['severity'],
                        'confidence': float(row['confidence']),
                        'description': row['description'] or '',
                    }
                    await _ws_manager.broadcast(payload)
                last_id = new_alerts[-1]['id']

            # Lepas transaksi (SELECT membuka transaksi implicit) agar tidak
            # menahan lock tabel alerts dan memblokir ALTER/migrasi lain.
            db.rollback()

            # Heartbeat setiap iterasi
            try:
                await websocket.send_json({
                    'event': 'heartbeat',
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                })
            except WebSocketDisconnect:
                break

            await asyncio.sleep(WS_POLL_INTERVAL)

    except WebSocketDisconnect:
        logger.info('[WS] Client disconnect secara normal.')
    except Exception as exc:
        logger.error('[WS] Error: %s', exc)
    finally:
        _ws_manager.disconnect(websocket)
        db.close()


# ─── Entry Point ──────────────────────────────────────────────────────────────
if __name__ == '__main__':
    import uvicorn
    from api.config import API_HOST, API_PORT
    uvicorn.run(
        'api.server:app',
        host=API_HOST,
        port=API_PORT,
        reload=False,
        log_level=LOG_LEVEL.lower(),
        access_log=True,
    )
