import json
import os
import sqlite3
import ssl
from datetime import datetime
import pandas as pd
from fastapi import FastAPI
import paho.mqtt.client as mqtt
import uvicorn

# =====================================================
# FASTAPI APP
# =====================================================

app = FastAPI(
    title="IoT Transport Monitoring API",
    version="2.0"
)

# =====================================================
# DATABASE
# =====================================================

DB_NAME = "transport.db"

def init_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS telemetry (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bus_id TEXT,
        trip_id TEXT,
        stop_id TEXT,
        timestamp TEXT,
        lat REAL,
        lon REAL,
        speed_kmh REAL,
        occupancy INTEGER
    )
    """)

    conn.commit()
    conn.close()

init_database()

# =====================================================
# ANALYTICS ENGINE (NEW)
# =====================================================

def compute_metrics(df):
    if df.empty:
        return {
            "avg_speed": 0,
            "avg_occupancy": 0,
            "congested_buses": 0,
            "slow_buses": 0,
            "total_records": 0
        }

    return {
        "avg_speed": round(df["speed_kmh"].mean(), 2),
        "avg_occupancy": round(df["occupancy"].mean(), 2),
        "congested_buses": int(len(df[df["occupancy"] >= 40])),
        "slow_buses": int(len(df[df["speed_kmh"] <= 20])),
        "total_records": len(df)
        
    }

# =====================================================
# MQTT CONFIGURATION
# =====================================================

BROKER = "5bedf517a53645328ea3e3a30e67f571.s1.eu.hivemq.cloud"
PORT = 8883
USERNAME = "ADMIN"
PASSWORD = "AdminBus123"
TOPIC = "transport/bus"

# =====================================================
# MQTT CALLBACKS
# =====================================================

def on_connect(client, userdata, flags, rc):

    print(f"\nMQTT Connected | RC={rc}")

    if rc == 0:
        client.subscribe(TOPIC, qos=1)
        print(f"Subscribed to: {TOPIC}")
    else:
        print("MQTT connection failed")


def on_disconnect(client, userdata, rc):
    print(f"\nMQTT Disconnected | RC={rc}")


def on_message(client, userdata, msg):

    print("\n🔥 MQTT MESSAGE RECEIVED")

    try:
        payload = msg.payload.decode()
        data = json.loads(payload)

        bus_id = data.get("bus_id")
        if not bus_id:
            print("❌ Missing bus_id")
            return

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO telemetry (
                bus_id,
                trip_id,
                stop_id,
                timestamp,
                lat,
                lon,
                speed_kmh,
                occupancy
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            bus_id,
            data.get("trip_id"),
            data.get("stop_id"),
            data.get("timestamp"),
            data.get("lat"),
            data.get("lon"),
            data.get("speed_kmh"),
            data.get("occupancy")
        ))

        conn.commit()
        conn.close()

        print(f"✅ Saved: {bus_id}")

    except Exception as e:
        print("❌ MQTT ERROR:", e)

# =====================================================
# MQTT CLIENT
# =====================================================

client = mqtt.Client()

client.username_pw_set(USERNAME, PASSWORD)
client.tls_set()
# client.tls_set(cert_reqs=ssl.CERT_NONE)
# client.tls_insecure_set(True)

client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message

print("Connecting to HiveMQ Cloud...")

client.connect(BROKER, PORT, 60)
client.loop_start()

# =====================================================
# API ROUTES
# =====================================================

@app.get("/")
def home():
    return {
        "status": "running",
        "service": "IoT Transport Monitoring API",
        "time": datetime.now().isoformat()
    }

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/telemetry")
def telemetry():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()
    cursor.execute("""
        SELECT *
        FROM telemetry
        ORDER BY id DESC
        LIMIT 100
    """)

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]

@app.get("/latest")
def latest():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()
    cursor.execute("""
        SELECT *
        FROM telemetry
        WHERE id IN (
            SELECT MAX(id)
            FROM telemetry
            GROUP BY bus_id
        )
        ORDER BY bus_id
    """)

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]

# =====================================================
# NEW: METRICS ENDPOINT (THESIS FEATURE)
# =====================================================

@app.get("/metrics")
def metrics():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql("SELECT * FROM telemetry", conn)
    conn.close()

    return compute_metrics(df)

# =====================================================
# MAIN
# =====================================================
port = int(os.environ.get("PORT", 10001))
if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port   
    )
