-- Skema Database PostgreSQL untuk Unified Network Guard

CREATE TABLE IF NOT EXISTS devices (
    id SERIAL PRIMARY KEY,
    device_name VARCHAR(100) NOT NULL,
    ip_address VARCHAR(45) NOT NULL UNIQUE,
    mac_address VARCHAR(20),
    device_type VARCHAR(50),
    status VARCHAR(20) DEFAULT 'offline',
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS network_traffic (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source_ip VARCHAR(45) NOT NULL,
    destination_ip VARCHAR(45) NOT NULL,
    protocol VARCHAR(20) NOT NULL,
    source_port INTEGER,
    destination_port INTEGER,
    packet_count INTEGER DEFAULT 1,
    bytes INTEGER DEFAULT 0,
    is_syn BOOLEAN NOT NULL DEFAULT false,
    icmp_type INTEGER
);

CREATE TABLE IF NOT EXISTS alerts (
    id          SERIAL PRIMARY KEY,
    timestamp   TIMESTAMP          DEFAULT CURRENT_TIMESTAMP,
    source_ip   VARCHAR(45)        NOT NULL,
    target_ip   VARCHAR(45)        NOT NULL,
    attack_type VARCHAR(100)       NOT NULL,
    severity    VARCHAR(20)        NOT NULL, -- LOW, MEDIUM, HIGH, CRITICAL
    confidence  DOUBLE PRECISION   DEFAULT 1.0,
    description TEXT,
    mitigated   BOOLEAN            NOT NULL DEFAULT false,
    mitigated_at TIMESTAMP
);

-- Tabel telemetri MQTT dari ESP32 node
CREATE TABLE IF NOT EXISTS mqtt_telemetry (
    id          SERIAL PRIMARY KEY,
    timestamp   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    device_id   VARCHAR(50)  NOT NULL,
    topic       VARCHAR(200) NOT NULL,
    payload     JSONB,
    source_ip   VARCHAR(45)
);

-- ─── Index Performa ───────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_telemetry_device_time
    ON mqtt_telemetry (device_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_traffic_timestamp
    ON network_traffic (timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_alerts_timestamp
    ON alerts (timestamp DESC);

-- Tabel hasil prediksi ML (Isolation Forest + Random Forest)
CREATE TABLE IF NOT EXISTS ml_predictions (
    id           SERIAL PRIMARY KEY,
    timestamp    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    source_ip    VARCHAR(45)  NOT NULL,
    time_bucket  TIMESTAMP,
    if_score     FLOAT,
    is_anomaly   BOOLEAN      DEFAULT FALSE,
    attack_class VARCHAR(50),
    confidence   FLOAT        DEFAULT 0.0,
    features     JSONB
);

CREATE INDEX IF NOT EXISTS idx_mlpred_timestamp
    ON ml_predictions (timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_mlpred_anomaly
    ON ml_predictions (is_anomaly, timestamp DESC);

-- Seed awal data perangkat IoT
INSERT INTO devices (device_name, ip_address, device_type, status)
VALUES 
    ('ESP32-01', '192.168.20.101', 'Climate Sensor (Temp/Humidity)', 'registered'),
    ('ESP32-02', '192.168.20.102', 'Security Sensor (Motion/Light)', 'registered'),
    ('ESP32-03', '192.168.20.103', 'Energy Meter (Power/Voltage)', 'registered'),
    ('ESP32-04', '192.168.20.104', 'Air Quality (CO2/PM2.5)', 'registered'),
    ('ESP32-05', '192.168.20.105', 'Heartbeat & Gateway Node', 'registered')
ON CONFLICT (ip_address) DO NOTHING;
