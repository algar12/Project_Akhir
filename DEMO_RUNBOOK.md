# DEMO RUNBOOK — Unified Network Guard (IoT Defense Lab)

Checklist langkah-demi-langkah untuk menjalankan & mendemonstrasikan seluruh sistem.
Dokumen ini mengacu kondisi **aktual** sistem (timezone UTC konsisten, deteksi pada data nyata).

---

## 1. Arsitektur Singkat (yang didemo)

```
┌─ Data Source ──────────────────────────────────────────────────────────┐
│ ESP32 node (asli/simulator) → MQTT Mosquitto :1883                    │
│ Trafik jaringan nyata (Scapy, enp9s0, filter net IOT_SUBNET)          │
│ Suricata IDS (AF_PACKET enp9s0, 14 rules → /var/log/suricata/eve.json)│
└──────────────────────────────┬─────────────────────────────────────────┘
                               ▼
┌─ Storage: PostgreSQL (UTC) ────────────────────────────────────────────┐
│ network_traffic · mqtt_telemetry · alerts · ml_predictions · devices  │
└───────────────┬───────────────────────────────┬───────────────────────┘
                ▼                               ▼
┌─ Detection ──────────────────────┐   ┌─ ML Predictor ─────────────────┐
│ RuleEngine (5 rule, id-checkpoint)│   │ Isolation Forest (kalibrasi)  │
│ EveParser (tail eve.json)         │   │ Random Forest (klasifikasi)   │
└───────────────┬───────────────────┘   └──────────────┬────────────────┘
                └──────────────┬───────────────────────┘
                               ▼
                    ┌─ AlertManager (dedup) ─┐
                    └──────────┬──────────────┘
                               ▼
        ┌─ API FastAPI :8000 (X-API-Key) ─┐
        │ REST + WebSocket /ws/alerts      │
        └──────────────┬───────────────────┘
                       ▼
            Dashboard Next.js :3001
```

**Aturan kejujuran demo:** semua angka berasal dari data nyata yang mengalir saat itu.
Tidak ada fallback buatan (mis. "40896 paket"). Serangan disimulasikan **hanya saat presentasi**,
dari mesin penyerang terpisah, dan dihentikan setelah ditunjukkan.

---

## 2. Prasyarat

| Komponen | Keterangan |
|---|---|
| Docker Compose | PostgreSQL, Mosquitto, Grafana |
| Python venv | `venv/` di root proyek (dependencies terpasang) |
| Node.js | Dashboard Next.js |
| Suricata | Terpasang (`/usr/bin/suricata` v8.0.3) |
| sudo | Untuk collector (raw socket) & Suricata (AF_PACKET) |
| Mesin penyerang (opsional) | Perangkat lain di LAN `192.168.20.0/24` untuk skenario serangan |

Konfigurasi aktif (`.env`):
- `CAPTURE_INTERFACE=enp9s0` · `IOT_SUBNET=192.168.20.0/24` · `TRAFFIC_SPIKE_BPS=5000000`
- `API_KEY=dummy_key` · CORS/rate-limit aktif
- Semua timestamp **UTC** (host WIB +7 → data tersimpan UTC)

---

## 3. Menjalankan Layanan (urut)

Semua dari root proyek: `cd /home/gopung/Desktop/project akhir/unified-network-guard`

```bash
# 1. Infrastruktur (PostgreSQL, Mosquitto, Grafana)
docker compose up -d

# 2. API (FastAPI) — terminal 1
venv/bin/uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload

# 3. Dashboard — terminal 2
cd dashboard && npm run dev        # → http://localhost:3001

# 4. Detection (rule engine + EveParser) — terminal 3
venv/bin/python -m detection.main

# 5. ML Predictor — terminal 4
venv/bin/python -m ml.main predict --with-alerts

# 6. Collector (butuh sudo) — terminal 5
sudo ./venv/bin/python -m collector.main

# 7. Suricata IDS (butuh sudo) — terminal 6
sudo bash scripts/start_suricata.sh
```

> Catatan: API + dashboard biasanya sudah berjalan. Jika sudah, lewati langkah 2–3.

---

## 4. Verifikasi Kesehatan (sebelum demo)

```bash
# API
curl -s -H "X-API-Key: dummy_key" http://localhost:8000/api/v1/system/status
#   → {"database":"connected", "suricata_online":true, "total_traffic":…}

curl -s -H "X-API-Key: dummy_key" http://localhost:8000/api/v1/system/network
#   → {"interface":"enp9s0","subnet":"192.168.20.0/24","local_ip":"192.168.20.101",…}

# Dashboard
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:3001/      # 200

# Log
tail -5 logs/detection.log     # RuleEngine aktif, EveParser "Menunggu alert baru..."
tail -5 logs/predictor.log     # "Kalibrasi dimuat → threshold=-0.6047 score_min=-0.8029"

# Proses
ps aux | grep -E "collector.main|detection.main|ml.main predict|suricata -c"
```

**Cek cepat UTC:** data traffic baru harus ber-timestamp ±UTC sekarang
(`date -u`), bukan waktu lokal WIB.

---

## 5. Alur Demo (presentasi)

### 5.1 Buka dashboard — http://localhost:3001
- Kartu statistik: total traffic (nyata, terus bertambah), alerts, critical, endpoint IoT.
- Label interface menampilkan `enp9s0` (dinamis, bukan hardcode).
- Jelaskan bahwa angka berasal dari data nyata yang mengalir.

### 5.2 Tunjukkan komponen live
- **API Swagger** http://localhost:8000/docs — endpoint & skema (klaim "API terdokumentasi").
- **Grafana** http://localhost:3002 (admin/admin) — metrik tambahan.
- **WebSocket**: buka `ws://localhost:8000/ws/alerts?token=dummy_key` (mis. lewat
  browser console) — terima `connected`, lalu `new_alert` real-time.

### 5.3 Data IoT (opsional, halal — bukan serangan)
```bash
venv/bin/python tools/simulate_esp32.py --all
```
- Muncul `devices` online + `mqtt_telemetry` di dashboard (endpoint IoT → online).
- Hentikan (Ctrl+C) → perangkat kembali offline (deteksi heartbeat 12 detik).

### 5.4 Skenario serangan — **dari mesin penyerang terpisah** di LAN
> Penting: traffic host pemantau sendiri (192.168.20.101) sengaja dikecualikan
> (host = pengamat). Serangan harus datang dari IP LAN lain agar terdeteksi.
> Contoh penyerang: laptop/Kali di `192.168.20.x`, target = host `192.168.20.101`.

| Skenario | Perintah (dari penyerang) | Alert yang diharapkan |
|---|---|---|
| Port scan | `nmap -sS -p 1-2000 192.168.20.101` | `PORT_SCAN` (MEDIUM, is_syn > 20 port unik) |
| SYN flood | `hping3 -S -p 80 --flood 192.168.20.101` | `SYN_FLOOD` (HIGH, ≥100 SYN ke 1 target) |
| ICMP flood | `ping -f 192.168.20.101` | `ICMP_FLOOD` (HIGH, ≥50 echo request type 8) |
| Traffic spike | `iperf3 -c 192.168.20.101` (atau download besar) | `TRAFFIC_SPIKE` (MEDIUM, ≥5 MB/5 dtk) |
| MQTT abuse | publish ≥30 pesan/detik ke broker :1883 dari IP lain | `MQTT_RATE_ABUSE` (MEDIUM) |
| Suricata | serangan apa pun di atas | rule SID 1000001–1000041 (mis. port scan SID 1000001) |

- Saksikan alert muncul **real-time** di dashboard (WebSocket) + tabel alerts.
- Tekan **Mitigate** pada satu alert → status jadi RESOLVED & tersimpan di DB
  (`POST /api/v1/alerts/{id}/mitigate`).
- Hentikan serangan segera setelah ditunjukkan (Ctrl+C).

### 5.5 Tunjukkan deteksi ML
- Halaman predictions/anomalies: confidence terkalibrasi (threshold -0.6047,
  score_min -0.8029 — dari `ml/models/if_calibration.json`).
- Jelaskan: keputusan anomali pakai threshold hasil training, bukan angka acak.

---

## 6. Troubleshooting Cepat

| Gejala | Cek / Solusi |
|---|---|
| Traffic tidak bertambah | Collector mati → `sudo ./venv/bin/python -m collector.main` |
| Timestamp aneh (±7 jam) | Pastikan collector versi baru (UTC); data lama sudah dimigrasi −7 jam |
| `suricata_online: false` | Suricata belum jalan → `sudo bash scripts/start_suricata.sh` |
| Alert tidak muncul | Rule hanya memproses source privat & bukan IP host; serangan harus dari IP LAN lain |
| API 500 | Cek `logs/api.log`; uji ulang via Swagger |
| WS terputus / rate limit | Maks 10 koneksi WS/menit per IP — tunggu sebentar |
| DB lock / query menggantung | `SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state='idle in transaction';` |
| Port 3000 dipakai | Next.js = 3001, Grafana = 3002 (bukan 3000) |

Akses cepat:
- DB: `docker exec ung_postgres psql -U guard_user -d network_guard`
- API key: header `X-API-Key: dummy_key`
- Rules Suricata: `suricata/rules/local.rules` (14 SID: 1000001–1000041)

---

## 7. Catatan Kejujuran (untuk presentasi)

- **Angka nyata**: traffic, alert, prediksi berasal dari data yang mengalir live — tidak ada angka tempel.
- **Simulasi ESP32**: perangkat nyata atau simulator — jelaskan mana yang dipakai.
- **Serangan**: simulasi terkontrol, dijalankan hanya saat sesi demo, dari mesin penyerang terpisah.
- **Timezone**: seluruh pipeline UTC; dashboard menampilkan waktu tersebut.
- **Suricata rule** menarget subnet lab `192.168.10.0/24` (desain artikel);
  pada jaringan live `192.168.20.0/24` hanya rule yang relevan topologi yang fire.