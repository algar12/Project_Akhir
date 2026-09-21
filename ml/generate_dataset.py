"""
generate_dataset.py — Generator dataset berlabel untuk Unified Network Guard ML.

1. Ambil fitur traffic NYATA dari DB (24 jam terakhir) → kelas 'normal'
2. Generate serangan sintetik realistis (dengan noise) untuk 5 kelas serangan
3. Simpan:
   - ml/datasets/normal.csv   (untuk training Isolation Forest)
   - ml/datasets/labeled.csv  (untuk training Random Forest)
"""

import os
import sys
import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

sys.path.insert(0, '/home/gopung/Desktop/project akhir/unified-network-guard')

from ml.config import (
    FEATURE_COLUMNS, FEATURE_WINDOW_SECONDS, DATASET_DIR, RF_CLASSES,
)
from ml.feature_extractor import extract_from_db

random.seed(42)
np.random.seed(42)

WINDOW = FEATURE_WINDOW_SECONDS  # 10 detik


def _norm_vec(rng, base):
    """Vector fitur normal berdasarkan sampel nyata + sedikit noise."""
    vec = base.copy()
    for c in FEATURE_COLUMNS:
        if c in ('proto_tcp_ratio', 'proto_udp_ratio', 'proto_icmp_ratio', 'mqtt_ratio'):
            vec[c] = np.clip(vec[c] + rng.normal(0, 0.03), 0.0, 1.0)
        else:
            vec[c] = max(0.0, vec[c] * (1 + rng.normal(0, 0.10)))
    return vec


def _clamp(vec, limits):
    for c, (lo, hi) in limits.items():
        vec[c] = float(np.clip(vec[c], lo, hi))
    return vec


def _make_attack(base, kind, n, rng):
    rows = []
    limits = {}

    for _ in range(n):
        vec = _norm_vec(rng, base)

        if kind == 'port_scan':
            # Banyak port tujuan berbeda, paket kecil (SYN), rate sedang-tinggi.
            # Rentang lebar: nmap scan bisa menyentuh ratusan-ribuan port & ratusan pkt/s.
            vec['unique_dst_ports'] = rng.uniform(20, 3000)
            vec['unique_dst_ips'] = rng.uniform(1, 10)
            vec['packet_rate'] = rng.uniform(5, 350)
            vec['packet_count'] = vec['packet_rate'] * WINDOW
            vec['avg_packet_size'] = rng.uniform(60, 120)
            vec['byte_count'] = vec['avg_packet_size'] * vec['packet_count']
            vec['byte_rate'] = vec['byte_count'] / WINDOW
            vec['proto_tcp_ratio'] = rng.uniform(0.6, 1.0)
            vec['proto_udp_ratio'] = 1 - vec['proto_tcp_ratio']
            vec['proto_icmp_ratio'] = 0.0
            vec['mqtt_ratio'] = 0.0

        elif kind == 'syn_flood':
            # Ledakan paket TCP kecil (SYN), rate sangat tinggi, port tujuan sedikit.
            # Penting: byte_rate HARUS konsisten = avg_packet_size × packet_rate.
            vec['unique_dst_ports'] = rng.uniform(1, 5)
            vec['unique_dst_ips'] = rng.uniform(1, 3)
            vec['packet_rate'] = rng.uniform(60, 600)
            vec['packet_count'] = vec['packet_rate'] * WINDOW
            vec['avg_packet_size'] = rng.uniform(40, 64)   # paket SYN nyata kecil
            vec['byte_count'] = vec['avg_packet_size'] * vec['packet_count']
            vec['byte_rate'] = vec['byte_count'] / WINDOW
            vec['proto_tcp_ratio'] = rng.uniform(0.95, 1.0)
            vec['proto_udp_ratio'] = 0.0
            vec['proto_icmp_ratio'] = 0.0
            vec['mqtt_ratio'] = 0.0

        elif kind == 'icmp_flood':
            # Banjir ICMP echo request: hampir semua paket ICMP, rate tinggi.
            # byte_rate konsisten = avg_packet_size × packet_rate.
            vec['unique_dst_ports'] = 0.0
            vec['unique_dst_ips'] = rng.uniform(1, 4)
            vec['packet_rate'] = rng.uniform(60, 600)
            vec['packet_count'] = vec['packet_rate'] * WINDOW
            vec['avg_packet_size'] = rng.uniform(60, 90)
            vec['byte_count'] = vec['avg_packet_size'] * vec['packet_count']
            vec['byte_rate'] = vec['byte_count'] / WINDOW
            vec['proto_tcp_ratio'] = 0.0
            vec['proto_udp_ratio'] = 0.0
            vec['proto_icmp_ratio'] = rng.uniform(0.9, 1.0)
            vec['mqtt_ratio'] = 0.0

        elif kind == 'traffic_spike':
            # Lonjakan volume traffic: paket besar, byte_rate sangat besar.
            # byte_rate konsisten = avg_packet_size × packet_rate.
            vec['unique_dst_ports'] = rng.uniform(1, 20)
            vec['unique_dst_ips'] = rng.uniform(1, 10)
            vec['packet_rate'] = rng.uniform(20, 200)
            vec['packet_count'] = vec['packet_rate'] * WINDOW
            vec['avg_packet_size'] = rng.uniform(800, 1_500)
            vec['byte_count'] = vec['avg_packet_size'] * vec['packet_count']
            vec['byte_rate'] = vec['byte_count'] / WINDOW
            vec['proto_tcp_ratio'] = rng.uniform(0.5, 1.0)
            vec['proto_udp_ratio'] = 1 - vec['proto_tcp_ratio']
            vec['proto_icmp_ratio'] = 0.0
            vec['mqtt_ratio'] = rng.uniform(0.0, 0.3)

        elif kind == 'mqtt_anomaly':
            # Penyalahgunaan MQTT: hampir semua paket ke port 1883, rate tinggi.
            # byte_rate konsisten = avg_packet_size × packet_rate.
            vec['unique_dst_ports'] = rng.uniform(1, 3)
            vec['unique_dst_ips'] = rng.uniform(1, 3)
            vec['packet_rate'] = rng.uniform(30, 300)
            vec['packet_count'] = vec['packet_rate'] * WINDOW
            vec['avg_packet_size'] = rng.uniform(80, 300)
            vec['byte_count'] = vec['avg_packet_size'] * vec['packet_count']
            vec['byte_rate'] = vec['byte_count'] / WINDOW
            vec['proto_tcp_ratio'] = rng.uniform(0.9, 1.0)
            vec['proto_udp_ratio'] = 0.0
            vec['proto_icmp_ratio'] = 0.0
            vec['mqtt_ratio'] = rng.uniform(0.85, 1.0)

        # Jaga agar semua nilai non-negatif
        vec['packet_count'] = max(vec['packet_count'], 1)
        vec['connection_count'] = vec['packet_count']
        vec['packet_rate'] = vec['packet_count'] / WINDOW
        vec['byte_rate'] = vec['byte_count'] / WINDOW
        vec['avg_packet_size'] = vec['byte_count'] / vec['packet_count']
        rows.append({c: vec[c] for c in FEATURE_COLUMNS} | {'label': kind})

    return pd.DataFrame(rows)


def _make_archetypes(n: int, rng) -> pd.DataFrame:
    """
    Archetype: pola serangan realistis khas tool penetrasi (nmap, hping3,
    ping flood, slowloris-ish, MQTT abuse). Nilai ditentukan manual sesuai
    karakteristik nyata + noise kecil, agar RF robust pada kombinasi ekstrem
    yang tidak tercakup oleh distribusi random yang terlalu sempit.

    Setiap archetype konsisten: byte_count = avg_packet_size × packet_count.
    """
    archetypes = []

    def add(kind, base):
        rows = []
        for _ in range(n):
            vec = _norm_vec(rng, base)
            for c in base:
                if c in ('proto_tcp_ratio', 'proto_udp_ratio', 'proto_icmp_ratio', 'mqtt_ratio'):
                    vec[c] = float(np.clip(vec[c] + rng.normal(0, 0.02), 0.0, 1.0))
                elif c in ('unique_dst_ports', 'unique_dst_ips'):
                    vec[c] = max(1.0, vec[c] * (1 + rng.normal(0, 0.15)))
                else:
                    vec[c] = max(0.0, vec[c] * (1 + rng.normal(0, 0.08)))
            vec['packet_count'] = max(vec['packet_rate'] * WINDOW, 1)
            vec['byte_count'] = vec['avg_packet_size'] * vec['packet_count']
            vec['packet_rate'] = vec['packet_count'] / WINDOW
            vec['byte_rate'] = vec['byte_count'] / WINDOW
            vec['connection_count'] = vec['packet_count']
            vec['avg_packet_size'] = vec['byte_count'] / vec['packet_count']
            rows.append({c: vec[c] for c in FEATURE_COLUMNS} | {'label': kind})
        return rows

    # hping3 -S --flood ke satu port (SYN flood murni)
    archetypes += add('syn_flood', {
        'packet_rate': 400, 'byte_count': 240000, 'packet_count': 4000,
        'connection_count': 4000, 'byte_rate': 24000, 'avg_packet_size': 60,
        'unique_dst_ports': 1, 'unique_dst_ips': 1,
        'proto_tcp_ratio': 1.0, 'proto_udp_ratio': 0.0,
        'proto_icmp_ratio': 0.0, 'mqtt_ratio': 0.0,
    })
    # nmap -sS: ribuan port, paket kecil SYN
    archetypes += add('port_scan', {
        'packet_rate': 300, 'byte_count': 180000, 'packet_count': 3000,
        'connection_count': 3000, 'byte_rate': 18000, 'avg_packet_size': 60,
        'unique_dst_ports': 3000, 'unique_dst_ips': 1,
        'proto_tcp_ratio': 1.0, 'proto_udp_ratio': 0.0,
        'proto_icmp_ratio': 0.0, 'mqtt_ratio': 0.0,
    })
    # ping flood: semua ICMP echo request
    archetypes += add('icmp_flood', {
        'packet_rate': 500, 'byte_count': 320000, 'packet_count': 5000,
        'connection_count': 5000, 'byte_rate': 32000, 'avg_packet_size': 64,
        'unique_dst_ports': 0, 'unique_dst_ips': 10,
        'proto_tcp_ratio': 0.0, 'proto_udp_ratio': 0.0,
        'proto_icmp_ratio': 1.0, 'mqtt_ratio': 0.0,
    })
    # Lonjakan unduhan / streaming: paket besar, byte_rate tinggi
    archetypes += add('traffic_spike', {
        'packet_rate': 150, 'byte_count': 1800000, 'packet_count': 1500,
        'connection_count': 1500, 'byte_rate': 180000, 'avg_packet_size': 1200,
        'unique_dst_ports': 5, 'unique_dst_ips': 3,
        'proto_tcp_ratio': 0.9, 'proto_udp_ratio': 0.1,
        'proto_icmp_ratio': 0.0, 'mqtt_ratio': 0.0,
    })
    # Penyalahgunaan MQTT: lalu lintas padat ke port 1883
    archetypes += add('mqtt_anomaly', {
        'packet_rate': 200, 'byte_count': 300000, 'packet_count': 2000,
        'connection_count': 2000, 'byte_rate': 30000, 'avg_packet_size': 150,
        'unique_dst_ports': 1, 'unique_dst_ips': 1,
        'proto_tcp_ratio': 1.0, 'proto_udp_ratio': 0.0,
        'proto_icmp_ratio': 0.0, 'mqtt_ratio': 0.95,
    })

    return pd.DataFrame(archetypes)


def main():
    os.makedirs(DATASET_DIR, exist_ok=True)

    # ── 1. Ambil data normal NYATA dari DB ──────────────────────────────────
    print('[1/3] Mengekstrak fitur normal dari DB (24 jam terakhir)...')
    until = datetime.now()
    since = until - timedelta(hours=24)
    df_norm = extract_from_db(since=since, until=until)
    if df_norm.empty:
        print('❌ Tidak ada data di DB.')
        sys.exit(1)

    df_norm = df_norm.drop(columns=['source_ip', 'time_bucket'])
    df_norm['label'] = 'normal'
    df_norm = df_norm[FEATURE_COLUMNS + ['label']]
    print(f'   → {len(df_norm)} sampel normal nyata')

    # ── 2. Generate serangan sintetik ───────────────────────────────────────
    print('[2/3] Menggenerate serangan sintetik...')
    rng = np.random.default_rng(42)
    # Base vector: ambil sampel nyata acak sebagai "dasar"
    base_vecs = df_norm[FEATURE_COLUMNS].to_numpy()

    attack_dfs = []
    N_PER_CLASS = 600
    for kind in ['port_scan', 'syn_flood', 'icmp_flood', 'traffic_spike', 'mqtt_anomaly']:
        base_row = base_vecs[rng.integers(0, len(base_vecs))]
        base_dict = dict(zip(FEATURE_COLUMNS, base_row))
        attack_df = _make_attack(base_dict, kind, N_PER_CLASS, rng)
        attack_dfs.append(attack_df)
        print(f'   → {kind}: {len(attack_df)} sampel random')

    # Archetype: pola serangan realistis khas tool (nmap, hping3, ping flood) —
    # dipastikan masuk training agar RF tidak miss pada kombinasi ekstrem.
    archetypes = _make_archetypes(N_PER_CLASS // 2, rng)
    attack_dfs.append(archetypes)
    print(f'   → archetypes (tool nyata): {len(archetypes)} sampel')

    df_labeled = pd.concat([df_norm] + attack_dfs, ignore_index=True)

    # ── 3. Simpan ───────────────────────────────────────────────────────────
    normal_path = os.path.join(DATASET_DIR, 'normal.csv')
    labeled_path = os.path.join(DATASET_DIR, 'labeled.csv')

    df_norm.to_csv(normal_path, index=False)
    df_labeled.to_csv(labeled_path, index=False)

    print(f'[3/3] Tersimpan:')
    print(f'   • {normal_path}  ({len(df_norm)} baris)')
    print(f'   • {labeled_path} ({len(df_labeled)} baris)')
    print('\nDistribusi label:')
    print(df_labeled['label'].value_counts().to_string())


if __name__ == '__main__':
    main()