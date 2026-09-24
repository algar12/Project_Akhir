"""
routes/eval.py — Unified Network Guard: API
---------------------------------------------
Endpoint kontrol sesi evaluasi Tabel 1 (S1-S6).

Dipakai oleh tools/attacker.py (HP) untuk mengkoordinasikan sesi evaluasi
dari jarak jauh, sehingga satu ketuk di HP = eval penuh yang tercatat di
Edge PC.

POST /api/v1/eval/session/start            — mulai sesi (truncate + migrasi kolom source)
POST /api/v1/eval/session/begin/{sid}      — tandai skenario S1-S6 mulai
POST /api/v1/eval/session/end/{sid}        — tandai skenario selesai
POST /api/v1/eval/session/finish           — finalisasi sesi
GET  /api/v1/eval/session                  — tampilkan sesi saat ini

File sesi: ml/eval_session.json (dipakai bersama tools/eval_session.py & ml/evaluator_tabel1.py).
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from api.deps import verify_api_key, SessionLocal

router = APIRouter(prefix="/eval", tags=["Evaluation"])

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SESSION_FILE = PROJECT_ROOT / "ml" / "eval_session.json"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _load() -> dict:
    if SESSION_FILE.exists():
        return json.loads(SESSION_FILE.read_text(encoding="utf-8"))
    return {"scenarios": {}, "started_at": None, "finished_at": None}


def _save(s: dict) -> None:
    SESSION_FILE.write_text(json.dumps(s, indent=2, default=str, ensure_ascii=False), encoding="utf-8")


@router.post("/session/start", summary="Mulai sesi evaluasi (truncate + migrasi kolom source)")
def session_start(_: str = Depends(verify_api_key)):
    """Mulai sesi evaluasi baru. Mengosongkan alerts, ml_predictions, network_traffic
    dan menambahkan kolom alerts.source jika belum ada, lalu mencatat timestamp mulai."""
    try:
        db = SessionLocal()
        db.execute(text("ALTER TABLE alerts ADD COLUMN IF NOT EXISTS source VARCHAR(20) DEFAULT 'rule'"))
        db.execute(text("TRUNCATE TABLE alerts RESTART IDENTITY"))
        db.execute(text("TRUNCATE TABLE ml_predictions RESTART IDENTITY"))
        db.execute(text("TRUNCATE TABLE network_traffic RESTART IDENTITY"))
        db.commit()
        db.close()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DB error: {exc}")
    s = {"scenarios": {}, "started_at": _utc_now(), "finished_at": None}
    _save(s)
    return {"message": f"sesi evaluasi dimulai @ {s['started_at'].isoformat()}Z; "
                       f"alerts + ml_predictions + network_traffic di-truncate",
            "started_at": s["started_at"].isoformat() + "Z"}


@router.post("/session/begin/{sid}", summary="Tandai skenario S1-S6 dimulai")
def session_begin(sid: str, _: str = Depends(verify_api_key)):
    s = _load()
    if not s.get("started_at"):
        raise HTTPException(status_code=400, detail="sesi belum dimulai — panggil /session/start dulu")
    sid = sid.upper()
    s["scenarios"][sid] = {"begin": _utc_now(), "end": None}
    _save(s)
    return {"message": f"{sid} dimulai @ {s['scenarios'][sid]['begin'].isoformat()}Z",
            "scenario": sid, "begin": s["scenarios"][sid]["begin"].isoformat() + "Z"}


@router.post("/session/end/{sid}", summary="Tandai skenario S1-S6 selesai")
def session_end(sid: str, _: str = Depends(verify_api_key)):
    s = _load()
    sid = sid.upper()
    if sid not in s["scenarios"] or not s["scenarios"][sid].get("begin"):
        raise HTTPException(status_code=400, detail=f"{sid} belum di-begin")
    s["scenarios"][sid]["end"] = _utc_now()
    _save(s)
    return {"message": f"{sid} selesai @ {s['scenarios'][sid]['end'].isoformat()}Z",
            "scenario": sid, "end": s["scenarios"][sid]["end"].isoformat() + "Z"}


@router.post("/session/finish", summary="Finalisasi sesi evaluasi")
def session_finish(_: str = Depends(verify_api_key)):
    s = _load()
    if not s.get("started_at"):
        raise HTTPException(status_code=400, detail="sesi belum dimulai")
    s["finished_at"] = _utc_now()
    _save(s)
    return {"message": f"sesi selesai @ {s['finished_at'].isoformat()}Z; {len(s['scenarios'])} skenario tercatat",
            "finished_at": s["finished_at"].isoformat() + "Z",
            "scenarios": list(s["scenarios"].keys())}


@router.get("/session", summary="Tampilkan sesi evaluasi saat ini")
def session_show(_: str = Depends(verify_api_key)):
    return _load()
