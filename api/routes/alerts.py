"""
routes/alerts.py — Unified Network Guard: API
-----------------------------------------------
Endpoint data alert keamanan.

GET /api/v1/alerts         — list alert (paginated + filter)
GET /api/v1/alerts/stats   — statistik agregat alert
GET /api/v1/alerts/{id}    — detail satu alert
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.config import utc_now, to_naive_utc
from api.deps import get_db, verify_api_key, PaginationParams
from api.schemas import AlertOut, AlertListResponse, AlertStats

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/alerts', tags=['Security Alerts'])


@router.get(
    '',
    response_model=AlertListResponse,
    summary='List alert keamanan',
    description='Mengembalikan alert keamanan yang dihasilkan rule engine, Suricata, atau ML.',
)
def list_alerts(
    severity: Optional[str] = Query(
        None,
        pattern=r'^(LOW|MEDIUM|HIGH|CRITICAL)$',
        description="Filter by severity (case-sensitive)",
    ),
    attack_type: Optional[str] = Query(
        None, max_length=100,
        description="Filter by attack type (substring match, case-insensitive)",
    ),
    source_ip: Optional[str] = Query(None, description="Filter by source IP"),
    since: Optional[datetime] = Query(None),
    until: Optional[datetime] = Query(None),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    _:  str     = Depends(verify_api_key),
) -> AlertListResponse:
    # Default: 24 jam terakhir (UTC naive)
    if since is None and until is None:
        until = utc_now()
        since = until - timedelta(hours=24)
    since = to_naive_utc(since)
    until = to_naive_utc(until)

    # Sanitasi attack_type: hapus karakter non-alphanumeric kecuali _-
    if attack_type:
        import re
        attack_type = re.sub(r'[^\w\-\s]', '', attack_type)

    params = {
        'sev':   severity,
        'atype': f'%{attack_type}%' if attack_type else None,
        'src':   source_ip,
        'since': since,
        'until': until,
        'limit': pagination.limit,
        'off':   pagination.offset,
    }

    count_sql = text("""
        SELECT COUNT(*) FROM alerts
        WHERE (:sev   IS NULL OR severity    = :sev)
          AND (:atype IS NULL OR UPPER(attack_type) LIKE UPPER(:atype))
          AND (:src   IS NULL OR source_ip   = :src)
          AND (:since IS NULL OR timestamp  >= :since)
          AND (:until IS NULL OR timestamp   < :until)
    """)
    total = db.execute(count_sql, params).scalar_one()

    data_sql = text("""
        SELECT id, timestamp, source_ip, target_ip,
               attack_type, severity, confidence, description,
               mitigated, mitigated_at
        FROM alerts
        WHERE (:sev   IS NULL OR severity    = :sev)
          AND (:atype IS NULL OR UPPER(attack_type) LIKE UPPER(:atype))
          AND (:src   IS NULL OR source_ip   = :src)
          AND (:since IS NULL OR timestamp  >= :since)
          AND (:until IS NULL OR timestamp   < :until)
        ORDER BY timestamp DESC
        LIMIT :limit OFFSET :off
    """)
    rows = db.execute(data_sql, params).mappings().all()

    return AlertListResponse(
        total=total,
        alerts=[AlertOut(**dict(r)) for r in rows],
    )


@router.get(
    '/stats',
    response_model=AlertStats,
    summary='Statistik agregat alert',
    description='Menghitung distribusi alert per severity dan tipe serangan dalam period tertentu.',
)
def alert_stats(
    hours: int = Query(
        24, ge=1, le=720,
        description="Periode analisis dalam jam (1–720)",
    ),
    db: Session = Depends(get_db),
    _:  str     = Depends(verify_api_key),
) -> AlertStats:
    since = utc_now() - timedelta(hours=hours)

    total_sql = text(
        "SELECT COUNT(*) FROM alerts WHERE timestamp >= :since"
    )
    total = db.execute(total_sql, {'since': since}).scalar_one()

    sev_sql = text("""
        SELECT severity, COUNT(*) AS cnt
        FROM alerts WHERE timestamp >= :since
        GROUP BY severity ORDER BY cnt DESC
    """)
    by_sev = {r['severity']: r['cnt']
              for r in db.execute(sev_sql, {'since': since}).mappings()}

    type_sql = text("""
        SELECT attack_type, COUNT(*) AS cnt
        FROM alerts WHERE timestamp >= :since
        GROUP BY attack_type ORDER BY cnt DESC LIMIT 10
    """)
    by_type = {r['attack_type']: r['cnt']
               for r in db.execute(type_sql, {'since': since}).mappings()}

    src_sql = text("""
        SELECT source_ip, COUNT(*) AS cnt
        FROM alerts WHERE timestamp >= :since
        GROUP BY source_ip ORDER BY cnt DESC LIMIT 5
    """)
    top_sources = [
        {'source_ip': r['source_ip'], 'count': r['cnt']}
        for r in db.execute(src_sql, {'since': since}).mappings()
    ]

    return AlertStats(
        total_alerts=total,
        by_severity=by_sev,
        by_attack_type=by_type,
        most_active_sources=top_sources,
        period_hours=hours,
    )


@router.get(
    '/{alert_id}',
    response_model=AlertOut,
    summary='Detail satu alert',
)
def get_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    _:  str     = Depends(verify_api_key),
) -> AlertOut:
    sql = text("""
        SELECT id, timestamp, source_ip, target_ip,
               attack_type, severity, confidence, description,
               mitigated, mitigated_at
        FROM alerts WHERE id = :id
    """)
    row = db.execute(sql, {'id': alert_id}).mappings().first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert dengan id={alert_id} tidak ditemukan.",
        )
    return AlertOut(**dict(row))


@router.post(
    '/{alert_id}/mitigate',
    response_model=AlertOut,
    summary='Tandai alert sebagai mitigated',
    description=(
        'Menandai alert sebagai telah ditangani (mitigated). '
        'Menyimpan mitigated=true + mitigated_at (UTC). Idempotent.'
    ),
)
def mitigate_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    _:  str     = Depends(verify_api_key),
) -> AlertOut:
    # Cek keberadaan alert
    exists = db.execute(
        text("SELECT id FROM alerts WHERE id = :id"),
        {'id': alert_id},
    ).scalar_one_or_none()
    if exists is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert dengan id={alert_id} tidak ditemukan.",
        )

    db.execute(text("""
        UPDATE alerts
        SET mitigated = TRUE, mitigated_at = :now
        WHERE id = :id
    """), {'id': alert_id, 'now': utc_now()})
    db.commit()

    row = db.execute(text("""
        SELECT id, timestamp, source_ip, target_ip,
               attack_type, severity, confidence, description,
               mitigated, mitigated_at
        FROM alerts WHERE id = :id
    """), {'id': alert_id}).mappings().first()
    return AlertOut(**dict(row))
