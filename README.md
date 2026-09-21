# Unified Network Guard (UNG)

> Platform keamanan jaringan IoT berbasis **Edge Computing** untuk deteksi anomali dan serangan siber secara **real-time**.

Unified Network Guard (UNG) menggabungkan tiga pendekatan deteksi secara **hybrid** — Signature-Based IDS (Suricata), Rule-Based / Threshold Engine, dan Machine Learning (Isolation Forest + Random Forest) — yang seluruhnya diproses di edge (PC lokal) sehingga latensi rendah dan data sensitif tidak meninggalkan jaringan lokal.

Proyek ini merupakan tugas akhir yang menggabungkan bidang **IoT, Networking, Edge Computing, Cybersecurity, Machine Learning, dan Dashboard Monitoring**.

---

## Daftar Isi

- [Fitur Utama](#fitur-utama)
- [Arsitektur Sistem](#arsitektur-sistem)
- [Stack Teknologi](#stack-teknologi)
- [Struktur Direktori](#struktur-direktori)
- [Prasyarat](#prasyarat)
- [Instalasi](#instalasi)
- [Konfigurasi](#konfigurasi)
- [Menjalankan Sistem](#menjalankan-sistem)
- [API Endpoints](#api-endpoints)
- [Skenario Pengujian / Serangan](#skenario-pengujian--serangan)
- [Database Schema](#database-schema)
- [Aturan Kejujuran Demo](#aturan-kejujuran-demo)
- [Troubleshooting](#troubleshooting)
- [Lisensi](#lisensi)

---

## Fitur Utama

- **Hybrid Detection (3 lapis)**
  - **Suricata IDS** — 14 signature rule kustom (SID 1000001–1000041) untuk port scan, SYN/UDP/ICMP flood, brute force SSH/HTTP, dan MQTT abuse.
  - **Rule Engine** — sliding-window threshold engine (Port Scan, SYN Flood, ICMP Flood, Traffic Spike, MQTT Rate Abuse) dengan alert suppression & deduplikasi.
  - **Machine Learning** — Isolation Forest (anomali, terkalibrasi) + Random Forest (klasifikasi 6 kelas serangan), 12 fitur agregasi traffic pada window 10 detik.
- **Real-Time Pipeline** — data trafik nyata (Scapy) + telemetri MQTT dari ESP32 → PostgreSQL (timezone UTC konsisten).
- **FastAPI Backend** — REST + WebSocket `/ws/alerts` dengan proteksi `X-API-Key`, rate limiting, dan CORS.
- **Next.js 16 + React 19 Dashboard** — kartu statistik, gauge, line chart, topology map live, panel ancaman & tingkat risiko, dengan WebSocket push.
- **IoT Testbed** — 5 firmware ESP32 (`.ino`, PubSubClient + ArduinoJson) + simulator `simulate_esp32.py` untuk perangkat tanpa hardware fisik.
- **Infrastruktur Container** — PostgreSQL, Mosquitto MQTT, dan Grafana via Docker Compose.
- **Honest Audit Trail** — semua angka berasal dari data nyata; tidak ada fallback buatan.

---

## Arsitektur Sistem

```
┌─ Data Source ──────────────────────────────────────────────────────────┐
│ ESP32 node (asli/simulator) → MQTT Mosquitto :1883                    │
│ Trafik jaringan nyata (Scapy, CAPTURE_INTERFACE, filter IOT_SUBNET)    │
│ Suricata IDS (AF_PACKET, 14 rules → /var/log/suricata/eve.json)       │
└──────────────────────────────┬─────────────────────────────────────────┘
                               ▼
┌─ Storage: PostgreSQL (UTC) ───────────────────────────────────────────┐
│ network_traffic · mqtt_telemetry · alerts · ml_predictions · devices  │
└───────────────┬───────────────────────────────┬───────────────────────┘
                ▼                               ▼
┌─ Detection ──────────────────────┐   ┌─ ML Predictor ─────────────────┐
│ RuleEngine (sliding window)      │   │ Isolation Forest (kalibrasi)  │
│ EveParser (tail eve.json)        │   │ Random Forest (klasifikasi)    │
└───────────────┬──────────────────┘   └──────────────┬────────────────┘
                └──────────────┬─────────────────────┘
                               ▼
                    ┌─ AlertManager (dedup) ─┐
                    └──────────┬─────────────┘
                               ▼
        ┌─ API FastAPI :8000 (X-API-Key) ─┐
        │ REST + WebSocket /ws/alerts      │
        └────────────┬─────────────────────┘
                     ▼
          Dashboard Next.js :3001
```

### Alur Data End-to-End

1. **ESP32** (atau simulator) mempublikasi telemetri via **MQTT** ke broker Mosquitto.
2. **Collector** (Scapy `traffic_sniffer` + `mqtt_subscriber`) menangkap trafik jaringan nyata dan telemetri MQTT, lalu menulis batch ke PostgreSQL.
3. **Suricata** memantau interface `AF_PACKET` dan menghasilkan event `eve.json`.
4. **Detection** (`rule_engine` + `eve_parser` + `alert_manager`) menganalisis traffic & event, memunculkan alert dengan deduplikasi.
5. **ML Predictor** mengagregasi 12 fitur traffic per window 10 detik, menjalankan Isolation Forest & Random Forest, menyimpan hasil ke `ml_predictions`, dan meng-emit alert anomali.
6. **API FastAPI** menyajikan data via REST + WebSocket real-time, dilindungi `X-API-Key` & rate limit.
7. **Dashboard Next.js** menampilkan statistik, ancaman, dan prediksi live via WebSocket.

---

## Stack Teknologi

| Lapisan | Teknologi |
|---|---|
| **IoT Node** | ESP32, PubSubClient, ArduinoJson (firmware `.ino`) |
| **Capture / Collector** | Scapy, pyshark, paho-mqtt |
| **MQTT Broker** | Eclipse Mosquitto 2.0 |
| **Database** | PostgreSQL 15 (Alpine) |
| **Signature IDS** | Suricata 8.x (AF_PACKET, 14 custom rules) |
| **Rule Engine** | Python (sliding-window threshold) |
| **ML** | scikit-learn (Isolation Forest + Random Forest), pandas, numpy, joblib |
| **Backend API** | FastAPI, Uvicorn, SQLAlchemy 2, Pydantic 2 |
| **Frontend Dashboard** | Next.js 16, React 19, TypeScript, Tailwind v4, Chart.js, lucide-react |
| **Monitoring Tambahan** | Grafana |
| **Orkestrasi** | Docker Compose |

---

## Struktur Direktori

```
unified-network-guard/
├── api/                  # Backend FastAPI (server, routes, schemas, deps, rate_limit, network_info)
│   └── routes/           # alerts, devices, predictions, traffic
├── collector/            # Pengumpul data (traffic_sniffer, mqtt_subscriber, db, main)
├── detection/            # Mesin deteksi (rule_engine, eve_parser, alert_manager, main)
├── ml/                   # Modul ML (feature_extractor, trainer, predictor, evaluator, generate_dataset)
│   ├── datasets/         # Dataset latih & skenario
│   └── models/           # Model terlatih (if_calibration.json, *.pkl)
├── database/             # schema.sql (5 tabel: devices, network_traffic, alerts, mqtt_telemetry, ml_predictions)
├── dashboard/            # Frontend Next.js 16 + React 19
│   └── src/
│       ├── app/          # layout, page
│       ├── components/   # StatCards, LiveTopologyMap, ThreatsPanel, RiskLevelPanel, MultiLineChart, views/*
│       ├── contexts/     # DashboardContext (state global + WebSocket)
│       └── hooks/        # useCanvas
├── esp32/                # 5 firmware .ino (node01–node05) — sensor iklim, keamanan, energi, udara, aktuator
├── mqtt/                 # mosquitto.conf
├── scripts/              # start_suricata.sh, build_ikomti_docx.py
├── suricata/
│   ├── suricata.yaml     # Konfigurasi Suricata (af-packet, eve-log, local.rules)
│   └── rules/local.rules# 14 custom SID (1000001–1000041)
├── tools/                # simulate_esp32.py (simulator node IoT)
├── logs/                 # Log runtime (api.log, detection.log, predictor.log, ...)
├── artikel/              # Artikel ilmiah & dokumentasi lengkap + referensi PDF
├── docker-compose.yml    # PostgreSQL + Mosquitto + Grafana
├── requirements.txt      # Dependensi Python
├── .env.example          # Template konfigurasi lingkungan
└── DEMO_RUNBOOK.md       # Checklist demo presentasi
```

---

## Prasyarat

| Komponen | Keterangan |
|---|---|
| **Docker Compose** | Untuk PostgreSQL, Mosquitto, Grafana |
| **Python 3.10+** | `venv/` di root proyek berisi dependensi |
| **Node.js 18+** | Untuk dashboard Next.js |
| **Suricata** | `/usr/bin/suricata` (v8.0.3 pada env demo) |
| **sudo** | Collector butuh raw socket; Suricata butuh AF_PACKET |
| **Mesin penyerang (opsional)** | Perangkat lain di LAN untuk skenario serangan |

---

## Instalasi

```bash
# 1. Clone / masuk ke direktori proyek
cd unified-network-guard

# 2. Buat & aktifkan virtual environment Python
python3 -m venv venv
source venv/bin/activate          # Linux/macOS
# .\venv\Scripts\activate         # Windows

# 3. Pasang dependensi Python
pip install -r requirements.txt

# 4. Pasang dependensi dashboard
cd dashboard && npm install && cd ..

# 5. Salin & sesuaikan konfigurasi
cp .env.example .env
#    → Ubah API_KEY ke nilai aman: python -c "import secrets; print(secrets.token_hex(32))"
#    → Sesuaikan CAPTURE_INTERFACE, IOT_SUBNET, GATEWAY_IP dengan jaringan lab Anda

# 6. Jalankan infrastruktur container
docker compose up -d              # PostgreSQL :5432, Mosquitto :1883/:9001, Grafana :3002
```

---

## Konfigurasi

Semua konfigurasi ada di `.env` (salin dari `.env.example`). Bagian penting:

```ini
# Jaringan
CAPTURE_INTERFACE=enp9s0          # interface capture trafik
IOT_SUBNET=192.168.20.0/24        # subnet IoT yang dipantau
GATEWAY_IP=192.168.20.1

# MQTT
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=1883
MQTT_TOPIC_BASE=iot/#

# Database
DB_HOST=localhost
DB_NAME=network_guard
DB_USER=guard_user
DB_PASSWORD=guard_secret

# Suricata
SURICATA_EVE_PATH=/var/log/suricata/eve.json

# Threshold Detection
PORTSCAN_PKT_THRESHOLD=20         # SYN > 20 port unik / 5 detik
SYNFLOOD_PKT_THRESHOLD=100        # ≥100 SYN ke 1 target / 2 detik
ICMPFLOOD_PKT_THRESHOLD=50        # ≥50 echo request / 3 detik
TRAFFIC_SPIKE_BPS=5000000         # 5 MB / 5 detik
MQTT_RATE_THRESHOLD=30            # ≥30 pesan MQTT / detik
ALERT_SUPPRESS_SECONDS=30         # deduplikasi alert

# ML
IF_N_ESTIMATORS=200
FEATURE_WINDOW_SECONDS=10
RF_N_ESTIMATORS=150
PREDICTOR_POLL_INTERVAL=10

# API
API_KEY=GANTI_DENGAN_KEY_AMAN_MINIMAL_32_KARAKTER
CORS_ORIGINS=http://localhost:3000,http://192.168.10.10:3000
RATE_LIMIT_DEFAULT=120/minute
RATE_LIMIT_HEAVY=30/minute
WS_POLL_INTERVAL=2.0
```

> **Penting:** Seluruh pipeline menggunakan **timezone UTC**. Dashboard menampilkan waktu UTC; host WIB (+7) tetap menyimpan data dalam UTC.

---

## Menjalankan Sistem

Jalankan dari root proyek, masing-masing di terminal terpisah:

```bash
# 0. Infrastruktur (sekali saja)
docker compose up -d

# 1. API (FastAPI)
venv/bin/uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload

# 2. Dashboard (Next.js)
cd dashboard && npm run dev        # → http://localhost:3001

# 3. Detection (rule engine + EveParser)
venv/bin/python -m detection.main

# 4. ML Predictor (dengan alert)
venv/bin/python -m ml.main predict --with-alerts

# 5. Collector (butuh sudo — raw socket)
sudo ./venv/bin/python -m collector.main

# 6. Suricata IDS (butuh sudo — AF_PACKET)
sudo bash scripts/start_suricata.sh
```

### Verifikasi Cepat

```bash
# API status
curl -s -H "X-API-Key: dummy_key" http://localhost:8000/api/v1/system/status
#   → {"database":"connected", "suricata_online":true, "total_traffic":…}

# API network info
curl -s -H "X-API-Key: dummy_key" http://localhost:8000/api/v1/system/network

# Dashboard
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:3001/   # 200

# Swagger UI
# http://localhost:8000/docs

# Grafana
# http://localhost:3002  (admin/admin)
```

---

## API Endpoints

Semua endpoint (kecuali `/docs`) wajib menyertakan header `X-API-Key: <API_KEY>`.

| Method | Endpoint | Deskripsi |
|---|---|---|
| GET | `/api/v1/system/status` | Status kesehatan sistem (DB, Suricata, total traffic) |
| GET | `/api/v1/system/network` | Info interface, subnet, IP lokal, gateway |
| GET | `/api/v1/traffic` | Daftar trafik jaringan (paginated) |
| GET | `/api/v1/traffic/summary` | Ringkasan agregasi trafik |
| GET | `/api/v1/alerts` | Daftar alert (filter: severity, attack_type, source_ip) |
| GET | `/api/v1/alerts/stats` | Statistik agregat alert |
| GET | `/api/v1/alerts/{id}` | Detail satu alert |
| POST | `/api/v1/alerts/{id}/mitigate` | Tandai alert sebagai RESOLVED |
| GET | `/api/v1/predictions` | Daftar prediksi ML |
| GET | `/api/v1/predictions/anomalies` | Daftar anomali terdeteksi |
| GET | `/api/v1/predictions/stats` | Statistik prediksi |
| GET | `/api/v1/devices` | Daftar perangkat IoT |
| GET | `/api/v1/devices/{id}/telemetry` | Telemetri perangkat |
| WS | `/ws/alerts?token=<API_KEY>` | Stream alert real-time (maks 10 koneksi/menit/IP) |

---

## Skenario Pengujian / Serangan

> **Penting:** Host pemantau (mis. `192.168.20.101`) sengaja dikecualikan agar menjadi pengamat. Serangan **harus datang dari IP LAN lain** agar terdeteksi. Jalankan dari mesin penyerang terpisah di subnet yang sama.

| Skenario | Perintah (dari penyerang) | Alert yang diharapkan |
|---|---|---|
| Port scan | `nmap -sS -p 1-2000 192.168.20.101` | `PORT_SCAN` (MEDIUM) + Suricata SID 1000001 |
| SYN flood | `hping3 -S -p 80 --flood 192.168.20.101` | `SYN_FLOOD` (HIGH) |
| ICMP flood | `ping -f 192.168.20.101` | `ICMP_FLOOD` (HIGH) |
| Traffic spike | `iperf3 -c 192.168.20.101` | `TRAFFIC_SPIKE` (MEDIUM) |
| MQTT abuse | publish ≥30 pesan/detik ke `:1883` | `MQTT_RATE_ABUSE` (MEDIUM) |
| SSH brute force | `hydra -l admin ssh://192.168.20.101` | Suricata SID SSH brute force |
| HTTP brute force | brute force `:3000` | Suricata SID HTTP brute force |

### Simulasi Perangkat IoT (non-serangan, aman)

```bash
venv/bin/python tools/simulate_esp32.py --all
```

Akan muncul `devices` online + `mqtt_telemetry` di dashboard. Hentikan (Ctrl+C) → perangkat kembali offline (deteksi heartbeat 12 detik).

---

## Database Schema

Skema lengkap ada di `database/schema.sql`. 5 tabel utama:

| Tabel | Isi |
|---|---|
| `devices` | Perangkat IoT (id, device_name, ip_address, mac, type, status, last_seen) |
| `network_traffic` | Trafik jaringan (timestamp, src/dst ip, protocol, ports, packet_count, bytes, is_syn, icmp_type) |
| `alerts` | Alert dari detection (severity, attack_type, confidence, mitigated) |
| `mqtt_telemetry` | Telemetri MQTT dari ESP32 (device_id, topic, payload JSONB) |
| `ml_predictions` | Hasil prediksi ML (if_score, is_anomaly, attack_class, confidence, features JSONB) |

Seed awal menambahkan 5 perangkat ESP32 (192.168.10.101–105). Index performa dibuat pada kolom timestamp yang paling sering di-query.

Akses cepat ke DB:
```bash
docker exec ung_postgres psql -U guard_user -d network_guard
```

---

## Aturan Kejujuran Demo

Dokumen `DEMO_RUNBOOK.md` menetapkan prinsip berikut untuk presentasi:

- **Angka nyata** — traffic, alert, dan prediksi berasal dari data yang mengalir live. Tidak ada angka tempel.
- **Simulasi ESP32** — perangkat nyata atau simulator; jelaskan mana yang dipakai.
- **Serangan** — simulasi terkontrol, dijalankan hanya saat sesi demo, dari mesin penyerang terpisah, dan dihentikan setelah ditunjukkan.
- **Timezone** — seluruh pipeline UTC; dashboard menampilkan waktu tersebut.
- **Suricata rule** menarget subnet lab desain (`192.168.10.0/24`); pada jaringan live (`192.168.20.0/24`) hanya rule yang relevan topologi yang aktif.

---

## Troubleshooting

| Gejala | Cek / Solusi |
|---|---|
| Traffic tidak bertambah | Collector mati → `sudo ./venv/bin/python -m collector.main` |
| Timestamp ±7 jam | Pastikan collector versi baru (UTC); data lama sudah dimigrasi −7 jam |
| `suricata_online: false` | Suricata belum jalan → `sudo bash scripts/start_suricata.sh` |
| Alert tidak muncul | Rule hanya memproses source privat & bukan IP host; serangan harus dari IP LAN lain |
| API 500 | Cek `logs/api.log`; uji ulang via Swagger |
| WS terputus / rate limit | Maks 10 koneksi WS/menit per IP — tunggu sebentar |
| Port 3000 dipakai | Next.js = 3001, Grafana = 3002 (bukan 3000) |
| DB lock / query menggantung | `SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state='idle in transaction';` |

---

## Lisensi

Proyek akhir — lihat detail di `artikel/` untuk konteks akademik. Kode ditujukan untuk keperluan penelitian dan edukasi.

---

## Dokumentasi Tambahan

- `DEMO_RUNBOOK.md` — Checklist langkah-demi-langkah demonstrasi sistem
- `artikel/Artikel_Ilmiah_Unified_Network_Guard.md` — Artikel ilmiah
- `artikel/Dokumentasi_Lengkap_Unified_Network_Guard.md` — Dokumentasi lengkap (22 bab)
- `artikel/referensi/` — 5 referensi PDF (CMC, CSSE, Applied Sciences, Scientific Reports, Sensors)
- `graphify-out/` — Knowledge graph hasil ekstraksi otomatis (`graph.html`, `GRAPH_REPORT.md`, `graph.json`)
