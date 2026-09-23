# Dokumentasi Lengkap Proyek Unified Network Guard

## Platform Unified Network Guard Berbasis Edge Computing untuk Deteksi Anomali dan Serangan Siber pada Infrastruktur IoT

**Versi Dokumen:** 1.0  
**Tanggal:** 22 September 2026  
**Penulis:** Tim Proyek Akhir  

---

## Daftar Isi

1. [Pendahuluan](#1-pendahuluan)
2. [Konsep dan Tujuan Proyek](#2-konsep-dan-tujuan-proyek)
3. [Arsitektur Sistem](#3-arsitektur-sistem)
4. [Perangkat Keras (Hardware)](#4-perangkat-keras-hardware)
5. [Topologi Jaringan](#5-topologi-jaringan)
6. [Perangkat Lunak (Software Stack)](#6-perangkat-lunak-software-stack)
7. [Struktur Direktori Proyek](#7-struktur-direktori-proyek)
8. [Infrastruktur & Containerization](#8-infrastruktur--containerization)
9. [Database PostgreSQL](#9-database-postgresql)
10. [Firmware ESP32 — IoT Testbed](#10-firmware-esp32--iot-testbed)
11. [MQTT Broker & Data Pipeline](#11-mqtt-broker--data-pipeline)
12. [Modul Collector — Pengumpul Data](#12-modul-collector--pengumpul-data)
13. [Modul Detection — Mesin Deteksi](#13-modul-detection--mesin-deteksi)
14. [Suricata IDS — Signature-Based Detection](#14-suricata-ids--signature-based-detection)
15. [Modul Machine Learning](#15-modul-machine-learning)
16. [API Server — Backend FastAPI](#16-api-server--backend-fastapi)
17. [Dashboard — Frontend Next.js](#17-dashboard--frontend-nextjs)
18. [Alur Data End-to-End](#18-alur-data-end-to-end)
19. [Skenario Pengujian](#19-skenario-pengujian)
20. [Metrik Evaluasi](#20-metrik-evaluasi)
21. [Panduan Menjalankan Sistem](#21-panduan-menjalankan-sistem)
22. [Kesimpulan](#22-kesimpulan)

---

## 1. Pendahuluan

Unified Network Guard (UNG) adalah platform keamanan jaringan IoT berbasis Edge Computing yang dirancang untuk mendeteksi anomali dan serangan siber secara real-time. Sistem ini menggabungkan tiga pendekatan deteksi secara hybrid:

1. **Signature-Based Detection** menggunakan Suricata IDS
2. **Rule-Based / Threshold Detection** menggunakan custom rule engine
3. **Machine Learning Anomaly Detection** menggunakan Isolation Forest dan Random Forest

Seluruh pemrosesan dilakukan di edge (PC lokal), bukan di cloud, sehingga latensi deteksi sangat rendah dan data sensitif tidak meninggalkan jaringan lokal.

---

## 2. Konsep dan Tujuan Proyek

### 2.1 Bidang yang Digabungkan

| Bidang | Peran dalam UNG |
|---|---|
| **IoT** | ESP32 sebagai node sensor yang menghasilkan telemetri |
| **Networking** | Router, subnet, DHCP, traffic capture |
| **Edge Computing** | PC Ryzen 5 sebagai Edge Security Node |
| **Cybersecurity** | IDS, anomaly detection, alert system |
| **Machine Learning** | Isolation Forest untuk deteksi anomali |
| **Dashboard Monitoring** | Visualisasi real-time status jaringan |

### 2.2 Alur Konseptual

```
ESP32 menghasilkan aktivitas IoT
        ↓
Router membentuk jaringan IoT (192.168.20.0/24)
        ↓
Edge PC mengumpulkan dan menganalisis traffic
        ↓
Deteksi anomali / serangan (Hybrid: Suricata + Rule Engine + ML)
        ↓
Alert → Database → Dashboard
```

### 2.3 Tujuan Sistem

Sistem akhir diharapkan mampu:

1. Mengenali dan memantau perangkat IoT secara otomatis
2. Memantau seluruh traffic jaringan secara real-time
3. Mengekstrak fitur traffic untuk analisis
4. Mendeteksi pola traffic abnormal (anomaly detection)
5. Mendeteksi serangan yang dikenal (signature-based)
6. Menghasilkan alert dengan tingkat severity yang tepat
7. Menyimpan histori kejadian ke database
8. Menampilkan kondisi jaringan pada dashboard interaktif
9. Mengukur performa deteksi secara kuantitatif
10. Menunjukkan manfaat Edge Computing dalam pemrosesan keamanan jaringan IoT

---

## 3. Arsitektur Sistem

### 3.1 Arsitektur Hybrid Detection

```
┌──────────────────────────────────────┐
│       UNIFIED NETWORK GUARD          │
├──────────────────────────────────────┤
│ Packet Capture (Scapy)               │
│          ↓                           │
│ Feature Extraction                   │
│          ↓                           │
│ ┌──────────────┬─────────────────┐   │
│ │              │                 │   │
│ ▼              ▼                 ▼   │
│Suricata     Rule Engine     Isolation│
│IDS                          Forest   │
│ │              │                 │   │
│ └──────────────┴────────┬────────┘   │
│                         ▼            │
│                   Alert Engine       │
│                         │            │
│                         ▼            │
│                      Database        │
│                    (PostgreSQL)       │
│                         │            │
│                    ┌────┴────┐       │
│                    ▼         ▼       │
│                REST API   WebSocket  │
│                    │         │       │
│                    └────┬────┘       │
│                         ▼            │
│                  Next.js Dashboard   │
└──────────────────────────────────────┘
```

### 3.2 Komponen Arsitektur

| Komponen | Teknologi | Port | Fungsi |
|---|---|---|---|
| Database | PostgreSQL 15 Alpine | 5432 | Penyimpanan data traffic, device, alert, prediksi ML |
| MQTT Broker | Eclipse Mosquitto 2.0 | 1883, 9001 | Pertukaran data telemetri ESP32 |
| API Server | FastAPI + Uvicorn | 8000 | REST API + WebSocket real-time alert stream |
| Dashboard | Next.js 16.3 + React | 3001 | Frontend monitoring interaktif |
| Grafana | Grafana latest | 3002 | Dashboard metrik tambahan (host 3002 agar tak bentrok Next.js) |
| Traffic Sniffer | Scapy (Python) | — | Capture paket jaringan |
| Rule Engine | Python (threading) | — | Deteksi berbasis threshold |
| Suricata | Suricata IDS | — | Deteksi berbasis signature |
| ML Engine | scikit-learn | — | Isolation Forest + Random Forest |

---

## 4. Perangkat Keras (Hardware)

### 4.1 Daftar Perangkat

| Perangkat | Jumlah | Fungsi | IP Address |
|---|:---:|---|---|
| PC Ryzen 5 5500GT (RAM 8 GB) | 1 | Edge Computing Server | `192.168.20.100` |
| TP-Link TL-WR820N | 1 | Router jaringan IoT | `192.168.20.1` (LAN) |
| TP-Link TL-WR840N | 1 | Router jaringan pengujian/attacker | `192.168.10.1` |
| ESP32 #1 (Node01) | 1 | Climate Sensor (Temp/Humidity) | `192.168.20.101` |
| ESP32 #2 (Node02) | 1 | Security Sensor (Motion/Light) | `192.168.20.102` |
| ESP32 #3 (Node03) | 1 | Energy Meter (Power/Voltage) | `192.168.20.103` |
| ESP32 #4 (Node04) | 1 | Air Quality (CO2/PM2.5) | `192.168.20.104` |
| ESP32 #5 (Node05) | 1 | Smart Actuator & Gateway | `192.168.20.105` |

### 4.2 Perangkat Tambahan

- Kabel LAN (Cat5e/Cat6)
- Kabel USB Micro / Type-C untuk ESP32
- Breadboard, LED, Resistor (opsional untuk demo)
- Power supply untuk ESP32

### 4.3 Spesifikasi Router TL-WR820N

| Parameter | Nilai |
|---|---|
| Model | TP-Link TL-WR820N |
| Firmware | 0.9.1 4.17 |
| Operation Mode | WISP / Wireless Router |
| LAN IP | 192.168.20.1 |
| LAN Subnet | 255.255.255.0 (/24) |
| Wi-Fi SSID | TP-Link_D38E |
| Band | 2.4 GHz, Channel 6 |

---

## 5. Topologi Jaringan

### 5.1 Topologi Keseluruhan

```
                    INTERNET
                        │
                   Router Utama
                   192.168.1.1
                        │
              ┌─────────┴─────────┐
              │                   │
    ┌─────────────────┐   ┌──────────────┐
    │  TL-WR820N      │   │  TL-WR840N   │
    │  IoT Network    │   │  Attack Lab  │
    │  192.168.20.0/24│   │  192.168.10.0/24│
    └────────┬────────┘   └───────┬──────┘
             │                    │
    ┌────────┼────────┐           │
    │   │    │   │    │      Test PC
  ESP01 02  03  04  05     192.168.10.100
    │   │    │   │    │    (Lab Attacker)
    └────────┼────────┘
             │
        Edge PC (Ryzen 5)
        192.168.20.100
```

### 5.2 Tabel IP Address

**Jaringan IoT (192.168.20.0/24):**

| Device | IP Address | Fungsi |
|---|---|---|
| TL-WR820N LAN Gateway | `192.168.20.1` | Router / Access Point |
| Edge PC (Ryzen 5) | `192.168.20.100` | Edge Security Node |
| ESP32-01 | `192.168.20.101` | Climate Sensor |
| ESP32-02 | `192.168.20.102` | Security Sensor |
| ESP32-03 | `192.168.20.103` | Energy Meter |
| ESP32-04 | `192.168.20.104` | Air Quality Sensor |
| ESP32-05 | `192.168.20.105` | Smart Actuator |

**Jaringan Pengujian (192.168.10.0/24):**

| Device | IP Address | Fungsi |
|---|---|---|
| TL-WR840N | `192.168.10.1` | Router Attacker |
| Test PC | `192.168.10.100` | Lab Attacker / Pentest |

### 5.3 Segmentasi Jaringan

Dua router digunakan untuk memisahkan secara fisik dan logis:
- **Jaringan IoT** — tempat ESP32 node dan Edge PC beroperasi normal
- **Jaringan Pengujian** — tempat simulasi serangan dilakukan secara terisolasi

> **Catatan Keamanan:** Seluruh simulasi serangan hanya dilakukan pada perangkat dan jaringan lab milik sendiri. Tidak ada pengujian terhadap jaringan publik atau perangkat pihak lain.

---

## 6. Perangkat Lunak (Software Stack)

### 6.1 Edge PC (Ubuntu Linux)

| Kategori | Software | Fungsi |
|---|---|---|
| **OS & Tools** | Ubuntu 22.04/24.04 LTS, Git, Curl, Net-tools, tcpdump, TShark, htop, jq | Sistem operasi dan utilitas jaringan |
| **Container** | Docker Engine, Docker Compose | Menjalankan PostgreSQL, Mosquitto, Grafana |
| **MQTT** | Eclipse Mosquitto 2.0 | Broker MQTT untuk telemetri IoT |
| **IDS** | Suricata IDS | Intrusion Detection System berbasis signature |
| **Python** | Python 3.10+ | Runtime utama untuk backend |
| **Database** | PostgreSQL 15 | Penyimpanan data relasional |
| **Monitoring** | Grafana + Custom Dashboard (Next.js) | Visualisasi |

### 6.2 Dependensi Python (requirements.txt)

```
# Core Network & Packet Analysis
scapy>=2.5.0
pyshark>=0.6.0

# Machine Learning & Scientific Computing
numpy>=1.24.0
pandas>=2.0.0
scikit-learn>=1.3.0
joblib>=1.3.0

# IoT & Messaging
paho-mqtt>=1.6.1

# Backend API & Database
fastapi>=0.100.0
uvicorn[standard]>=0.23.0
pydantic>=2.0
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0

# API Security
python-multipart>=0.0.6

# Utilities
python-dotenv>=1.0.0
requests>=2.31.0
```

### 6.3 Dashboard (Next.js)

| Teknologi | Versi | Fungsi |
|---|---|---|
| Next.js | 16.3.5 | Framework React SSR/SSG |
| React | 19 | Library UI |
| TypeScript | 5.x | Type-safe JavaScript |
| Tailwind CSS | 4.x | Utility-first CSS framework |
| Lucide React | — | Icon library |

### 6.4 ESP32 Development

| Komponen | Fungsi |
|---|---|
| Arduino IDE / PlatformIO | IDE pemrograman ESP32 |
| WiFi.h | Library Wi-Fi bawaan ESP32 |
| PubSubClient | Library MQTT client |
| ArduinoJson | Serialisasi JSON telemetri |

### 6.5 Tool Pengujian Serangan

| Tool | Skenario | Fungsi |
|---|---|---|
| **Nmap** | Port Scanning | Scanning port terhadap node ESP32 & Edge PC |
| **Hping3** | TCP SYN / ICMP Flood | Stress test flooding |
| **Mosquitto Client** | MQTT Injection | Injeksi paket MQTT dari client tidak sah |
| **Apache Benchmark** | HTTP Spike | Connection spike / request flooding |

---

## 7. Struktur Direktori Proyek

```
unified-network-guard/
│
├── collector/                  # Modul pengumpul data jaringan
│   ├── __init__.py
│   ├── config.py               # Konfigurasi collector (interface, MQTT, DB)
│   ├── main.py                 # Entry point: jalankan sniffer + MQTT subscriber
│   ├── db.py                   # Fungsi insert batch ke PostgreSQL
│   ├── mqtt_subscriber.py      # Subscribe data telemetri dari ESP32 via MQTT
│   └── traffic_sniffer.py      # Capture paket jaringan real-time via Scapy
│
├── detection/                  # Modul deteksi serangan & anomali
│   ├── __init__.py
│   ├── config.py               # Threshold rule engine, path Suricata eve.json
│   ├── main.py                 # Entry point: jalankan rule engine + eve parser
│   ├── rule_engine.py          # Deteksi Port Scan, SYN Flood, ICMP Flood, dll.
│   ├── eve_parser.py           # Parser log eve.json dari Suricata IDS
│   └── alert_manager.py        # De-duplikasi alert + insert ke DB
│
├── ml/                         # Modul Machine Learning
│   ├── __init__.py
│   ├── config.py               # Hyperparameter IF & RF, feature columns
│   ├── main.py                 # CLI: train / predict / evaluate
│   ├── feature_extractor.py    # Ekstraksi 12 fitur dari traffic DB
│   ├── trainer.py              # Training Isolation Forest + Random Forest
│   ├── predictor.py            # Real-time prediction loop
│   ├── evaluator.py            # Evaluasi model (accuracy, precision, recall, F1)
│   ├── generate_dataset.py     # Generator dataset CSV dari traffic DB
│   ├── models/                 # File model (.pkl) yang sudah di-train
│   ├── datasets/               # Dataset CSV hasil generate
│   └── scenarios_eval.json     # Skenario evaluasi
│
├── api/                        # Backend REST API
│   ├── __init__.py
│   ├── config.py               # API key, CORS, rate limit, pagination
│   ├── server.py               # Aplikasi FastAPI utama + WebSocket
│   ├── schemas.py              # Pydantic v2 schemas (validasi ketat)
│   ├── deps.py                 # Dependency injection (DB session, auth)
│   └── routes/
│       ├── __init__.py
│       ├── devices.py          # CRUD perangkat IoT
│       ├── traffic.py          # Query data traffic jaringan
│       ├── alerts.py           # Query alert keamanan
│       └── predictions.py      # Query prediksi ML
│
├── dashboard/                  # Frontend Next.js
│   ├── package.json
│   ├── next.config.ts
│   ├── tsconfig.json
│   └── src/
│       ├── app/
│       │   ├── layout.tsx      # Root layout + provider
│       │   ├── page.tsx        # Halaman utama dashboard
│       │   └── globals.css     # Tailwind CSS global styles
│       ├── contexts/
│       │   └── DashboardContext.tsx  # State management + data fetching
│       ├── hooks/
│       │   └── useCanvas.ts    # Custom hook untuk rendering canvas
│       └── components/
│           ├── Header.tsx              # Navigasi, notifikasi, settings
│           ├── StatCards.tsx            # Kartu statistik (packets, alerts, nodes)
│           ├── MainGaugeCard.tsx        # Gauge utama skor keamanan
│           ├── RiskLevelPanel.tsx       # Panel risk level + severity distribution
│           ├── ThreatsPanel.tsx         # Panel attack classification + topology
│           ├── LiveTopologyMap.tsx      # Peta topologi real-time (canvas 60fps)
│           ├── BottomHealthPanels.tsx   # Panel kesehatan sistem
│           ├── MultiLineChart.tsx       # Grafik multi-line traffic
│           ├── TopSmallLineChart.tsx    # Mini chart header
│           └── views/
│               ├── EndpointsView.tsx    # Tab: daftar perangkat IoT
│               ├── NetworkView.tsx      # Tab: analisis jaringan
│               ├── ThreatsView.tsx      # Tab: daftar ancaman
│               ├── IncidentsView.tsx    # Tab: insiden keamanan
│               └── ReportsView.tsx      # Tab: laporan/ekspor
│
├── esp32/                      # Firmware Arduino untuk 5 ESP32 node
│   ├── node01/node01.ino       # Climate Sensor (Temp/Humidity)
│   ├── node02/node02.ino       # Security Sensor (Motion/Light)
│   ├── node03/node03.ino       # Energy Meter (Power/Voltage)
│   ├── node04/node04.ino       # Air Quality (CO2/PM2.5)
│   └── node05/node05.ino       # Smart Actuator & Gateway
│
├── suricata/                   # Konfigurasi Suricata IDS
│   └── rules/
│       └── local.rules         # 14 custom signature rules UNG
│
├── mqtt/
│   └── mosquitto.conf          # Konfigurasi MQTT broker
│
├── database/
│   └── schema.sql              # Skema DDL PostgreSQL (5 tabel + indeks)
│
├── tools/
│   └── simulate_esp32.py       # Simulasi 5 ESP32 tanpa hardware fisik
│
├── logs/                       # Log runtime
│   ├── api.log
│   ├── predictor.log
│   └── dashboard.log
│
├── docker-compose.yml          # Orchestrasi PostgreSQL, Mosquitto, Grafana
├── requirements.txt            # Dependensi Python
└── .env                        # Environment variables (tidak di-commit)
```

---

## 8. Infrastruktur & Containerization

### 8.1 Docker Compose

Tiga service dijalankan via Docker Compose:

```yaml
services:
  postgres:
    image: postgres:15-alpine
    container_name: ung_postgres
    environment:
      POSTGRES_DB: network_guard
      POSTGRES_USER: guard_user
      POSTGRES_PASSWORD: guard_secret
    ports: ["5432:5432"]
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database/schema.sql:/docker-entrypoint-initdb.d/schema.sql:ro

  mosquitto:
    image: eclipse-mosquitto:2.0
    container_name: ung_mosquitto
    ports: ["1883:1883", "9001:9001"]
    volumes:
      - ./mqtt/mosquitto.conf:/mosquitto/config/mosquitto.conf

  grafana:
    image: grafana/grafana:latest
    container_name: ung_grafana
    ports: ["3002:3000"]
    environment:
      GF_SECURITY_ADMIN_USER: admin
      GF_SECURITY_ADMIN_PASSWORD: admin
```

### 8.2 Script Setup Edge PC

File `setup_edge.sh` otomatis menginstal seluruh dependensi sistem:
- Git, Curl, Wget, Net-tools, tcpdump, TShark
- Python 3 + pip + venv
- Mosquitto MQTT Broker & Client
- Suricata IDS
- Docker Engine & Docker Compose
- Nmap, Hping3, Apache Benchmark (untuk pengujian)

Jalankan: `sudo bash setup_edge.sh`

---

## 9. Database PostgreSQL

### 9.1 Skema Database

Database `network_guard` terdiri dari **5 tabel** utama:

#### Tabel `devices` — Registrasi Perangkat IoT

| Kolom | Tipe | Keterangan |
|---|---|---|
| `id` | SERIAL PK | ID auto-increment |
| `device_name` | VARCHAR(100) | Nama perangkat (ESP32-01, dst.) |
| `ip_address` | VARCHAR(45) UNIQUE | Alamat IP perangkat |
| `mac_address` | VARCHAR(20) | MAC address (nullable) |
| `device_type` | VARCHAR(50) | Jenis sensor |
| `status` | VARCHAR(20) | `online` / `offline` / `registered` |
| `last_seen` | TIMESTAMP | Waktu terakhir heartbeat diterima |

#### Tabel `network_traffic` — Data Lalu Lintas Jaringan

| Kolom | Tipe | Keterangan |
|---|---|---|
| `id` | SERIAL PK | ID auto-increment |
| `timestamp` | TIMESTAMP | Waktu paket ditangkap |
| `source_ip` | VARCHAR(45) | IP sumber |
| `destination_ip` | VARCHAR(45) | IP tujuan |
| `protocol` | VARCHAR(20) | TCP / UDP / ICMP / OTHER |
| `source_port` | INTEGER | Port sumber (nullable untuk ICMP) |
| `destination_port` | INTEGER | Port tujuan |
| `packet_count` | INTEGER | Jumlah paket (selalu 1 per record) |
| `bytes` | INTEGER | Ukuran paket dalam byte |

#### Tabel `alerts` — Alert Keamanan

| Kolom | Tipe | Keterangan |
|---|---|---|
| `id` | SERIAL PK | ID auto-increment |
| `timestamp` | TIMESTAMP | Waktu alert dibuat |
| `source_ip` | VARCHAR(45) | IP sumber serangan |
| `target_ip` | VARCHAR(45) | IP target serangan |
| `attack_type` | VARCHAR(100) | Jenis serangan |
| `severity` | VARCHAR(20) | LOW / MEDIUM / HIGH / CRITICAL |
| `confidence` | DOUBLE PRECISION | Tingkat keyakinan (0.0–1.0) |
| `description` | TEXT | Deskripsi detail alert |

#### Tabel `mqtt_telemetry` — Data Telemetri IoT

| Kolom | Tipe | Keterangan |
|---|---|---|
| `id` | SERIAL PK | ID auto-increment |
| `timestamp` | TIMESTAMP | Waktu data diterima |
| `device_id` | VARCHAR(50) | ID perangkat pengirim |
| `topic` | VARCHAR(200) | MQTT topic |
| `payload` | JSONB | Data sensor dalam format JSON |
| `source_ip` | VARCHAR(45) | IP sumber |

#### Tabel `ml_predictions` — Hasil Prediksi ML

| Kolom | Tipe | Keterangan |
|---|---|---|
| `id` | SERIAL PK | ID auto-increment |
| `timestamp` | TIMESTAMP | Waktu prediksi |
| `source_ip` | VARCHAR(45) | IP yang dianalisis |
| `time_bucket` | TIMESTAMP | Window waktu agregasi |
| `if_score` | FLOAT | Skor anomali Isolation Forest |
| `is_anomaly` | BOOLEAN | Hasil: anomali atau normal |
| `attack_class` | VARCHAR(50) | Kelas serangan (Random Forest) |
| `confidence` | FLOAT | Tingkat keyakinan |
| `features` | JSONB | Vektor fitur yang digunakan |

### 9.2 Index Performa

```sql
CREATE INDEX idx_telemetry_device_time ON mqtt_telemetry (device_id, timestamp DESC);
CREATE INDEX idx_traffic_timestamp ON network_traffic (timestamp DESC);
CREATE INDEX idx_alerts_timestamp ON alerts (timestamp DESC);
CREATE INDEX idx_mlpred_timestamp ON ml_predictions (timestamp DESC);
CREATE INDEX idx_mlpred_anomaly ON ml_predictions (is_anomaly, timestamp DESC);
```

### 9.3 Seed Data Awal

Lima perangkat ESP32 didaftarkan saat inisialisasi database:

```sql
INSERT INTO devices (device_name, ip_address, device_type, status) VALUES
    ('ESP32-01', '192.168.20.101', 'Climate Sensor (Temp/Humidity)', 'registered'),
    ('ESP32-02', '192.168.20.102', 'Security Sensor (Motion/Light)', 'registered'),
    ('ESP32-03', '192.168.20.103', 'Energy Meter (Power/Voltage)', 'registered'),
    ('ESP32-04', '192.168.20.104', 'Air Quality (CO2/PM2.5)', 'registered'),
    ('ESP32-05', '192.168.20.105', 'Smart Actuator & Gateway', 'registered')
ON CONFLICT (ip_address) DO NOTHING;
```

---

## 10. Firmware ESP32 — IoT Testbed

### 10.1 Pembagian Peran 5 Node

| Node | File | Peran | Data yang Dikirim |
|---|---|---|---|
| ESP32-01 | `node01.ino` | Indoor Climate | Suhu (°C) & Kelembapan (%) |
| ESP32-02 | `node02.ino` | Security Sensor | Motion (detected/clear) & Light (lux) |
| ESP32-03 | `node03.ino` | Energy Meter | Power (W) & Voltage (V) |
| ESP32-04 | `node04.ino` | Air Quality | CO2 (ppm) & PM2.5 (µg/m³) |
| ESP32-05 | `node05.ino` | Smart Actuator | Status relay & command response |

### 10.2 Arsitektur Firmware

Setiap node ESP32 menjalankan alur yang sama:

1. **Setup Wi-Fi** — Koneksi ke SSID `TP-Link_D38E` pada subnet `192.168.20.0/24`
2. **Koneksi MQTT** — Terhubung ke broker di `192.168.20.100:1883`
3. **Simulasi Sensor** — Generate data sensor dengan random walk realistis
4. **Publish** — Kirim payload JSON ke topic `iot/esp32-XX/telemetry` setiap 4 detik
5. **Heartbeat** — LED built-in berkedip sebagai indikator status

### 10.3 Contoh Payload MQTT

```json
{
  "device_id": "ESP32-01",
  "temperature": 29.4,
  "humidity": 72.3,
  "uptime_s": 1234,
  "wifi_rssi": -45,
  "seq": 308,
  "timestamp": "2026-09-22T00:15:00"
}
```

### 10.4 Konfigurasi Jaringan ESP32

```cpp
const char* ssid        = "TP-Link_D38E";
const char* password    = "12345678";
const char* mqtt_broker = "192.168.20.100";
const int   mqtt_port   = 1883;
const char* mqtt_topic  = "iot/esp32-01/telemetry";
const unsigned long PUBLISH_INTERVAL_MS = 4000;
```

### 10.5 Simulasi ESP32 Tanpa Hardware

File `tools/simulate_esp32.py` memungkinkan simulasi 5 node ESP32 secara software, sehingga pengujian dapat dilakukan tanpa hardware fisik yang terhubung.

---

## 11. MQTT Broker & Data Pipeline

### 11.1 Konfigurasi Mosquitto

Mosquitto berjalan di port `1883` (TCP) dan `9001` (WebSocket), dengan listener `allow_anonymous true` untuk lingkungan lab.

### 11.2 Struktur Topic MQTT

```
iot/
├── esp32-01/telemetry    # Data suhu & kelembapan
├── esp32-02/telemetry    # Data motion & light
├── esp32-03/telemetry    # Data power & voltage
├── esp32-04/telemetry    # Data CO2 & PM2.5
└── esp32-05/telemetry    # Data actuator status
```

### 11.3 Alur Data MQTT

```
ESP32 Node → Wi-Fi → Router (192.168.20.1) → Mosquitto Broker (192.168.20.100:1883)
                                                        ↓
                                               MQTT Subscriber (collector)
                                                        ↓
                                               PostgreSQL (mqtt_telemetry)
                                                        ↓
                                               Device Status Update (devices)
```

---

## 12. Modul Collector — Pengumpul Data

### 12.1 Komponen Collector

Modul collector terdiri dari dua sub-komponen yang berjalan paralel:

#### A. Traffic Sniffer (`traffic_sniffer.py`)

**Fungsi:** Menangkap paket jaringan secara real-time menggunakan Scapy.

**Fitur yang Diekstrak per Paket:**
- `timestamp` — Waktu paket ditangkap
- `source_ip` — Alamat IP sumber
- `destination_ip` — Alamat IP tujuan
- `protocol` — TCP / UDP / ICMP / OTHER
- `source_port`, `destination_port` — Port (null untuk ICMP)
- `packet_count` — Selalu 1 per paket
- `bytes` — Panjang paket dalam byte

**Mekanisme Batch Insert:**
- Paket dikumpulkan ke buffer (list) terlebih dahulu
- Di-flush ke PostgreSQL setiap `TRAFFIC_BATCH_SIZE` (50) paket atau `TRAFFIC_FLUSH_INTERVAL` (5) detik
- Thread-safe dengan `threading.Lock`

**Konfigurasi:**

| Parameter | Default | Keterangan |
|---|---|---|
| `CAPTURE_INTERFACE` | `eth0` | Interface jaringan untuk sniffing |
| `CAPTURE_BPF_FILTER` | `net 192.168.20.0/24` | BPF filter — hanya tangkap traffic subnet IoT |
| `TRAFFIC_BATCH_SIZE` | 50 | Jumlah paket per batch insert |
| `TRAFFIC_FLUSH_INTERVAL` | 5 detik | Interval flush berkala |

#### B. MQTT Subscriber (`mqtt_subscriber.py`)

**Fungsi:** Subscribe ke semua topic `iot/#` di broker Mosquitto untuk menerima telemetri ESP32.

**Proses:**
1. Subscribe wildcard topic `iot/#`
2. Parse payload JSON dari setiap pesan
3. Simpan ke tabel `mqtt_telemetry` di PostgreSQL
4. Update `last_seen` dan `status` perangkat di tabel `devices`

### 12.2 Database Helper (`db.py`)

- `insert_traffic_batch()` — Batch insert data traffic ke `network_traffic`
- `insert_telemetry()` — Insert telemetri MQTT ke `mqtt_telemetry`
- `upsert_device_status()` — Update status dan `last_seen` perangkat

### 12.3 Menjalankan Collector

```bash
sudo ./venv/bin/python -m collector.main
```

> Membutuhkan `sudo` karena Scapy memerlukan akses raw socket untuk sniffing.

---

## 13. Modul Detection — Mesin Deteksi

### 13.1 Rule Engine (`rule_engine.py`)

Engine deteksi berbasis aturan threshold yang beroperasi real-time menggunakan sliding time window.

#### Jenis Serangan yang Dideteksi:

| # | Serangan | Threshold | Window | Severity |
|---|---|---|---|---|
| 1 | **Port Scan** | ≥ 20 port unik dari 1 source | 5 detik | MEDIUM |
| 2 | **SYN Flood** | ≥ 100 paket SYN ke 1 target | 2 detik | HIGH |
| 3 | **ICMP Flood** | ≥ 50 paket ICMP echo | 3 detik | HIGH |
| 4 | **Traffic Spike** | ≥ 5 MB total bytes dalam 5 detik (≈1 MB/s) | 5 detik | MEDIUM |
| 5 | **MQTT Rate Abuse** | ≥ 30 pesan MQTT dalam 1 detik | 1 detik | MEDIUM |

#### Arsitektur Sliding Window:

```
                 Network Traffic DB
                         │
                         ▼ (poll setiap 3 detik)
              ┌──────────────────────┐
              │    Rule Engine       │
              │                      │
              │  TimeWindow per IP   │
              │  ├── Port Scan       │
              │  ├── SYN Flood       │
              │  ├── ICMP Flood      │
              │  ├── Traffic Spike   │
              │  └── MQTT Abuse      │
              └──────────┬───────────┘
                         │
                         ▼
                   Alert Manager
                         │
                         ▼
                   PostgreSQL (alerts)
```

### 13.2 Alert Manager (`alert_manager.py`)

**Tanggung jawab:**
1. Memetakan classtype / nama serangan ke severity (LOW/MEDIUM/HIGH/CRITICAL)
2. De-duplikasi: alert identik tidak di-insert ulang selama 30 detik
3. Insert alert ke tabel `alerts` di PostgreSQL
4. Menyediakan dataclass `Alert` sebagai struktur data internal

**Severity Map:**

| Classtype / Attack | Severity |
|---|---|
| `attempted-recon`, `PORT_SCAN` | MEDIUM |
| `attempted-dos`, `SYN_FLOOD`, `ICMP_FLOOD` | HIGH |
| `attempted-admin` | CRITICAL |
| `policy-violation`, `TRAFFIC_SPIKE`, `MQTT_RATE_ABUSE` | MEDIUM |
| `trojan-activity` | CRITICAL |

### 13.3 EVE Parser (`eve_parser.py`)

Parser log `eve.json` dari Suricata IDS. Membaca file secara tail-follow dan mengkonversi event alert Suricata menjadi objek `Alert` yang dikirim ke Alert Manager.

---

## 14. Suricata IDS — Signature-Based Detection

### 14.1 Custom Rules (`local.rules`)

UNG menggunakan **14 custom Suricata rules** yang dibagi dalam 5 kelompok:

#### Kelompok 1: Reconnaissance / Port Scanning (SID 1000001–1000003)

```
# TCP Port Scan ke subnet IoT (≥20 SYN dalam 5 detik)
alert tcp any any -> 192.168.20.0/24 any (
    msg:"UNG-ALERT: Possible TCP Port Scan to IoT Network";
    flags:S; threshold:type threshold, track by_src, count 20, seconds 5;
    classtype:attempted-recon; sid:1000001; rev:2;)

# Port Scan khusus dari subnet attacker (≥10 dalam 3 detik)
alert tcp 192.168.10.0/24 any -> 192.168.20.0/24 any (
    msg:"UNG-ALERT: TCP Port Scan from Attacker Subnet";
    flags:S; threshold:type threshold, track by_src, count 10, seconds 3;
    classtype:attempted-recon; sid:1000002; rev:2;)

# UDP Port Scan
alert udp any any -> 192.168.20.0/24 any (
    msg:"UNG-ALERT: UDP Port Scan to IoT Network";
    threshold:type threshold, track by_src, count 30, seconds 5;
    classtype:attempted-recon; sid:1000003; rev:1;)
```

#### Kelompok 2: DoS / Flood (SID 1000010–1000012)

- **ICMP Ping Flood** — ≥50 ICMP echo dalam 3 detik
- **TCP SYN Flood** — ≥100 SYN per target dalam 2 detik
- **UDP Flood** — ≥200 paket UDP per target dalam 2 detik

#### Kelompok 3: MQTT / IoT Protocol Anomaly (SID 1000020–1000023)

- **Unauthorized MQTT** dari subnet attacker
- **MQTT dari IP eksternal** yang bukan subnet IoT
- **MQTT WebSocket** dari non-IoT subnet
- **MQTT Rate Abuse** — ≥30 koneksi baru per detik

#### Kelompok 4: Brute Force (SID 1000030–1000031)

- **SSH Brute Force** ke Edge PC (port 22)
- **HTTP Brute Force** ke dashboard (port 3001)

#### Kelompok 5: Anomaly Traffic General (SID 1000040–1000041)

- **IoT node ke port tidak lazim** (bukan MQTT/HTTP)
- **Traffic keluar** dari IoT subnet ke internet (suspicious exfiltration)

---

## 15. Modul Machine Learning

### 15.1 Pipeline ML

```
Network Traffic DB
        ↓
Feature Extraction (per IP per 10-detik window)
        ↓
12 Fitur Numerik
        ↓
┌──────────────────┬─────────────────┐
│  Isolation Forest │  Random Forest  │
│  (Unsupervised)   │  (Supervised)   │
│                   │  [Opsional]     │
└────────┬─────────┴────────┬────────┘
         ↓                  ↓
    Anomaly Score      Attack Class
         ↓                  ↓
    is_anomaly?      (normal/port_scan/
         │            syn_flood/icmp_flood/
         ↓            traffic_spike/mqtt_anomaly)
    Alert Engine
         ↓
    PostgreSQL (ml_predictions + alerts)
```

### 15.2 Feature Engineering (12 Fitur)

Fitur diekstrak dari tabel `network_traffic` per source IP per window 10 detik:

| # | Fitur | Deskripsi |
|---|---|---|
| 1 | `packet_count` | Jumlah total paket dalam window |
| 2 | `byte_count` | Total bytes dalam window |
| 3 | `connection_count` | Jumlah baris unik (unique flow) |
| 4 | `packet_rate` | packet_count / window_seconds |
| 5 | `byte_rate` | byte_count / window_seconds |
| 6 | `avg_packet_size` | byte_count / packet_count |
| 7 | `unique_dst_ports` | Jumlah port tujuan unik |
| 8 | `unique_dst_ips` | Jumlah IP tujuan unik |
| 9 | `proto_tcp_ratio` | Proporsi paket TCP (0.0–1.0) |
| 10 | `proto_udp_ratio` | Proporsi paket UDP (0.0–1.0) |
| 11 | `proto_icmp_ratio` | Proporsi paket ICMP (0.0–1.0) |
| 12 | `mqtt_ratio` | Proporsi paket ke/dari port 1883 |

### 15.3 Isolation Forest (Algoritma Utama)

**Mengapa Isolation Forest?**

1. **Unsupervised** — Tidak membutuhkan label lengkap
2. **Cocok untuk anomaly detection** — Traffic anomali "mudah diisolasi" dari data normal
3. **Ringan untuk Edge Computing** — Cocok untuk resource PC terbatas (RAM 8 GB)
4. **Efektif untuk traffic IoT** — Pola IoT berulang membuat anomali sangat kontras

**Hyperparameter:**

| Parameter | Nilai | Keterangan |
|---|---|---|
| `n_estimators` | 200 | Jumlah pohon isolasi |
| `contamination` | 0.05 | Proporsi anomali yang diharapkan (5%) |
| `max_samples` | auto | Jumlah sampel per pohon |
| `random_state` | 42 | Seed reprodusibilitas |
| Score Threshold | otomatis (kalibrasi training) | Skor ≤ threshold = anomali; threshold dihitung dari contamination 0.05 pada data training (`ml/models/if_calibration.json`). Dapat ditimpa via env `IF_SCORE_THRESHOLD` |

### 15.4 Random Forest (Opsional — Klasifikasi)

Untuk mengklasifikasikan jenis serangan jika dataset memiliki label:

| Parameter | Nilai |
|---|---|
| `n_estimators` | 150 |
| `max_depth` | 15 |
| `n_jobs` | -1 (semua CPU core) |

**Kelas Klasifikasi:**
- `normal`
- `port_scan`
- `syn_flood`
- `icmp_flood`
- `traffic_spike`
- `mqtt_anomaly`

### 15.5 Menjalankan ML

```bash
# Training model dari dataset
python -m ml.main train

# Real-time prediction loop
python -m ml.main predict

# Evaluasi model
python -m ml.main evaluate
```

---

## 16. API Server — Backend FastAPI

### 16.1 Endpoint REST API

Semua endpoint di bawah prefix `/api/v1/` membutuhkan header `X-API-Key`.

#### System

| Method | Endpoint | Fungsi |
|---|---|---|
| GET | `/` | Health check publik (tanpa auth) |
| GET | `/api/v1/system/status` | Status sistem + statistik DB |

#### Devices

| Method | Endpoint | Fungsi |
|---|---|---|
| GET | `/api/v1/devices` | List perangkat IoT (paginated) |
| GET | `/api/v1/devices/{id}` | Detail satu perangkat |

#### Traffic

| Method | Endpoint | Fungsi |
|---|---|---|
| GET | `/api/v1/traffic` | List data traffic (paginated + filter) |
| GET | `/api/v1/traffic/summary` | Ringkasan per source IP |

#### Alerts

| Method | Endpoint | Fungsi |
|---|---|---|
| GET | `/api/v1/alerts` | List alert (paginated + filter) |
| GET | `/api/v1/alerts/stats` | Statistik agregat alert |
| GET | `/api/v1/alerts/{id}` | Detail satu alert |

#### Predictions

| Method | Endpoint | Fungsi |
|---|---|---|
| GET | `/api/v1/predictions` | List prediksi ML (paginated) |
| GET | `/api/v1/predictions/stats` | Statistik anomali ML |

### 16.2 WebSocket Real-Time

| Endpoint | Fungsi |
|---|---|
| `ws://host:8000/ws/alerts?token=<api_key>` | Stream alert baru secara real-time |

WebSocket polling DB setiap 2 detik, mengirim alert baru ke semua client yang terhubung.

### 16.3 Fitur Keamanan API

| Fitur | Implementasi |
|---|---|
| **Autentikasi** | API Key via header `X-API-Key` |
| **CORS Whitelist** | Hanya origin tertentu yang diizinkan |
| **Security Headers** | X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, HSTS |
| **Rate Limiting** | 120 req/menit default, 30 req/menit untuk endpoint berat |
| **Pydantic Validation** | Validasi ketat pada semua input/output |
| **Trusted Host** | TrustedHostMiddleware untuk mencegah Host header injection |
| **SQL Injection Prevention** | Parameterized queries via SQLAlchemy `text()` |

### 16.4 Startup Behavior

Saat API server dimulai, status perangkat yang masih `online` tapi sudah tidak mengirim heartbeat > 10 detik secara otomatis di-reset ke `offline`.

### 16.5 Menjalankan API

```bash
uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload
```

---

## 17. Dashboard — Frontend Next.js

### 17.1 Arsitektur Frontend

Dashboard dibangun dengan **Next.js 16.3 + React 19 + TypeScript + Tailwind CSS**. Semua state management terpusat di `DashboardContext.tsx`.

### 17.2 Mekanisme Data Fetching

1. **Polling REST API** setiap 2.5 detik ke:
   - `/api/v1/system/status`
   - `/api/v1/alerts/stats`
   - `/api/v1/devices`
   - `/api/v1/traffic`
   - `/api/v1/alerts?limit=10`

2. **WebSocket** ke `ws://host:8000/ws/alerts` untuk alert real-time

3. **Diff-checking** pada setiap poll — hanya update state jika data berubah (efisien)

### 17.3 Komponen Dashboard Utama

#### Header (`Header.tsx`)
- Navigasi tab: Dashboard, Endpoints, Network, Threats, Incidents, Reports
- Search bar, notifikasi alert real-time, time range selector
- Status koneksi WebSocket, user profile

#### Stat Cards (`StatCards.tsx`)
- **Total Captured Packets** — jumlah paket yang ditangkap Scapy
- **Security Alerts** — jumlah alert Suricata & rule engine
- **IoT Nodes Online** — jumlah ESP32 yang aktif (heartbeat < 12 detik)

#### Live Topology Map (`LiveTopologyMap.tsx`)
- Peta topologi jaringan real-time menggunakan HTML Canvas (60 FPS)
- Menampilkan Router, Edge PC, 5 ESP32 node, dan Lab Attacker
- Animasi partikel travelling packet antar node
- Status node: ONLINE / OFFLINE / AKTIF / STANDBY / UP
- **Heartbeat freshness detection** — node hanya dianggap online jika `last_seen` < 12 detik
- **Attack freshness detection** — Lab Attacker hanya AKTIF jika ada alert/traffic dari `192.168.20.x` dalam 15 detik terakhir

#### Risk Level Panel (`RiskLevelPanel.tsx`)
- Distribusi severity: Critical, High, Low
- Gauge skor risiko (circular arc chart)

#### Threats Panel (`ThreatsPanel.tsx`)
- Histogram distribusi jenis serangan (Port Scan, SYN Flood, ICMP Flood, MQTT Anomaly, Spike DoS)
- Live Topology Map embedding
- Footer dengan status Gateway, Edge PC, dan Lab Attacker (dinamis)

#### Bottom Health Panels (`BottomHealthPanels.tsx`)
- Multi-line chart traffic trend
- Mini chart per metrik

### 17.4 Tab Views

| Tab | Komponen | Fungsi |
|---|---|---|
| Dashboard | `page.tsx` | Overview utama |
| Endpoints | `EndpointsView.tsx` | Daftar perangkat IoT + status |
| Network | `NetworkView.tsx` | Analisis traffic jaringan |
| Threats | `ThreatsView.tsx` | Daftar alert keamanan |
| Incidents | `IncidentsView.tsx` | Insiden keamanan |
| Reports | `ReportsView.tsx` | Laporan & ekspor data |

### 17.5 Proxy Configuration

```typescript
// next.config.ts
rewrites: [
  { source: '/api/:path*', destination: 'http://localhost:8000/api/:path*' }
]
```

Dashboard di port 3001 mem-proxy semua request `/api/*` ke FastAPI di port 8000.

### 17.6 Menjalankan Dashboard

```bash
cd unified-network-guard/dashboard
npm install
npm run dev    # Development (port 3001)
npm run build  # Production build
```

---

## 18. Alur Data End-to-End

### 18.1 Alur Normal Operation

```
ESP32 Node                  Mosquitto Broker              Collector
(192.168.20.10x)            (192.168.20.100:1883)         (Python)
     │                              │                        │
     │── MQTT Publish ──────────────►│                        │
     │   topic: iot/esp32-XX/       │                        │
     │   payload: {temp, hum, ...}  │                        │
     │                              │── Subscribe iot/# ─────►│
     │                              │                        │
     │                              │                        ├── Insert mqtt_telemetry
     │                              │                        ├── Update devices.last_seen
     │                              │                        └── Update devices.status
     │                              │                        
     │                              │                     Traffic Sniffer
     │                              │                        │
     │── Network Packet ────────────────────────────────────►│
     │                              │                        ├── Extract features
     │                              │                        └── Batch insert network_traffic
```

### 18.2 Alur Deteksi Serangan

```
Attacker PC                 Suricata IDS              Rule Engine
(192.168.10.100)           (interface sniff)         (Python thread)
     │                          │                        │
     │── Port Scan ─────────────►│                        │
     │── SYN Flood ──────────────►│                        │
     │── ICMP Flood ─────────────►│                        │
     │                          │                        │
     │                          ├── eve.json log         │
     │                          │      │                 │
     │                          │      ▼                 │
     │                          │  EVE Parser            │
     │                          │      │                 │
     │                          │      ▼                 │
     │                          │  Alert Manager ◄───────┤
     │                          │      │                 │
     │                          │      ▼                 │
     │                          │  PostgreSQL (alerts)   │
     │                          │      │                 │
     │                          │      ▼                 │
     │                          │  WebSocket broadcast   │
     │                          │      │                 │
     │                          │      ▼                 │
     │                          │  Dashboard (real-time) │
```

### 18.3 Alur Prediksi ML

```
network_traffic DB
        │
        ▼ (poll setiap 10 detik)
Feature Extractor
        │
        ▼
12 fitur numerik per IP per window
        │
        ├──────────────────┐
        ▼                  ▼
Isolation Forest     Random Forest
   (anomaly?)          (attack class)
        │                  │
        ▼                  ▼
   ml_predictions DB
        │
        ▼ (jika anomali)
   Alert Manager → alerts DB → WebSocket → Dashboard
```

---

## 19. Skenario Pengujian

### 19.1 Skenario Minimal (Wajib)

| Kode | Skenario | Deskripsi | Tool |
|---|---|---|---|
| **S1** | Traffic Normal | ESP32 mengirim data sensor secara normal | ESP32 / simulate_esp32.py |
| **S2** | Traffic Abnormal / Connection Spike | Lonjakan koneksi mendadak | Apache Benchmark (`ab`) |
| **S3** | Port Scanning | Scanning port terhadap node IoT | Nmap |
| **S4** | Traffic Flooding / Stress Test | SYN Flood dan ICMP Flood | Hping3 |

### 19.2 Skenario Opsional

| Kode | Skenario | Deskripsi | Tool |
|---|---|---|---|
| **S5** | Unauthorized MQTT Client | Injeksi dari client tidak sah | Mosquitto client |
| **S6** | MQTT Anomaly | Pesan rate abuse dari satu client | Python script |

### 19.3 Prosedur Pengujian

Setiap skenario:
1. Diulang beberapa kali dengan prosedur identik
2. Ground truth dicatat secara manual
3. Waktu mulai dan selesai serangan didokumentasikan
4. Alert yang muncul dicatat dan dibandingkan dengan ground truth

### 19.4 Contoh Alur Demo

```
09:00   — Semua normal (S1)
09:05   — ESP32-03 traffic meningkat
09:05:03 — Anomaly detected (Rule Engine)
09:06   — Port scan dimulai dari 192.168.10.100 (S3)
09:06:01 — Suricata → ALERT (signature match)
09:06:02 — Unified Network Guard → HIGH ALERT
09:06:02 — Dashboard → alert real-time
```

---

## 20. Metrik Evaluasi

### 20.1 Confusion Matrix

| | Predicted Positive | Predicted Negative |
|---|---|---|
| **Actual Positive** | TP (True Positive) | FN (False Negative) |
| **Actual Negative** | FP (False Positive) | TN (True Negative) |

### 20.2 Metrik Kuantitatif

| Metrik | Formula | Keterangan |
|---|---|---|
| **Accuracy** | (TP + TN) / (TP + TN + FP + FN) | Ketepatan keseluruhan |
| **Precision** | TP / (TP + FP) | Ketepatan prediksi positif |
| **Recall** | TP / (TP + FN) | Sensitivitas deteksi |
| **F1-Score** | 2 × Precision × Recall / (Precision + Recall) | Harmonic mean |
| **False Positive Rate** | FP / (FP + TN) | Tingkat alarm palsu |
| **Detection Latency** | t_alert - t_attack | Waktu respons deteksi |

### 20.3 Contoh Format Hasil (Angka Ilustrasi)

| Metode | Accuracy | Precision | Recall | F1 |
|---|:---:|:---:|:---:|:---:|
| Rule-Based | 92% | 89% | 91% | 90% |
| Isolation Forest | 96% | 95% | 94% | 94.5% |
| Hybrid (UNG) | 98% | 97% | 96% | 96.5% |

> **Catatan:** Angka di atas hanya contoh format. Hasil aktual harus berasal dari eksperimen.

---

## 21. Panduan Menjalankan Sistem

### 21.1 Prasyarat

1. Ubuntu Linux 22.04/24.04/26.04 LTS
2. Python 3.10+
3. Docker & Docker Compose
4. Node.js 18+ (untuk dashboard)

### 21.2 Langkah Instalasi

```bash
# 1. Setup sistem (menginstal semua dependensi OS)
sudo bash setup_edge.sh

# 2. Jalankan infrastruktur (PostgreSQL, Mosquitto, Grafana)
cd unified-network-guard
docker-compose up -d

# 3. Setup Python virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Setup dashboard
cd dashboard
npm install
```

### 21.3 Menjalankan Semua Komponen

```bash
# Terminal 1: API Server
cd unified-network-guard
source venv/bin/activate
uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Collector (membutuhkan sudo untuk Scapy sniffing)
cd unified-network-guard
sudo ./venv/bin/python -m collector.main

# Terminal 3: Detection Engine (rule engine + Suricata eve parser)
cd unified-network-guard
source venv/bin/activate
python -m detection.main

# Terminal 4: ML Predictor (real-time anomaly detection)
cd unified-network-guard
source venv/bin/activate
python -m ml.main predict

# Terminal 5: Dashboard
cd unified-network-guard/dashboard
npm run dev
```

### 21.4 Akses Dashboard

- **Custom Dashboard:** http://localhost:3001
- **Grafana:** http://localhost:3002 (admin/admin)
- **API Docs (Swagger):** http://localhost:8000/docs
- **API Docs (ReDoc):** http://localhost:8000/redoc

### 21.5 Environment Variables (.env)

```env
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=network_guard
DB_USER=guard_user
DB_PASSWORD=guard_secret

# Network
CAPTURE_INTERFACE=enp9s0
IOT_SUBNET=192.168.20.0/24
GATEWAY_IP=192.168.20.1

# MQTT
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=1883

# API
API_KEY=dummy_key
CORS_ORIGINS=http://localhost:3001,http://localhost:3002,http://192.168.20.101:3001

# Suricata
SURICATA_EVE_PATH=/var/log/suricata/eve.json

# ML
FEATURE_WINDOW_SECONDS=10
IF_N_ESTIMATORS=200
ANOMALY_CONTAMINATION=0.05

# Logging
LOG_LEVEL=INFO
```

---

## 22. Kesimpulan

Platform Unified Network Guard berhasil dibangun sebagai prototype laboratorium yang menggabungkan:

- **3–5 ESP32** sebagai node IoT testbed
- **TP-Link TL-WR820N** sebagai router jaringan IoT
- **TP-Link TL-WR840N** sebagai router jaringan pengujian
- **PC Ryzen 5 5500GT** sebagai Edge Computing Security Node
- **Eclipse Mosquitto** sebagai MQTT broker
- **Scapy** untuk packet capture real-time
- **Suricata IDS** untuk deteksi serangan berbasis signature
- **Rule Engine** untuk deteksi berbasis threshold
- **Isolation Forest** untuk deteksi anomali berbasis Machine Learning
- **Random Forest** (opsional) untuk klasifikasi jenis serangan
- **PostgreSQL** untuk penyimpanan data
- **FastAPI** sebagai backend REST API + WebSocket
- **Next.js** sebagai dashboard monitoring interaktif

Pendekatan **Hybrid Detection** (Suricata + Rule Engine + Isolation Forest) memberikan cakupan deteksi yang komprehensif: serangan yang sudah dikenal ditangani oleh signature, pola anomali baru dideteksi oleh ML, dan threshold sederhana memberikan baseline cepat.

Seluruh pemrosesan dilakukan di edge (local), membuktikan bahwa Edge Computing mampu menjadi solusi keamanan jaringan IoT yang efisien tanpa bergantung pada cloud.

---

> **Catatan Etika & Keamanan:** Seluruh simulasi scanning, flooding, brute force, atau pengujian serangan dalam proyek ini dilakukan hanya pada perangkat dan jaringan lab yang dimiliki/berwenang diuji. Pengujian terhadap jaringan publik atau perangkat pihak lain sangat dilarang.

---

*Dokumen ini di-generate dari analisis menyeluruh terhadap seluruh source code, konfigurasi, dan dokumentasi proyek Unified Network Guard.*
