#!/usr/bin/env python3
"""
eval_session.py — Unified Network Guard
========================================
Tool pencatat sesi evaluasi Tabel 1 (S1-S6). Mencatat timestamp mulai/akhir
tiap skenario ke ml/eval_session.json, lalu ml/evaluator_tabel1.py memakai
pencatat ini untuk menghitung metrik per-metode per-skenario.

Alur pakai:
  python tools/eval_session.py start            # mulai sesi (truncate alerts+ml_predictions)
  python tools/eval_session.py begin S2         # tandai skenario S2 mulai
  ... (jalankan perintah attacker 5x) ...
  python tools/eval_session.py end S2           # tandai skenario S2 selesai
  ... (ulang untuk S3, S4, S5, S6) ...
  python tools/eval_session.py finish           # finalisasi sesi

S1 (normal) tidak perlu begin/end — antara start sesi dan skenario S2,
atau jalankan: python tools/eval_session.py begin S1 ... end S1.

Catatan waktu: semua UTC naive (konsisten dengan pipeline).
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SESSION_FILE = PROJECT_ROOT / "ml" / "eval_session.json"


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def load_session() -> dict:
    if SESSION_FILE.exists():
        return json.loads(SESSION_FILE.read_text(encoding="utf-8"))
    return {"scenarios": {}, "started_at": None, "finished_at": None}


def save_session(s: dict) -> None:
    SESSION_FILE.write_text(json.dumps(s, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def truncate_tables() -> None:
    """Kosongkan alerts + ml_predictions agar evaluasi bersih (hanya sesi ini)."""
    try:
        sys.path.insert(0, str(PROJECT_ROOT))
        from sqlalchemy import text
        from collector.db import get_engine  # reuse engine yang sudah ada
    except Exception as exc:
        print(f"[!] Tidak bisa import DB layer: {exc}")
        print("    Pastikan venv aktif & .env benar. Lanjut tanpa truncate.")
        return
    try:
        engine = get_engine()
        with engine.connect() as conn:
            # Migrasi idempotent: tambah kolom source jika belum ada
            conn.execute(text("ALTER TABLE alerts ADD COLUMN IF NOT EXISTS source VARCHAR(20) DEFAULT 'rule'"))
            conn.execute(text("TRUNCATE TABLE alerts RESTART IDENTITY"))
            conn.execute(text("TRUNCATE TABLE ml_predictions RESTART IDENTITY"))
            conn.execute(text("TRUNCATE TABLE network_traffic RESTART IDENTITY"))
            conn.commit()
        print("[OK] Migrasi kolom source + truncate alerts, ml_predictions, network_traffic selesai.")
    except Exception as exc:
        print(f"[!] Gagal migrate/truncate: {exc}")
        print("    Anda bisa manual: ALTER TABLE alerts ADD COLUMN IF NOT EXISTS source VARCHAR(20) DEFAULT 'rule';")
        print("    lalu TRUNCATE alerts, ml_predictions, network_traffic RESTART IDENTITY;")


def cmd_start(args):
    if args.no_truncate:
        print("[i] Skip truncate (--no-truncate).")
    else:
        confirm = input("Truncate tabel alerts + ml_predictions + network_traffic? (y/N) ").strip().lower()
        if confirm == "y":
            truncate_tables()
        else:
            print("[i] Tidak truncate. Pastikan tabel bersih agar evaluasi valid.")
    s = {"scenarios": {}, "started_at": utc_now(), "finished_at": None}
    save_session(s)
    print(f"[OK] Sesi evaluasi dimulai @ {s['started_at'].isoformat()}Z")
    print("     Jalankan: python tools/eval_session.py begin S1")


def cmd_begin(args):
    s = load_session()
    if s.get("started_at") is None:
        print("[!] Sesi belum dimulai. Jalankan: python tools/eval_session.py start")
        sys.exit(1)
    sid = args.scenario.upper()
    s["scenarios"][sid] = {"begin": utc_now(), "end": None}
    save_session(s)
    print(f"[OK] {sid} dimulai @ {s['scenarios'][sid]['begin'].isoformat()}Z")
    if sid != "S1":
        print(f"     Jalankan perintah attacker untuk {sid} (5 repetisi). Lalu: end {sid}")


def cmd_end(args):
    s = load_session()
    sid = args.scenario.upper()
    if sid not in s["scenarios"] or s["scenarios"][sid].get("begin") is None:
        print(f"[!] {sid} belum di-begin.")
        sys.exit(1)
    s["scenarios"][sid]["end"] = utc_now()
    save_session(s)
    print(f"[OK] {sid} selesai @ {s['scenarios'][sid]['end'].isoformat()}Z")
    print("     Lanjut ke skenario berikutnya, atau finish jika sudah S6.")


def cmd_finish(args):
    s = load_session()
    if s.get("started_at") is None:
        print("[!] Sesi belum dimulai.")
        sys.exit(1)
    s["finished_at"] = utc_now()
    save_session(s)
    n = len(s["scenarios"])
    print(f"[OK] Sesi evaluasi selesai @ {s['finished_at'].isoformat()}Z")
    print(f"     {n} skenario tercatat: {list(s['scenarios'].keys())}")
    print("     Sekarang jalankan: python ml/evaluator_tabel1.py")


def cmd_show(args):
    s = load_session()
    print(json.dumps(s, indent=2, ensure_ascii=False, default=str))


def main():
    p = argparse.ArgumentParser(description="Pencatat sesi evaluasi Tabel 1 UNG")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("start", help="Mulai sesi evaluasi")
    sp.add_argument("--no-truncate", action="store_true", help="Jangan truncate tabel")
    sp.set_defaults(func=cmd_start)

    sp = sub.add_parser("begin", help="Tandai skenario mulai")
    sp.add_argument("scenario", help="ID skenario, mis. S2")
    sp.set_defaults(func=cmd_begin)

    sp = sub.add_parser("end", help="Tandai skenario selesai")
    sp.add_argument("scenario", help="ID skenario, mis. S2")
    sp.set_defaults(func=cmd_end)

    sub.add_parser("finish", help="Finalisasi sesi").set_defaults(func=cmd_finish)
    sub.add_parser("show", help="Tampilkan sesi saat ini").set_defaults(func=cmd_show)


if __name__ == "__main__":
    main()
