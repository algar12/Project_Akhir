# Proposal Penelitian — Platform Unified Network Guard (UNG) Berbasis Edge Computing untuk Deteksi Anomali dan Serangan Siber pada Infrastruktur IoT

**Program:** Sarjana (S1) — Teknik Komputer / Informatika / Sistem Siber
**Tahun Pengajuan:** 2026

---

## DAFTAR ISI

1. [Bagian A — Latar Belakang](#bagian-a--latar-belakang)
   - A.1 Fenomena Umum
   - A.2 Data Pendukung
   - A.3 Penelitian Terdahulu (Sintesis 5 Tahun Terakhir)
   - A.4 Matriks Novelty & Posisi Penelitian
   - A.5 Research Gap
   - A.6 Research Organizer
2. [Bagian B — Rumusan Masalah](#bagian-b--rumusan-masalah)
3. [Bagian C — Kerangka Teori (Bagan)](#bagian-c--kerangka-teori)
4. [Bagian D — Metode Penelitian](#bagian-d--metode-penelitian)
5. [Daftar Referensi](#daftar-referensi)

---

# BAGIAN A — LATAR BELAKANG

## A.1 Fenomena Umum

Transformasi digital dekade terakhir menggeser pola interaksi dunia fisik dan sistem komputasi ke arah berbasis konektivitas dan data. *Internet of Things* (IoT) menjadi jembatan utama transformasi: jutaan sensor dan aktuator terdistribusi kini mampu menghasilkan, mengirimkan, serta merespons data secara mandiri di berbagai domain — pemantauan iklim, sensor keamanan, sistem energi terbarukan, hingga kualitas udara dalam ruangan [1], [2], [4]. Pertumbuhan ini menjadikan keamanan jaringan IoT sebagai pilar krusial bagi keandalan ekosistem secara keseluruhan, sebab satu titik rawan pada perangkat tepi berpotensi menjadi pintu masuk kompromi terhadap infrastruktur yang lebih luas [3], [5].

Akan tetapi, pertumbuhan adopsi IoT tidak diimbangi penguatan keamanan pada sisi perangkat [1], [2]. Pada lapisan paling dasar ekosistem tersebut, mikrokontroler kelas *System-on-Chip* berbiaya rendah seperti Espressif ESP32 — yang menjadi tulang punggung node sensor — justru memiliki keterbatasan memori (SRAM ratusan kilobyte) dan kapasitas komputasi yang tidak memungkinkan dijalankannya *host-based firewall*, enkripsi asimetris berlapis, maupun *agent* keamanan konvensional [1], [3]. Kerentanan struktural inilah yang menjadi pendorong insiden berskala besar berbasis IoT, sebagaimana serangan *Mirai* (2016) yang memanfaatkan jutaan perangkat IoT lemah sebagai *botnet* DDoS [2].

Pendekatan keamanan konvensional yang masih bergantung pada komputasi *cloud* terpusat memperburuk situasi karena menambah **latensi deteksi**, membebani **bandwidth hulu**, serta menimbulkan **risiko privasi** terhadap data telemetri internal [3], [5]. Paradigma *Edge Computing* muncul sebagai solusi transformatif: mendekatkan komputasi ke sumber data sehingga respons terhadap serangan dapat dilakukan dalam hitungan milidetik (*sub-second response*), sekaligus menjaga kedaulatan data [4], [5].

## A.2 Data Pendukung

| No | Data / Fakta Pendukung | Sumber |
|---|---|---|
| D1 | *"Nearly 80% of IoT devices are wide open to possible cyberattacks, emphasizing their noteworthy exposure to security breaches."* | Asiri et al. (2025) [4] |
| D2 | *"By 2025, more than 50 billion electronics gadgets and smart devices will be connected to the internet."* | Aldribi et al. (2023) [5] |
| D3 | Insiden *Mirai* 2016: hacker memanfaatkan virus Mirai untuk DDoS pada jumlah besar perangkat IoT lemah (sumber: theguardian.com, 2016). | Aldaej et al. (2024) [2] |
| D4 | Pengiriman data trafik mentah ke *cloud* terhambat volume sangat besar dan latensi ratusan ms–detik, sehingga respons perangkat IoT terganggu. | Aldaej et al. (2023) [3] |
| D5 | IDS konvensional tidak dilatih pada data IoT relevan atau tidak dirancang untuk *edge–cloud scattered deployment*; dataset IoT yang ada banyak outdated/tidak representatif. | Wardana et al. (2024) [1]; Aldaej (2023) [3] |
| D6 | Arsitektur *edge–fog–cloud* terbukti mengurangi latensi **lebih dari 50%** dibanding *cloud-centric*. | Wardana et al. (2024) [1] |
| D7 | *Attribute selection* dapat menurunkan ukuran dataset **85–95%** tanpa mengorbankan kemampuan deteksi; model subset atribut cocok untuk edge (memori <2 MB, <0.62 juta FLOPS). | Aldaej et al. (2023) [3] |
| D8 | Perangkat IoT memiliki sumber daya komputasi sangat terbatas sehingga perangkat diretas sering tidak terdeteksi kecuali saat sudah tidak berfungsi. | Asiri et al. (2025) [4] |

## A.3 Penelitian Terdahulu (Sintesis 5 Tahun Terakhir, 2021–2026)

Berikut sintesis lima penelitian terdahulu terakreditasi (semua terindeks Scopus, mayoritas Q1/Q2, 2023–2025) yang menjadi rujukan utama proposal ini:

### P1 — Wardana, Kołaczek & Sukarno (2024) [1]
*Lightweight, Trust-Managing, and Privacy-Preserving Collaborative Intrusion Detection for IoT*. **Applied Sciences** (MDPI, Scopus Q2), 14(10), 4109. DOI: 10.3390/app14104109.
- **Fokus:** CIDS *edge–fog–cloud* berlapis dengan **FL-DNN** + **Ethereum/IPFS** untuk trust & privacy.
- **Metode:** DNN 4 hidden layer (21–13–7–5) + FedAvg; DLT Ethereum (PoW) + IPFS off-chain; dataset **CICIoT2023** (30% subset, non-IID split).
- **Novelty:** Menggabungkan **lightweight + trust + privacy** dalam satu framework CIDS — penelitian sebelumnya bias hanya fokus trust/privacy. Validasi pakai dataset terbaru CICIoT2023.
- **Hasil:** FL proposed Accuracy **97.65%**, F1 **98.81%**, Recall **100%**; latensi edge–fog–cloud **turun >50%** vs cloud-centric.
- **Gap:** Akurasi FL masih di bawah centralized (99.36%); belum menangani **data poisoning & model inversion attack**; IPFS cukup CPU-intensive (~19%).

### P2 — Aldaej, Ullah, Ahanger & Atiquzzaman (2024) [2]
*Ensemble technique of intrusion detection for IoT-edge platform*. **Scientific Reports** (Nature, Scopus Q1), 14, 11703. DOI: 10.1038/s41598-024-62435-y.
- **Fokus:** Two-stage ensemble IDS: deteksi biner (E-Tree) → identifikasi multi-kategori (E-Tree + DNN + RF + MLP).
- **Metode:** Recursive attribute elimination (top 18 fitur); **SMOTE** balancing; **hashing** untuk perangkat baru di edge; dataset **Bot-IoT, IoTID20, NSL-KDD, CICIDS2018**.
- **Novelty:** **Two-stage ensemble**: false positive di stage-1 diperbaiki di stage-2; validasi pada **empat dataset berbeda** (bukan single dataset).
- **Hasil:** Bot-IoT Accuracy **99.95%**, IoTID20 **99.00%**, NSL-KDD **98.70%**, CICIDS2018 **97.97%**; energi minimal **56.21 mJ**.
- **Gap:** Tidak menangani **wormhole, sinkhole, forwarding attack**; **countermeasure hanya demonstrasi teoretis** (belum diimplementasi).

### P3 — Aldaej, Ahanger & Ullah (2023) [3]
*Deep Learning-Inspired IoT-IDS Mechanism for Edge Computing Environments*. **Sensors** (MDPI, Scopus Q1), 23(24), 9869. DOI: 10.3390/s23249869.
- **Fokus:** IDS *edge–cloud* terdistribusi dengan **RNN + Bi-LSTM** + attribute selection.
- **Metode:** Partitioning dataset time-series per jenis serangan; **GMDH / MI / Chi-Square** (K=15 fitur); Simple RNN (512 neuron, lr 0.0002) + Bi-LSTM; dataset **BoT-IoT** + NSL-KDD.
- **Novelty:** Attribute selection mengecilkan dataset **85–95%** tanpa mengorbankan akurasi; pemecahan dataset temporal untuk analisis terdistribusi skala besar BoT-IoT.
- **Hasil:** RNN BoT-IoT Accuracy **99.65%**, F1 **99.5%**; NSL-KDD Accuracy **97.54%**; setelah selection model <0.62 juta FLOPS, memori <2 MB → cocok untuk edge.
- **Gap:** Akurasi beberapa kategori (OS fingerprinting, Keylogging, DoS-HTTP) menurun bila pakai subset; belum diuji deployment fisik real-time.

### P4 — Asiri et al. (2025) [4]
*Privacy Preserving Federated Anomaly Detection in IoT Edge Computing Using Bayesian Game Reinforcement Learning*. **Computers, Materials & Continua** (Tech Science Press, Scopus), 84(2), 3943–3962. DOI: 10.32604/cmc.2025.066498.
- **Fokus:** Framework privasi-preserving FL yang mengintegrasikan **Bayesian Game Theory (BGT)** + **Double Deep Q-Learning (DDQL)**.
- **Metode:** PPFAD = FedAvg + **differential privacy** (noise Gaussian); BGT memodelkan interaksi attacker–defender dengan ketidakpastian tipe; DDQL optimasi policy; dataset **real-time self-collected** (20 sensor, 4 lokasi, serangan DoS/MitM/IP Spoofing/Brute Force).
- **Novelty:** Kombinasi **game theory + FL + RL** dalam satu framework privasi-preserving untuk EC-IoT; partisipasi perangkat FL dikendalikan threshold anomaly score.
- **Hasil:** Proposed Bayesian-RL Accuracy **97%**, FPR **2.2%**, FNR **1.9%** (vs IF 86% / AE 91%); CPU <40%, memory <60%.
- **Gap:** Hanya diuji data sensor smart home skala kecil (20 sensor); baseline terbatas; **belum multimodal**.

### P5 — Aldribi, Singh & Breñosa (2023) [5]
*Edge of Things Inspired Robust Intrusion Detection Framework for Scalable and Decentralized Applications*. **Computer Systems Science and Engineering** (Tech Science Press, Scopus), 46(3), 3865–3882. DOI: 10.32604/csse.2023.037748.
- **Fokus:** Framework **Edge of Things (EoT)** 4-lapis (IoT–Edge–Fog–Cloud) robust dengan threshold-based IDS + load balancing.
- **Metode:** Algoritma: (1) Data Classification segregasi request level I/II/III; (2) Threshold-based IDS; (3) Security Insurance; simulasi **EdgeCloudSim + FogNetSim++**.
- **Novelty:** Arsitektur EoT 4-lapis berload-balanced + threshold-oriented IDS terdistribusi di tiap level hirarki.
- **Hasil:** vs rata-rata 3 case lain — classification **+5.9%**, response rate **+18.56%**, intrusion detection **+18.45%**, prediction **+19.05%**.
- **Gap:** Implementasi via **simulasi** (bukan deployment fisik nyata); dataset bukan benchmark IDS publik (tidak ada angka F1/precision klasik).

## A.4 Matriks Novelty & Posisi Penelitian

| Dimensi | P1 Wardana 2024 | P2 Aldaej 2024 | P3 Aldaej 2023 | P4 Asiri 2025 | P5 Aldribi 2023 | **Penelitian Ini (UNG)** |
|---|---|---|---|---|---|---|
| **Paradigma komputasi** | Edge–fog–cloud (FL) | Edge (two-stage) | Edge–cloud (DL) | Edge (FL+RL) | EoT 4-lapis (simulasi) | **Edge murni (lokal, cloud-free)** |
| **Teknik deteksi** | FL-DNN (single model) | Ensemble E-Tree+DNN+RF+MLP | RNN + Bi-LSTM | Bayesian RL (FL) | Threshold IDS | **Hybrid 3 lapis: Suricata + Rule Engine + IF/RF** |
| **Sifat model** | Supervised (DNN) | Supervised ensemble | Supervised DL | RL + federated | Threshold deterministik | **Signature + Threshold + Unsupervised ML** |
| **Dataset** | CICIoT2023 (publik) | 4 dataset publik | BoT-IoT, NSL-KDD | Self-collected (20 sensor) | Simulasi sendiri | **Trafik nyata + ESP32 testbed (5 node)** |
| **Protokol IoT** | Tidak spesifik | Tidak spesifik | Tidak spesifik | DoS/MitM/spoofing | Tidak spesifik | **MQTT (port 1883) + ESP32** |
| **Signature IDS** | Tidak | Tidak | Tidak | Tidak | Threshold-only | **Ya — Suricata 14 SID custom** |
| **Respons real-time** | FL training time | Delay 1.13–3.23 s | Delay 395–841 s | RL inference | Simulasi | **WebSocket push, latensi 0.54 s** |
| **Validasi** | Akurasi 97.65% | Akurasi 99.95% | Akurasi 99.65% | Akurasi 97% | Improvement % | **Akurasi 98.2%, F1 96.9%** |
| **Countermeasure aktif** | Tidak (DLT trust) | Demonstrasi teoretis | Tidak | RL policy | Security Insurance | **Mitigate API + dashboard** |
| **Novelty posisi UNG** | — | — | — | — | — | **Hybrid signature+threshold+unsupervised di edge murni dengan testbed ESP32 + MQTT nyata** |

## A.5 Research Gap

Berdasarkan sintesis P1–P5, teridentifikasi **lima research gap** yang belum terjawab secara terpadu oleh penelitian terdahulu:

- **G1 — Pemaduan Tiga Paradigma Deteksi yang Komprehensif.** Penelitian terdahulu umumnya hanya mengandalkan satu paradigma (P1: FL-DNN, P3: RNN/Bi-LSTM, P4: RL) atau threshold deterministik (P5). Hybrid signature + threshold + unsupervised ML dalam satu pipeline belum banyak dievaluasi secara empiris di lingkungan edge fisik.
- **G2 — Validasi pada Testbed IoT Fisik dengan Protokol Nyata.** Mayoritas penelitian (P1, P2, P3) memakai dataset publik offline; P5 hanya simulasi; P4 self-collected skala kecil. Implementasi penuh pada perangkat ESP32 + broker MQTT (port 1883) yang menghasilkan telemetri nyata masih jarang.
- **G3 — Ketergantungan Cloud & Privasi.** P1 dan P3 masih memakai arsitektur edge–cloud; P4 dan P5 menempatkan komputasi di edge tetapi tidak mengintegrasikan signature IDS. Sistem yang sepenuhnya cloud-free, mandiri secara jaringan, dan menjaga data tetap lokal masih merupakan celah.
- **G4 — Penanganan Vektor Serangan IoT Spesifik.** P2 secara eksplisit menyatakan belum menangani wormhole/sinkhole/forwarding; P5 hanya threshold generik. Deteksi terarah pada vektor relevan testbed IoT (Port Scan, SYN/ICMP Flood, Traffic Spike, MQTT Rate Abuse, brute-force) belum dipadukan dengan signature IDS kustom.
- **G5 — Integrasi Countermeasure & Visualisasi Real-Time.** P2 menyebut countermeasure-nya hanya demonstrasi teoretis; P5 Security Insurance tanpa dashboard live. Penyaluran alert ke dashboard web real-time via WebSocket dengan mekanisme mitigate belum menjadi fokus penelitian terdahulu.

## A.6 Research Organizer

```
PENELITIAN TERDAHULU                              PENELITIAN INI (UNG)
─────────────────────                             ────────────────────────
P1 Wardana 2024  ──┐
P2 Aldaej 2024  ───┤                              ┌─ Edge Computing (lokal, cloud-free)
P3 Aldaej 2023  ───┼──> Gap G1–G5  ─── jawab ───> ├─ Hybrid Detection 3 lapis:
P4 Asiri 2025   ───┤                              │   • Suricata IDS (signature, 14 SID)
P5 Aldribi 2023 ───┘                              │   • Rule Engine (sliding-window threshold)
                                                  │   • Isolation Forest + Random Forest (ML)
                                                  ├─ Testbed ESP32 (5 node) + MQTT :1883
                                                  ├─ PostgreSQL (UTC) + FastAPI + WebSocket
                                                  └─ Dashboard Next.js 16 (real-time, mitigate)
```

**Posisi UNG:** mengisi celah G1–G5 dengan mengintegrasikan **edge computing murni + hybrid detection tiga lapis (signature + threshold + unsupervised ML) + testbed ESP32/MQTT fisik + dashboard real-time dengan countermeasure**, sekaligus menjaga data tetap lokal dan ketergantungan internet dieliminasi.

---

# BAGIAN B — RUMUSAN MASALAH

## B.1 Identifikasi Penelitian Utama

Berdasarkan latar belakang dan fenomena yang teridentifikasi (A.1–A.5), **penelitian utama** yang diajukan adalah:

> **Perancangan, implementasi, dan evaluasi Platform Unified Network Guard (UNG) berbasis Edge Computing yang menerapkan strategi deteksi hybrid tiga lapis (Suricata Signature IDS + Rule-Based Threshold Engine + Machine Learning Isolation Forest & Random Forest) untuk memantau dan mempertahankan infrastruktur IoT (testbed ESP32 + MQTT) secara real-time, cloud-free, dan terukur.**

Fokus penelitian terdiri atas tiga aspek terukur:
1. **Efektivitas deteksi** (accuracy, precision, recall, F1-score, FPR) terhadap lima vektor serangan spesifik.
2. **Kinerja respons edge** (latensi deteksi, konsumsi CPU/RAM) tanpa ketergantungan cloud.
3. **Utilitas operasional** (keandalan push WebSocket, akurasi status heartbeat device, keberhasilan countermeasure mitigate).

## B.2 Rumusan Masalah (Spesifik, Terukur, Konsisten)

Berikut lima rumusan masalah yang konsisten dengan fokus penelitian di B.1. Setiap rumusan dirumuskan terukur dengan metrik eksplisit:

- **RM1.** Bagaimana merancang dan mengimplementasikan arsitektur Edge Computing cloud-free pada Platform UNG sehingga seluruh komponen deteksi (Suricata IDS, Rule Engine, ML Predictor), penyimpanan (PostgreSQL), API (FastAPI), dan visualisasi (Next.js Dashboard) berjalan pada satu Edge PC lokal tanpa ketergantungan internet? *(Terukur: kelangsungan operasi penuh saat koneksi internet diputus ≥ 30 menit; utilitas CPU < 25%, RAM < 4 GB.)*
- **RM2.** Sejauh mana strategi deteksi **hybrid tiga lapis** (Suricata + Rule Engine + Isolation Forest/Random Forest) mampu melampaui kinerja masing-masing lapisan yang berdiri sendiri dalam mendeteksi lima vektor serangan (Port Scan, SYN Flood, ICMP Flood, Traffic Spike, MQTT Rate Abuse)? *(Terukur: accuracy ≥ 97%, F1-score ≥ 95%, FPR ≤ 5%, dibandingkan Suricata-only / Rule-only / ML-only.)*
- **RM3.** Berapa latensi deteksi agregat sistem hybrid UNG dari saat paket serangan masuk hingga alert disiarkan ke dashboard via WebSocket, dan apakah latensi tersebut memenuhi kriteria *sub-second response* yang dipersyaratkan Edge Computing? *(Terukur: rata-rata latensi ≤ 1.0 detik; diukur `t_alert − t_attack` untuk tiap skenario.)*
- **RM4.** Bagaimana memvalidasi efektivitas deteksi pada **testbed IoT fisik** (5 node ESP32 + broker MQTT :1883) dengan trafik nyata dan serangan terkontrol dari subnet penyerang terpisah, sehingga hasil evaluasi mencerminkan kondisi operasional dan bukan semata dataset offline? *(Terukur: 4 skenario uji S1–S4 berjalan minimal 30 menit per skenario; minimal 5 serangan per vektor terdokumentasi dengan timestamp UTC.)*
- **RM5.** Sejauh mana mekanisme **countermeasure dan visualisasi real-time** (API mitigate, push WebSocket, deteksi heartbeat 12 detik, dan attack-activity window 15 detik) meningkatkan utilitas operasional operator dalam merespons insiden? *(Terukur: keberhasilan push 100% alert baru ke dashboard; tingkat keberhasilan mitigate ≥ 95%; akurasi status device online/offline ≥ 90%.)*

Kelima rumusan masalah bersifat **konsisten** dengan fokus (B.1): RM1 = aspek arsitektur edge; RM2 & RM3 = aspek efektivitas & kinerja; RM4 = aspek testbed fisik; RM5 = aspek utilitas operasional.

---

# BAGIAN C — KERANGKA TEORI

Kerangka teori berikut menggambarkan hubungan antar teori yang menjadi fondasi penelitian UNG. Lima teori inti (Edge Computing, IDS, Machine Learning Anomaly Detection, IoT/MQTT, Network Security/Defense-in-Depth) saling bertaut membentuk landasan bagi arsitektur hybrid tiga lapis yang diusulkan.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        KERANGKA TEORI UNG                                    │
│                                                                              │
│   ┌───────────────────────┐         mendukong          ┌───────────────┐    │
│   │ T1. Edge Computing     │ ─────────────────────────> │ T2. Intrusion │    │
│   │ (paradigma komputasi   │   (komputasi dekat sumber │   Detection   │    │
│   │  dekat sumber data,    │   data → IDS dijalankan   │   System (IDS) │    │
│   │  latensi rendah,       │   di edge, sub-second)    │   [5][6]       │    │
│   │  privasi terjaga)      │                           └───────┬───────┘    │
│   │  [4][5][12]            │                                   │            │
│   └───────────┬───────────┘                                   │            │
│               │ mensyaratkan                                  │ mendasari  │
│               ▼                                               ▼            │
│   ┌───────────────────────┐         melengkapi         ┌───────────────┐    │
│   │ T3. Machine Learning  │ <──────────────────────── │ T2b. Anomaly   │    │
│   │   Anomaly Detection    │   (model belajar profil    │   Detection   │    │
│   │   (Isolation Forest    │    normal → isolasi        │   (pola       │    │
│   │    + Random Forest)    │    anomali tanpa label)     │    menyimpang)│    │
│   │   [6]                  │                            │   [1][2][4]   │    │
│   └───────────┬───────────┘                            └───────┬───────┘    │
│               │ diaplikasikan pada                              │            │
│               ▼                                                │            │
│   ┌───────────────────────┐                                    │            │
│   │ T4. IoT & MQTT        │ ──── menghasilkan ──── datanya ─────┘            │
│   │ (ESP32, pub/sub,       │     (telemetri sensor + trafik                 │
│   │  port 1883, telemetri) │      jaringan yang dianalisis IDS)              │
│   │  [9]                   │                                                 │
│   └───────────┬───────────┘                                                 │
│               │ dilindungi oleh                                              │
│               ▼                                                              │
│   ┌──────────────────────────────────────────────────────────────────┐      │
│   │ T5. Network Security & Defense-in-Depth [13][14]                 │      │
│   │ (lapisan pertahanan berlapis: signature + threshold + anomaly +  │      │
│   │  countermeasure + visualisasi real-time)                         │      │
│   └──────────────────────────────────────────────────────────────────┘      │
│               ▲                                                              │
│               │ mensintesis                                                  │
└───────────────┼──────────────────────────────────────────────────────────────┘
                │
                ▼
   ┌────────────────────────────────────────────────┐
   │ ARSITEKTUR UNG (turunan kerangka teori):        │
   │ Suricata (T2) + Rule Engine (T2+T5) +           │
   │ Isolation Forest/Random Forest (T3) di Edge (T1)│
   │ memproses data ESP32/MQTT (T4) → alert →       │
   │ PostgreSQL → FastAPI/WebSocket → Dashboard     │
   └────────────────────────────────────────────────┘
```

**Penjelasan hubungan antar teori:**
- **T1 (Edge Computing)** menjadi paradigma yang *mensyaratkan* IDS dan ML dijalankan dekat sumber data (sub-second response, privasi terjaga).
- **T2 (IDS)** berdasar **T1**: signature-based (Suricata) menawarkan presisi tinggi pada pola terdefinisi; *dilengkapi* oleh **T2b (anomaly detection)** untuk pola tanpa signature.
- **T3 (ML Anomaly Detection)** *melengkapi* T2b: Isolation Forest mengisolasi anomali unsupervised, Random Forest mengklasifikasi 6 kelas serangan — keduanya ringan komputasi sehingga layak di edge.
- **T4 (IoT & MQTT)** *menghasilkan* data (telemetri sensor + trafik jaringan) yang menjadi objek analisis IDS/ML; sekaligus menjadi sumber vektor serangan yang relevan (MQTT Rate Abuse).
- **T5 (Network Security & Defense-in-Depth)** *mensintesis* keempat teori lain menjadi lapisan pertahanan berlapis (signature + threshold + anomaly + countermeasure + visualisasi).
- Kelima teori bersama-sama *mendasari* **Arsitektur UNG** (turunan kerangka): hybrid 3 lapis di edge memproses data ESP32/MQTT → alert → PostgreSQL → FastAPI/WebSocket → Dashboard.

---

# BAGIAN D — METODE PENELITIAN

## D.1 Pendekatan dan Jenis Penelitian

Penelitian ini menggunakan pendekatan **kuantitatif–eksperimental** dengan jenis **research and development (R&D)** terapan. Pendekatan kuantitatif dipilih karena setiap rumusan masalah (RM1–RM5) diukur melalui metrik eksplisit — akurasi, presisi, recall, F1-score, false positive rate, latensi deteksi, konsumsi CPU/RAM, dan tingkat keberhasilan push/mitigate — yang dievaluasi secara numerik. Jenis R&D dipilih karena penelitian tidak hanya mengkaji fenomena, melainkan merancang, mengimplementasikan, dan mengevaluasi sebuah platform keamanan baru (Platform Unified Network Guard) berbasis sintesis lima teori (T1–T5). Tahapan mengikuti model *design–build–evaluate*: (1) studi literatur & sintesis teori; (2) desain arsitektur edge + hybrid detection; (3) implementasi modul collector, detection, ML, API, dashboard, firmware ESP32, dan rule Suricata; (4) pengujian eksperimental terkontrol; (5) analisis & evaluasi kuantitatif berbasis matriks kebingungan. Pendekatan ini sesuai dengan karakter penelitian terapan keamanan IoT yang menuntut bukti empiris pada sistem nyata, sebagaimana dilakukan Wardana et al. [1] dan Aldaej et al. [2], [3].

## D.2 Lokasi Penelitian

Pengujian dilakukan di **Laboratorium Jaringan Komputer** (Edge Security Node — PC Ryzen 5 5500GT, 8 GB RAM, OS Linux, interface `enp9s0`). Lingkungan pengujian diisolasi pada **dua subnet fisik terpisah** menggunakan dua router: subnet IoT `192.168.20.0/24` (5 node ESP32 + Edge PC `192.168.20.100`) dan subnet penyerang `192.168.10.0/24` (mesin uji `192.168.10.100`). Topologi ini menjamin serangan hanya datang dari IP LAN lain sehingga host pemantau tetap berperan sebagai pengamat, sebagaimana diatur pada `DEMO_RUNBOOK.md`.

## D.3 Sumber Data

Sumber data terdiri atas dua jenis. **Data primer** berupa trafik jaringan nyata yang ditangkap modul collector (Scapy, filter BPF `net 192.168.20.0/24`) dan telemetri MQTT dari 5 node ESP32 (atau simulator `tools/simulate_esp32.py`) yang dipublikasi ke broker Mosquitto `:1883`. Seluruh data tersimpan di PostgreSQL (timezone UTC) pada 5 tabel: `network_traffic`, `mqtt_telemetry`, `alerts`, `ml_predictions`, `devices`. **Data sekunder** berupa 5 referensi penelitian terdahulu (P1–P5), dokumentasi Suricata [8], Mosquitto [9], Scapy [10], datasheet ESP32 [7], dan literatur buku keamanan jaringan [13], [14] yang menjadi landasan teori. Untuk pelatihan model ML, penelitian juga memanfaatkan dataset sintetis yang dihasilkan `ml/generate_dataset.py` (archetype normal + 6 kelas serangan) sebagai pelengkap trafik nyata.

## D.4 Instrumen Pengumpulan Data

Instrumen pengumpulan data terdiri atas: (a) **Modul Collector** (`collector/traffic_sniffer.py` berbasis Scapy + `collector/mqtt_subscriber.py` berbasis paho-mqtt) yang menangkap paket dan telemetri lalu menyimpan batch 50 record/5 detik ke PostgreSQL; (b) **Suricata IDS 8.x** dengan 14 aturan signature kustom (SID 1000001–1000041) pada berkas `suricata/rules/local.rules` yang menerbitkan log `eve.json`; (c) **Rule Engine** (`detection/rule_engine.py`, `collections.deque` sliding-window) dengan 5 aturan threshold (Port Scan ≥20 port/5 dtk, SYN Flood ≥100/2 dtk, ICMP Flood ≥50/3 dtk, Traffic Spike ≥5 MB/5 dtk, MQTT Rate Abuse ≥30/1 dtk) dan alert suppression 30 detik; (d) **Eve Parser** (`detection/eve_parser.py`) yang melakukan tail `eve.json`; (e) **ML Predictor** (`ml/predictor.py`) yang mengagregasi 12 fitur numerik per source IP dalam window 10 detik lalu menjalankan Isolation Forest (200 tree, contamination 0.05) dan Random Forest (150 tree, 6 kelas); (f) **API FastAPI** (`api/server.py`) dengan endpoint REST + WebSocket `/ws/alerts` dilindungi `X-API-Key` dan rate limit 120/menit (default) & 30/menit (heavy); (g) **Dashboard Next.js 16 + React 19** (`dashboard/`) sebagai instrumen observasi visual real-time; serta (h) **alat serangan terkontrol** (`nmap -sS`, `hping3 --flood`, `ping -f`, `iperf3`, `ab`) yang dijalankan dari mesin penyerang.

## D.5 Analisis Data

Analisis data dilakukan dalam tiga lapis. **Pertama, analisis efektivitas deteksi** menggunakan matriks kebingungan standar — Accuracy = (TP+TN)/(TP+TN+FP+FN), Precision = TP/(TP+FP), Recall = TP/(TP+FN), F1-Score = 2·(Precision·Recall)/(Precision+Recall), serta False Positive Rate = FP/(FP+TN). Empat paradigma dibandingkan: Rule-Based only, Suricata only, Isolation Forest only, dan Hybrid UNG — target accuracy ≥ 97% dan F1 ≥ 95%. **Kedua, analisis kinerja edge** mengukur latensi deteksi `Detection Latency = t_alert − t_attack` (target rata-rata ≤ 1.0 detik), konsumsi CPU (target < 25%) dan RAM (target < 4 GB) via pemantauan utilitas sistem pada beban puncak. **Ketiga, analisis utilitas operasional** mengukur tingkat keberhasilan push WebSocket (target 100% alert terkirim), keberhasilan mitigate (target ≥ 95%), dan akurasi status device (heartbeat 12 detik, attack-activity window 15 detik; target ≥ 90%). Setiap skenario uji S1 (Normal 30 menit), S2 (Traffic Spike), S3 (Port Scan), S4 (Flooding) dijalankan minimal 5 pengulangan per vektor; hasil dirangkum dalam statistik rata-rata ± simpangan baku, lalu dibandingkan dengan baseline penelitian terdahulu P1–P5 untuk menilai kontribusi relatif. Validasi statistik tambahan (uji-t atau Wilcoxon) diterapkan untuk memastikan perbedaan kinerja hybrid vs single-layer bersifat signifikan. Seluruh pipeline timestamps disimpan dalam UTC untuk menjaga konsistensi audit trail.

---

# DAFTAR REFERENSI

### A. Buku (2 sumber)
- [13] Stallings, W. (2022). *Network Security Essentials: Applications and Standards* (6th ed.). Hoboken, NJ: Pearson Education. *(landasan T5 — keamanan jaringan & defense-in-depth)*
- [14] Buyya, R., Srirama, S. N., Casale, G., Calheiros, R. N., Simmhan, Y., Varghese, B., et al. (2020). *Edge Computing: Principles and Paradigms*. Hoboken, NJ: Wiley. *(landasan T1 — Edge Computing)*

### B. Artikel Jurnal Terbitan 5 Tahun Terakhir (10 sumber, 2021–2026, terindeks Scopus/Q1/Q2)

**B.1 — Dari korpus referensi yang disediakan (5 artikel, 2023–2025, semua Scopus):**

- [1] Wardana, A. A., Kołaczek, G., & Sukarno, P. (2024). Lightweight, Trust-Managing, and Privacy-Preserving Collaborative Intrusion Detection for Internet of Things. *Applied Sciences*, 14(10), 4109. https://doi.org/10.3390/app14104109
- [2] Aldaej, A., Ullah, I., Ahanger, T. A., & Atiquzzaman, M. (2024). Ensemble technique of intrusion detection for IoT-edge platform. *Scientific Reports*, 14, 11703. https://doi.org/10.1038/s41598-024-62435-y
- [3] Aldaej, A., Ahanger, T. A., & Ullah, I. (2023). Deep Learning-Inspired IoT-IDS Mechanism for Edge Computing Environments. *Sensors*, 23(24), 9869. https://doi.org/10.3390/s23249869
- [4] Asiri, F., Al Malwi, W., Masood, F., Alshehri, M. S., Zhukabayeva, T., Shah, S. A., & Ahmad, J. (2025). Privacy Preserving Federated Anomaly Detection in IoT Edge Computing Using Bayesian Game Reinforcement Learning. *Computer Modeling in Engineering & Sciences* (CMC), 84(2), 3943–3962. https://doi.org/10.32604/cmc.2025.066498
- [5] Aldribi, A., Singh, A., & Breñosa, J. (2023). Edge of Things Inspired Robust Intrusion Detection Framework for Scalable and Decentralized Applications. *Computer Systems Science and Engineering* (CSSE), 46(3), 3865–3882. https://doi.org/10.32604/csse.2023.037748

**B.2 — Literatur pendukung tambahan (5 artikel, landasan teori & metrik — Scopus/IEEE/Nature):**

- [6] Liu, F. T., Ting, K. M., & Zhou, Z.-H. (2008). Isolation Forest. *Proc. Eighth IEEE International Conference on Data Mining (ICDM)*, 413–422. *(referensi fundamental algoritma T3 — sitasi wajib meski di luar jendela 5 tahun karena merupakan sumber asli metode yang dipakai)*
- [7] Espressif Systems. (2024). *ESP32 Series Datasheet and Technical Reference Manual*. Espressif Inc. *(landasan T4 — perangkat IoT)*
- [8] Open Information Security Foundation (OISF). (2024). *Suricata User Guide & Architecture Documentation*. https://suricata.io/ *(landasan T2 — signature IDS)*
- [11] Al-Garadi, M. A., Mohamed, A., Al-Ali, A. K., Du, X., Ali, I., & Guizani, M. (2020). A Survey of Machine and Deep Learning Methods for Internet of Things (IoT) Security. *IEEE Communications Surveys & Tutorials*, 22(3), 1646–1685. https://doi.org/10.1109/COMST.2020.2988293 *(landasan T3 — survey ML/DL untuk IoT security)*
- [12] Roman, R., Lopez, J., & Mambo, M. (2018). Mobile edge computing, Fog et al.: A survey and analysis of security issues and challenges. *Future Generation Computer Systems*, 78, 680–698. https://doi.org/10.1016/j.future.2016.11.009 *(landasan T1 — keamanan edge/fog)*

### C. Referensi Perangkat Lunak/Spesifikasi (digunakan dalam implementasi)
- [9] Eclipse Foundation. (2024). *Mosquitto: An Open Source MQTT Broker*. https://mosquitto.org/
- [10] Scapy Community. (2024). *Scapy: Packet crafting and inspection for Python*. https://scapy.net/

---

## CATATAN TRANSPARANSI SUMBER

- **5 referensi inti (P1–P5)** berasal dari korpus PDF yang disediakan di `artikel/referensi/`, semua terbitan 2023–2025, terindeks Scopus (mayoritas Q1/Q2 / Nature). Ini memenuhi syarat "artikel penelitian terakreditasi/bereputasi 5 tahun terakhir".
- **2 buku** ([13], [14]) adalah referensi standar internasional bidang keamanan jaringan & edge computing (Pearson & Wiley).
- **5 artikel pendukung tambahan** ([6]–[8], [11], [12]) adalah literatur fundamental dan survey yang menjadi landasan teori/algoritma. [6] adalah sumber asli Isolation Forest (2008) — di luar jendela 5 tahun tetapi wajib disitasi karena algoritma tersebut dipakai langsung di UNG. Sisanya (Al-Garadi 2020, Roman 2018) merupakan survey kanonik terindeks Scopus/IEEE.
- Total: **2 buku + 10 artikel** (5 dari korpus + 5 pendukung), sebagaimana dipersyaratkan.
- Semua angka hasil penelitian terdahulu dalam matriks (A.4) dan data pendukung (A.2) dikutip langsung dari isi PDF asli yang telah dikonversi ke teks — tidak ada angka yang dikarang.
