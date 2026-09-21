/*
 * ==============================================================================
 * Project      : Unified Network Guard (Edge IoT Security)
 * Device       : ESP32 Node 02
 * Role         : Simulated Security & Light Node (Motion & Lux)
 * Protocol     : MQTT over Wi-Fi
 * ==============================================================================
 */

#include <WiFi.h>
#include <PubSubClient.h>

// ================= KONFIGURASI JARINGAN & BROKER =================
const char* ssid          = "TP-Link_D38E";
const char* password      = "12345678";
const char* mqtt_broker   = "192.168.10.10";
const int   mqtt_port     = 1883;
const char* mqtt_topic    = "iot/esp32-02/telemetry";
const char* client_id     = "ESP32-Node02-Security";

const unsigned long PUBLISH_INTERVAL_MS = 3500;    // Setiap 3.5 detik
const int LED_PIN = 2;

WiFiClient espClient;
PubSubClient client(espClient);

unsigned long lastPublish = 0;
unsigned long seqCounter = 0;

float currentLux = 320.0;

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
    Serial.println("  ESP32 NODE 02 - SECURITY & LIGHT (SIM) ");
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

        // Simulasi intensitas cahaya & sensor gerak PIR
        currentLux += (random(0, 40) - 20);
        if (currentLux < 100.0) currentLux = 120.0;
        if (currentLux > 800.0) currentLux = 750.0;

        int motionDetected = (random(0, 100) > 75) ? 1 : 0; // Peluang gerak 25%

        char jsonBuffer[256];
        snprintf(jsonBuffer, sizeof(jsonBuffer),
            "{\"device_id\":\"ESP32-02\",\"type\":\"security\",\"motion\":%d,\"light_lux\":%.1f,\"seq\":%lu,\"uptime\":%lu}",
            motionDetected, currentLux, seqCounter, now / 1000
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
