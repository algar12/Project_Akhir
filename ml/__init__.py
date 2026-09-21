"""
ML Module — Unified Network Guard
===================================
Pipeline Machine Learning untuk deteksi anomali traffic jaringan IoT.

Struktur modul:
  config.py          — konfigurasi path, hyperparameter, fitur
  feature_extractor.py — ekstraksi & agregasi fitur dari tabel network_traffic
  trainer.py         — pelatihan Isolation Forest + Random Forest
  predictor.py       — inferensi real-time, hasilkan alert jika anomali
  evaluator.py       — hitung Accuracy/Precision/Recall/F1/FPR/Latency
  main.py            — entry point (train / predict / evaluate)
"""
