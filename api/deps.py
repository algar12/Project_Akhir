"""
deps.py — Unified Network Guard: API
======================================
Dependency injection FastAPI yang dipakai secara bersama oleh semua route.

Komponen:
  1. get_db()       — yield sesi database SQLAlchemy per-request
  2. verify_api_key — FastAPI Security dependency untuk API Key auth
  3. PaginationParams — Pydantic model reusable untuk parameter paginasi

Desain keamanan:
  - API key dibandingkan menggunakan secrets.compare_digest() untuk
    mencegah timing attack.
  - Koneksi DB dikembalikan ke pool setelah request selesai (with statement).
  - Error auth selalu mengembalikan 401 dengan pesan generik (tidak bocorkan detail).
"""

import logging
import secrets

from fastapi import Depends, HTTPException, Query, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from api.config import DATABASE_URL, API_KEY, API_KEY_HEADER, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE

logger = logging.getLogger(__name__)

# ─── Database Engine & SessionLocal ──────────────────────────────────────────
_engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=1800,
    echo=False,
)
SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)


def get_db():
    """
    Dependency: yield sesi DB per-request, tutup otomatis setelah selesai.
    Dipakai dengan Depends(get_db) di setiap route yang butuh DB.
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─── API Key Authentication ───────────────────────────────────────────────────
_api_key_scheme = APIKeyHeader(name=API_KEY_HEADER, auto_error=False)


def verify_api_key(
    key: str | None = Security(_api_key_scheme),
) -> str:
    """
    Dependency: validasi API key dari header X-API-Key.

    Menggunakan secrets.compare_digest() untuk mencegah timing attack.
    Mengembalikan key yang sudah divalidasi (untuk logging jika perlu).

    Raises:
        HTTPException 401: Jika key tidak ada atau salah.
    """
    if not key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key diperlukan. Sertakan header: X-API-Key: <key>",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Timing-safe comparison
    if not secrets.compare_digest(key.encode(), API_KEY.encode()):
        logger.warning("[Auth] API key tidak valid dari request.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key tidak valid.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return key


def verify_ws_token(token: str | None) -> bool:
    """
    Validasi token untuk WebSocket connection (via query param ?token=<key>).
    Mengembalikan True jika valid, False jika tidak.
    """
    if not token:
        return False
    return secrets.compare_digest(token.encode(), API_KEY.encode())


# ─── Pagination ───────────────────────────────────────────────────────────────
class PaginationParams:
    """
    Dependency reusable untuk parameter paginasi (limit + offset).
    Nilai limit dibatasi maksimum MAX_PAGE_SIZE agar tidak overload DB.
    """
    def __init__(
        self,
        limit: int  = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE,
                            description=f"Jumlah record per halaman (max {MAX_PAGE_SIZE})"),
        offset: int = Query(0, ge=0, description="Mulai dari record ke-N"),
    ):
        self.limit  = limit
        self.offset = offset
