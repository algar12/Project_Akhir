/*
 * ==============================================================================
 * Project      : Unified Network Guard (Edge IoT Security)
 * Device       : ESP32 Node 04
 * Role         : Simulated Air Quality & Environment Node
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
const char* mqtt_topic    = "iot/esp32-04/telemetry";
const char* client_id     = "ESP32-Node04-AirQuality";

const unsigned long PUBLISH_INTERVAL_MS = 4500;    // Setiap 4.5 detik
const int LED_PIN = 2;

WiFiClient espClient;
PubSubClient client(espClient);

unsigned long lastPublish = 0;
unsigned long seqCounter = 0;

int currentCo2 = 460;
int currentTvoc = 110;
float currentPm25 = 18.5;

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
    Serial.println("  ESP32 NODE 04 - AIR QUALITY (SIM)      ");
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

        // Variasi CO2 (400 - 750 ppm), TVOC (50 - 200 ppb), PM2.5 (10 - 35 ug/m3)
        currentCo2 += (random(0, 30) - 15);
        if (currentCo2 < 400) currentCo2 = 410;
        if (currentCo2 > 750) currentCo2 = 720;

        currentTvoc += (random(0, 10) - 5);
        if (currentTvoc < 40) currentTvoc = 45;
        if (currentTvoc > 250) currentTvoc = 230;

        currentPm25 += ((random(0, 20) - 10) / 10.0);
        if (currentPm25 < 8.0) currentPm25 = 9.5;
        if (currentPm25 > 45.0) currentPm25 = 42.0;

        char jsonBuffer[256];
        snprintf(jsonBuffer, sizeof(jsonBuffer),
            "{\"device_id\":\"ESP32-04\",\"type\":\"air_quality\",\"co2_ppm\":%d,\"tvoc_ppb\":%d,\"pm25\":%.1f,\"seq\":%lu,\"uptime\":%lu}",
            currentCo2, currentTvoc, currentPm25, seqCounter, now / 1000
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
