
import json
import os
import time
import random
import threading
from datetime import datetime

import paho.mqtt.client as mqtt

# =====================================================
# HIVEMQ CLOUD CONFIGURATION
# =====================================================

BROKER = "5bedf517a53645328ea3e3a30e67f571.s1.eu.hivemq.cloud"
PORT = 8883
TOPIC = "transport/bus"

# Set these as PowerShell environment variables before running.
USERNAME = os.getenv("MQTT_USERNAME")
PASSWORD = os.getenv("MQTT_PASSWORD")

if not USERNAME or not PASSWORD:
    raise SystemExit(
        "❌ MQTT credentials missing. Set MQTT_USERNAME and MQTT_PASSWORD."
    )

# =====================================================
# ROUTE A
# =====================================================

ROUTE_A = [
    {"stop_id": "KUTO", "lat": 7.1557, "lon": 3.3451},
    {"stop_id": "PANSEKE", "lat": 7.1650, "lon": 3.3500},
    {"stop_id": "CAMP", "lat": 7.1750, "lon": 3.3600},
    {"stop_id": "ADATAN", "lat": 7.1850, "lon": 3.3700},
    {"stop_id": "LAFENWA", "lat": 7.1950, "lon": 3.3800}
]

# =====================================================
# ROUTE B
# =====================================================

ROUTE_B = [
    {"stop_id": "ITA_EKO", "lat": 7.1580, "lon": 3.3470},
    {"stop_id": "OMIDA", "lat": 7.1605, "lon": 3.3485},
    {"stop_id": "IJAYE", "lat": 7.1680, "lon": 3.3550},
    {"stop_id": "OKE_ILEWO", "lat": 7.1780, "lon": 3.3650},
    {"stop_id": "TOTORO", "lat": 7.1900, "lon": 3.3750}
]

# =====================================================
# BUS FLEET
# =====================================================

BUSES = {
    "BUS001": ROUTE_A,
    "BUS002": ROUTE_A,
    "BUS003": ROUTE_A,
    "BUS004": ROUTE_A,
    "BUS005": ROUTE_A,
    "BUS006": ROUTE_B,
    "BUS007": ROUTE_B,
    "BUS008": ROUTE_B,
    "BUS009": ROUTE_B,
    "BUS010": ROUTE_B
}

# =====================================================
# TRACK BUS POSITIONS
# =====================================================

bus_positions = {}

for i, bus in enumerate(BUSES.keys()):
    bus_positions[bus] = i % 5

# Generate one trip ID per bus for this simulation session.
trip_ids = {
    bus: f"{bus}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    for bus in BUSES
}

# =====================================================
# MQTT CONNECTION STATUS
# =====================================================

connection_event = threading.Event()
mqtt_connected = False

# =====================================================
# MQTT CALLBACKS (PAHO API VERSION 2)
# =====================================================

def on_connect(client, userdata, connect_flags, reason_code, properties):
    global mqtt_connected

    if reason_code == 0:
        mqtt_connected = True
        print("✅ Connected to HiveMQ Cloud")
        print(f"📡 Submitting telemetry to: {TOPIC}")
    else:
        mqtt_connected = False
        print(f"❌ Connection failed. RC={reason_code}")

    connection_event.set()


def on_disconnect(
    client, userdata, disconnect_flags, reason_code, properties
):
    global mqtt_connected

    mqtt_connected = False
    print(f"⚠️ Disconnected from HiveMQ. RC={reason_code}")


# =====================================================
# MQTT CLIENT
# =====================================================

client = mqtt.Client(
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    protocol=mqtt.MQTTv311
)

client.username_pw_set(
    USERNAME,
    PASSWORD
)

# Secure TLS with certificate verification enabled.
client.tls_set()

client.on_connect = on_connect
client.on_disconnect = on_disconnect

# =====================================================
# CONNECT TO HIVEMQ CLOUD
# =====================================================

try:
    print("Connecting to HiveMQ Cloud...")

    client.connect(
        BROKER,
        PORT,
        keepalive=60
    )

    client.loop_start()

    # Wait for the initial connection callback.
    if not connection_event.wait(timeout=15):
        raise TimeoutError("HiveMQ connection timed out.")

    if not mqtt_connected:
        raise ConnectionError("Could not connect to HiveMQ Cloud.")

except Exception as e:
    print(f"❌ Connection Error: {e}")

    try:
        client.loop_stop()
        client.disconnect()
    except Exception:
        pass

    raise SystemExit(1)


# =====================================================
# START BUS SIMULATION
# =====================================================

print("\n🚌 Starting Abeokuta Smart Transport Simulation")
print("🚌 Total Buses: 10")
print("🛣️ Route A: Kuto - Panseke - Camp - Adatan - Lafenwa")
print("🛣️ Route B: Ita Eko - Omida - Ijaye - Oke Ilewo - Totoro")
print("\nPress CTRL + C to stop simulation.\n")


try:

    while True:

        for bus, route in BUSES.items():

            position = bus_positions[bus]

            stop = route[position]

            # =========================================
            # GENERATE BUS TELEMETRY
            # =========================================

            payload = {
                "bus_id": bus,

                "trip_id": trip_ids[bus],

                "stop_id": stop["stop_id"],

                "timestamp": datetime.now().isoformat(),

                "lat": round(
                    stop["lat"] + random.uniform(-0.0010, 0.0010),
                    6
                ),

                "lon": round(
                    stop["lon"] + random.uniform(-0.0010, 0.0010),
                    6
                ),

                "speed_kmh": round(
                    random.uniform(20, 60),
                    2
                ),

                "occupancy": random.randint(5, 50)
            }

            # =========================================
            # PUBLISH TELEMETRY TO HIVEMQ
            # =========================================

            if not mqtt_connected:
                print(f"⚠️ MQTT disconnected. Skipping {bus}.")
            else:

                try:

                    result = client.publish(
                        TOPIC,
                        json.dumps(payload),
                        qos=1
                    )

                    if result.rc == mqtt.MQTT_ERR_SUCCESS:

                        result.wait_for_publish(timeout=5)

                        if result.is_published():

                            print(
                                f"✅ Published: {bus} | "
                                f"Stop={stop['stop_id']} | "
                                f"Speed={payload['speed_kmh']} km/h | "
                                f"Passengers={payload['occupancy']}"
                            )

                        else:

                            print(
                                f"❌ Publish not confirmed: {bus}"
                            )

                    else:

                        print(
                            f"❌ Publish failed for {bus}. "
                            f"RC={result.rc}"
                        )

                except (ValueError, RuntimeError, TimeoutError) as e:

                    print(
                        f"❌ Publishing error for {bus}: {e}"
                    )

            # =========================================
            # MOVE BUS TO NEXT STOP
            # =========================================

            bus_positions[bus] = (
                bus_positions[bus] + 1
            ) % len(route)

            time.sleep(0.5)

        print("\n🔄 Route cycle completed\n")

        time.sleep(3)


except KeyboardInterrupt:

    print("\n🛑 Simulation stopped by user.")


finally:

    print("🔌 Closing MQTT connection...")

    client.loop_stop()
    client.disconnect()

    print("✅ MQTT publisher shut down successfully.")
