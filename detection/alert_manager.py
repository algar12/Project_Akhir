"""
alert_manager.py — Unified Network Guard: Detection
====================================================
Pengelola alert terpusat yang dipakai oleh rule_engine dan eve_parser.

Tanggung jawab:
  1. Memetakan classtype / nama serangan ke severity (LOW/MEDIUM/HIGH/CRITICAL)
  2. De-duplikasi: alert identik (source_ip + attack_type) tidak di-insert
     ulang selama ALERT_SUPPRESS_SECONDS untuk menghindari banjir DB.
  3. Insert alert ke tabel 'alerts' di PostgreSQL.
  4. Menyediakan dataclass Alert sebagai struktur data internal.

Dataclass dipakai agar pertukaran data antar modul type-safe dan readable.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import QueuePool

from detection.config import (
    DATABASE_URL,
    ALERT_SUPPRESS_SECONDS,
)

logger = logging.getLogger(__name__)

# ─── Singleton engine (dipakai di seluruh modul detection) ───────────────────
_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(
            DATABASE_URL,
            poolclass=QueuePool,
            pool_size=3,
            max_overflow=5,
            pool_pre_ping=True,
            pool_recycle=1800,
            echo=False,
        )
        logger.info("[AlertMgr] DB engine siap → %s", DATABASE_URL)
    return _engine


# ─── Dataclass Alert ─────────────────────────────────────────────────────────
@dataclass
class Alert:
    """
    Representasi sebuah alert keamanan jaringan.

    Diisi oleh rule_engine atau eve_parser lalu diteruskan ke AlertManager.
    """
    source_ip:   str
    target_ip:   str
    attack_type: str
    severity:    str                        # LOW | MEDIUM | HIGH | CRITICAL
    confidence:  float       = 1.0
    description: str         = ''
    timestamp:   datetime    = field(
        default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    source:      str         = 'rule'       # 'rule' | 'suricata' | 'ml'


# ─── Peta Severity ───────────────────────────────────────────────────────────
# Mapping dari classtype Suricata / nama serangan → severity
SEVERITY_MAP: dict[str, str] = {
    # Suricata classtype
    'attempted-recon':         'MEDIUM',
    'attempted-dos':           'HIGH',
    'denial-of-service':       'HIGH',
    'attempted-admin':         'CRITICAL',
    'attempted-user':          'HIGH',
    'policy-violation':        'MEDIUM',
    'protocol-command-decode': 'LOW',
    'web-application-attack':  'HIGH',
    'network-scan':            'MEDIUM',
    'trojan-activity':         'CRITICAL',
    'bad-unknown':             'LOW',

    # Rule engine internal
    'PORT_SCAN':               'MEDIUM',
    'SYN_FLOOD':               'HIGH',
    'ICMP_FLOOD':              'HIGH',
    'TRAFFIC_SPIKE':           'MEDIUM',
    'MQTT_RATE_ABUSE':         'MEDIUM',
    'UNAUTHORIZED_MQTT':       'HIGH',
    'UNKNOWN':                 'LOW',
}


def map_severity(classtype_or_name: str) -> str:
    """
    Memetakan nama serangan / Suricata classtype ke nilai severity.
    Fallback ke 'MEDIUM' jika tidak dikenal.

    Normalisasi: spasi & hyphen → underscore, agar 'syn_flood', 'SYN_FLOOD',
    maupun 'syn-flood' semuanya cocok dengan kunci map ('SYN_FLOOD').
    """
    key = classtype_or_name.lower().strip().replace(' ', '_').replace('-', '_')
    # Cari persis
    for k, v in SEVERITY_MAP.items():
        if k.lower() == key:
            return v
    # Cari substring (untuk classtype Suricata seperti 'attempted-recon')
    for k, v in SEVERITY_MAP.items():
        kk = k.lower()
        if kk in key or key in kk:
            return v
    return 'MEDIUM'


# ─── AlertManager ─────────────────────────────────────────────────────────────
class AlertManager:
    """
    Pengelola siklus hidup alert: de-duplikasi → insert DB.

    Pola singleton sederhana: satu instance dipakai bersama oleh
    rule_engine dan eve_parser melalui parameter/dependency injection.
    """

    def __init__(self, suppress_seconds: int = ALERT_SUPPRESS_SECONDS) -> None:
        self.suppress_seconds = suppress_seconds
        # Cache de-duplikasi: (source_ip, attack_type) → waktu insert terakhir
        self._seen: dict[tuple[str, str], datetime] = {}
        self._total_received = 0
        self._total_suppressed = 0
        self._total_inserted = 0

    # ─── Public: Proses Alert ────────────────────────────────────────────────
    def process(self, alert: Alert) -> bool:
        """
        Proses satu Alert: cek duplikat lalu insert ke DB jika lolos.

        Args:
            alert: Objek Alert yang akan diproses.

        Returns:
            True  → Alert berhasil di-insert ke DB.
            False → Alert duplikat / suppressed / gagal DB.
        """
        self._total_received += 1

        # De-duplikasi
        key = (alert.source_ip, alert.attack_type)
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        last_seen = self._seen.get(key)
        if last_seen and (now - last_seen) < timedelta(seconds=self.suppress_seconds):
            self._total_suppressed += 1
            logger.debug(
                "[AlertMgr] Suppressed [%s] %s → %s",
                alert.attack_type, alert.source_ip, alert.target_ip,
            )
            return False

        # Simpan waktu sekarang sebelum insert
        self._seen[key] = now

        # Bersihkan cache lama (garbage collect sederhana setiap 500 alert)
        if self._total_received % 500 == 0:
            self._purge_cache()

        # Insert ke DB
        ok = self._insert(alert)
        if ok:
            self._total_inserted += 1
            logger.warning(
                "[ALERT][%s] %s | %s → %s | conf=%.2f | %s",
                alert.severity,
                alert.attack_type,
                alert.source_ip,
                alert.target_ip,
                alert.confidence,
                alert.description[:80],
            )
        return ok

    # ─── Internal: Insert DB ─────────────────────────────────────────────────
    def _insert(self, alert: Alert) -> bool:
        sql = text("""
            INSERT INTO alerts
                (timestamp, source_ip, target_ip, attack_type,
                 severity, confidence, description)
            VALUES
                (:timestamp, :source_ip, :target_ip, :attack_type,
                 :severity, :confidence, :description)
        """)
        params = {
            'timestamp':   alert.timestamp,
            'source_ip':   alert.source_ip,
            'target_ip':   alert.target_ip,
            'attack_type': alert.attack_type,
            'severity':    alert.severity,
            'confidence':  alert.confidence,
            'description': alert.description,
        }
        try:
            engine = _get_engine()
            with engine.connect() as conn:
                conn.execute(sql, params)
                conn.commit()
            return True
        except SQLAlchemyError as exc:
            logger.error("[AlertMgr] Gagal insert alert: %s", exc)
            return False

    # ─── Internal: Bersihkan Cache Lama ─────────────────────────────────────
    def _purge_cache(self) -> None:
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=self.suppress_seconds * 2)
        stale_keys = [k for k, v in self._seen.items() if v < cutoff]
        for k in stale_keys:
            del self._seen[k]
        if stale_keys:
            logger.debug("[AlertMgr] Cache purged: %d entri lama dihapus.", len(stale_keys))

    # ─── Properti Statistik ──────────────────────────────────────────────────
    @property
    def stats(self) -> dict[str, int]:
        return {
            'total_received':   self._total_received,
            'total_suppressed': self._total_suppressed,
            'total_inserted':   self._total_inserted,
        }
