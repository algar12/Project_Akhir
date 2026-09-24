#!/usr/bin/env bash
# ==============================================================================
# ung.sh — Unified Network Guard · One-Click Launcher
# ==============================================================================
# Menjalankan SELURUH platform UNG dengan satu perintah.
#
#   ./ung.sh start [--sim] [--dash] [--no-suricata]   # start semua
#   ./ung.sh stop                                     # hentikan semua
#   ./ung.sh status                                   # cek status tiap service
#   ./ung.sh logs <service>                           # tail log (suricata/collector/detection/predictor/api/dashboard/simulator)
#   ./ung.sh restart <service>                        # restart satu service
#
# Service yang dijalankan (berurutan):
#   docker   (infra: postgres, mosquitto, grafana)   — via docker compose
#   suricata (IDS signature, butuh sudo)            — scripts/start_suricata.sh
#   collector (sniffer Scapy + MQTT subscriber)
#   detection (rule engine + eve parser + alert manager)
#   predictor (ML inferensi real-time IF+RF)
#   api       (FastAPI :8000)
#   dashboard (Next.js :3001)            [opsional, --dash]
#   simulator (5 ESP32 MQTT simulator)  [opsional, --sim]
#
# Log: logs/<service>.log   PID: logs/.pids/<service>.pid
# ==============================================================================
set -uo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

VENV="$PROJECT_DIR/venv/bin/activate"
LOG_DIR="$PROJECT_DIR/logs"
PID_DIR="$PROJECT_DIR/logs/.pids"
mkdir -p "$LOG_DIR" "$PID_DIR"

# Warna
G="\033[1;32m"; Y="\033[1;33m"; R="\033[1;31m"; C="\033[1;36m"; N="\033[0m"
say() { echo -e "${C}[UNG]${N} $*"; }
ok()  { echo -e "${G}✓${N} $*"; }
warn(){ echo -e "${Y}⚠${N} $*"; }
err() { echo -e "${R}✗${N} $*"; }

# Service python (pakai venv)
PY_SVCS=(collector detection predictor api)
ALL_SVCS=(suricata collector detection predictor api dashboard simulator)

# ─── Helpers ────────────────────────────────────────────────────────────────
activate_venv() {
  if [ -f "$VENV" ]; then source "$VENV"; else warn "venv tidak ditemukan di $VENV"; return 1; fi
}

is_running() {  # arg: service name
  local pidfile="$PID_DIR/$1.pid"
  [ -f "$pidfile" ] || return 1
  local pid; pid="$(cat "$pidfile" 2>/dev/null)"
  # ps -p bekerja untuk proses milik root (suricata/collector) tanpa izin, beda dengan kill -0
  [ -n "$pid" ] && ps -p "$pid" >/dev/null 2>&1
}

PYBIN="$PROJECT_DIR/venv/bin/python"

start_py_svc() {  # arg: service name
  local svc="$1" log="$LOG_DIR/$1.log" pidfile="$PID_DIR/$1.pid"
  if is_running "$svc"; then warn "$svc sudah jalan (pid $(cat "$pidfile"))"; return 0; fi
  # Pakai array agar path ber-spasi ("project akhir") tidak ter-split
  local -a cmd=()
  case "$svc" in
    collector)  cmd=(sudo "$PYBIN" -m collector.main) ;;            # Scapy butuh sudo
    detection)  cmd=("$PYBIN" -m detection.main) ;;
    predictor)  cmd=("$PYBIN" -m ml.main predict --with-alerts) ;;  # --with-alerts wajib supaya ML emit alert
    api)        cmd=("$PYBIN" -m api.server) ;;
    *) err "service py tidak dikenal: $svc"; return 1 ;;
  esac
  nohup "${cmd[@]}" > "$log" 2>&1 &
  echo $! > "$pidfile"
  sleep 3
  if is_running "$svc"; then ok "$svc mulai (pid $(cat "$pidfile")) → $log"; else err "$svc gagal mulai — cek $log"; fi
}

start_suricata() {
  local pidfile="$PID_DIR/suricata.pid" log="$LOG_DIR/suricata.log"
  # Cek instance suricata yang sudah jalan (pgrep), reuse — jangan tumpuk
  local existing; existing="$(pgrep -f "suricata -c.*suricata.yaml" | head -1)"
  if [ -n "$existing" ]; then echo "$existing" > "$pidfile"; ok "suricata sudah jalan (pid $existing) — reuse"; return 0; fi
  if is_running "suricata"; then warn "suricata sudah jalan"; return 0; fi
  if ! command -v suricata >/dev/null; then warn "suricata belum terinstall — skip"; return 1; fi
  # sudo sudah di-autentikasi sekali di cmd_start (sudo -v). Background suricata dengan kredensial cache.
  sudo bash "$PROJECT_DIR/scripts/start_suricata.sh" > "$log" 2>&1 &
  # Beri waktu Suricata inisialisasi (load rules ~3-5s)
  local pid=""
  for i in $(seq 1 10); do
    pid="$(pgrep -f "suricata -c.*suricata.yaml" | head -1)"
    [ -n "$pid" ] && break
    sleep 1
  done
  if [ -n "$pid" ]; then echo "$pid" > "$pidfile"; ok "suricata mulai (pid $pid) → $log"; else err "suricata gagal mulai — cek $log"; fi
}

sudo_auth_once() {
  # Autentikasi sudo sekali di foreground (prompt menunggu sampai selesai).
  # Dipakai bersama oleh suricata & collector (Scapy raw socket).
  if sudo -n true 2>/dev/null; then ok "sudo sudah ter-cache (tanpa password)"; return 0; fi
  say "platform butuh sudo (Suricata + Scapy collector) — silakan ketik password (prompt menunggu sampai selesai):"
  if ! sudo -v; then err "autentikasi sudo gagal — service butuh-sudo dilewati"; return 1; fi
  ok "sudo ter-autentikasi (ter-cache ~15 menit)"
}

start_docker() {
  if ! command -v docker >/dev/null; then warn "docker belum terinstall — infra DB/MQTT tidak jalan"; return 1; fi
  say "docker compose up -d ..."
  docker compose up -d >/dev/null 2>&1
  # tunggu postgres sehat
  for i in $(seq 1 15); do
    if docker exec ung_postgres pg_isready -U guard_user >/dev/null 2>&1; then ok "infra siap (postgres, mosquitto, grafana)"; return 0; fi
    sleep 1
  done
  warn "postgres belum siap setelah 15s — lanjut saja"
}

start_dashboard() {
  local pidfile="$PID_DIR/dashboard.pid" log="$LOG_DIR/dashboard.log"
  if is_running "dashboard"; then warn "dashboard sudah jalan"; return 0; fi
  if [ ! -d "$PROJECT_DIR/dashboard/node_modules" ]; then
    warn "dashboard/node_modules belum ada — jalankan: cd dashboard && npm install"; return 1
  fi
  (cd "$PROJECT_DIR/dashboard" && nohup npm run dev > "$log" 2>&1 & echo $! > "$pidfile")
  sleep 2
  ok "dashboard mulai (pid $(cat "$pidfile")) → http://localhost:3001 → $log"
}

start_simulator() {
  local pidfile="$PID_DIR/simulator.pid" log="$LOG_DIR/simulator.log"
  if is_running "simulator"; then warn "simulator sudah jalan"; return 0; fi
  nohup $PYBIN tools/simulate_esp32.py --all > "$log" 2>&1 &
  echo $! > "$pidfile"
  sleep 1
  ok "simulator ESP32 mulai (pid $(cat "$pidfile")) → $log"
}

# ─── Perintah ───────────────────────────────────────────────────────────────
cmd_start() {
  local run_sim=0 run_dash=0 run_suricata=1
  while [ $# -gt 0 ]; do
    case "$1" in
      --sim) run_sim=1 ;;
      --dash) run_dash=1 ;;
      --no-suricata) run_suricata=0 ;;
      *) warn "flag tidak dikenal: $1" ;;
    esac
    shift
  done

  say "=== START Unified Network Guard ==="
  activate_venv || { err "venv wajib. Jalankan: python3 -m venv venv && pip install -r requirements.txt"; exit 1; }

  # 0. pre-flight
  [ -f "$PROJECT_DIR/.env" ] || { err ".env tidak ada — salin dari .env.example"; exit 1; }
  [ -d "$PROJECT_DIR/ml/models" ] && [ -f "$PROJECT_DIR/ml/models/isolation_forest.pkl" ] || warn "model ML belum ada — predictor akan gagal"

  # 1. infra docker
  start_docker

  # 1b. autentikasi sudo sekali (untuk suricata + collector Scapy)
  sudo_auth_once

  # 2. suricata
  [ "$run_suricata" -eq 1 ] && start_suricata || warn "suricata dilewati (--no-suricata)"

  # 3. pipeline python
  for svc in "${PY_SVCS[@]}"; do start_py_svc "$svc"; done

  # 4. opsional
  [ "$run_sim" -eq 1 ] && start_simulator
  [ "$run_dash" -eq 1 ] && start_dashboard

  echo
  say "=== STATUS ==="
  cmd_status
  echo
  ok "Akses:"
  echo "    Dashboard : http://localhost:3001   (--dash)"
  echo "    API       : http://localhost:8000   (docs: /docs)"
  echo "    Grafana   : http://localhost:3000"
  echo "    Cek log   : ./ung.sh logs <service>"
  echo "    Stop      : ./ung.sh stop"
}

cmd_stop() {
  say "menghentikan semua service..."
  for svc in "${ALL_SVCS[@]}"; do
    local pidfile="$PID_DIR/$svc.pid"
    if [ -f "$pidfile" ]; then
      local pid; pid="$(cat "$pidfile" 2>/dev/null)"
      if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        kill "$pid" 2>/dev/null
        # beri waktu, lalu SIGKILL jika perlu
        for i in 1 2 3; do kill -0 "$pid" 2>/dev/null || break; sleep 0.5; done
        kill -9 "$pid" 2>/dev/null
        ok "$svc dihentikan"
      else
        rm -f "$pidfile"
      fi
    fi
  done
  # suricata: matikan SEMUA instance (sudo pkill, ada di luar pidfile karena berjalan sebagai root)
  if pgrep -f "suricata -c.*suricata.yaml" >/dev/null 2>&1; then
    sudo pkill -f "suricata -c.*suricata.yaml" 2>/dev/null
    for i in 1 2 3 4 5; do pgrep -f "suricata -c.*suricata.yaml" >/dev/null 2>&1 || break; sleep 0.5; done
    sudo pkill -9 -f "suricata -c.*suricata.yaml" 2>/dev/null
    # juga matikan skrip pembungkusnya
    sudo pkill -f "scripts/start_suricata.sh" 2>/dev/null
    ok "suricata dihentikan (semua instance)"
  fi
  # collector berjalan sebagai root (sudo) — pastikan juga mati
  if pgrep -f "python -m collector.main" >/dev/null 2>&1; then
    sudo pkill -f "python -m collector.main" 2>/dev/null
    ok "collector dihentikan (root)"
  fi
  rm -f "$PID_DIR"/*.pid
  say "docker infra tetap jalan (hentikan manual: docker compose down)"
}

cmd_status() {
  printf "%-12s %-8s %-8s %s\n" "SERVICE" "STATUS" "PID" "LOG"
  printf "%-12s %-8s %-8s %s\n" "-------" "------" "---" "---"
  for svc in "${ALL_SVCS[@]}"; do
    local pidfile="$PID_DIR/$svc.pid" pid="-" st="${R}DOWN${N}"
    if [ -f "$pidfile" ] && is_running "$svc"; then
      pid="$(cat "$pidfile")"; st="${G}UP${N}"
    fi
    printf "%-12s %-8s %-8s logs/%s.log\n" "$svc" "$(echo -e "$st")" "$pid" "$svc"
  done
  # docker
  if command -v docker >/dev/null; then
    local dc; dc="$(docker ps --format '{{.Names}}' 2>/dev/null | grep -c ung_)"
    printf "%-12s %-8s %-8s %s\n" "docker-infra" "$(echo -e "${G:-}$([ $dc -gt 0 ] && echo UP || echo DOWN)${N}")" "$dc" "ung_postgres/ung_mosquitto/ung_grafana"
  fi
}

cmd_logs() {
  local svc="${1:-}"
  [ -z "$svc" ] && { say "pakai: ./ung.sh logs <service>  (suricata|collector|detection|predictor|api|dashboard|simulator)"; return; }
  local log="$LOG_DIR/$svc.log"
  [ -f "$log" ] && { say "tail -f $log (Ctrl+C keluar)"; tail -n 50 -f "$log"; } || err "log tidak ada: $log"
}

cmd_restart() {
  local svc="${1:-}"
  case "$svc" in
    suricata) start_suricata ;;
    dashboard) start_dashboard ;;
    simulator) start_simulator ;;
    collector|detection|predictor|api)
      local pidfile="$PID_DIR/$svc.pid"
      [ -f "$pidfile" ] && kill "$(cat "$pidfile")" 2>/dev/null && sleep 1
      rm -f "$pidfile"; start_py_svc "$svc" ;;
    *) err "service tidak dikenal: $svc";;
  esac
}

# ─── Main ───────────────────────────────────────────────────────────────────
case "${1:-}" in
  start)   shift; cmd_start "$@" ;;
  stop)    cmd_stop ;;
  status)  cmd_status ;;
  logs)    shift; cmd_logs "$@" ;;
  restart) shift; cmd_restart "$@" ;;
  *) echo "Pakai: ./ung.sh {start [--sim] [--dash] [--no-suricata] | stop | status | logs <svc> | restart <svc>}"; exit 1 ;;
esac
