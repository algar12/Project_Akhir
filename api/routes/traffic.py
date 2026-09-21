"""
routes/traffic.py — Unified Network Guard: API
================================================
Endpoint data traffic jaringan.

GET /api/v1/traffic         — list traffic (paginated + filter)
GET /api/v1/traffic/summary — ringkasan per source IP dalam window waktu
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.config import utc_now, to_naive_utc
from api.deps import get_db, verify_api_key, PaginationParams
from api.schemas import (
    TrafficOut, TrafficFilter,
    TrafficSummaryItem, TrafficSummaryResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/traffic', tags=['Network Traffic'])


@router.get(
    '',
    summary='List data traffic jaringan',
    description=(
        'Mengembalikan record traffic jaringan yang ditangkap sniffer. '
        'Mendukung filter by source_ip, protocol, dan rentang waktu.'
    ),
)
def list_traffic(
    source_ip: Optional[str] = Query(None, description="Filter by source IP"),
    protocol:  Optional[str] = Query(
        None, pattern=r'^(TCP|UDP|ICMP|OTHER|\w{1,20})$',
    ),
    since: Optional[datetime] = Query(None),
    until: Optional[datetime] = Query(None),
    pagination: PaginationParams = Depends(),
    db: Session  = Depends(get_db),
    _:  str      = Depends(verify_api_key),
) -> dict:
    # Default: 1 jam terakhir jika tidak ada filter waktu (semua dalam UTC naive)
    if since is None and until is None:
        until = utc_now()
        since = until - timedelta(hours=1)
    since = to_naive_utc(since)
    until = to_naive_utc(until)

    params = {
        'src':      source_ip,
        'proto':    protocol,
        'since':    since,
        'until':    until,
        'limit':    pagination.limit,
        'offset':   pagination.offset,
    }

    count_sql = text("""
        SELECT COUNT(*) FROM network_traffic
        WHERE (:src   IS NULL OR source_ip = :src)
          AND (:proto IS NULL OR protocol  = :proto)
          AND (:since IS NULL OR timestamp >= :since)
          AND (:until IS NULL OR timestamp <  :until)
    """)
    total = db.execute(count_sql, params).scalar_one()

    data_sql = text("""
        SELECT id, timestamp, source_ip, destination_ip,
               protocol, source_port, destination_port, packet_count, bytes,
               is_syn, icmp_type
        FROM network_traffic
        WHERE (:src   IS NULL OR source_ip = :src)
          AND (:proto IS NULL OR protocol  = :proto)
          AND (:since IS NULL OR timestamp >= :since)
          AND (:until IS NULL OR timestamp <  :until)
        ORDER BY timestamp DESC
        LIMIT :limit OFFSET :offset
    """)
    rows = db.execute(data_sql, params).mappings().all()

    return {
        'total':   total,
        'traffic': [TrafficOut(**dict(r)).model_dump() for r in rows],
        'filter':  {
            'source_ip': source_ip,
            'protocol':  protocol,
            'since':     since,
            'until':     until,
        },
    }


@router.get(
    '/summary',
    response_model=TrafficSummaryResponse,
    summary='Ringkasan traffic per source IP',
    description=(
        'Mengagregasi traffic per source IP dalam window waktu N detik terakhir. '
        'Berguna untuk melihat distribusi traffic dan mendeteksi sumber trafik tinggi.'
    ),
)
def traffic_summary(
    window_seconds: int = Query(
        300, ge=10, le=86400,
        description="Window agregasi dalam detik (10 s/d 86400 = 1 hari)",
    ),
    db: Session = Depends(get_db),
    _:  str     = Depends(verify_api_key),
) -> TrafficSummaryResponse:
    until = utc_now()
    since = until - timedelta(seconds=window_seconds)

    sql = text("""
        SELECT
            source_ip,
            COUNT(*)                       AS packet_count,
            COALESCE(SUM(bytes), 0)        AS total_bytes,
            COUNT(DISTINCT destination_port)     AS unique_ports,
            SUM(CASE WHEN protocol='TCP'  THEN 1 ELSE 0 END) AS tcp_count,
            SUM(CASE WHEN protocol='UDP'  THEN 1 ELSE 0 END) AS udp_count,
            SUM(CASE WHEN protocol='ICMP' THEN 1 ELSE 0 END) AS icmp_count
        FROM network_traffic
        WHERE timestamp >= :since AND timestamp < :until
        GROUP BY source_ip
        ORDER BY packet_count DESC
        LIMIT 50
    """)
    rows = db.execute(sql, {
        'since': since, 'until': until,
    }).mappings().all()

    # Rate dihitung di Python (hindari cast ::float pada parameter — ambiguous
    # untuk psycopg2/SQLAlchemy).
    items = []
    for r in rows:
        items.append(TrafficSummaryItem(
            source_ip=r['source_ip'],
            packet_count=r['packet_count'],
            total_bytes=r['total_bytes'],
            packet_rate=round(float(r['packet_count']) / window_seconds, 4),
            byte_rate=round(float(r['total_bytes']) / window_seconds, 4),
            unique_ports=r['unique_ports'],
            protocol_breakdown={
                'TCP':  r['tcp_count'],
                'UDP':  r['udp_count'],
                'ICMP': r['icmp_count'],
            },
        ))

    return TrafficSummaryResponse(window_seconds=window_seconds, items=items)
