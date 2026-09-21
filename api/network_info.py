"""
network_info.py — Unified Network Guard: API
===============================================
Deteksi informasi jaringan yang sedang tersambung (dinamis).

Tidak terkunci pada satu interface: interface aktif dideteksi otomatis
dari default route (koneksi internet/utama), lalu IP, subnet, dan gateway
diambil dari interface tersebut. Dengan begitu dashboard menyesuaikan
jaringan yang tersambung saat itu — WiFi, Ethernet/LAN, hotspot, dsb.
"""

import ipaddress
import os
import re
import subprocess
import time
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

# Fallback dari environment (dipakai jika tidak ada default route / deteksi gagal)
CAPTURE_INTERFACE: str = os.getenv('CAPTURE_INTERFACE', 'enp9s0')
IOT_SUBNET: str = os.getenv('IOT_SUBNET', '192.168.41.0/24')


def suricata_is_running(fresh_seconds: float = 30.0) -> bool:
    """
    Deteksi jujur apakah Suricata IDS aktif: eve.json ditulis Suricata setiap
    ada event — jika mtime-nya diperbarui dalam N detik terakhir, Suricata
    dianggap berjalan (dan log bisa dibaca tanpa root: file readable).

    Returns:
        True jika /var/log/suricata/eve.json baru ditulis dalam fresh_seconds.
    """
    try:
        path = os.environ.get('SURICATA_EVE_PATH', '/var/log/suricata/eve.json')
        mtime = os.path.getmtime(path)
        return (time.time() - mtime) <= fresh_seconds
    except Exception:
        return False


def _run(cmd: list[str]) -> str:
    """Jalankan perintah, kembalikan stdout (kosong jika gagal)."""
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        return out.stdout.strip()
    except Exception:
        return ''


def detect_active_interface() -> str | None:
    """
    Interface aktif = interface yang membawa default route (koneksi utama).
    Contoh output: "default via 192.168.20.1 dev enp9s0 proto dhcp ..."
    """
    out = _run(['ip', 'route', 'show', 'default'])
    m = re.search(r'default\s+via\s+\S+\s+dev\s+(\S+)', out)
    return m.group(1) if m else None


def detect_local_ip(iface: str) -> str | None:
    """IP lokal (IPv4) dari interface yang sedang aktif."""
    out = _run(['ip', '-4', '-o', 'addr', 'show', iface])
    # Contoh: "2: enp9s0    inet 192.168.20.101/24 brd 192.168.20.255 ..."
    m = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)', out)
    return m.group(1) if m else None


def detect_subnet(iface: str) -> str | None:
    """Subnet CIDR aktual dari interface (misal 192.168.20.0/24)."""
    out = _run(['ip', '-4', '-o', 'addr', 'show', iface])
    m = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)/(\d+)', out)
    if not m:
        return None
    try:
        return str(ipaddress.ip_network(f'{m.group(1)}/{m.group(2)}', strict=False))
    except Exception:
        return None


def detect_gateway(iface: str) -> str | None:
    """Gateway default pada interface aktif (via 'ip route')."""
    out = _run(['ip', 'route', 'show', 'dev', iface])
    m = re.search(r'default\s+via\s+(\d+\.\d+\.\d+\.\d+)', out)
    if m:
        return m.group(1)
    # Fallback: cari via di route default global
    out2 = _run(['ip', 'route', 'show', 'default'])
    m2 = re.search(r'via\s+(\d+\.\d+\.\d+\.\d+)', out2)
    return m2.group(1) if m2 else None


def get_network_info() -> dict:
    """Kumpulkan informasi jaringan saat ini (dinamis, interface-agnostic)."""
    iface = detect_active_interface() or CAPTURE_INTERFACE
    local_ip = detect_local_ip(iface)
    subnet = detect_subnet(iface) or IOT_SUBNET
    gateway = detect_gateway(iface)
    return {
        'interface': iface,
        'subnet':    subnet,
        'local_ip':  local_ip,
        'gateway':   gateway,
    }