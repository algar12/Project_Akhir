"""
rate_limit.py — Unified Network Guard: API
============================================
Rate limiting sederhana berbasis sliding window (in-memory, per IP).

Diimplementasikan sendiri (tanpa dependency eksternal) agar klaim keamanan
pada dokumentasi benar-benar berfungsi:
  - REST /api/v1/*  → RATE_LIMIT_DEFAULT (120/menit) per IP
  - Endpoint berat  → RATE_LIMIT_HEAVY   (30/menit) per IP
  - WebSocket       → RATE_LIMIT_WS      (10/menit) per IP (handshake connect)

Catatan: bersifat best-effort in-process; untuk multi-worker gunakan
store terdistribusi (mis. Redis).
"""

import logging
import time
from collections import defaultdict, deque
from typing import Callable, Optional

from api.config import (
    RATE_LIMIT_DEFAULT,
    RATE_LIMIT_HEAVY,
    RATE_LIMIT_WS,
)

logger = logging.getLogger(__name__)

# key -> deque(timestamps) — batasi per (ip:group) agar adil antar endpoint
_buckets: dict[str, deque[float]] = defaultdict(deque)


def _parse_limit(spec: str) -> tuple[int, float]:
    """Parse 'N/minute' → (N, window detik). Default 120/60 jika gagal."""
    try:
        count_str, period = spec.strip().lower().split('/')
        count = max(int(count_str), 1)
        window = {
            'second': 1.0, 'minute': 60.0, 'hour': 3600.0, 'day': 86400.0,
        }.get(period, 60.0)
        return count, window
    except Exception:  # noqa: BLE001
        return 120, 60.0


DEFAULT_LIMIT, DEFAULT_WINDOW = _parse_limit(RATE_LIMIT_DEFAULT)
HEAVY_LIMIT,  HEAVY_WINDOW  = _parse_limit(RATE_LIMIT_HEAVY)
WS_LIMIT,     WS_WINDOW     = _parse_limit(RATE_LIMIT_WS)


def _bucket(key: str) -> deque[float]:
    return _buckets[key]


def check_rate_limit(key: str, limit: int, window: float = 60.0) -> bool:
    """
    Return True jika request masih dalam batas; False jika harus ditolak (429).
    """
    now = time.monotonic()
    dq = _bucket(key)

    # Evict entry kedaluwarsa
    while dq and dq[0] < now - window:
        dq.popleft()

    if len(dq) >= limit:
        logger.warning("[RateLimit] %s terlampaui (%d/%d)", key, len(dq), limit)
        return False

    dq.append(now)
    return True


def reset() -> None:
    """Hapus semua bucket (berguna saat unit test)."""
    _buckets.clear()


def is_heavy_path(path: str) -> bool:
    """Endpoint berat: agregasi/statistik yang memakan resource."""
    heavy_markers = ('/summary', '/stats', '/anomalies')
    return any(m in path for m in heavy_markers)


def rate_limit_for_path(path: str) -> tuple[int, float]:
    """(limit, window) untuk path tertentu."""
    if is_heavy_path(path):
        return HEAVY_LIMIT, HEAVY_WINDOW
    return DEFAULT_LIMIT, DEFAULT_WINDOW