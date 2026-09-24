#!/usr/bin/env python3
"""
evaluator_tabel1.py — Unified Network Guard
============================================
Evaluator per-metode × per-skenario untuk Tabel 1 artikel IKOMTI.

Membaca:
  - ml/eval_session.json        (timestamp mulai/akhir tiap skenario, dari tools/eval_session.py)
  - ml/scenarios_tabel1.json   (definisi S1-S6 + ground truth + expected attack_types)
  - tabel alerts (DB)           (dengan kolom `source`: suricata|rule|ml)

Menghasilkan:
  - ml/models/tabel1_eval.json  (matriks lengkap per-metode per-skenario)
  - cetak tabel formatted ke stdout

Metodologi (binary detection, sesuai paragraf 53 artikel — "keputusan deteksi vs ground truth"):
  Tiap skenario dipecah jadi N slice (N=reps_per_scenario, default 5).
  - Skenario serangan (S2-S6): per slice, metode "mendeteksi" jika >=1 alert dari metode di slice tsb.
      TP = slice terdeteksi, FN = slice tidak terdeteksi, FP = 0, TN = 0.
      Precision = 1 (jika ada deteksi) — tidak mungkin FP dalam window serangan.
      Recall = TP/N. F1 = 2*P*R/(P+R). Accuracy = TP/N. FPR = 0.
      Latency = rata-rata (first_alert_ts - slice_start) ms, untuk slice terdeteksi.
  - Skenario normal (S1): per slice, metode "false alarm" jika >=1 alert.
      FP = slice dengan alert, TN = slice tanpa alert, TP = FN = 0.
      Precision/Recall/F1 = N/A ("—"). FPR = FP/N. Accuracy = TN/N. Latency = "—".
  - Hibrida = union alert semua metode (>=1 alert dari metode mana pun).
  - Baris Rata-rata (Hibrida, Usulan) = agregasi TP/FP/TN/FN lintas S1-S6:
      TP dari S2-S6 (max 25), FN=25-TP, FP dari S1, TN dari S1.
      Accuracy=(TP+TN)/(TP+TN+FP+FN), Precision=TP/(TP+FP), Recall=TP/(TP+FN),
      F1=2PR/(P+R), FPR=FP/(FP+TN), Latency=rata-rata semua slice serangan terdeteksi.

Catatan: per-metode Rata-rata juga dihitung (disimpan di JSON) untuk referensi,
walau di Tabel 1 hanya baris "Rata-rata / Hibrida" yang ditampilkan.
"""
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import text
from collector.db import get_engine

SCENARIOS_FILE = PROJECT_ROOT / "ml" / "scenarios_tabel1.json"
SESSION_FILE = PROJECT_ROOT / "ml" / "eval_session.json"
OUT_FILE = PROJECT_ROOT / "ml" / "models" / "tabel1_eval.json"

METHOD_KEYS = ["suricata", "rule", "ml", "hibrida"]
METHOD_LABELS = {
    "suricata": "Suricata (Signature)",
    "rule": "Rule-Based (Threshold)",
    "ml": "Isolation Forest (ML)",
    "hibrida": "Hibrida (Usulan)",
}


def parse_ts(s):
    if isinstance(s, datetime):
        return s
    return datetime.fromisoformat(s)


def fetch_alerts(begin, end):
    engine = get_engine()
    sql = text("""
        SELECT id, timestamp, source_ip, attack_type, source
        FROM alerts
        WHERE timestamp >= :b AND timestamp <= :e
        ORDER BY timestamp
    """)
    with engine.connect() as conn:
        rows = conn.execute(sql, {"b": begin, "e": end}).fetchall()
    return [
        {"id": r[0], "ts": r[1], "source_ip": r[2], "attack_type": r[3], "source": r[4] or "rule"}
        for r in rows
    ]


def alerts_for_method(alerts, method):
    if method == "hibrida":
        return alerts
    return [a for a in alerts if a["source"] == method]


def slice_windows(begin, end, n):
    total = (end - begin).total_seconds()
    step = total / n
    return [(begin + timedelta(seconds=step * i),
             begin + timedelta(seconds=step * (i + 1)))
            for i in range(n)]


def safe_div(a, b):
    return a / b if b else 0.0


def compute_scenario(scenario, begin, end, reps):
    """Hitung metrik 4 metode untuk satu skenario window."""
    alerts = fetch_alerts(begin, end)
    slices = slice_windows(begin, end, reps)
    is_attack = scenario["is_attack"]

    result = {"scenario": scenario["id"], "is_attack": is_attack,
              "begin": begin.isoformat(), "end": end.isoformat(),
              "n_alerts": len(alerts), "methods": {}}

    for m in METHOD_KEYS:
        m_alerts = alerts_for_method(alerts, m)
        if is_attack:
            tp = fp = fn = tn = 0
            lats = []
            for (sb, se) in slices:
                in_slice = [a for a in m_alerts if sb <= a["ts"] <= se]
                if in_slice:
                    tp += 1
                    lats.append((in_slice[0]["ts"] - sb).total_seconds() * 1000.0)
                else:
                    fn += 1
            precision = 1.0 if tp > 0 else 0.0   # tidak mungkin FP di window serangan
            recall = safe_div(tp, tp + fn)
            f1 = safe_div(2 * precision * recall, precision + recall) if (precision + recall) else 0.0
            acc = safe_div(tp + tn, tp + tn + fp + fn)
            fpr = 0.0
            latency = round(sum(lats) / len(lats), 1) if lats else None
            result["methods"][m] = {
                "TP": tp, "FP": fp, "TN": tn, "FN": fn,
                "accuracy": round(acc, 4), "precision": round(precision, 4),
                "recall": round(recall, 4), "f1": round(f1, 4),
                "fpr": round(fpr, 4), "latency_ms": latency,
                "n_alerts": len(m_alerts),
            }
        else:
            # Skenario normal (S1)
            fp = fn = tp = 0
            tn = 0
            for (sb, se) in slices:
                in_slice = [a for a in m_alerts if sb <= a["ts"] <= se]
                if in_slice:
                    fp += 1
                else:
                    tn += 1
            acc = safe_div(tn, tn + fp)
            fpr = safe_div(fp, fp + tn)
            result["methods"][m] = {
                "TP": 0, "FP": fp, "TN": tn, "FN": 0,
                "accuracy": round(acc, 4),
                "precision": None, "recall": None, "f1": None,
                "fpr": round(fpr, 4), "latency_ms": None,
                "n_alerts": len(m_alerts),
            }
    return result


def compute_average(per_scenario):
    """Agregat Hibrida lintas S1-S6 untuk baris Rata-rata."""
    n_attack = sum(1 for s in per_scenario if s["is_attack"])
    n_normal = sum(1 for s in per_scenario if not s["is_attack"])
    reps = per_scenario[0]["methods"]["hibrida"]["TP"] + per_scenario[0]["methods"]["hibrida"]["FN"] if per_scenario else 5

    out = {}
    for m in METHOD_KEYS:
        tp = fp = tn = fn = 0
        lats = []
        for s in per_scenario:
            mm = s["methods"][m]
            if s["is_attack"]:
                tp += mm["TP"]
                fn += mm["FN"]
                # kumpulkan latency per slice terdeteksi (rekonstruksi dari rata-rata & TP)
                if mm["latency_ms"] is not None and mm["TP"] > 0:
                    lats.extend([mm["latency_ms"]] * mm["TP"])
            else:
                fp += mm["FP"]
                tn += mm["TN"]
        acc = safe_div(tp + tn, tp + tn + fp + fn)
        prec = safe_div(tp, tp + fp)
        rec = safe_div(tp, tp + fn)
        f1 = safe_div(2 * prec * rec, prec + rec) if (prec + rec) else 0.0
        fpr = safe_div(fp, fp + tn)
        lat = round(sum(lats) / len(lats), 1) if lats else None
        out[m] = {
            "TP": tp, "FP": fp, "TN": tn, "FN": fn,
            "accuracy": round(acc, 4), "precision": round(prec, 4),
            "recall": round(rec, 4), "f1": round(f1, 4),
            "fpr": round(fpr, 4), "latency_ms": lat,
        }
    return out


def fmt(v, is_pct=True):
    if v is None:
        return "—"
    if is_pct:
        return f"{v*100:.2f}"
    return f"{v:.2f}"


def fmt_lat(v):
    if v is None:
        return "—"
    return f"{v:.1f}"


def print_table(results, average):
    print("\n" + "=" * 110)
    print("TABEL 1 — Perbandingan performa deteksi (S1-S6 × 4 metode × 6 metrik)")
    print("=" * 110)
    hdr = f"{'Skenario':<8}{'Metode':<28}{'Acc':>8}{'Prec':>8}{'Rec':>8}{'F1':>8}{'FPR':>8}{'Lat(ms)':>10}"
    print(hdr)
    print("-" * 110)
    for r in results:
        sc = r["scenario"]
        for m in METHOD_KEYS:
            mm = r["methods"][m]
            row = (f"{sc:<8}{METHOD_LABELS[m]:<28}"
                   f"{fmt(mm['accuracy']):>8}{fmt(mm['precision']):>8}"
                   f"{fmt(mm['recall']):>8}{fmt(mm['f1']):>8}"
                   f"{fmt(mm['fpr']):>8}{fmt_lat(mm['latency_ms']):>10}")
            print(row)
        print()
    # Rata-rata
    print("-" * 110)
    print(f"{'Rata-rata':<8}{'Hibrida (Usulan)':<28}"
          f"{fmt(average['hibrida']['accuracy']):>8}{fmt(average['hibrida']['precision']):>8}"
          f"{fmt(average['hibrida']['recall']):>8}{fmt(average['hibrida']['f1']):>8}"
          f"{fmt(average['hibrida']['fpr']):>8}{fmt_lat(average['hibrida']['latency_ms']):>10}")
    # Rata-rata per-metode (bonus, untuk referensi)
    print("\n[Referensi internal — Rata-rata per-metode lintas S1-S6]")
    for m in METHOD_KEYS:
        mm = average[m]
        print(f"  {METHOD_LABELS[m]:<28} Acc={fmt(mm['accuracy'])}  Prec={fmt(mm['precision'])}  "
              f"Rec={fmt(mm['recall'])}  F1={fmt(mm['f1'])}  FPR={fmt(mm['fpr'])}  Lat={fmt_lat(mm['latency_ms'])}ms  "
              f"(TP={mm['TP']} FP={mm['FP']} TN={mm['TN']} FN={mm['FN']})")
    print("=" * 110)
    print("Catatan: angka dalam persen (kecuali Latensi dalam ms). '—' = N/A")
    print("         S1: Precision/Recall/F1/Latensi N/A (tidak ada serangan).")
    print("         S2-S6: Precision=1 & FPR=0 jika terdeteksi (binary detection, tak mungkin FP di window serangan).")
    print("         Baris Rata-rata (Hibrida) = metrik diskriminatif lintas skenario.")


def main():
    if not SESSION_FILE.exists():
        print("[!] ml/eval_session.json tidak ada. Jalankan tools/eval_session.py dulu.")
        sys.exit(1)
    if not SCENARIOS_FILE.exists():
        print("[!] ml/scenarios_tabel1.json tidak ada.")
        sys.exit(1)

    session = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
    scen_def = json.loads(SCENARIOS_FILE.read_text(encoding="utf-8"))
    reps = scen_def["_meta"]["reps_per_scenario"]
    scen_list = scen_def["scenarios"]

    results = []
    missing = []
    for s in scen_list:
        sid = s["id"]
        rec = session["scenarios"].get(sid)
        if not rec or not rec.get("begin") or not rec.get("end"):
            missing.append(sid)
            continue
        begin = parse_ts(rec["begin"])
        end = parse_ts(rec["end"])
        r = compute_scenario(s, begin, end, reps)
        results.append(r)
        print(f"[OK] {sid} ({s['name']}): {r['n_alerts']} alert diproses")

    if missing:
        print(f"[!] Skenario belum tercatat di sesi: {missing}")
        print("    Jalankan tools/eval_session.py begin/end untuk skenario tsb.")
    if not results:
        print("[!] Tidak ada skenario dengan window lengkap. Evaluasi dibatalkan.")
        sys.exit(1)

    average = compute_average(results)

    out = {
        "evaluated_at": datetime.utcnow().isoformat() + "Z",
        "reps_per_scenario": reps,
        "methodology": "binary detection per slice; S1 measures FPR/accuracy, S2-S6 measures recall/latency; Rata-rata Hibrida aggregates across S1-S6",
        "scenarios": results,
        "average": average,
    }
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"\n[OK] Hasil disimpan: {OUT_FILE}")

    print_table(results, average)


if __name__ == "__main__":
    main()
