# EVAL_RUNBOOK — Evaluasi Tabel 1 (S1–S6 × 4 Metode)

Runbook untuk menghasilkan **Tabel 1** artikel IKOMTI dengan angka **nyata & jujur** dari sesi pengujian live di jaringan Anda.

> Aturan kejujuran UNG: semua angka berasal dari data yang mengalir live. Tidak ada angka tempel.

---

## 0. Prasyarat

- Jaringan sudah disesuaikan (IoT 192.168.20.0/24, attacker 192.168.10.100) — lihat `.env`.
- Tool attacker terinstall di mesin attacker (192.168.10.100): `nmap`, `hping3`, `mosquitto-clients`.
- Database PostgreSQL jalan, pipeline bisa start.
- venv aktif: `source venv/bin/activate`.

## 1. File yang dipakai

| File | Peran |
|---|---|
| `ml/scenarios_tabel1.json` | Definisi S1–S6 + ground truth + perintah attacker |
| `tools/eval_session.py` | Pencatat timestamp mulai/akhir tiap skenario + truncate DB |
| `ml/evaluator_tabel1.py` | Hitung metrik per-metode × per-skenario → `ml/models/tabel1_eval.json` |
| `artikel/fill_tabel1.py` | Isi Tabel 1 di `bak2.docx` dari hasil evaluator |

## 2. Metodologi (singkat)

- Tiap skenario dipecah jadi **5 slice** (repetisi).
- **S1 (normal)**: 5 slice × 60s. Metode "false alarm" = ada alert di slice. → ukur **FPR & Accuracy**.
- **S2–S6 (serangan)**: 5 slice. Metode "mendeteksi" = ada alert dari metode di slice. → ukur **Recall, Accuracy, Latensi**. Precision=1 & FPR=0 by konstruksi (tidak mungkin FP di window serangan).
- **Hibrida** = union alert semua metode (≥1 alert dari metode mana pun).
- **Baris Rata-rata (Hibrida)** = agregat TP/FP/TN/FN lintas S1–S6 → metrik diskriminatif (Precision, FPR global).
- Metrik: Accuracy, Precision, Recall, F1, FPR (persen), Latensi (ms).

## 3. Alur eksekusi

> **PILIH A: HP sebagai attacker (paling mudah, no-root)** atau **B: mesin terpisah 192.168.10.100**.
>
> ### A. HP Android via Termux (no-root, satu ketuk)
>
> 1. Di HP: install Termux (dari F-Droid), `pkg install -y python git`, clone proyek,
>    jalankan `bash tools/termux_setup.sh` (sekali).
> 2. Hubungkan HP ke WiFi **upstream TL-WR840N (192.168.10.1)** — BUKAN router IoT.
> 3. Di Edge PC: `./ung.sh start --sim` (pastikan platform hidup).
> 4. Di Termux HP, jalankan **eval penuh satu ketuk**:
>    ```bash
>    python tools/attacker.py --auto
>    ```
>    HP akan: panggil API Edge PC `session/start` → tunggu S1 5 menit → jalankan
>    S2-S6 (5 repetisi, begin/end otomatis via API) → `session/finish`.
>    Atau pakai menu interaktif: `python tools/attacker.py`
> 5. Selesai: di Edge PC jalankan `python ml/evaluator_tabel1.py` lalu `artikel/fill_tabel1.py`.
>
> Teknik no-root: UDP/TCP connect via Python socket — tetap menghasilkan paket
> SYN/UDP asli di wire → tertangkap collector Edge PC → memicu rule.
>
> ### B. Mesin attacker terpisah 192.168.10.100 (manual, butuh nmap/hping3/mosquitto)

### Langkah 1 — Start pipeline (5 terminal terpisah)

```bash
# Terminal 1: infra
docker compose up -d                       # PostgreSQL, Mosquitto, Grafana

# Terminal 2: Suricata (IDS signature)
sudo suricata -c suricata/suricata.yaml -i enp9s0

# Terminal 3: Collector (sniffer + MQTT)
python collector/main.py

# Terminal 4: Detection (rule engine + eve parser + alert manager)
python detection/main.py

# Terminal 5: ML predictor (inferensi real-time)
python ml/main.py predict

# Terminal 6: API (opsional, untuk pantau dashboard)
python api/server.py
cd dashboard && npm run dev
```

Pastikan `detection.log` / `predictor.log` menunjukkan pipeline hidup.

### Langkah 2 — Mulai sesi evaluasi

```bash
python tools/eval_session.py start
# → truncate alerts + ml_predictions + migrasi kolom source
```

### Langkah 3 — Jalankan S1 (normal, baseline 5 menit)

```bash
python tools/eval_session.py begin S1
# biarkan traffic normal ESP32 + simulator berjalan ~5 menit (tidak ada serangan)
python tools/eval_session.py end S1
```

### Langkah 4 — Jalankan S2–S6 (serangan, 5 repetisi tiap skenario)

Untuk tiap skenario, jalankan **5 repetisi** perintah attacker (tersebar dalam window ~2 menit), lalu tandai selesai.

```bash
# === S2: Traffic Spike ===
python tools/eval_session.py begin S2
# di mesin attacker 192.168.10.100, ulang 5x (jeda 15-20s):
hping3 --udp --flood -d 1400 192.168.20.100
python tools/eval_session.py end S2

# === S3: Port Scanning ===
python tools/eval_session.py begin S3
# ulang 5x:
nmap -sS -p 1-1000 192.168.20.100
python tools/eval_session.py end S3

# === S4: Traffic Flooding (SYN Flood) ===
python tools/eval_session.py begin S4
# ulang 5x (jeda 15-20s):
hping3 -S --flood -p 1883 192.168.20.100
python tools/eval_session.py end S4

# === S5: Unauthorized MQTT Client ===
python tools/eval_session.py begin S5
# ulang 5x:
mosquitto_pub -h 192.168.20.100 -t iot/esp32-01/telemetry -m '{"fake":true}' -u attacker -d
python tools/eval_session.py end S5

# === S6: MQTT Pattern Anomaly (Rate Abuse) ===
python tools/eval_session.py begin S6
# ulang 5x:
for i in $(seq 1 200); do mosquitto_pub -h 192.168.20.100 -t test/anomaly -m "x"; done
python tools/eval_session.py end S6
```

> **Penting:** tiap repetisi serangan harus berada di slice yang berbeda agar terhitung sebagai repetisi terpisah. Jeda 15–20 detik antar repetisi (window 120s ÷ 5 = 24s/slice).

### Langkah 5 — Finalisasi sesi

```bash
python tools/eval_session.py finish
python tools/eval_session.py show        # verifikasi 6 skenario tercatat
```

### Langkah 6 — Hitung metrik

```bash
python ml/evaluator_tabel1.py
# → cetak Tabel 1 ke stdout + simpan ml/models/tabel1_eval.json
```

### Langkah 7 — Isi Tabel 1 di artikel

```bash
cd artikel
python fill_tabel1.py
# → backup .preeval.docx dibuat, Tabel 1 di bak2.docx terisi
```

### Langkah 8 — Stop pipeline & verifikasi

Buka `artikel/Artikel_IKOMTI_Unified_Network_Guard_bak2.docx`, cek Tabel 1. Lanjut ke finalisasi narasi (Hasil, Pembahasan, Kesimpulan, abstrak tense lampau).

---

## 4. Troubleshooting

| Gejala | Penyebab | Solusi |
|---|---|---|
| `[!] kolom source BELUM ADA` | API belum start (migrasi via API startup) | `python tools/eval_session.py start` jalankan ALTER idempotent, atau start API sebentar |
| Suricata tidak ada alert | `eve.json` tidak ditulis / interface salah | cek `suricata_is_running()` via API, pastikan `-i enp9s0` & `local.rules` loaded |
| Rule engine tidak ada alert | traffic tidak masuk DB / threshold terlalu tinggi | cek `detection.log`, `network_traffic` tabel ada data? |
| ML tidak ada alert | model belum train / predictor belum catch up | `python ml/main.py train` lalu predict; predictor poll tiap 10s |
| Semua metode 0 di S2–S6 | attacker tidak tembus ke IoT subnet | cek routing 192.168.10.100 → 192.168.20.x; Suricata capture interface benar |
| S1 FPR tinggi | rule terlalu sensitif / traffic simulator mirip serangan | tinjau threshold di `detection/config.py` |

## 5. Setelah Tabel 1 terisi

1. Tulis **Hasil & Pembahasan** merujuk angka Tabel 1.
2. Ubah **abstrak** tense "diharapkan menunjukkan" → "menunjukkan" + cantumkan angka rata-rata Hibrida.
3. Tulis **Kesimpulan**.
4. Sajikan **Ucapan Terima Kasih** (butuh data penulis — Fase 1).
5. Cek integritas: angka Tabel 1 (nyata) ≠ angka lama di `Artikel_Ilmiah...md` (98,2%/0,54s) — pakai angka Tabel 1, hapus/perbarui artikel ilmiah lama.

## 6. Reproduksibilitas

`ml/models/tabel1_eval.json` menyimpan matriks lengkap + timestamp + metodologi. Sesi (`ml/eval_session.json`) menyimpan window tiap skenario. Keduanya bisa di-commit sebagai bukti evaluasi.
