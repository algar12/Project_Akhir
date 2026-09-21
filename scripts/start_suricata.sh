#!/usr/bin/env bash
# ==============================================================================
# start_suricata.sh — Unified Network Guard
# ==============================================================================
# Menjalankan Suricata IDS untuk demo/testbed IoT Defense Lab.
# Membutuhkan sudo (raw socket). Memakai konfigurasi proyek:
#   suricata/suricata.yaml + suricata/rules/local.rules (14 SID)
#
# Penggunaan:
#   sudo bash scripts/start_suricata.sh [interface]
#
# Default interface = CAPTURE_INTERFACE dari .env (jika tersedia) → enp9s0.
# ==============================================================================
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONF="$PROJECT_DIR/suricata/suricata.yaml"

# Interface dari argumen atau .env
IFACE="${1:-}"
if [ -z "$IFACE" ] && [ -f "$PROJECT_DIR/.env" ]; then
    IFACE="$(grep -E '^CAPTURE_INTERFACE=' "$PROJECT_DIR/.env" | head -1 | cut -d= -f2)"
fi
IFACE="${IFACE:-enp9s0}"

echo "[UNG] Memulai Suricata pada interface: $IFACE"
echo "[UNG] Konfigurasi : $CONF"
echo "[UNG] Rules       : $PROJECT_DIR/suricata/rules/local.rules"

# Pastikan rule dapat ditemukan relatif terhadap konfigurasi
cd "$PROJECT_DIR/suricata"

exec suricata -c "$CONF" -i "$IFACE"