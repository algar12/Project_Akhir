#!/usr/bin/env python3
"""
simulate_esp32.py — Unified Network Guard
=========================================
Script simulator untuk memvalidasi deteksi koneksi real-time ESP32.
Mengirimkan telemetri MQTT JSON ke broker Mosquitto (port 1883) persis seperti
firmware node01.ino - node05.ino.

Cara menjalankan:
  # Simulasikan ESP32-01 (Sensor Suhu & Kelembapan):
  python tools/simulate_esp32.py --node 1

  # Simulasikan semua node (ESP32-01 s.d ESP32-05):
  python tools/simulate_esp32.py --all

Tekan Ctrl+C untuk mematikan node dan melihat status berubah menjadi OFFLINE di dashboard.
"""

import argparse
import json
import logging
import os
import random
import signal
import sys
import time
from datetime import datetime

# Tambahkan root directory proyek ke sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("Error: paho-mqtt belum terinstall di environment. Jalankan: pip install paho-mqtt")
    sys.exit(1)

# Konfigurasi Node
NODES = {
    1: {
        "device_id": "ESP32-01",
        "ip": "192.168.20.101",
        "topic": "iot/esp32-01/telemetry",
        "type": "climate",
        "name": "Climate Sensor (Temp/Humidity)"
    },
    2: {
        "device_id": "ESP32-02",
        "ip": "192.168.20.102",
        "topic": "iot/esp32-02/telemetry",
        "type": "security",
        "name": "Security Sensor (Motion/Light)"
    },
    3: {
        "device_id": "ESP32-03",
        "ip": "192.168.20.103",
        "topic": "iot/esp32-03/telemetry",
        "type": "energy",
        "name": "Energy Meter (Power/Voltage)"
    },
    4: {
        "device_id": "ESP32-04",
        "ip": "192.168.20.104",
        "topic": "iot/esp32-04/telemetry",
        "type": "air_quality",
        "name": "Air Quality (CO2/PM2.5)"
    },
    5: {
        "device_id": "ESP32-05",
        "ip": "192.168.20.105",
        "topic": "iot/esp32-05/telemetry",
        "type": "heartbeat",
        "name": "Heartbeat / Gateway Node"
    }
}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-7s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('ESP32Sim')


def main():
    parser = argparse.ArgumentParser(description="Simulasi Perangkat IoT ESP32 untuk UNG")
    parser.add_argument("--node", type=int, choices=[1, 2, 3, 4, 5], help="Nomor node ESP32 (1-5)")
    parser.add_argument("--all", action="store_true", help="Jalankan semua node 1 s/d 5")
    parser.add_argument("--interval", type=float, default=3.0, help="Interval kirim pesan (detik)")
    args = parser.parse_args()

    selected_nodes = []
    if args.all:
        selected_nodes = [NODES[1], NODES[2], NODES[3], NODES[4], NODES[5]]
    elif args.node:
        selected_nodes = [NODES[args.node]]
    else:
        selected_nodes = [NODES[1]]

    logger.info("==================================================")
    logger.info("  Unified Network Guard — ESP32 Real-Time Simulator")
    logger.info("==================================================")
    logger.info("Menghubungkan ke MQTT broker di localhost:1883...")

    client = mqtt.Client(client_id=f"sim-esp32-{random.randint(100, 999)}")
    try:
        client.connect("localhost", 1883, 60)
        client.loop_start()
    except Exception as e:
        logger.error(f"Gagal koneksi ke MQTT broker localhost:1883: {e}")
        logger.error("Pastikan container ung_mosquitto berjalan via: docker-compose up -d")
        sys.exit(1)

    logger.info("MQTT Broker terhubung!")
    for n in selected_nodes:
        logger.info(f"  ● Node Aktif: {n['device_id']} ({n['ip']}) -> Topic: {n['topic']}")

    logger.info("\nMengirim telemetri berkala (tekan Ctrl+C untuk berhenti)...")

    # Update status online di database saat mulai
    try:
        from collector.db import update_device_status
        for n in selected_nodes:
            update_device_status(n["ip"], status="online")
            update_device_status(n["device_id"], status="online")
        logger.info("Status node di database diaktifkan: ONLINE")
    except Exception as e:
        logger.debug(f"Direct DB startup update skipped: {e}")

    seq = 0
    running = True

    def handle_exit(signum, frame):
        nonlocal running
        logger.info("\nMenghentikan simulator. Mengirim status OFFLINE ke broker dan database...")
        # 1. Update database langsung
        try:
            from collector.db import update_device_status
            for n in selected_nodes:
                update_device_status(n["ip"], status="offline")
                update_device_status(n["device_id"], status="offline")
            logger.info("Database berhasil diupdate ke OFFLINE.")
        except Exception as e:
            logger.warning(f"Gagal update DB langsung: {e}")

        # 2. Publish MQTT status offline
        for n in selected_nodes:
            offline_payload = json.dumps({
                "device_id": n["device_id"],
                "ip_address": n["ip"],
                "status": "offline",
                "timestamp": datetime.now().isoformat()
            })
            info = client.publish(n["topic"], offline_payload, qos=1)
            try:
                info.wait_for_publish(timeout=1.0)
            except Exception:
                pass
        running = False

    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    temp = 28.5
    humidity = 65.0

    try:
        while running:
            seq += 1
            temp += random.uniform(-0.3, 0.3)
            humidity += random.uniform(-0.5, 0.5)

            for n in selected_nodes:
                payload = {
                    "device_id": n["device_id"],
                    "ip_address": n["ip"],
                    "type": n["type"],
                    "seq": seq,
                    "uptime": seq * int(args.interval),
                    "timestamp": datetime.now().isoformat()
                }

                if n["type"] == "climate":
                    payload["temperature"] = round(temp, 2)
                    payload["humidity"] = round(humidity, 2)
                elif n["type"] == "security":
                    payload["motion"] = random.choice([True, False])
                    payload["light_lux"] = random.randint(200, 800)
                elif n["type"] == "energy":
                    payload["voltage"] = round(220.0 + random.uniform(-2, 2), 1)
                    payload["current_a"] = round(random.uniform(0.5, 2.5), 2)
                elif n["type"] == "air_quality":
                    payload["co2_ppm"] = random.randint(400, 1200)
                    payload["pm25"] = round(random.uniform(5.0, 75.0), 1)
                elif n["type"] == "heartbeat":
                    payload["rssi"] = random.randint(-75, -45)
                    payload["free_heap"] = random.randint(120000, 180000)

                json_str = json.dumps(payload)
                client.publish(n["topic"], json_str, qos=1)
                logger.info(f"[PUBLISH] {n['device_id']} ({n['ip']}) -> {json_str}")

            time.sleep(args.interval)

    finally:
        try:
            from collector.db import update_device_status
            for n in selected_nodes:
                update_device_status(n["ip"], status="offline")
                update_device_status(n["device_id"], status="offline")
            logger.info("Status node di database dipulihkan ke: OFFLINE")
        except Exception as e:
            logger.warning(f"Gagal update status offline saat exit: {e}")
        client.loop_stop()
        client.disconnect()
        logger.info("Simulator berhenti.")


if __name__ == "__main__":
    main()
