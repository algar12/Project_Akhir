/*
 * ==============================================================================
 * Project      : Unified Network Guard (Edge IoT Security)
 * Device       : ESP32 Node 01
 * Role         : Simulated Indoor Climate Node (Temperature & Humidity)
 * Protocol     : MQTT over Wi-Fi
 * ==============================================================================
 */

#include <WiFi.h>
#include <PubSubClient.h>

// ================= KONFIGURASI JARINGAN & BROKER =================
const char* ssid          = "TP-Link_D38E";        // Sesuaikan dengan SSID Router IoT
const char* password      = "12345678";            // Password Wi-Fi Router
const char* mqtt_broker   = "192.168.10.10";       // IP Edge Computing PC
const int   mqtt_port     = 1883;
const char* mqtt_topic    = "iot/esp32-01/telemetry";
const char* client_id     = "ESP32-Node01-Climate";

// Parameter Pengiriman
const unsigned long PUBLISH_INTERVAL_MS = 4000;    // Kirim data setiap 4 detik
const int LED_PIN = 2;                             // Built-in LED ESP32

WiFiClient espClient;
PubSubClient client(espClient);

unsigned long lastPublish = 0;
unsigned long seqCounter = 0;

// Variabel dasar simulasi suhu & kelembapan
float currentTemp = 28.5;
float currentHumidity = 65.0;

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
        digitalWrite(LED_PIN, !digitalRead(LED_PIN)); // Kedip saat connecting
    }

    digitalWrite(LED_PIN, HIGH); // Nyala konstan saat terkoneksi
    Serial.println("\n[WiFi] Terhubung!");
    Serial.print("[WiFi] IP Address: ");
    Serial.println(WiFi.localIP());
    Serial.print("[WiFi] MAC Address: ");
    Serial.println(WiFi.macAddress());
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

// Menghasilkan nilai acak yang realistis (smooth random walk)
void simulateSensorData() {
    // Variasi acak kecil antara -0.3 s.d +0.3
    float deltaTemp = ((random(0, 60) - 30) / 100.0);
    currentTemp += deltaTemp;
    if (currentTemp < 24.0) currentTemp = 24.5;
    if (currentTemp > 33.0) currentTemp = 32.5;

    float deltaHum = ((random(0, 100) - 50) / 100.0);
    currentHumidity += deltaHum;
    if (currentHumidity < 50.0) currentHumidity = 52.0;
    if (currentHumidity > 80.0) currentHumidity = 78.0;
}

void setup() {
    pinMode(LED_PIN, OUTPUT);
    Serial.begin(115200);
    delay(1000);

    Serial.println("\n=========================================");
    Serial.println("  ESP32 NODE 01 - CLIMATE SENSOR (SIM)   ");
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

        simulateSensorData();

        // Susun payload JSON
        char jsonBuffer[256];
        snprintf(jsonBuffer, sizeof(jsonBuffer),
            "{\"device_id\":\"ESP32-01\",\"type\":\"climate\",\"temperature\":%.2f,\"humidity\":%.2f,\"seq\":%lu,\"uptime\":%lu}",
            currentTemp, currentHumidity, seqCounter, now / 1000
        );

        Serial.print("[PUBLISH -> ");
        Serial.print(mqtt_topic);
        Serial.print("]: ");
        Serial.println(jsonBuffer);

        // Kedipkan LED sejenak tanda transmisi data
        digitalWrite(LED_PIN, LOW);
        client.publish(mqtt_topic, jsonBuffer);
        delay(50);
        digitalWrite(LED_PIN, HIGH);
    }
}
