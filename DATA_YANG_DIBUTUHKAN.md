# Data yang Dibutuhkan untuk Melengkapi Artikel IKOMTI

**Artikel:** `Artikel_IKOMTI_Unified_Network_Guard.docx`
**Judul:** Unified Network Guard: Deteksi Anomali dan Serangan Siber IoT Berbasis Edge Computing
**Diperbarui:** 24 Sep 2026

> Daftar ini merangkum data/konten yang masih perlu disiapkan untuk menyelesaikan artikel.
> Tanda ✅ = sudah ada; ⬜ = perlu disiapkan; 🔧 = bisa dibantu otomatis begitu data diberikan.

---

## A. Data Penulis & Administratif ⬜

Saat ini masih placeholder (`Nama Penulis 1/2/3`, `Program Studi, Fakultas, Institusi`, `email@institusi.ac.id`).

| # | Item | Contoh | Status |
|---|------|--------|--------|
| A1 | Nama lengkap + gelar penulis 1, 2, 3 | "Ahmad Fauzan, S.Kom." | ⬜ |
| A2 | NIM (mahasiswa) / NIP (dosen) | "2011101001" | ⬜ |
| A3 | Program Studi | "S1 Teknik Informatika" | ⬜ |
| A4 | Fakultas | "Fakultas Teknik dan Informatika" | ⬜ |
| A5 | Institusi | "Universitas Teknologi Digital Indonesia" | ⬜ |
| A6 | Email tiap penulis (aktif) | "ahmad@utdi.ac.id" | ⬜ |
| A7 | Penulis korespondensi (corresponding author) + email | pilih salah satu penulis | ⬜ |
| A8 | ORCID tiap penulis (opsional) | "0000-0001-2345-6789" | ⬜ |

🔧 Begitu A dikirim → ganti placeholder via `search_and_replace`.

---

## B. Data Eksperimen (penghalang terbesar) ⬜

Tabel 1 saat ini berisi placeholder `—`. Untuk mengisinya, jalankan pipeline UNG pada dataset UGN-IoT dan catat hasil berikut.

### B1. Ground truth skenario
- Label tiap rekaman PCAP: skenario (S1–S6), kelas (normal/serangan), jenis serangan.
- ⬜ File ground truth (CSV/JSON).

### B2. Output deteksi tiap metode
- **Suricata (signature)** → `eve.json` / `fast.log`
- **Rule-based/threshold** → hasil pengecekan `connection_rate` / `packet_rate` vs baseline
- **Isolation Forest (ML)** → label prediksi + anomaly score
- **Hibrida (fusion)** → keputusan final gabungan
- ⬜ Log/keluaran 4 metode di atas.

### B3. Confusion matrix per skenario per metode
- TP / TN / FP / FN.
- ⬜ Tabel/CSV confusion matrix (S1–S6 × 4 metode).

### B4. Enam metrik performa
Dihitung dari confusion matrix (saya bisa bantu hitung):
- Accuracy
- Precision
- Recall
- F1-score
- False Positive Rate (FPR)
- Detection Latency (ms)
- ⬜ Nilai 6 metrik (atau kirim TP/TN/FP/FN, saya hitung).

### B5. Waktu deteksi (latency)
- Timestamp serangan terjadi vs timestamp alert muncul (per peristiwa).
- ⬜ Log timestamp.

### B6. Konfigurasi/parameter eksperimen
- Threshold baseline (connection_rate, packet_rate).
- Parameter Isolation Forest (`n_estimators`, `contamination`, `max_samples`).
- Aturan Suricata yang dipakai.
- Interval/periode capture.
- ⬜ Catatan konfigurasi.

### Format pengiriman paling mudah
CSV dengan kolom:
```
skenario, metode, TP, TN, FP, FN, latency_ms
```
atau langsung:
```
skenario, metode, accuracy, precision, recall, f1, fpr, latency_ms
```
🔧 Begitu B dikirim → hitung metrik (bila perlu) + isi Tabel 1 + tambah baris Rata-rata via `add_table`/python-docx.

---

## C. Konten Narasi (butuh data B dulu) ⬜

### C1. Hasil dan Pembahasan
Saat ini hanya 1 paragraf intro. Perlu:
- ⬜ Presentasi hasil per skenario S1–S6 + perbandingan 4 metode.
- ⬜ Pembahasan: mengapa hibrida lebih baik/lemah, analisis FP/FN, pengaruh latency, dampak edge.
- ⬜ Perbandingan dengan studi terdahulu (rujuk [1][2][3][5][9][14]).

### C2. Kesimpulan
Saat ini placeholder. Perlu:
- ⬜ Temuan utama yang menjawab tujuan penelitian.
- ⬜ Kontribusi/kebaruan platform UNG.
- ⬜ Keterbatasan & saran pengembangan/kerja未来.

🔧 Begitu data B ada → tulis paragraf Hasil & Kesimpulan berbasis data riil (bukan fiktif).

---

## D. Gambar Pendukung (opsional, nilai tambah)

| # | Gambar | Sumber | Status |
|---|--------|--------|--------|
| D1 | Arsitektur/topologi (Gambar 1) | sudah dibuat | ✅ |
| D2 | Foto/diagram testbed fisik (3 ESP32 + 2 router + Edge PC) | foto/draw | ⬜ |
| D3 | Flow diagram pipeline deteksi | draw | ⬜ |
| D4 | Confusion matrix / heatmap | dari hasil B | ⬜ |
| D5 | Kurva ROC/PR atau distribusi latency | dari hasil B | ⬜ |

🔧 Gambar D2–D5 → sisipkan via `add_picture` + caption + layout full-width.

---

## E. Pernyataan & Kelengkapan Lain ⬜

- ⬜ E1. Pernyataan orisinalitas (manuskrip belum pernah dipublikasikan) — tanggung jawab penulis.
- ⬜ E2. Pernyataan konflik kepentingan (ada/tidak ada).
- ⬜ E3. Sumber pendanaan (bila ada) → untuk Ucapan Terima Kasih.
- ⬜ E4. Ucapan Terima Kasih (pembimbing, institusi, pihak pendukung).

---

## F. Cek Kepatuhan IKOMTI (opsional, untuk konfirmasi akhir)

- ⬜ F1. Panjang manuskrip sesuai batasan IKOMTI.
- ⬜ F2. Jumlah referensi minimal (≥10 jurnal + 2 buku) — saat ini 15 jurnal + 2 buku = ✅ 17.
- ⬜ F3. Abstrak EN/ID ±200 kata + 3–6 kata kunci — ✅.
- ⬜ F4. Semua referensi terakreditasi (Sinta 2 / Scopus Q2) — ✅ (kecuali buku referensi).
- ⬜ F5. Tabel & gambar diberi nomor + caption — ✅ Tabel 1, Gambar 1.

---

## Ringkasan Prioritas

1. **A — Data penulis** (paling mudah, sudah punya) → kirim sekarang.
2. **B — Data eksperimen** (penghalang utama) → jalankan testbed UGN-IoT.
3. **C — Narasi Hasil & Kesimpulan** → setelah B selesai.
4. **D — Gambar pendukung** → opsional, setelah B.
5. **E & F — Pernyataan & cek akhir** → sebelum submit.

---

## File terkait
- Artikel utama: `F:\project akhir\Artikel_IKOMTI_Unified_Network_Guard.docx`
- Latar belakang: `F:\project akhir\Latar_Belakang_Penelitian.md`
- Pembahasan proyek: `F:\project akhir\Pembahasan_Proyek_Akhir_Unified_Network_Guard.md`
- Daftar referensi tambahan: `F:\project akhir\Daftar_Referensi_Tambahan.md`
- Backup dokumen: `..._bak1.docx` (pre-gambar), `..._bak2.docx` (pre-regenerasi referensi)
