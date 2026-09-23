# Penjelasan Proyek — Unified Network Guard (UNG)

> Dokumen penjelasan menyeluruh proyek Unified Network Guard, disusun dari hasil analisis **knowledge graph** (graphify: 655 node · 1232 edge · 45 komunitas) plus verifikasi langsung pada kode, konfigurasi, dan laporan training/evaluasi.

---

## 1. Ringkasan

**Unified Network Guard (UNG)** adalah platform keamanan jaringan IoT berbasis **Edge Computing** untuk deteksi anomali dan serangan siber secara **real-time**. UNG menggabungkan **tiga lapis deteksi hibrida** — Signature-Based IDS (Suricata), Rule-Based/Threshold Engine, dan Machine Learning (Isolation Forest + Random Forest) — yang seluruhnya dieksekusi di **PC edge lokal** sehingga latensi rendah dan data sensitif tidak meninggalkan jaringan lokal.

Proyek ini merupakan **tugas akhir** yang menggabungkan enam bidang: IoT, Networking, Edge Computing, Cybersecurity, Machine Learning, dan Dashboard Monitoring.

**Skala proyek menurut graf pengetahuan:**
- 85 file · ~73.115 kata
- 655 node (simbol/konsep) · 1232 edge (relasi) · 45 komunitas (30 signifikan, 15 tipis)
- Ekstraksi: 94% EXTRACTED (dari kode/AST & dokumen) · 6% INFERRED (rata-rata confidence 0,89) · 0% AMBIGUOUS
- 0 token biaya LLM (korpus kode diekstrak via AST; semantik dari agen host)

---

## 2. Topologi Jaringan (jaringan riil yang dipakai)

```
[Internet]─[TL-WR840N 192.168.10.1 / 192.168.10.0/24]─[TL-WR820N 192.168.20.1 / 192.168.20.0/24]
              └─ Attacker 192.168.10.100                    ├─ Edge PC   192.168.20.100
                                                       ├─ ESP32-01  .101 (climate: suhu/kelembapan)
                                                       ├─ ESP32-02  .102 (security: gerak/cahaya)
                                                       ├─ ESP32-03  .103 (energy: tegangan/arus)
                                                       ├─ ESP32-04  .104 (air quality: CO2/PM2.5)
                                                       └─ ESP32-05  .105 (heartbeat/gateway)
```

- **Segmen IoT** = `192.168.20.0/24` (downstream, gateway TL-WR820N `192.168.20.1`) — berisi Edge PC + 5 ESP32.
- **Segmen pengujian attacker** = `192.168.10.0/24` (upstream, TL-WR840N `192.168.10.1`) — mesin penyerang `192.168.10.100` menjalankan nmap/hping3.
- **Edge PC**: AMD Ryzen 5 5500GT, RAM 8 GB, Ubuntu, interface capture `enp9s0`.
- Segmentasi dua tingkat ini menjamin serangan hanya datang dari subnet terpisah, sehingga host pemantau (Edge PC) berperan sebagai pengamat.

---

## 3. Arsitektur Sistem (Pipeline)

```
┌─ Data Source ──────────────────────────────────────────────┐
│ ESP32 (asli/simulator) → MQTT Mosquitto :1883               │
│ Trafik jaringan nyata (Scapy, CAPTURE_INTERFACE, BPF)        │
│ Suricata IDS (AF_PACKET, 14 rules → eve.json)               │
└──────────────────────────────┬──────────────────────────────┘
                               ▼
┌─ Storage: PostgreSQL (semua waktu UTC konsisten) ───────────┐
│ network_traffic · mqtt_telemetry · alerts · ml_predictions · devices │
└───────────────┬───────────────────────────────┬────────────┘
                ▼                               ▼
┌─ Detection ──────────────────────┐   ┌─ ML Predictor ──────────────┐
│ RuleEngine (sliding window)      │   │ Isolation Forest (kalibrasi)│
│ EveParser (tail eve.json)        │   │ Random Forest (klasifikasi)  │
└───────────────┬──────────────────┘   └──────────────┬─────────────┘
                └──────────────┬─────────────────────┘
                               ▼
                    ┌─ AlertManager (dedup) ─┐
                               ▼
        ┌─ API FastAPI :8000 (X-API-Key) ─┐
        │ REST + WebSocket /ws/alerts      │
        └────────────┬─────────────────────┘
                     ▼
          Dashboard Next.js 16 + React 19 (:3001)
```

### Alur Data End-to-End
1. **ESP32** (atau `simulate_esp32.py`) mempublikasi telemetri via **MQTT** ke broker Mosquitto.
2. **Collector** (`traffic_sniffer` Scapy + `mqtt_subscriber`) menangkap trafik nyata + telemetri MQTT, menulis batch ke PostgreSQL.
3. **Suricata** memantau interface `AF_PACKET`, menghasilkan event `eve.json`.
4. **Detection** (`rule_engine` + `eve_parser` + `alert_manager`) menganalisis traffic & event, memunculkan alert dengan **deduplikasi**.
5. **ML Predictor** mengagregasi **12 fitur traffic per IP sumber** dalam window **10 detik**, menjalankan Isolation Forest & Random Forest, menyimpan hasil ke `ml_predictions`, dan meng-emit alert anomali.
6. **API FastAPI** menyajikan REST + WebSocket push alert ke **dashboard** real-time.

---

## 4. Tiga Lapis Deteksi Hibrida (Hyperedge utama graf)

Graf mendeteksi hyperedge **"UNG Three-Tier Hybrid Detection Pipeline"** (confidence 1.00) yang mengikat: `artikel_ilmiah_hybrid_detection`, `suricata_ids`, `rule_engine`, `isolation_forest`, `data_pipeline`.

### Lapis 1 — Signature-Based IDS (Suricata)
- **14 aturan signature kustom** (SID 1000001–1000041) dalam `suricata/rules/local.rules`, dikelompokkan:
  1. **Reconnaissance**: TCP/UDP port scan (threshold SYN per src).
  2. **DoS/Flood**: ICMP ping flood, SYN flood (track by_dst), UDP flood.
  3. **MQTT/IoT anomaly**: koneksi MQTT dari subnet attacker, MQTT dari IP eksternal, MQTT WebSocket (9001), MQTT rate abuse.
  4. **Brute Force**: SSH (port 22) & HTTP dashboard (port 3000) ke Edge PC.
  5. **Anomaly umum**: ESP32 ke port tidak lazim, exfiltration IoT ke luar jaringan lokal.
- Output: `eve.json` diparse oleh `EveParser` → `AlertManager`.

### Lapis 2 — Rule-Based / Threshold Engine (Sliding Window)
- `RuleEngine` memakai `collections.deque` sebagai **sliding window** dengan 5 aturan kuantitatif:
  `PORT_SCAN`, `SYN_FLOOD` (penanda `is_syn` paket SYN asli), `ICMP_FLOOD`, `TRAFFIC_SPIKE`, `MQTT_RATE_ABUSE`.
- Dilengkapi **alert suppression & deduplikasi** lewat `AlertManager` (singleton), agar satu serangan tidak membanjiri DB.
- Threshold `TRAFFIC_SPIKE_BPS` = 5.000.000 (5 MB/5s) — browsing normal aman, flood DoS tetap terdeteksi.

### Lapis 3 — Machine Learning (Unsupervised + Supervised)
- **Isolation Forest** (200 pohon, `contamination=0.05`) — deteksi anomali **unsupervised**, dilatih hanya pada data `normal` (3.479 sample), threshold kalibrasi otomatis disimpan di `if_calibration.json` (score threshold ≈ −0.6047).
- **Random Forest** (150 pohon, max_depth 15) — klasifikasi **supervised** 6 kelas serangan, dilatih pada 7.979 sample berlabel.
- Keduanya memakai **12 fitur agregasi traffic** per IP sumber per window 10 detik.

---

## 5. Dataset UGN-IoT (original)

`ml/datasets/labeled.csv` — **7.979 baris · 13 kolom (12 fitur + label)**.

| Kelas | Jumlah |
|---|---|
| normal | 3.479 |
| port_scan | 900 |
| syn_flood | 900 |
| icmp_flood | 900 |
| traffic_spike | 900 |
| mqtt_anomaly | 900 |

**12 fitur:** `packet_count, byte_count, connection_count, packet_rate, byte_rate, avg_packet_size, unique_dst_ports, unique_dst_ips, proto_tcp_ratio, proto_udp_ratio, proto_icmp_ratio, mqtt_ratio`.

Dataset disintesis oleh `ml/generate_dataset.py` (Community 21 — "Dataset Generator Script") memakai **archetype** pola serangan realistis khas tool penetrasi (nmap, hping3, ping flood).

---

## 6. Komponen Inti (God Nodes — node paling terhubung di graf)

God nodes adalah abstraksi paling sentral proyek menurut analisis graf:

| # | Simbol | Edge | Peran |
|---|---|---|---|
| 1 | `useDashboard()` | 31 | React context pusat dashboard; menyangkut hampir seluruh view |
| 2 | `_Base` | 23 | Base class bersama (shared logging/config) |
| 3 | `AlertManager` | 17 | Singleton pengelola siklus hidup alert (dedup → insert DB) |
| 4 | `utc_now()` | 16 | Helper waktu UTC konsisten lintas pipeline |
| 5 | `compilerOptions` | 16 | Konfigurasi TS dashboard |
| 7 | `RuleEngine` | 14 | Mesin deteksi berbasis aturan sliding-window |
| 8 | `AnomalyPredictor` | 14 | Mesin inferensi ML real-time (IF + RF) |
| 9 | `TrafficSniffer` | 13 | Penangkap paket Scapy + ekstraksi fitur |

**Bridge node lintas-komunitas (betweenness tinggi):** `TrafficSniffer`, `AnomalyPredictor`, `MQTTSubscriber` — ketiganya menjembatani modul kolektor → deteksi → ML → API.

---

## 7. Struktur Modul berdasarkan Komunitas Graf (45 komunitas, 30 signifikan)

Graf mengelompokkan kode menjadi komunitas-komunitas yang merefleksikan arsitektur fisik proyek:

### Collector (pengumpul data)
- **Community 11 — MQTT Subscriber**: `MQTTSubscriber`, decode payload JSON, parse topic `iot/esp32-0x/telemetry`.
- **Community 12 — Traffic Sniffer & Feature Extraction**: `TrafficSniffer` (Scapy `store=False`), thread sniffer + periodic flush buffer, insert batch tanpa lock.
- **Community 16 — Collector DB Layer**: `insert_telemetry()`, `insert_traffic_batch()`, `ensure_schema()`.

### Detection (deteksi 3-lapis)
- **Community 6 — Rule Engine (Sliding-Window)**: `RuleEngine`, `TimeWindow`, `_analyze_record()`, `_fetch_new_traffic()`, `_emit_alert()`.
- **Community 7 — Alert Manager & Eve Parser**: `AlertManager`, `Alert`, `EveParser` (konversi Suricata classtype → nama attack_type konsisten).
- **Community 19 — Detection Shared Config/Logging**: `map_severity()`, shared config.

### ML (machine learning)
- **Community 5 — ML Pipeline Orchestration (main/CLI)**: `build_parser()`, `cmd_train()`, `cmd_predict()`, `cmd_evaluate()`, `main()`.
- **Community 17 — ML Feature Extractor**: `extract_from_db()`, `extract_recent()`, `load_dataset_csv()`, `_build_aggregation_query()`.
- **Community 27 — Isolation Forest Trainer**: `IsolationForestTrainer`, save/load model + scaler + kalibrasi.
- **Community 28 — Random Forest Trainer**: `RandomForestTrainer`, save/load model + label encoder.
- **Community 24 — Model Feature Matrix & Train**: `get_feature_matrix()`, `.train()` IF & RF.
- **Community 14 — ML Evaluator & Metrics**: `evaluate()`, `_annotate_ground_truth()`, `_calc_detection_latency()`, `_per_class_metrics()`.
- **Community 26 — ML Predictor DB Persistence**: `_ensure_predictions_table()`, `_insert_predictions()`.

### API (backend)
- **Community 10 — FastAPI Server & System Status**: `server.py`, `lifespan()`, `suricata_is_running()`, endpoint `/status`.
- **Community 3 — API Server Middleware & WebSocket**: `verify_ws_token()`, `check_rate_limit()`, `rate_limit_for_path()`, `ws_alert_stream()`.
- **Community 8 — API Schemas & Traffic Routes**: `list_traffic()`, `traffic_summary()`, `AlertStats`, `AnomalyStats`.
- **Community 15 — Predictions API Routes & Config**: `list_anomalies()`, `list_predictions()`, `to_naive_utc()`.
- **Community 18 — Devices & Telemetry API Routes**: `list_devices()`, `get_device()`, `get_device_telemetry()`, `PaginationParams`.
- **Community 20 — Alerts API Route**: `list_alerts()`, `get_alert()`, `mitigate_alert()`, `alert_stats()`.
- **Community 4 — Network Info Probe**: `detect_active_interface()`, `detect_gateway()`, `detect_local_ip()`, `detect_subnet()`, `get_network_info()`.
- **Community 23 — API Dependencies**: `get_db()`, `verify_api_key()` (header `X-API-Key`).
- **Community 25 — Alert Filter Validators**: `AlertFilter`, `_validate_ip()`.

### Dashboard (frontend)
- **Community 0 — Dashboard React Context & Live Views**: `useDashboard()`, `Dashboard()`, `LiveTopologyMap`, `EndpointsView`, `isHeartbeatFresh()`, `getActiveAttackerIp()`.
- **Community 2 — Dashboard Build Config & Package**: `dependencies`, `next`, `react`, `chart.js`, `react-chartjs-2`, `lucide-react`.
- **Community 13 — Dashboard tsconfig Options**.
- **Community 29 — Dashboard UI Design References (PNGs)**: dark navy palette (#13191A), severity color accents.

### Dokumentasi & Konsep
- **Community 1 — UNG Documentation & Architecture Concepts** (50 node): Artikel Ilmiah, Dokumentasi Lengkap, konsep Edge Computing, ESP32 Node, Evaluation Results, Three-tier Hybrid Strategy, UNG Data Pipeline, PostgreSQL Schema (5 tables), Docker Infrastructure.

---

## 8. Hyperedges (relasi kelompok)

Graf menemukan tiga hyperedge penting yang merefleksikan arsitektur tingkat tinggi:

1. **UNG Three-Tier Hybrid Detection Pipeline** (EXTRACTED 1.00) — Suricata IDS + Rule Engine + Isolation Forest + Data Pipeline.
2. **UNG Docker Infrastructure Stack** (EXTRACTED 1.00) — `docker-compose` (PostgreSQL, Mosquitto, Grafana) + `database/schema.sql`.
3. **UNG Edge-IoT Lab Testbed** (INFERRED 0.85) — testbed topology + ESP32 node + Edge Computing paradigm + MQTT protocol + firmware ESP32.

---

## 9. Surprising Connections (koneksi lintas-dokumen yang tidak terduga)

Graf menemukan koneksi semantik lintas file yang biasanya tidak terlihat:

- **Next.js Framework (bootstrap)** ↔ **Next.js Dashboard Frontend** [INFERRED, semantically similar] — `dashboard/README.md` → `Dokumentasi_Lengkap`.
- **AnomalyPredictor → Alert** [INFERRED] — `ml/predictor.py` → `detection/alert_manager.py` (predictor memakai tipe Alert dari modul detection).
- **Aldaej et al. (Scientific Reports 2024)** ↔ **Three-tier Hybrid Detection Strategy** [INFERRED, conceptually related] — referensi PDF → artikel ilmiah.
- **Wardana et al. (Applied Sciences 2024)** ↔ **Edge Computing Paradigm for IoT Security** [INFERRED].
- **Aldaej et al. (Sensors 2023)** ↔ **Edge Computing Paradigm for IoT Security** [INFERRED].

Ini menunjukkan fondasi literatur proyek tertelusur secara otomatis dan tertaut ke konsep arsitektur yang diadopsi.

---

## 10. Hasil Training Model

Dari `ml/models/training_report.json`:

### Isolation Forest
- Sampel latih: 3.479 (hanya data `normal`) · 12 fitur · 200 estimator · contamination 0.05
- Anomali ditandai: 174 (5,0%) · score mean −0.3845 (std 0.1018)
- Trained at: 2026-09-22

### Random Forest
- Sampel latih: 7.979 · 12 fitur · 150 estimator · max_depth 15 · 6 kelas
- **Cross-validation: accuracy 0.9996 · F1-weighted 0.9996 · precision 0.9996 · recall 0.9996**
- Per-kelas (train): seluruh 6 kelas precision/recall/F1 = 1.0

---

## 11. Hasil Evaluasi (dan catatan integritas penting)

Dari `ml/models/evaluation_report.json`:

- Periode: 2026-09-21 23:38 → 2026-09-22 00:07 (≈29 menit)
- **Hanya 3 prediksi** dalam 5 skenario · 3 alert · binary metrics: TP=3, FP=0, FN=0 → **accuracy 1.0, precision 1.0, recall 1.0, F1 1.0, FPR 0**
- Detection latency: **~12 detik** (agregasi window 10 detik + poll)
- Multi-class report: `icmp_flood` recall 0.33 (karena hanya 3 sample).

> ⚠️ **Catatan integritas (WAJIB DIPERHATIKAN):**
> Artikel ilmiah alternatif `Artikel_Ilmiah_Unified_Network_Guard.md` mencantumkan angka **akurasi 98,2%, F1 96,9%, latency 0,54 detik**. Angka ini **TIDAK cocok** dengan `evaluation_report.json` aktual (100% / 100% / 12 detik, hanya 3 prediksi). Artikel IKOMTI (`Artikel_IKOMTI_Unified_Network_Guard_bak2.docx`) dengan sengaja **meninggalkan Tabel 1 kosong** daripada mencantumkan angka yang belum terverifikasi. Pengisian Tabel 1 (S1–S6 × 4 metode × 7 metrik) memerlukan skenario evaluasi per-metode per-skenario yang belum dijalankan.

---

## 12. Stack Teknologi

| Lapisan | Teknologi |
|---|---|
| Capture | Scapy (BPF filter `IOT_SUBNET`), Suricata (AF_PACKET) |
| IoT | 5× ESP32 (firmware `.ino`, PubSubClient + ArduinoJson), MQTT Mosquitto :1883 |
| Backend API | FastAPI (REST + WebSocket), `X-API-Key`, rate limiting, CORS |
| DB | PostgreSQL (5 tabel: devices, network_traffic, alerts, mqtt_telemetry, ml_predictions), semua timestamp UTC |
| ML | scikit-learn (Isolation Forest + Random Forest), joblib |
| Dashboard | Next.js 16 + React 19, Chart.js, lucide-react, WebSocket push |
| Infra | Docker Compose (PostgreSQL, Mosquitto, Grafana) |
| OS Edge | Ubuntu (PC edge komoditas) |

---

## 13. Struktur Direktori

```
unified-network-guard/
├── api/            # FastAPI server, routes, schemas, rate_limit, network_info
├── collector/      # traffic_sniffer (Scapy), mqtt_subscriber, db layer
├── detection/      # rule_engine, eve_parser, alert_manager, config
├── ml/             # main, trainer, predictor, feature_extractor, evaluator
│   ├── datasets/   # labeled.csv, normal.csv
│   └── models/     # *.pkl, training_report.json, evaluation_report.json, if_calibration.json
├── dashboard/      # Next.js 16 + React 19 (src/, components/, views/)
├── suricata/       # rules/local.rules, suricata.yaml
├── esp32/          # node01–node05 .ino firmware
├── database/       # schema.sql (seed 5 ESP32)
├── tools/          # simulate_esp32.py (simulator 5 node)
├── mqtt/           # konfigurasi broker
├── scripts/        # skrip build artikel
├── artikel/        # artikel ilmiah + dokumentasi + referensi PDF
├── logs/           # detection.log, predictor.log, simulator.log
├── .env / .env.example
├── docker-compose.yml
├── requirements.txt
├── README.md, DEMO_RUNBOOK.md
└── DATA_YANG_DIBUTUHKAN.md
```

---

## 14. Cara Menjalankan (ringkas)

```bash
# 1. Environment
source venv/bin/activate
cp .env.example .env            # sesuaikan CAPTURE_INTERFACE, IOT_SUBNET, GATEWAY_IP
docker compose up -d            # PostgreSQL, Mosquitto, Grafana

# 2. Suricata (jalankan terpisah sebagai IDS)
sudo suricata -c suricata/suricata.yaml -i enp9s0

# 3. Collector (sniffer + MQTT subscriber)
python collector/main.py

# 4. Detection (rule engine + eve parser + alert manager)
python detection/main.py

# 5. ML (train sekali, lalu jalankan predictor real-time)
python ml/main.py train         # training IF + RF
python ml/main.py predict       # predictor real-time (poll DB tiap 10s)

# 6. API
python api/server.py            # FastAPI :8000

# 7. Dashboard
cd dashboard && npm install && npm run dev   # :3001

# (opsional) Simulator ESP32 jika tanpa hardware fisik
python tools/simulate_esp32.py --all
```

Skenario pengujian (serangan terkontrol dari `192.168.10.100`): `nmap -sS` (port scan), `hping3 -S --flood` (SYN flood), `ping -f` (ICMP flood), serta klien MQTT tak berotorisasi.

---

## 15. Komunitas Tipis & Knowledge Gaps

Graf menandai area yang mungkin kurang terdokumentasi:
- **84 node terisolasi** (≤1 koneksi) — sebagian besar adalah entry dependency config (`eslintConfig`, `nextConfig`, `name`, `version`) dan stub referensi kecil; bukan bug, tapi dokumentasi hubungan bisa diperkuat.
- **15 komunitas tipis (<3 node)** di-omit dari laporan — jelajahi via `graphify query`.
- **1 edge AMBIGUOUS**: `Gambar yang ditempelkan.png` ↔ dirinya sendiri (content_unreadable) — asset gambar yang tidak terbaca isinya.

---

## 16. Sumber Analisis

Dokumen ini disusun dari:
- **graphify-out/GRAPH_REPORT.md** — laporan audit graf (655 node, 1232 edge, 45 komunitas).
- **graphify query** — traversal BFS atas `graphify-out/graph.json` untuk menjelajahi pipeline deteksi & ML.
- Verifikasi langsung pada: `README.md`, `.env`, `suricata/rules/local.rules`, `database/schema.sql`, `ml/models/training_report.json`, `ml/models/evaluation_report.json`, `ml/datasets/labeled.csv`, dan struktur direktori.

Untuk menjelajahi graf secara interaktif: buka `graphify-out/graph.html` di browser. Untuk pertanyaan lanjutan jalankan `graphify query "<pertanyaan>"`.

---

*Disusun: 2026-09-24 · Berdasarkan knowledge graph graphify (snapshot 2026-09-22).*
