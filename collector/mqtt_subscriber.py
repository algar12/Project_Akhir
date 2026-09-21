"""
mqtt_subscriber.py — Unified Network Guard: Collector
======================================================
Subscribe ke MQTT Broker, menerima pesan telemetri JSON dari semua
ESP32 node, mem-parsing payload, lalu menyimpannya ke database.

Topic yang disubscribe (dari .env): iot/#
Contoh topic per node:
  - iot/esp32-01/telemetry   → Climate (suhu, kelembapan)
  - iot/esp32-02/telemetry   → Security (gerak, cahaya)
  - iot/esp32-03/telemetry   → Energy (daya, tegangan)
  - iot/esp32-04/telemetry   → Air Quality (CO2, PM2.5)
  - iot/esp32-05/telemetry   → Smart Actuator / Status

Alur kerja:
  1. Koneksi ke Mosquitto broker
  2. Subscribe topic wildcard 'iot/#'
  3. Setiap pesan masuk → parse JSON → validasi → simpan ke DB
  4. Jika koneksi terputus → auto-reconnect
"""

import json
import logging
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

from collector.config import (
    MQTT_BROKER_HOST,
    MQTT_BROKER_PORT,
    MQTT_TOPIC_BASE,
    MQTT_CLIENT_ID,
    MQTT_KEEPALIVE,
    MQTT_RECONNECT_DELAY,
)
from collector.db import insert_telemetry, update_device_status

logger = logging.getLogger(__name__)


# ─── Mapping topic → device_id (opsional, sebagai fallback) ──────────────────
# Jika payload JSON sudah mengandung field 'device_id', field ini lebih diprioritaskan.
TOPIC_DEVICE_MAP: dict[str, str] = {
    'iot/esp32-01/telemetry': 'ESP32-01',
    'iot/esp32-02/telemetry': 'ESP32-02',
    'iot/esp32-03/telemetry': 'ESP32-03',
    'iot/esp32-04/telemetry': 'ESP32-04',
    'iot/esp32-05/telemetry': 'ESP32-05',
}


class MQTTSubscriber:
    """
    Subscriber MQTT untuk telemetri IoT ESP32.

    Usage:
        sub = MQTTSubscriber()
        sub.start()   # blocking — gunakan thread jika ingin non-blocking
        ...
        sub.stop()
    """

    def __init__(
        self,
        broker_host: str = MQTT_BROKER_HOST,
        broker_port: int = MQTT_BROKER_PORT,
        topic: str       = MQTT_TOPIC_BASE,
        client_id: str   = MQTT_CLIENT_ID,
    ) -> None:
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.topic       = topic
        self.client_id   = client_id

        # Statistik runtime
        self._total_received = 0
        self._total_saved    = 0
        self._total_error    = 0

        # Setup Paho MQTT client
        self._client = mqtt.Client(
            client_id=self.client_id,
            clean_session=True,
            protocol=mqtt.MQTTv311,
        )
        self._client.on_connect    = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message    = self._on_message

    # ─── Callback: Saat Terkoneksi ────────────────────────────────────────────
    def _on_connect(
        self, client: mqtt.Client, userdata, flags, rc: int
    ) -> None:
        if rc == 0:
            logger.info(
                "[MQTT] Terhubung ke broker %s:%d — Subscribe '%s'",
                self.broker_host, self.broker_port, self.topic,
            )
            # Subscribe ulang setiap koneksi (termasuk reconnect)
            client.subscribe(self.topic, qos=1)
        else:
            logger.error("[MQTT] Koneksi gagal, kode: %d", rc)

    # ─── Callback: Saat Terputus ──────────────────────────────────────────────
    def _on_disconnect(
        self, client: mqtt.Client, userdata, rc: int
    ) -> None:
        if rc == 0:
            logger.info("[MQTT] Terputus secara normal.")
        else:
            logger.warning(
                "[MQTT] Terputus tidak terduga (rc=%d). Reconnecting dalam %d detik...",
                rc, MQTT_RECONNECT_DELAY,
            )
            # Paho akan auto-reconnect via loop_forever(); beri jeda
            time.sleep(MQTT_RECONNECT_DELAY)

    # ─── Callback: Saat Pesan Masuk ──────────────────────────────────────────
    def _on_message(
        self, client: mqtt.Client, userdata, msg: mqtt.MQTTMessage
    ) -> None:
        """
        Handler utama pesan MQTT.

        Alur:
          1. Decode payload bytes → string
          2. Parse JSON → dict
          3. Ekstrak device_id (dari payload atau mapping topic)
          4. Simpan ke database
          5. Update status device
        """
        self._total_received += 1
        topic   = msg.topic
        # Timestamp UTC (naive) — konsisten dengan seluruh pipeline
        ts_recv = datetime.now(timezone.utc).replace(tzinfo=None)

        # 1. Decode
        try:
            raw_payload = msg.payload.decode('utf-8').strip()
        except UnicodeDecodeError:
            logger.warning("[MQTT] Payload bukan UTF-8 pada topic '%s'. Dilewati.", topic)
            self._total_error += 1
            return

        # 2. Parse JSON
        try:
            data: dict = json.loads(raw_payload)
        except json.JSONDecodeError as exc:
            logger.warning(
                "[MQTT] Payload bukan JSON valid pada topic '%s': %s | Raw: %.80s",
                topic, exc, raw_payload,
            )
            self._total_error += 1
            return

        # 3. Ekstrak device_id
        #    Prioritas: field 'device_id' di payload → fallback ke TOPIC_DEVICE_MAP
        device_id = (
            data.get('device_id')
            or TOPIC_DEVICE_MAP.get(topic)
            or self._derive_device_id(topic)
        )

        # Ekstrak IP jika ada di payload (untuk pelacakan perangkat)
        source_ip: str | None = data.get('ip_address') or data.get('ip')

        logger.debug(
            "[MQTT] ← [%s] device=%s | %s",
            topic, device_id, raw_payload[:120],
        )

        # 4. Simpan ke database
        ok = insert_telemetry(
            device_id=device_id,
            topic=topic,
            payload=data,
            source_ip=source_ip,
            timestamp=ts_recv,
        )

        if ok:
            self._total_saved += 1
            # 5. Update status device ('online' atau 'offline' sesuai payload)
            target_ident = source_ip or device_id
            if target_ident:
                dev_status = str(data.get('status', 'online')).lower()
                update_device_status(target_ident, status=dev_status)
        else:
            self._total_error += 1

        # Log setiap 50 pesan
        if self._total_received % 50 == 0:
            logger.info(
                "[MQTT] Statistik → Diterima: %d | Disimpan: %d | Error: %d",
                self._total_received, self._total_saved, self._total_error,
            )

    # ─── Helper: Derive device_id dari topic ─────────────────────────────────
    @staticmethod
    def _derive_device_id(topic: str) -> str:
        """
        Mengekstrak bagian device dari topic MQTT sebagai fallback.
        Contoh: 'iot/esp32-04/telemetry' → 'ESP32-04'
        """
        parts = topic.split('/')
        if len(parts) >= 2:
            return parts[1].upper()
        return 'UNKNOWN'

    # ─── Public API ──────────────────────────────────────────────────────────
    def start(self, blocking: bool = True) -> None:
        """
        Memulai subscriber MQTT.

        Args:
            blocking: True  → blokir thread saat ini (cocok untuk thread worker).
                      False → jalankan di background (non-blocking).
        """
        logger.info(
            "[MQTT] Menghubungkan ke broker %s:%d ...",
            self.broker_host, self.broker_port,
        )
        self._client.connect(
            host=self.broker_host,
            port=self.broker_port,
            keepalive=MQTT_KEEPALIVE,
        )

        if blocking:
            # loop_forever() menangani reconnect otomatis
            self._client.loop_forever()
        else:
            # loop_start() membuat thread background paho
            self._client.loop_start()

    def stop(self) -> None:
        """Menghentikan subscriber MQTT dengan bersih."""
        logger.info("[MQTT] Menghentikan subscriber...")
        self._client.loop_stop()
        self._client.disconnect()
        logger.info(
            "[MQTT] Dihentikan. Total → Diterima: %d | Disimpan: %d | Error: %d",
            self._total_received, self._total_saved, self._total_error,
        )

    @property
    def stats(self) -> dict[str, int]:
        """Mengembalikan statistik runtime subscriber."""
        return {
            'total_received': self._total_received,
            'total_saved':    self._total_saved,
            'total_error':    self._total_error,
        }
