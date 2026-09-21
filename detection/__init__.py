"""
Detection Module — Unified Network Guard
=========================================
Modul ini mengandung tiga komponen utama:

  1. rule_engine.py   — Deteksi berbasis threshold/aturan real-time
                        (Port Scan, SYN Flood, ICMP Flood, MQTT Anomaly, dll.)

  2. eve_parser.py    — Parser log Suricata (eve.json) secara tail -f,
                        mengambil alert IDS lalu menyimpannya ke database.

  3. alert_manager.py — Pengelola alert terpusat: de-duplikasi,
                        severity mapping, insert ke tabel alerts.

  4. main.py          — Entry point yang menjalankan ketiga komponen.
"""
