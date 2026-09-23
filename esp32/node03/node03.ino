/*
 * ==============================================================================
 * Project      : Unified Network Guard (Edge IoT Security)
 * Device       : ESP32 Node 03
 * Role         : Simulated Smart Energy & Power Meter
 * Protocol     : MQTT over Wi-Fi
 * ==============================================================================
 */

#include <WiFi.h>
#include <PubSubClient.h>

// ================= KONFIGURASI JARINGAN & BROKER =================
const char* ssid          = "TP-Link_D38E";
const char* password      = "12345678";
const char* mqtt_broker   = "192.168.20.100";       // IP Edge Computing PC (di subnet IoT)
const int   mqtt_port     = 1883;
const char* mqtt_topic    = "iot/esp32-03/telemetry";
const char* client_id     = "ESP32-Node03-Energy";

const unsigned long PUBLISH_INTERVAL_MS = 5000;    // Setiap 5 detik
const int LED_PIN = 2;

WiFiClient espClient;
PubSubClient client(espClient);

unsigned long lastPublish = 0;
unsigned long seqCounter = 0;

float currentVoltage = 220.5;
float currentAmps = 1.25;
float totalKwh = 12.450;

void setupWifi() {
    delay(100);
    Serial.println();
    Serial.print("[WiFi] Menghubungkan ke: ");
    Serial.println(ssid);

    WiFi.mode(WIFI_STA);
    WiFi.begin(ssid, password);

    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
        digitalWrite(LED_PIN, !digitalRead(LED_PIN));
    }

    digitalWrite(LED_PIN, HIGH);
    Serial.println("\n[WiFi] Terhubung!");
    Serial.print("[WiFi] IP Address: ");
    Serial.println(WiFi.localIP());
}

void reconnectMqtt() {
    while (!client.connected()) {
        Serial.print("[MQTT] Menghubungkan ke broker: ");
        Serial.print(mqtt_broker);
        Serial.print("... ");

        if (client.connect(client_id)) {
            Serial.println("BERHASIL!");
        } else {
            Serial.print("GAGAL, rc=");
            Serial.print(client.state());
            Serial.println(". Coba lagi dalam 3 detik...");
            delay(3000);
        }
    }
}

void setup() {
    pinMode(LED_PIN, OUTPUT);
    Serial.begin(115200);
    delay(1000);

    Serial.println("\n=========================================");
    Serial.println("  ESP32 NODE 03 - ENERGY METER (SIM)     ");
    Serial.println("=========================================");

    setupWifi();
    client.setServer(mqtt_broker, mqtt_port);
}

void loop() {
    if (WiFi.status() != WL_CONNECTED) {
        setupWifi();
    }

    if (!client.connected()) {
        reconnectMqtt();
    }
    client.loop();

    unsigned long now = millis();
    if (now - lastPublish >= PUBLISH_INTERVAL_MS) {
        lastPublish = now;
        seqCounter++;

        // Variasi tegangan (218V - 224V) dan beban arus (0.5A - 2.5A)
        currentVoltage = 220.0 + ((random(0, 80) - 40) / 10.0);
        currentAmps = 0.8 + ((random(0, 150)) / 100.0);
        float powerWatts = currentVoltage * currentAmps;
        totalKwh += (powerWatts * (PUBLISH_INTERVAL_MS / 3600000.0) / 1000.0);

        char jsonBuffer[256];
        snprintf(jsonBuffer, sizeof(jsonBuffer),
            "{\"device_id\":\"ESP32-03\",\"type\":\"energy\",\"voltage\":%.1f,\"current\":%.2f,\"power_w\":%.1f,\"kwh\":%.3f,\"seq\":%lu,\"uptime\":%lu}",
            currentVoltage, currentAmps, powerWatts, totalKwh, seqCounter, now / 1000
        );

        Serial.print("[PUBLISH -> ");
        Serial.print(mqtt_topic);
        Serial.print("]: ");
        Serial.println(jsonBuffer);

        digitalWrite(LED_PIN, LOW);
        client.publish(mqtt_topic, jsonBuffer);
        delay(50);
        digitalWrite(LED_PIN, HIGH);
    }
}
