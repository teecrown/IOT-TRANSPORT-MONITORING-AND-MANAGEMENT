
import json
import os
import ssl
import time
import paho.mqtt.client as mqtt

BROKER = "5bedf517a53645328ea3e3a30e67f571.s1.eu.hivemq.cloud"
PORT = 8883

USERNAME = os.getenv("MQTT_USERNAME")
PASSWORD = os.getenv("MQTT_PASSWORD")

TOPIC = "transport/bus"

client = mqtt.Client(
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2
)

client.username_pw_set(USERNAME, PASSWORD)
client.tls_set()

client.connect(BROKER, PORT, 60)
client.loop_start()

time.sleep(2)

payload = {
    "bus_id": "TEST_BUS_001",
    "trip_id": "TEST_TRIP_001",
    "stop_id": "TEST_STOP_001",
    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    "lat": 6.8320,
    "lon": 3.6350,
    "speed_kmh": 35,
    "occupancy": 25
}

info = client.publish(TOPIC, json.dumps(payload), qos=1)
info.wait_for_publish()

print("Test telemetry published:", payload)

client.disconnect()
client.loop_stop()
