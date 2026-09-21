"""
db.py — Unified Network Guard: Collector
==========================================
Layer database menggunakan SQLAlchemy Core (non-ORM) untuk insert data
traffic jaringan, telemetri MQTT, dan alert.

Alasan SQLAlchemy Core vs ORM:
  - Kita hanya butuh INSERT massal yang cepat (batch insert).
  - Tidak perlu fitur ORM penuh seperti lazy-load atau relationship.
  - Lebih ringan dan straightforward untuk use-case ini.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import QueuePool

from collector.config import DATABASE_URL

logger = logging.getLogger(__name__)

# ─── Engine (singleton, dibuat sekali saat module di-import) ──────────────────
_engine = None


def get_engine():
    """Mengembalikan SQLAlchemy engine (singleton)."""
    global _engine
    if _engine is None:
        _engine = create_engine(
            DATABASE_URL,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,      # cek koneksi hidup sebelum dipakai
            pool_recycle=1800,       # daur ulang koneksi tiap 30 menit
            echo=False,
        )
        logger.info("[DB] Engine PostgreSQL berhasil dibuat → %s", DATABASE_URL)
    return _engine


# ─── DDL: Pastikan kolom tambahan ada (idempotent) ───────────────────────────
def ensure_schema() -> None:
    """
    Menambahkan kolom telemetri ke tabel jika belum ada.
    Aman dijalankan berulang kali (idempotent).
    """
    engine = get_engine()
    stmts = [
        # Tabel telemetri MQTT (jika belum dibuat via schema.sql)
        """
        CREATE TABLE IF NOT EXISTS mqtt_telemetry (
            id            SERIAL PRIMARY KEY,
            timestamp     TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
            device_id     VARCHAR(50) NOT NULL,
            topic         VARCHAR(200) NOT NULL,
            payload       JSONB,
            source_ip     VARCHAR(45)
        );
        """,
        # Kolom is_syn — penanda paket TCP SYN murni (untuk deteksi SYN flood akurat)
        """
        ALTER TABLE network_traffic
            ADD COLUMN IF NOT EXISTS is_syn BOOLEAN NOT NULL DEFAULT false;
        """,
        # Kolom icmp_type — tipe ICMP (echo request = 8, echo reply = 0)
        # agar rule ICMP_FLOOD hanya menghitung echo request dari penyerang.
        """
        ALTER TABLE network_traffic
            ADD COLUMN IF NOT EXISTS icmp_type INTEGER;
        """,
        # Index untuk mempercepat query time-series per device
        """
        CREATE INDEX IF NOT EXISTS idx_telemetry_device_time
            ON mqtt_telemetry (device_id, timestamp DESC);
        """,
        # Index untuk query traffic per waktu
        """
        CREATE INDEX IF NOT EXISTS idx_traffic_timestamp
            ON network_traffic (timestamp DESC);
        """,
    ]
    with engine.connect() as conn:
        for stmt in stmts:
            conn.execute(text(stmt))
        conn.commit()
    logger.info("[DB] Skema database siap.")


# ─── Insert: Network Traffic ──────────────────────────────────────────────────
def insert_traffic_batch(records: list[dict[str, Any]]) -> int:
    """
    Menyimpan sekumpulan record traffic jaringan ke tabel network_traffic.

    Args:
        records: List dict dengan key:
                 source_ip, destination_ip, protocol,
                 source_port, destination_port, packet_count, bytes, timestamp

    Returns:
        Jumlah record yang berhasil di-insert.
    """
    if not records:
        return 0

    sql = text("""
        INSERT INTO network_traffic
            (timestamp, source_ip, destination_ip, protocol,
             source_port, destination_port, packet_count, bytes, is_syn, icmp_type)
        VALUES
            (:timestamp, :source_ip, :destination_ip, :protocol,
             :source_port, :destination_port, :packet_count, :bytes, :is_syn, :icmp_type)
    """)

    try:
        engine = get_engine()
        with engine.connect() as conn:
            # is_syn/icmp_type opsional di record lama → default False/None
            for rec in records:
                rec.setdefault('is_syn', False)
                rec.setdefault('icmp_type', None)
            conn.execute(sql, records)
            conn.commit()
        logger.debug("[DB] Traffic batch insert: %d record.", len(records))
        return len(records)
    except SQLAlchemyError as exc:
        logger.error("[DB] Gagal insert traffic batch: %s", exc)
        return 0


# ─── Insert: MQTT Telemetry ───────────────────────────────────────────────────
def insert_telemetry(
    device_id: str,
    topic: str,
    payload: dict[str, Any],
    source_ip: str | None = None,
    timestamp: datetime | None = None,
) -> bool:
    """
    Menyimpan satu record telemetri MQTT ke tabel mqtt_telemetry.

    Args:
        device_id  : ID perangkat (misal 'ESP32-01')
        topic      : MQTT topic asal pesan
        payload    : Dict berisi data sensor (akan disimpan sebagai JSONB)
        source_ip  : IP perangkat pengirim (opsional)
        timestamp  : Waktu pesan diterima (default: sekarang)

    Returns:
        True jika berhasil, False jika gagal.
    """
    import json

    sql = text("""
        INSERT INTO mqtt_telemetry (timestamp, device_id, topic, payload, source_ip)
        VALUES (:timestamp, :device_id, :topic, :payload, :source_ip)
    """)

    params = {
        'timestamp': timestamp or datetime.now(timezone.utc).replace(tzinfo=None),
        'device_id': device_id,
        'topic':     topic,
        'payload':   json.dumps(payload),
        'source_ip': source_ip,
    }

    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(sql, params)
            conn.commit()
        return True
    except SQLAlchemyError as exc:
        logger.error("[DB] Gagal insert telemetri [%s]: %s", device_id, exc)
        return False


# ─── Update: Status Device ───────────────────────────────────────────────────
def update_device_status(identifier: str, status: str = 'online') -> None:
    """
    Memperbarui status dan last_seen perangkat di tabel devices.
    Jika perangkat belum terdaftar → auto-register (upsert) agar device
    baru yang mengirim telemetri tetap muncul di dashboard.

    Args:
        identifier : IP perangkat atau device_name yang akan diperbarui
        status     : 'online' | 'offline'
    """
    upd = text("""
        UPDATE devices
        SET status    = :status,
            last_seen = CURRENT_TIMESTAMP
        WHERE ip_address = :val OR UPPER(device_name) = UPPER(:val)
    """)
    try:
        engine = get_engine()
        with engine.connect() as conn:
            res = conn.execute(upd, {'status': status, 'val': identifier})

            # Auto-register: device baru (belum ada baris yang ter-update)
            if res.rowcount == 0:
                _looks_ip = (
                    identifier and len(identifier.split('.')) == 4
                    and all(p.isdigit() for p in identifier.split('.'))
                )
                if _looks_ip:
                    ip_col, name_col = identifier, f"Device-{identifier}"
                else:
                    ip_col, name_col = '0.0.0.0', identifier
                conn.execute(text("""
                    INSERT INTO devices (device_name, ip_address, device_type, status, last_seen)
                    VALUES (:name, :ip, 'auto', :status, CURRENT_TIMESTAMP)
                    ON CONFLICT (ip_address) DO UPDATE
                        SET status = :status, last_seen = CURRENT_TIMESTAMP
                """), {'name': name_col, 'ip': ip_col, 'status': status})
            conn.commit()
    except SQLAlchemyError as exc:
        logger.error("[DB] Gagal update status device [%s]: %s", identifier, exc)
