#!/usr/bin/env bash
# ==============================================================================
# termux_setup.sh — UNG Phone Attacker setup (Android / Termux)
# ==============================================================================
# Jalankan SEKALI di Termux di HP untuk menyiapkan environment attacker.
#
# Cara pakai (di HP):
#   1. Install Termux dari F-Droid (versi Play Store usang, jangan dipakai)
#   2. Buka Termux, jalankan:
#        pkg update && pkg upgrade -y
#        pkg install -y python git
#   3. Salin proyek ke HP (atau git clone), lalu:
#        cd unified-network-guard
#        bash tools/termux_setup.sh
#
# Setelah setup selesai, hubungkan HP ke WiFi router upstream TL-WR840N,
# lalu jalankan:
#        python tools/attacker.py
#
# Tidak butuh root. Tidak butuh pip install (attacker.py pakai stdlib saja).
# ==============================================================================
set -e

echo "[1/4] Cek Termux & package manager..."
if ! command -v pkg >/dev/null 2>&1; then
  echo "✗ Ini bukan Termux (pkg tidak ada). Install Termux dari F-Droid."
  exit 1
fi

echo "[2/4] Install python (jika belum)..."
if ! command -v python >/dev/null 2>&1 && ! command -v python3 >/dev/null 2>&1; then
  pkg install -y python
fi
PY="$(command -v python3 || command -v python)"
echo "  python: $($PY --version 2>&1)"

echo "[3/4] (Opsional) Install nmap untuk verifikasi scan manual..."
if ! command -v nmap >/dev/null 2>&1; then
  pkg install -y nmap || echo "  (nmap opsional — attacker.py tetap jalan tanpa ini)"
fi

echo "[4/4] Tes syntax attacker.py..."
$PY -m py_compile tools/attacker.py && echo "  ✓ attacker.py syntax OK" || { echo "  ✗ syntax error"; exit 1; }

echo ""
echo "═══════════════════════════════════════════════════════════"
echo " SETUP SELESAI"
echo "═══════════════════════════════════════════════════════════"
echo " Langkah berikutnya:"
echo "   1. Hubungkan HP ke WiFi router UPSTREAM (TL-WR840N, 192.168.10.1)"
echo "      BUKAN router IoT (TL-WR820N, 192.168.20.1)."
echo "   2. Pastikan pipeline UNG jalan di Edge PC:"
echo "        ./ung.sh start --sim"
echo "   3. Di Termux jalankan:"
echo "        python tools/attacker.py"
echo "      atau eval penuh satu-ketuk:"
echo "        python tools/attacker.py --auto"
echo ""
echo " Cek jaringan dari menu attacker (pilih 0):"
echo "   - IP HP harus 192.168.10.x"
echo "   - Edge PC 192.168.20.100:1883 reachable"
echo "═══════════════════════════════════════════════════════════"
