"""
schemas.py — Unified Network Guard: API
=========================================
Pydantic v2 schemas untuk semua request/response.

Keunggulan Pydantic v2 untuk keamanan:
  - Validasi tipe ketat saat deserialisasi — tidak ada implicit coercion berbahaya
  - Field dengan regex pattern mencegah injection via string input
  - Nilai default + batas range (ge/le) mencegah integer overflow / abuse
  - model_config dengan str_strip_whitespace=True bersihkan input otomatis
  - from_attributes=True untuk konversi dari ORM row tanpa repacking manual
"""

import re
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, field_serializer

# ─── Base Config ─────────────────────────────────────────────────────────────
class _Base(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
        populate_by_name=True,
    )

    @field_serializer('*', mode='wrap', when_used='json')
    def _serialize_datetimes(self, v, handler, info):
        res = handler(v)
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc).isoformat()
        return res


# ─── Validasi IP / String Umum ────────────────────────────────────────────────
_IP_PATTERN   = re.compile(r'^(\d{1,3}\.){3}\d{1,3}(/\d{1,2})?$')
_SAFE_STR     = re.compile(r'^[\w\s\-\./,:@]+$')    # karakter aman umum


def _validate_ip(v: Optional[str]) -> Optional[str]:
    if v is None:
        return v
    if not _IP_PATTERN.match(v):
        raise ValueError(f"Format IP tidak valid: {v!r}")
    return v


# ─── Device Schemas ───────────────────────────────────────────────────────────
class DeviceOut(_Base):
    id:          int
    device_name: str
    ip_address:  str
    mac_address: Optional[str] = None
    device_type: Optional[str] = None
    status:      str
    last_seen:   Optional[datetime] = None


class DeviceListResponse(_Base):
    total:   int
    devices: list[DeviceOut]


# ─── Traffic Schemas ──────────────────────────────────────────────────────────
class TrafficOut(_Base):
    id:               int
    timestamp:        datetime
    source_ip:        str
    destination_ip:   str
    protocol:         str
    source_port:      Optional[int] = None
    destination_port: Optional[int] = None
    packet_count:     int
    bytes:            int
    is_syn:           bool = False
    icmp_type:        Optional[int] = None


class TrafficFilter(_Base):
    """Query params untuk filter traffic — divalidasi ketat."""
    source_ip:   Optional[str] = Field(None, description="Filter by source IP")
    protocol:    Optional[str] = Field(
        None,
        pattern=r'^(TCP|UDP|ICMP|OTHER|\w{1,20})$',
        description="Filter by protocol (TCP/UDP/ICMP)",
    )
    since:  Optional[datetime] = Field(None, description="Mulai dari waktu (ISO 8601)")
    until:  Optional[datetime] = Field(None, description="Sampai waktu (ISO 8601)")

    @field_validator('source_ip', mode='before')
    @classmethod
    def validate_source_ip(cls, v):
        return _validate_ip(v)


class TrafficSummaryItem(_Base):
    source_ip:     str
    packet_count:  int
    total_bytes:   int
    packet_rate:   float
    byte_rate:     float
    unique_ports:  int
    protocol_breakdown: dict[str, int]


class TrafficSummaryResponse(_Base):
    window_seconds: int
    items:          list[TrafficSummaryItem]


# ─── Alert Schemas ────────────────────────────────────────────────────────────
_SEVERITY_VALUES = {'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'}


class AlertOut(_Base):
    id:          int
    timestamp:   datetime
    source_ip:   str
    target_ip:   str
    attack_type: str
    severity:    str
    confidence:  float
    description: Optional[str] = None
    mitigated:   bool = False
    mitigated_at: Optional[datetime] = None


class AlertFilter(_Base):
    severity:    Optional[str] = Field(
        None,
        description="Filter by severity: LOW/MEDIUM/HIGH/CRITICAL",
    )
    attack_type: Optional[str] = Field(
        None,
        max_length=100,
        description="Filter by attack type (substring match)",
    )
    source_ip:   Optional[str] = Field(None, description="Filter by source IP")
    since:       Optional[datetime] = None
    until:       Optional[datetime] = None

    @field_validator('severity', mode='before')
    @classmethod
    def validate_severity(cls, v):
        if v is not None and v.upper() not in _SEVERITY_VALUES:
            raise ValueError(f"Severity harus salah satu dari: {_SEVERITY_VALUES}")
        return v.upper() if v else v

    @field_validator('source_ip', mode='before')
    @classmethod
    def validate_source_ip(cls, v):
        return _validate_ip(v)

    @field_validator('attack_type', mode='before')
    @classmethod
    def validate_attack_type(cls, v):
        if v and not _SAFE_STR.match(v):
            raise ValueError("attack_type mengandung karakter tidak valid.")
        return v


class AlertStats(_Base):
    total_alerts:         int
    by_severity:          dict[str, int]
    by_attack_type:       dict[str, int]
    most_active_sources:  list[dict[str, Any]]
    period_hours:         int


class AlertListResponse(_Base):
    total:  int
    alerts: list[AlertOut]


# ─── Telemetry Schemas ────────────────────────────────────────────────────────
class TelemetryOut(_Base):
    id:        int
    timestamp: datetime
    device_id: str
    topic:     str
    payload:   Optional[dict[str, Any]] = None
    source_ip: Optional[str] = None


class TelemetryListResponse(_Base):
    device_id: str
    total:     int
    items:     list[TelemetryOut]


# ─── ML Prediction Schemas ────────────────────────────────────────────────────
class PredictionOut(_Base):
    id:           int
    timestamp:    datetime
    source_ip:    str
    time_bucket:  Optional[datetime] = None
    if_score:     Optional[float]    = None
    is_anomaly:   bool
    attack_class: Optional[str]      = None
    confidence:   float


class PredictionListResponse(_Base):
    total:       int
    predictions: list[PredictionOut]


class AnomalyStats(_Base):
    total_predictions: int
    total_anomalies:   int
    anomaly_rate:      float
    by_attack_class:   dict[str, int]
    period_hours:      int


# ─── System Status Schemas ────────────────────────────────────────────────────
class ModuleStatus(_Base):
    name:    str
    running: bool
    detail:  Optional[str] = None


class SystemStatus(_Base):
    api_version:     str = '1.0.0'
    timestamp:       datetime
    database:        str
    total_devices:   int
    total_alerts:    int
    total_traffic:   int
    total_anomalies: int
    suricata_online: bool = False   # True bila eve.json aktif ditulis Suricata


class NetworkInfo(_Base):
    interface: str
    subnet:    str
    local_ip:  Optional[str] = None
    gateway:   Optional[str] = None


# ─── Generic Response ─────────────────────────────────────────────────────────
class MessageResponse(_Base):
    message: str
    success: bool = True


# ─── WebSocket Alert Message ──────────────────────────────────────────────────
class WSAlertMessage(_Base):
    event:   str = 'new_alert'
    payload: AlertOut
