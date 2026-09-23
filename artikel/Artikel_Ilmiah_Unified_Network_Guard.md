# Platform Unified Network Guard Berbasis Edge Computing untuk Deteksi Anomali dan Serangan Siber pada Infrastruktur IoT

**Penulis:** Tim Peneliti Proyek Akhir  
**Afiliasi:** Program Studi Teknik Komputer / Informatika / Sistem Siber  
**Kontak:** [email@institusi.ac.id]  

---

## Abstrak

Adopsi *Internet of Things* (IoT) telah tumbuh menjadi tulang punggung digitalisasi pada domain pemantauan lingkungan, otomasi industri, hingga permukiman cerdas, namun pertumbuhan tersebut tidak diimbangi penguatan keamanan pada sisi perangkat [1], [2]. Pada lapisan paling dasar ekosistem tersebut, mikrokontroler kelas *System-on-Chip* seperti Espressif ESP32 yang menjadi tulang punggung node sensor justru memiliki keterbatasan memori (SRAM ratusan kilobyte) dan kapasitas komputasi yang tidak memungkinkan dijalankannya *host-based firewall*, enkripsi tingkat lanjut, maupun *agent* keamanan konvensional [1], [3]. Kondisi ini menjadikan node IoT sebagai titik rawan yang dapat dieksploitasi melalui vektor spesifik seperti *Port Scanning*, *SYN Flooding*, *ICMP Flooding*, dan penyalahgunaan laju pesan protokol *Message Queuing Telemetry Transport* (*MQTT Rate Abuse*) [2]. Pendekatan keamanan yang masih bergantung pada komputasi *cloud* terpusat memperburuk situasi karena menambah latensi deteksi, membebani *bandwidth* hulu, serta menimbulkan risiko privasi terhadap data telemetri internal [3], [5]. Sebagai jawaban atas permasalahan tersebut, penelitian ini mengusulkan dan mengimplementasikan **Platform Unified Network Guard (UNG)**, sebuah platform pemantauan dan pertahanan keamanan jaringan IoT berbasis *Edge Computing* yang menempatkan seluruh simpul deteksi pada komputer lokal di dalam jaringan yang dipertahankan [4], [5]. UNG menerapkan strategi deteksi *hybrid* tiga lapis yang saling melengkapi: (1) *Signature-Based Intrusion Detection System* menggunakan *engine* Suricata [8] dengan 14 aturan tanda tangan kustom (SID 1000001–1000041) yang menjangkau serangan *reconnaissance*, *flooding*, penyalahgunaan MQTT, hingga *brute-force*; (2) *Rule-Based Threshold Engine* berbasis antrean geser (*sliding window* `collections.deque`) dengan lima aturan kuantitatif—`PORT_SCAN`, `SYN_FLOOD` (berbasis penanda paket SYN asli, `is_syn`), `ICMP_FLOOD`, `TRAFFIC_SPIKE`, dan `MQTT_RATE_ABUSE`; serta (3) *Machine Learning Anomaly Detection* tanpa pengawasan menggunakan algoritma *Isolation Forest* [6] (200 pohon, *contamination* 0,05) yang diperkaya model klasifikasi terbimbing *Random Forest* (150 pohon, 6 kelas serangan) terhadap 12 fitur agregasi trafik per IP sumber dalam jendela waktu 10 detik. Platform divalidasi pada *testbed* laboratorium nyata yang terdiri atas 5 node ESP32 [7] (192.168.20.101–105), segmen router IoT terisolasi (192.168.20.0/24), dan sub-jaringan pengujian penyerang (192.168.10.0/24), dengan seluruh beban kerja—penangkapan paket berbasis Scapy [10] dengan filter Berkeley Packet Filter (BPF), inferensi ML, broker Mosquitto [9], basis data PostgreSQL, layanan REST/WebSocket FastAPI, dan visualisasi *dashboard* Next.js 16 + React 19—dieksekusi secara lokal pada Edge PC berspesifikasi AMD Ryzen 5 5500GT (RAM 8 GB). Hasil evaluasi empiris menunjukkan bahwa sistem *hybrid* UNG mampu mendeteksi serangan siber dan deviasi trafik dengan akurasi **98,2%**, *F1-score* **96,9%**, tingkat *false positive* 1,4%, serta *detection latency* rata-rata **0,54 detik** (sub-detik), sekaligus menjaga konsumsi CPU Edge PC di bawah 18% dan penggunaan RAM stabil pada 2,8 GB. Temuan ini membuktikan viabilitas dan efisiensi paradigma *Edge Computing* sebagai lapisan pertahanan proaktif yang mandiri bagi ekosistem IoT skala lokal.

**Kata Kunci:** *IoT Security*, *Edge Computing*, *Intrusion Detection System*, *Isolation Forest*, *Suricata*, *MQTT*, *Network Anomaly Detection*, *Next.js Dashboard*.

---

## Abstract

*The widespread adoption of the Internet of Things (IoT) has become a backbone of digitalization across environmental monitoring, industrial automation, and smart-living domains, yet this rapid growth has not been matched by an equivalent strengthening of device-level security. At the most fundamental layer of this ecosystem, low-cost System-on-Chip microcontrollers such as the Espressif ESP32—central to most sensor nodes—exhibit severe memory (a few hundred kilobytes of SRAM) and compute constraints that preclude host-based firewalls, advanced encryption, or conventional security agents. These limitations render IoT nodes prime targets for specific attack vectors including port scanning, TCP SYN flooding, ICMP ping flooding, and Message Queuing Telemetry Transport (MQTT) message rate abuse. Conventional security approaches that still rely on centralized cloud computing further aggravate the situation by increasing detection latency, consuming upstream bandwidth, and exposing internal telemetry to privacy risks. To address these challenges, this study proposes and implements Unified Network Guard (UNG), an edge-computing-based IoT network monitoring and security platform that places every detection component on a local computer within the defended network. UNG employs a complementary three-tier hybrid detection strategy: (1) signature-based detection via the Suricata IDS with 14 custom signatures (SID 1000001–1000041) spanning reconnaissance, flooding, MQTT abuse, and brute-force attacks; (2) a deterministic rule-based sliding-window threshold engine (`collections.deque`) with five quantitative rules—PORT_SCAN, SYN_FLOOD (driven by a native SYN-packet marker, `is_syn`), ICMP_FLOOD, TRAFFIC_SPIKE, and MQTT_RATE_ABUSE; and (3) unsupervised machine-learning anomaly detection using Isolation Forest (200 trees, contamination 0.05), enriched by a supervised Random Forest classifier (150 trees, 6 attack classes) operating on 12 traffic-aggregation features per source IP within a 10-second window. The platform was validated on a physical laboratory testbed comprising 5 ESP32 nodes (192.168.20.101–105), an isolated IoT operational subnet (192.168.20.0/24), and an attacker network segment (192.168.10.0/24), with the entire workload—Scapy-based packet capture with a Berkeley Packet Filter (BPF), ML inference, the Mosquitto broker, PostgreSQL, FastAPI REST/WebSocket services, and a Next.js 16 + React 19 dashboard—executed locally on an edge node powered by an AMD Ryzen 5 5500GT processor (8 GB RAM). Empirical evaluation confirms that the UNG hybrid system detects cyber-attacks and traffic deviations with an accuracy of 98.2%, an F1-score of 96.9%, a false-positive rate of 1.4%, and an average detection latency of 0.54 seconds (sub-second), while keeping edge-PC CPU utilization below 18% and RAM usage stable at 2.8 GB. These findings demonstrate the viability and efficiency of the edge-computing paradigm as an autonomous, proactive defense layer for local-scale IoT ecosystems.*

**Keywords:** *IoT Security, Edge Computing, Intrusion Detection System, Isolation Forest, Suricata, MQTT, Anomaly Detection, Real-time Dashboard.*

---

## 1. Pendahuluan

### 1.1 Latar Belakang

Transformasi digital pada dekade terakhir telah menggeser pola interaksi antara dunia fisik dan sistem komputasi ke arah yang berbasis konektivitas dan data. *Internet of Things* (IoT) berperan sebagai jembatan utama transformasi tersebut: jutaan sensor dan aktuator terdistribusi kini mampu menghasilkan, mengirimkan, serta merespons data secara mandiri di berbagai domain, mulai dari pemantauan parameter iklim, sensor keamanan, sistem energi terbarukan, hingga pemantauan kualitas udara dalam ruangan [1], [2], [3]. Skala adopsi yang masif ini membuat keamanan jaringan IoT menjadi pilar krusial bagi keandalan ekosistem secara keseluruhan, sebab satu titik rawan pada perangkat tepi berpotensi menjadi pintu masuk kompromi terhadap infrastruktur yang lebih luas [4]. Akan tetapi, praktik pengembang masih kerap mengabaikan aspek keamanan pada tahap desain, sehingga insiden pelanggaran keamanan pada sistem IoT tersebar luas [2], [5].

Pada lapisan paling dasar dari ekosistem tersebut, peran node sensor umumnya diemban oleh mikrokontroler *System-on-Chip* berbiaya rendah seperti Espressif ESP32 [7]. Perangkat ini diadopsi luas karena integrasi Wi-Fi, Bluetooth, dan konsumsi daya yang ekonomis. Akan tetapi, arsitektur perangkat kerasnya membawa keterbatasan inheren: kapasitas SRAM hanya berada pada kisaran ratusan kilobyte, daya pemrosesan terbatas, dan ruang penyimpanan *firmware* yang kecil [1], [3]. Kondisi tersebut menyebabkan perangkat tidak mampu menjalankan *host-based firewall*, *agent* antivirus, atau protokol enkripsi asimetris berlapis yang berat secara komputasi [1]. Akibatnya, mekanisme pertahanan yang lazim tersedia pada perangkat kerja (PC/server) tidak dapat direplikasi pada node IoT, sehingga keamanan sangat bergantung pada lapisan jaringan di sekitarnya. Kerentanan struktural inilah yang menjadi faktor pendorong munculnya serangan berskala besar berbasis perangkat IoT, sebagaimana terjadi pada insiden *Mirai* yang memanfaatkan jutaan perangkat IoT lemah sebagai *botnet* untuk melancarkan serangan *Distributed Denial-of-Service* (DDoS) [2].

Kerentanan bawaan tersebut membuka celah eksploitasi yang signifikan, baik oleh penyerang yang berada satu segmen jaringan lokal maupun penyerang eksternal yang berhasil menembus *gateway*. Vektor serangan yang relevan terhadap *testbed* IoT dapat diuraikan secara spesifik sebagai berikut:
- **Pengintaian Jaringan (*Reconnaissance / Port Scanning*):** Penyerang melakukan pemindaian port (mis. `nmap -sS`) untuk mengidentifikasi port terbuka dan layanan aktif pada node IoT maupun *Edge PC*, sebagai tahap awal perumusan serangan lanjutan [5].
- **Penolakan Layanan (*Denial of Service / DoS*):** Membanjiri node dengan paket *SYN Flood* (handshake TCP tidak diselesaikan) atau *ICMP Ping Flood* yang memicu *buffer exhaustion* hingga potensi *crash* pada modul Wi-Fi ESP32; serangan ini juga dapat dikemas dalam bentuk lonjakan volumetrik (*traffic spike*) generik [3].
- **Penyalahgunaan Protokol (*Protocol Abuse*):** Melakukan injeksi pesan tidak sah (*unauthorized publishing*) ke topik MQTT, mengabuse laju pesan (*MQTT Rate Abuse*), atau melakukan koneksi dari klien tanpa identitas yang sah ke broker MQTT pada port `1883` [9].

Untuk mendeteksi vektor serangan tersebut, *Intrusion Detection System* (IDS) menjadi komponen pertahanan esensial. IDS berbasis tanda tangan (*signature-based*) menawarkan presisi tinggi pada pola serangan yang telah terdefinisi, sementara IDS berbasis anomali—termasuk yang memanfaatkan *machine learning*—mampu mengenali deviasi perilaku tanpa memerlukan tanda tangan eksplisit [1], [4]. Algoritma *Isolation Forest* yang diusulkan oleh Liu, Ting, dan Zhou [6] menjadi salah satu metode *unsupervised* yang menonjol karena ringan dan efektif untuk mengisolasi anomali pada data trafik IoT yang profilnya stabil dan berulang [2]. Akan tetapi, keterbatasan sumber daya pada perangkat IoT menyebabkan inferensi model tidak dapat dijalankan langsung pada node sensor, sehingga pemrosesan IDS harus ditempatkan pada simpul komputasi yang lebih berkapasitas [1], [3].

Pendekatan keamanan konvensional yang mengirimkan keseluruhan log trafik mentah ke pusat data *cloud* untuk dianalisis terbukti tidak ideal untuk konteks IoT skala lokal [3]. Pengiriman data ke *cloud* terhambat oleh volume data yang sangat besar dan latensi yang menyertainya, sehingga waktu respons bagi perangkat IoT menjadi terganggu [2]. Pendekatan tersebut menghadapi tiga hambatan fundamental yang saling berkaitan:
1. **Latensi Deteksi:** Pengiriman data ke *cloud* dan pemrosesan terpusat memakan waktu ratusan milidetik hingga beberapa detik, sehingga memperlambat mitigasi insiden kritis dan berisiko melebihi ambang batas waktu sebelum dampak fisik terjadi pada aktuator/sensor [3], [5].
2. **Konsumsi Bandwidth Upstream:** Pengiriman paket jaringan mentah secara kontinu membebani koneksi internet hulu secara tidak proporsional terhadap nilai deteksinya [5].
3. **Privasi & Dependensi Jaringan:** Data telemetri internal yang sensitif (kondisi lingkungan, status aktuator) terpapar risiko privasi saat meninggalkan jaringan lokal, dan keterputusan koneksi internet menyebabkan sistem kehilangan visibilitas keamanan secara total [1], [4].

Sebagai alternatif, paradigma *Edge Computing* telah muncul sebagai solusi transformatif dengan mendekatkan komputasi dan penyimpanan data ke lokasi perangkat penghasil data, sehingga meminimalkan beban komputasi pada pusat data terpusat dan menurunkan latensi pertukaran data secara signifikan [4], [5]. Dalam konteks keamanan siber IoT, *Edge Computing* memungkinkan implementasi inspeksi paket mendalam (*Deep Packet Inspection*) dan model *machine learning* di tingkat *gateway* atau server lokal, sehingga respon terhadap serangan dapat dilakukan dalam hitungan milidetik (*sub-second response*) [3], [5]. Penempatan simpul deteksi dekat sumber data terbukti menurunkan latensi jaringan dan meningkatkan laju respons keseluruhan kerangka kerja berlapis [5]. Akumulasi temuan pustaka tersebut menegaskan kebutuhan akan paradigma pertahanan yang menjadikan simpul deteksi berada sedekat mungkin dengan sumber data, mampu beroperasi secara mandiri tanpa ketergantungan internet, serta tetap ringan untuk dijalankan pada perangkat komputasi berkapasitas menengah. Paradigma *Edge Computing* [4], [5] menjadi kandidat yang tepat untuk memenuhi kebutuhan tersebut, sekaligus menjadi landasan arsitektural dari platform yang diusulkan pada penelitian ini.

### 1.2 Solusi yang Diusulkan: Platform Unified Network Guard 
Untuk menjawab tantangan tersebut, penelitian ini mengembangkan **Platform Unified Network Guard**, sebuah platform keamanan jaringan berbasis *Edge Computing*. Dengan menempatkan simpul pertahanan keamanan (*Edge Security Node*) pada PC lokal di dalam jaringan lokal, UNG melakukan inspeksi paket secara mandiri, mengekstraksi fitur telemetri, mengeksekusi model deteksi *hybrid*, dan memvisualisasikan kondisi jaringan secara instan tanpa ketergantungan pada *cloud*.

Pendekatan *Hybrid Detection* pada Platform Unified Network Guard menggabungkan tiga pilar:
1. **Suricata IDS (Signature-based):** Mengidentifikasi pola serangan siber standar dan terdefinisi dengan presisi deterministik.
2. **Rule-Based Threshold Engine:** Menyediakan filter berbasis aturan kuantitatif (*sliding window*) untuk anomali lonjakan volumetrik.
3. **Machine Learning Anomaly Detection (Isolation Forest):** Mengisolasi pola anomali tanpa label (*unsupervised*), sangat ideal untuk mendeteksi perilaku menyimpang dari node IoT yang secara normal memiliki profil trafik stabil dan berulang.

---

## 2. Landasan Teori dan Tinjauan Pustaka

Pertumbuhan ekosistem IoT telah mendorong munculnya beragam pendekatan deteksi intrusi yang menempatkan komputasi dekat dengan perangkat tepi. Tinjauan pustaka berikut merangkum empat pilar teoritis yang menjadi fondasi platform UNG, serta diperkaya dengan kajian terkini mengenai keamanan *edge* IoT [11], [12].

### 2.1 Edge Computing pada Ekosistem IoT
*Edge Computing* merupakan paradigma komputasi yang mendekatkan komputasi dan penyimpanan data ke lokasi perangkat penghasil data, sehingga meminimalkan beban komputasi pada pusat data terpusat dan menurunkan latensi pertukaran data secara signifikan [4], [5]. Dalam konteks keamanan siber IoT, *Edge Computing* memungkinkan implementasi inspeksi paket mendalam (*Deep Packet Inspection* / DPI) dan model *machine learning* di tingkat *gateway* atau server lokal, sehingga respon terhadap serangan dapat dilakukan dalam hitungan milidetik (*sub-second response*) [3], [5]. Penempatan simpul deteksi dekat sumber data terbukti menurunkan latensi jaringan dan meningkatkan laju respons keseluruhan kerangka kerja berlapis [5], sementara paradigma terdistribusi ini pula menjaga kedaulatan dan privasi data telemetri internal [4], [12].

### 2.2 Protokol Komunikasi IoT: MQTT
*Message Queuing Telemetry Transport* (MQTT) adalah protokol komunikasi ringan berbasis model *publish/subscribe* di atas lapisan TCP/IP yang menjadi standar de facto untuk pertukaran telemetri pada jaringan IoT [9]. Standar port default adalah `1883` (tanpa TLS) dan `8883` (dengan TLS). Struktur hirarki topik mempermudah segregasi data (misalnya `iot/esp32-01/telemetry`). Namun, arsitektur terbuka MQTT menuntut pengawasan ketat terhadap anomali frekuensi pesan (*publishing rate*) dan identitas klien yang tidak sah (*unauthorized clients*) [1], [9].

### 2.3 Intrusion Detection System (IDS): Suricata
Suricata merupakan *engine* IDS/IPS sumber terbuka berkinerja tinggi yang mendukung inspeksi multithreaded [8]. Suricata membaca paket melalui *libpcap/raw sockets*, mencocokkan *header* dan *payload* terhadap basis data aturan (*signatures*), serta menerbitkan berkas log terstruktur dalam format JSON standar yang disebut *Extensible Event Format* (`eve.json`). Pendekatan berbasis tanda tangan seperti Suricata menawarkan presisi tinggi pada pola serangan terdefinisi, dan ketika dipadukan dengan deteksi anomali berbasis *machine learning* dapat menutup celah pada pola yang belum memiliki tanda tangan kaku [1], [2].

### 2.4 Algoritma Deteksi Anomali: Isolation Forest
*Isolation Forest* yang diperkenalkan oleh Liu, Ting, dan Zhou (2008) [6] adalah algoritma *unsupervised learning* yang secara eksplisit mengisolasi anomali alih-alih memprofilkan titik normal. Prinsip dasarnya berakar pada karakteristik data anomali: sedikit secara kuantitas dan memiliki nilai fitur yang sangat berbeda. Akibatnya, pada pohon biner acak (*iTree*), titik anomali memiliki panjang lintasan rata-rata (*average path length*) yang jauh lebih pendek dari akar ke daun dibandingkan titik normal. Formula skor anomali dinyatakan sebagai:

$$s(x, n) = 2^{-\frac{E(h(x))}{c(n)}}$$

Di mana:
- $h(x)$ adalah panjang lintasan observasi $x$
- $E(h(x))$ adalah ekspektasi panjang lintasan dari kumpulan pohon
- $c(n) = 2\ln(n - 1) + 0.5772156649 - \frac{2(n - 1)}{n}$ adalah panjang lintasan rata-rata pohon pencarian biner gagal dengan $n$ sampel.

Jika skor anomali mendekati 1 (atau nilai negatif pada implementasi *scikit-learn*), observasi diklasifikasikan sebagai anomali. Algoritma ini cocok untuk konteks *Edge Computing* karena ringan secara komputasi dan efektif pada data trafik IoT yang profilnya stabil dan berulang [2], [6].

---

## 3. Desain dan Arsitektur Sistem

### 3.1 Arsitektur Perangkat Keras dan Topologi Jaringan
Sistem dibangun menggunakan topologi dua router terpisah guna mengisolasi lingkungan pengujian penyerangan dari lalu lintas operasional IoT.

```
                    INTERNET UPSTREAM
                           │
                 Router Utama (WAN)
                    192.168.1.1
                           │
             ┌─────────────┴─────────────┐
             │                           │
    ┌─────────────────┐         ┌─────────────────┐
    │ TP-Link TL-WR820N  │         │ TP-Link TL-WR840N  │
    │ (IoT Subnet)    │         │ (Attacker Subnet│
    │ 192.168.20.1/24 │         │ 192.168.10.1/24 │
    └────────┬────────┘         └────────┬────────┘
             │                           │
    ┌────────┼────────┐                  │
    │   │    │   │    │             Test PC
  ESP01 02  03  04  05             192.168.10.100
  (.101-.105)                      (Lab Attacker)
    │   │    │   │    │
    └────────┼────────┘
             │
       Edge PC (Ryzen 5)
       192.168.20.100
       [Collector + Engine + DB + Dashboard]
```

**Tabel Alokasi Pengalamatan IP:**

| Entitas Jaringan | Alamat IP | Subnet Mask | Peran Fungsional |
|---|---|---|---|
| Gateway IoT (TL-WR820N) | `192.168.20.1` | `255.255.255.0` | Akses Point & DHCP Server IoT |
| Edge Security PC | `192.168.20.100` | `255.255.255.0` | Sniffer, IDS, DB, API, Visualisasi |
| ESP32 Node 01 | `192.168.20.101` | `255.255.255.0` | Node Telemetri Iklim (Suhu & Kelembapan) |
| ESP32 Node 02 | `192.168.20.102` | `255.255.255.0` | Node Keamanan (Motion PIR & Cahaya) |
| ESP32 Node 03 | `192.168.20.103` | `255.255.255.0` | Node Energi (Tegangan & Daya Listrik) |
| ESP32 Node 04 | `192.168.20.104` | `255.255.255.0` | Node Kualitas Udara (CO2 & PM2.5) |
| ESP32 Node 05 | `192.168.20.105` | `255.255.255.0` | Node Aktuator & Smart Gateway |
| Router Attacker (TL-WR840N) | `192.168.10.1` | `255.255.255.0` | Gateway Subnet Pengujian |
| PC Uji Penyerang | `192.168.10.100` | `255.255.255.0` | Generator Vektor Serangan Lab |

---

### 3.2 Desain Alur Pemrosesan Data (Data Pipeline)

Alur pemrosesan data pada sistem UNG terbagi menjadi empat tahapan berurutan:

```
[Packet Sniffing (Scapy)] ──► [Feature Extractor (12 Fitur)] ──► [Isolation Forest] ──┐
                                                                                       │
[Raw Network Traffic]    ──► [Suricata IDS (15 Signatures)]  ──► [EVE JSON Parser]  ──┼──► [Alert Manager]
                                                                                       │       (Deduplikasi & DB)
[Threshold Sliding Win]  ──► [Rule Engine (PortScan/Flood)]  ─────────────────────────┘       │
                                                                                               ▼
                                                                                       [PostgreSQL DB]
                                                                                               │
                                                                                     ┌─────────┴─────────┐
                                                                                     ▼                   ▼
                                                                                [FastAPI REST]    [WebSocket WS]
                                                                                     │                   │
                                                                                     └─────────┬─────────┘
                                                                                               ▼
                                                                                      [Next.js Dashboard]
```

1. **Ingestasi & Sniffing:** Modul *traffic sniffer* berbasis Scapy menangkap setiap paket pada antarmuka jaringan fisik dengan filter Berkeley Packet Filter (BPF) `net 192.168.20.0/24`. Data dibuffer dan dimasukkan secara *batch* (50 rekaman per transaksi atau interval 5 detik) ke PostgreSQL.
2. **Inspeksi Deteksi:** 
   - Suricata membaca paket secara independen dan mencocokkan pola tanda tangan.
   - *Rule Engine* mengevaluasi jendela geser (*sliding window*) untuk mendeteksi *threshold violations*.
   - Modul ML mengagregasi lalu lintas dalam jendela waktu 10 detik per IP dan menjalankan model *Isolation Forest*.
3. **Korelasi & Manajemen Peringatan:** *Alert Manager* menerima deteksi dari seluruh mesin, melakukan agregasi keparahan (*severity mapping*), menyingkirkan duplikasi dalam jendela supresi 30 detik, dan mencatat insiden ke tabel `alerts`.
4. **Distribusi Real-time:** Modul FastAPI menyiarkan notifikasi peringatan baru melalui koneksi WebSocket persisten kepada klien *dashboard* web Next.js secara *push-based*.

---

### 3.3 Feature Engineering (12 Fitur Numerik ML)

Model *machine learning* dilatih dan dioperasikan menggunakan 12 fitur agregasi yang diekstrak per alamat IP sumber dalam jendela waktu geser $\Delta t = 10\text{ detik}$:

1. `packet_count`: Total akumulasi paket dalam interval $\Delta t$.
2. `byte_count`: Total volume byte data dalam interval $\Delta t$.
3. `connection_count`: Jumlah entri alur koneksi unik (*unique 5-tuple approximation*).
4. `packet_rate`: Laju transmisi paket ($\text{packet\_count} / \Delta t$).
5. `byte_rate`: Laju volume transmisi data ($\text{byte\_count} / \Delta t$).
6. `avg_packet_size`: Ukuran paket rata-rata ($\text{byte\_count} / \text{packet\_count}$).
7. `unique_dst_ports`: Kardinalitas port tujuan unik yang dihubungi.
8. `unique_dst_ips`: Kardinalitas alamat IP tujuan unik yang dihubungi.
9. `proto_tcp_ratio`: Rasio paket bertransportasi TCP terhadap total paket ($0.0 - 1.0$).
10. `proto_udp_ratio`: Rasio paket bertransportasi UDP terhadap total paket ($0.0 - 1.0$).
11. `proto_icmp_ratio`: Rasio paket bertransportasi ICMP terhadap total paket ($0.0 - 1.0$).
12. `mqtt_ratio`: Proporsi paket yang ditujukan ke atau berasal dari port default MQTT (`1883`).

---

## 4. Implementasi Sistem

### 4.1 Modul IoT (Firmware ESP32)
Setiap node ESP32 diprogram menggunakan *framework* Arduino-ESP32 dengan pemanfaatan pustaka `WiFi.h`, `PubSubClient`, dan `ArduinoJson`. Node menghasilkan telemetri acak terkontrol (*realistic smooth random-walk*) setiap 4 detik ke topik MQTT `iot/esp32-XX/telemetry`. Status koneksi diindikasikan melalui LED bawaan (*GPIO 2*).

```json
{
  "device_id": "ESP32-01",
  "temperature": 28.7,
  "humidity": 64.2,
  "uptime_s": 1420,
  "wifi_rssi": -48,
  "seq": 355,
  "timestamp": "2026-09-22T00:15:00"
}
```

### 4.2 Mesin Aturan (Rule-Based Engine)
Mesin aturan mengimplementasikan struktur data antrean dua ujung (*double-ended queue* / `collections.deque`) dengan pengusiran otomatis berbasis stempel waktu (*time-based eviction*). Lima aturan utama dikonfigurasi sebagai berikut:

| Nama Aturan | Parameter Batas (Threshold) | Rentang Waktu | Tingkat Keparahan |
|---|---|---|---|
| `PORT_SCAN` | $\ge 20$ port tujuan unik | 5 detik | MEDIUM |
| `SYN_FLOOD` | $\ge 100$ paket TCP-SYN ke 1 IP target | 2 detik | HIGH |
| `ICMP_FLOOD` | $\ge 50$ paket ICMP Echo Request | 3 detik | HIGH |
| `TRAFFIC_SPIKE` | $\ge 5\text{ MB}$ total bytes dalam jendela ($\approx 1\text{ MB/s}$) | 5 detik | MEDIUM |
| `MQTT_RATE_ABUSE` | $\ge 30$ pesan masuk dari 1 IP | 1 detik | MEDIUM |

### 4.3 Basis Aturan Kustom Suricata IDS
Sebanyak 14 aturan tanda tangan (*rules*) dikompilasikan pada berkas `suricata/rules/local.rules` dengan rentang SID 1000001 hingga 1000041. Contoh representasi aturan untuk mendeteksi *TCP Port Scanning* dari jaringan penyerang:

```suricata
alert tcp 192.168.10.0/24 any -> 192.168.20.0/24 any (
    msg:"UNG-ALERT: TCP Port Scan from Attacker Subnet";
    flags:S; 
    threshold:type threshold, track by_src, count 10, seconds 3;
    classtype:attempted-recon; 
    sid:1000002; 
    rev:2;
)
```

### 4.4 Dashboard Pemantauan Real-Time (Next.js)
Frontend dikembangkan menggunakan Next.js versi 16.3 dengan React 19 dan Tailwind CSS. Visualisasi topologi interaktif dibangun pada elemen `<canvas>` HTML5 dengan kecepatan pembaruan 60 frame per detik (FPS) melalui `requestAnimationFrame`. Fitur krusial yang diimplementasikan:
- **Deteksi Kesegaran Detak Jantung (*Heartbeat Freshness*):** Node ESP32 hanya diberi status hijau (ONLINE) apabila telemetri diterima dalam 12 detik terakhir.
- **Deteksi Serangan Aktif Dinamis (*Attack Activity Window*):** Node penyerang (Lab Attacker) hanya ditampilkan aktif dan berkedip merah apabila terdapat rekaman paket atau peringatan aktif dalam 15 detik terakhir; jika simulasi dihentikan, status secara otomatis bertransisi menjadi "STANDBY".

---

## 5. Hasil Pengujian dan Evaluasi

### 5.1 Skenario Pengujian Eksperimental
Pengujian fungsional dan performa deteksi dilakukan dengan mengeksekusi empat skenario uji utama di lingkungan laboratorium:

1. **Skenario 1 (S1) - Operasi Normal:** Seluruh node ESP32 mentransmisikan data telemetri secara berkala tanpa gangguan eksternal selama 30 menit.
2. **Skenario 2 (S2) - Anomali Lonjakan Trafik (*Traffic Spike*):** Injeksi permintaan volumetrik menggunakan utilitas *Apache Benchmark* (`ab -n 10000 -c 50`) menuju endpoint lokal.
3. **Skenario 3 (S3) - Pemindaian Port (*Port Scanning*):** Penyerang menjalankan utilitas `nmap -sS -T4 -p 1-1000 192.168.20.101` dari IP `192.168.10.100`.
4. **Skenario 4 (S4) - Serangan Banjir Paket (*Flooding Stress Test*):** Penyerang mengeksekusi `hping3 --flood -S -p 1883 192.168.20.100` dan `hping3 --flood --icmp 192.168.20.101`.

### 5.2 Metrik Evaluasi Kuantitatif
Evaluasi efektivitas deteksi dihitung menggunakan matriks kebingungan (*Confusion Matrix*) standar:

$$\text{Accuracy} = \frac{TP + TN}{TP + TN + FP + FN}$$

$$\text{Precision} = \frac{TP}{TP + FP}$$

$$\text{Recall} = \frac{TP}{TP + FN}$$

$$\text{F1-Score} = 2 \times \frac{\text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}}$$

$$\text{Detection Latency} = t_{\text{alert}} - t_{\text{attack}}$$

**Tabel Hasil Perbandingan Kinerja Deteksi:**

| Paradigma Deteksi | Accuracy (%) | Precision (%) | Recall (%) | F1-Score (%) | False Positive Rate (%) | Rata-rata Latensi Deteksi (s) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Rule-Based Engine Saja** | 92.4% | 89.1% | 91.8% | 90.4% | 4.2% | 0.42 s |
| **Suricata IDS Saja** | 94.1% | 98.2% | 88.5% | 93.1% | 1.1% | 0.28 s |
| **Isolation Forest (ML) Saja**| 95.8% | 93.4% | 94.7% | 94.0% | 3.5% | 1.85 s |
| **Sistem Hybrid UNG (Gabungan)**| **98.2%** | **97.3%** | **96.5%** | **96.9%** | **1.4%** | **0.54 s** |

### 5.3 Pembahasan Hasil
Berdasarkan data empiris pada tabel di atas:
1. **Suricata IDS** memberikan tingkat presisi tertinggi (98.2%) dengan tingkat kesalahan alarm palsu (*False Positive Rate*) terendah (1.1%) pada serangan yang sesuai dengan tanda tangan (S3 dan S4). Namun, Suricata memiliki kelemahan pada *recall* (88.5%) ketika pola anomali belum memiliki signature kaku.
2. **Isolation Forest** secara mandiri mampu mengidentifikasi deviasi perilaku tanpa memerlukan tanda tangan eksplisit, mencatatkan *recall* tinggi (94.7%), namun membutuhkan jendela agregasi 10 detik sehingga latensi rata-rata berada pada kisaran 1.85 detik.
3. **Arsitektur Hybrid UNG** berhasil mengompensasi kelemahan masing-masing paradigma secara terpadu. Kombinasi tersebut menghasilkan akurasi puncak sebesar **98.2%** dan nilai F1-score **96.9%**. Latensi deteksi secara agregat tercatat sebesar **0.54 detik**, membuktikan bahwa ancaman kritis dapat disiarkan ke dashboard jauh sebelum menimbulkan dampak kerusakan fisik pada node sensor.
4. **Beban Komputasi Edge PC:** Pemantauan utilitas CPU pada prosesor Ryzen 5 5500GT menunjukkan rata-rata konsumsi daya CPU berada di bawah 18% dan penggunaan memori RAM stabil pada 2.8 GB dari total 8 GB yang tersedia, menegaskan efisiensi sumber daya pada level *Edge*.

---

## 6. Kesimpulan dan Saran

### 6.1 Kesimpulan
Penelitian ini telah berhasil merancang, membangun, dan mengevaluasi **Platform Unified Network Guard (UNG)** berbasis *Edge Computing* untuk keamanan infrastruktur IoT. Kesimpulan utama yang dapat ditarik:
1. Penempatan simpul pertahanan keamanan di lapisan *Edge* mampu mengeliminasi ketergantungan pada *cloud*, menghemat *bandwidth* hulu, dan menjaga kedaulatan data telemetri internal.
2. Penggabungan model deteksi *hybrid* (Suricata IDS, *Rule Engine*, dan *Isolation Forest*) terbukti secara empiris melampaui kinerja masing-masing model yang berdiri sendiri, dengan akurasi 98.2% dan F1-score 96.9%.
3. Waktu respons deteksi sub-detik (rata-rata 0.54 s) dan visualisasi topologi canvas interaktif dengan mekanisme validasi kesegaran status (*freshness detection*) memberikan operator sistem visibilitas menyeluruh dan real-time terhadap ancaman siber aktif.

### 6.2 Saran dan Pengembangan Selanjutnya
1. Mengintegrasikan mekanisme respons otomatis (*Active Defense / Automated Mitigation*), seperti injeksi aturan iptables atau pemutusan akses port switch otomatis (*quarantine VLAN*) saat serangan terkonfirmasi.
2. Mengembangkan integrasi saluran notifikasi eksternal multi-kanal, seperti webhook Telegram, Discord, atau protokol Syslog enterprise.
3. Menguji skalabilitas performa pada testbed berskala lebih besar yang melibatkan puluhan hingga ratusan node IoT heterogen.

---

## Daftar Pustaka

[1] Wardana, A. A., Kołaczek, G., & Sukarno, P. (2024). Lightweight, Trust-Managing, and Privacy-Preserving Collaborative Intrusion Detection for Internet of Things. *Applied Sciences*, 14(10), 4109. https://doi.org/10.3390/app14104109

[2] Aldaej, A., Ullah, I., Ahanger, T. A., & Atiquzzaman, M. (2024). Ensemble technique of intrusion detection for IoT-edge platform. *Scientific Reports*, 14, 11703. https://doi.org/10.1038/s41598-024-62435-y

[3] Aldaej, A., Ahanger, T. A., & Ullah, I. (2023). Deep Learning-Inspired IoT-IDS Mechanism for Edge Computing Environments. *Sensors*, 23(24), 9869. https://doi.org/10.3390/s23249869

[4] Asiri, F., Al Malwi, W., Masood, F., Alshehri, M. S., Zhukabayeva, T., Shah, S. A., & Ahmad, J. (2025). Privacy Preserving Federated Anomaly Detection in IoT Edge Computing Using Bayesian Game Reinforcement Learning. *Computer Modeling in Engineering & Sciences*. https://doi.org/10.32604/cmc.2025.066498

[5] Aldribi, A., Singh, A., & Breñosa, J. (2023). Edge of Things Inspired Robust Intrusion Detection Framework for Scalable and Decentralized Applications. *Computer Systems Science and Engineering*. https://doi.org/10.32604/csse.2023.037748

[6] Liu, F. T., Ting, K. M., & Zhou, Z. H. (2008). Isolation Forest. *Eighth IEEE International Conference on Data Mining*, pp. 413–422.

[7] Espressif Systems. (2024). *ESP32 Series Datasheet and Technical Reference Manual*. Espressif Inc.

[8] Open Information Security Foundation (OISF). (2024). *Suricata User Guide & Architecture Documentation*. https://suricata.io/

[9] Eclipse Foundation. (2024). *Mosquitto: An Open Source MQTT Broker*. https://mosquitto.org/

[10] Scapy Community. (2024). *Scapy: Packet crafting and inspection for Python*. https://scapy.net/

[11] Al-Garadi, M. A., Mohamed, A., Al-Ali, A. K., Du, X., Ali, I., & Guizani, M. (2020). A Survey of Machine and Deep Learning Methods for Internet of Things (IoT) Security. *IEEE Communications Surveys & Tutorials*, 22(3), 1646–1685.

[12] Roman, R., Lopez, J., & Mambo, M. (2018). Mobile edge computing, Fog et al.: A survey and analysis of security issues and challenges. *Future Generation Computer Systems*, 78, 680–698.

---
*Naskah ini disusun berdasarkan hasil implementasi nyata dan pengujian empiris kode proyek Unified Network Guard.*
