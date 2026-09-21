"""
routes/predictions.py — Unified Network Guard: API
-----------------------------------------------------
Endpoint hasil prediksi ML (Isolation Forest).

GET /api/v1/predictions              — list semua prediksi
GET /api/v1/predictions/anomalies    — hanya anomali
GET /api/v1/predictions/stats        — statistik anomali
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.config import utc_now, to_naive_utc
from api.deps import get_db, verify_api_key, PaginationParams
from api.schemas import PredictionOut, PredictionListResponse, AnomalyStats

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/predictions', tags=['ML Predictions'])


@router.get(
    '',
    response_model=PredictionListResponse,
    summary='List hasil prediksi ML',
)
def list_predictions(
    source_ip:  Optional[str] = Query(None),
    is_anomaly: Optional[bool] = Query(None, description="True = hanya anomali"),
    since: Optional[datetime]  = Query(None),
    until: Optional[datetime]  = Query(None),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    _:  str     = Depends(verify_api_key),
) -> PredictionListResponse:
    if since is None and until is None:
        until = utc_now()
        since = until - timedelta(hours=1)
    since = to_naive_utc(since)
    until = to_naive_utc(until)

    params = {
        'src':    source_ip,
        'anom':   is_anomaly,
        'since':  since,
        'until':  until,
        'limit':  pagination.limit,
        'off':    pagination.offset,
    }

    where = """
        WHERE (:src   IS NULL OR source_ip  = :src)
          AND (:anom  IS NULL OR is_anomaly = :anom)
          AND (:since IS NULL OR timestamp >= :since)
          AND (:until IS NULL OR timestamp  < :until)
    """

    total = db.execute(
        text(f"SELECT COUNT(*) FROM ml_predictions {where}"),
        params,
    ).scalar_one()

    rows = db.execute(
        text(f"""
            SELECT id, timestamp, source_ip, time_bucket,
                   if_score, is_anomaly, attack_class, confidence
            FROM ml_predictions
            {where}
            ORDER BY timestamp DESC
            LIMIT :limit OFFSET :off
        """),
        params,
    ).mappings().all()

    return PredictionListResponse(
        total=total,
        predictions=[PredictionOut(**dict(r)) for r in rows],
    )


@router.get(
    '/anomalies',
    response_model=PredictionListResponse,
    summary='List anomali yang terdeteksi ML',
)
def list_anomalies(
    hours: int = Query(24, ge=1, le=720),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    _:  str     = Depends(verify_api_key),
) -> PredictionListResponse:
    since = utc_now() - timedelta(hours=hours)
    params = {'since': since, 'limit': pagination.limit, 'off': pagination.offset}

    total = db.execute(
        text("SELECT COUNT(*) FROM ml_predictions WHERE is_anomaly=TRUE AND timestamp >= :since"),
        params,
    ).scalar_one()

    rows = db.execute(
        text("""
            SELECT id, timestamp, source_ip, time_bucket,
                   if_score, is_anomaly, attack_class, confidence
            FROM ml_predictions
            WHERE is_anomaly = TRUE AND timestamp >= :since
            ORDER BY if_score ASC, timestamp DESC
            LIMIT :limit OFFSET :off
        """),
        params,
    ).mappings().all()

    return PredictionListResponse(
        total=total,
        predictions=[PredictionOut(**dict(r)) for r in rows],
    )


@router.get(
    '/stats',
    response_model=AnomalyStats,
    summary='Statistik prediksi dan anomali ML',
)
def prediction_stats(
    hours: int = Query(24, ge=1, le=720),
    db: Session = Depends(get_db),
    _:  str     = Depends(verify_api_key),
) -> AnomalyStats:
    since = utc_now() - timedelta(hours=hours)

    total_sql  = text("SELECT COUNT(*) FROM ml_predictions WHERE timestamp >= :s")
    anom_sql   = text("SELECT COUNT(*) FROM ml_predictions WHERE is_anomaly=TRUE AND timestamp >= :s")
    class_sql  = text("""
        SELECT attack_class, COUNT(*) AS cnt
        FROM ml_predictions
        WHERE is_anomaly=TRUE AND timestamp >= :s
        GROUP BY attack_class ORDER BY cnt DESC
    """)

    total      = db.execute(total_sql,  {'s': since}).scalar_one()
    total_anom = db.execute(anom_sql,   {'s': since}).scalar_one()
    by_class   = {
        r['attack_class']: r['cnt']
        for r in db.execute(class_sql, {'s': since}).mappings()
    }
    rate = round(total_anom / total * 100, 2) if total > 0 else 0.0

    return AnomalyStats(
        total_predictions=total,
        total_anomalies=total_anom,
        anomaly_rate=rate,
        by_attack_class=by_class,
        period_hours=hours,
    )
