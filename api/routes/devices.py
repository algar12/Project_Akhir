"""
routes/devices.py — Unified Network Guard: API
================================================
Endpoint untuk manajemen perangkat IoT yang terdaftar.

GET /api/v1/devices           — list semua device
GET /api/v1/devices/{id}      — detail satu device
GET /api/v1/devices/{id}/telemetry — telemetri terbaru device
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.deps import get_db, verify_api_key, PaginationParams
from api.schemas import DeviceOut, DeviceListResponse, TelemetryOut, TelemetryListResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/devices', tags=['Devices'])


from datetime import datetime, timezone

# ─── List Devices ─────────────────────────────────────────────────────────────
@router.get(
    '',
    response_model=DeviceListResponse,
    summary='List semua perangkat IoT',
    description='Mengembalikan daftar perangkat IoT yang terdaftar beserta status terakhir.',
)
def list_devices(
    status_filter: Optional[str] = Query(
        None, alias='status', pattern=r'^(online|offline|registered)$',
        description='Filter by status: online/offline/registered',
    ),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    # Auto-offline timeout: jika perangkat online tidak kirim heartbeat dalam 10 detik, tandai offline
    try:
        auto_offline_sql = text("""
            UPDATE devices
            SET status = 'offline'
            WHERE status = 'online'
              AND (last_seen IS NULL OR last_seen < (CURRENT_TIMESTAMP - INTERVAL '10 seconds'))
        """)
        db.execute(auto_offline_sql)
        db.commit()
    except Exception as e:
        logger.warning(f"Failed to auto-update offline devices: {e}")

    # Count query
    count_sql = text("""
        SELECT COUNT(*) FROM devices
        WHERE (:status IS NULL OR status = :status)
    """)
    total = db.execute(count_sql, {'status': status_filter}).scalar_one()

    # Data query
    data_sql = text("""
        SELECT id, device_name, ip_address, mac_address,
               device_type, status, last_seen
        FROM devices
        WHERE (:status IS NULL OR status = :status)
        ORDER BY device_name ASC
        LIMIT :limit OFFSET :offset
    """)
    rows = db.execute(data_sql, {
        'status': status_filter,
        'limit':  pagination.limit,
        'offset': pagination.offset,
    }).mappings().all()

    now_utc = datetime.now(timezone.utc)
    devices_out = []
    for r in rows:
        d = dict(r)
        if d.get('status') == 'online':
            ls = d.get('last_seen')
            if not ls:
                d['status'] = 'offline'
            else:
                ls_utc = ls if ls.tzinfo else ls.replace(tzinfo=timezone.utc)
                if (now_utc - ls_utc).total_seconds() > 10:
                    d['status'] = 'offline'
        devices_out.append(DeviceOut(**d))

    return DeviceListResponse(
        total=total,
        devices=devices_out,
    )


@router.get(
    '/{device_id}',
    response_model=DeviceOut,
    summary='Detail satu perangkat IoT',
)
def get_device(
    device_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    sql = text("""
        SELECT id, device_name, ip_address, mac_address,
               device_type, status, last_seen
        FROM devices WHERE id = :id
    """)
    row = db.execute(sql, {'id': device_id}).mappings().first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device dengan id={device_id} tidak ditemukan.",
        )
    d = dict(row)
    if d.get('status') == 'online':
        ls = d.get('last_seen')
        if not ls:
            d['status'] = 'offline'
        else:
            ls_utc = ls if ls.tzinfo else ls.replace(tzinfo=timezone.utc)
            if (datetime.now(timezone.utc) - ls_utc).total_seconds() > 10:
                d['status'] = 'offline'
    return DeviceOut(**d)


@router.get(
    '/{device_id}/telemetry',
    response_model=TelemetryListResponse,
    summary='Telemetri terbaru dari satu device',
)
def get_device_telemetry(
    device_id: int,
    limit: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    # Cari device_name dulu untuk query MQTT
    dev_sql = text("SELECT device_name FROM devices WHERE id = :id")
    dev_row = db.execute(dev_sql, {'id': device_id}).mappings().first()
    if not dev_row:
        raise HTTPException(status_code=404, detail="Device tidak ditemukan.")

    device_name = dev_row['device_name']

    sql = text("""
        SELECT id, timestamp, device_id, topic, payload, source_ip
        FROM mqtt_telemetry
        WHERE device_id = :device_id
        ORDER BY timestamp DESC
        LIMIT :limit
    """)
    rows = db.execute(sql, {'device_id': device_name, 'limit': limit}).mappings().all()
    count_sql = text("SELECT COUNT(*) FROM mqtt_telemetry WHERE device_id = :d")
    total = db.execute(count_sql, {'d': device_name}).scalar_one()

    return TelemetryListResponse(
        device_id=device_name,
        total=total,
        items=[TelemetryOut(**dict(r)) for r in rows],
    )
