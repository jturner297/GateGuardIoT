# asyncio allows for running multiple background tasks (like checking sensors) simultaneously without freezing the system
# json handles converting python dictionaries to JSON strings for AWS, and vice versa
# os allows the script to navigate the file system to safely find config files regardless of where the script is run from
# paho.mqtt.client allows Pi to connect to the local Mosquitto broker to feed the local web dashboard
# AWSIoTPythonSDK allows Pi to securely punch through Amazon's Zero-Trust firewall using certificates
# BleakClient handles the physical Bluetooth Low Energy (BLE) connections to the ESP32 nodes
# datetime generates exact time records so we know exactly when an event occurred
import asyncio
import json
import os
import paho.mqtt.client as mqtt
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
from bleak import BleakClient
from datetime import datetime

# ==========================================
# 1. DYNAMIC CONFIGURATION
# ==========================================
# Smart Config Loader: Checks local folder first, then parent folder just in case you run this from the /pi directory
config_path = 'config.json'
if not os.path.exists(config_path):
    config_path = '../config.json'

# --- LOAD CONFIGURATION ---
with open(config_path, 'r') as f:
    config = json.load(f)

# Extract Local and BLE variables from the config dictionary
TRUSTED_DEVICES = config["trusted_devices"]
DATA_CHAR_UUID = config["ble"]["data_char_uuid"]
LOCAL_BROKER = config["mqtt"]["broker"]
LOCAL_PORT = config["mqtt"]["port"]
ALERT_TOPIC = config["alert_topics"][0]

# Extract AWS Zero-Trust variables from the config dictionary
AWS_ENDPOINT = config["aws"]["endpoint"]
PATH_TO_ROOT = config["aws"]["root_ca"]
PATH_TO_KEY = config["aws"]["private_key"]
PATH_TO_CERT = config["aws"]["device_cert"]
CLIENT_ID = config["aws"]["client_id"]
AWS_TOPIC_TELEMETRY = config["aws"]["cloud_telemetry_topic"]
AWS_TOPIC_ALERTS = config["aws"]["cloud_alert_topic"]

# ==========================================
# 2. CLOUD & LOCAL CONNECTIONS
# ==========================================
print("Initializing AWS IoT Core connection...")
# Creates the instance of the AWS client and configures it using our downloaded certificates
aws_client = AWSIoTMQTTClient(CLIENT_ID)
aws_client.configureEndpoint(AWS_ENDPOINT, 8883)
aws_client.configureCredentials(PATH_TO_ROOT, PATH_TO_KEY, PATH_TO_CERT)

# Configure AWS connection stability parameters so the Pi doesn't crash if the WiFi drops
aws_client.configureOfflinePublishQueueing(-1)
aws_client.configureDrainingFrequency(2)
aws_client.configureConnectDisconnectTimeout(10)
aws_client.configureMQTTOperationTimeout(5)
aws_client.connect()
print("SUCCESS: Connected to AWS Cloud Broker.")

print(f"Initializing Local MQTT (For Dashboard) at {LOCAL_BROKER}:{LOCAL_PORT}...")
# Creates the instance of the local Mosquitto client and connects it
# Fixes the DeprecationWarning
local_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1) 
local_client.connect(LOCAL_BROKER, LOCAL_PORT)

# ==========================================
# 3. THE CONCURRENT EDGE WORKER
# ==========================================
# This function runs independently for every MAC address in your config
# It handles the BLE connection, data validation, and dual-routing
async def connect_to_device(mac_address, local_topic):
    print(f"[{mac_address}] Scanning for node...")
    
    # Infinite retry loop ensures the gateway never gives up if a sensor temporarily loses power
    while True: 
        try:
            async with BleakClient(mac_address) as client:
                print(f"[{mac_address}] ALLOWED: Connected to Verified Device.")
                
                # Active connection loop
                while True:
                    # Pulls the raw bytes from the ESP32 and converts to a readable string
                    raw_data = await client.read_gatt_char(DATA_CHAR_UUID)
                    payload_str = raw_data.decode('utf-8')
                    
                    try:
                        # 1. Parse the raw JSON payload from the hardware
                        json_data = json.loads(payload_str)
                        
                        # 2. METADATA STAMPING: Inject the MAC address into the payload so AWS knows which hardware sent it
                        json_data["mac_address"] = mac_address
                        
                        # 3. Repackage the enriched JSON dictionary back into a string format
                        enriched_payload = json.dumps(json_data)
                        
                        # --- THE DUAL ROUTE ---
                        # 4a. Fire to Local Web Dashboard for zero-latency UI rendering
                        local_client.publish(local_topic, enriched_payload)
                        # 4b. Fire to AWS DynamoDB for permanent cloud storage
                        aws_client.publish(AWS_TOPIC_TELEMETRY, enriched_payload, 1)
                        
                        # Timestamp purely for the terminal log output
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        print(f"[{timestamp}] [{mac_address}] ROUTED TO LOCAL & CLOUD: {enriched_payload}")
                        
                    # Triggers if the payload is not perfect JSON (simulating a spoofed or malformed packet)
                    except json.JSONDecodeError:
                        print(f"[{mac_address}] BLOCKED: Malformed payload detected.")
                        error_msg = f"Invalid JSON from {mac_address}"
                        
                        # Packages the error so AWS SNS can read it and send the SMS Text Message
                        aws_alert_msg = json.dumps({"default": f"GATEGUARD INTRUSION: {error_msg}"})
                        
                        # Route Alerts to both the local dashboard and the cloud
                        local_client.publish(ALERT_TOPIC, error_msg)
                        aws_client.publish(AWS_TOPIC_ALERTS, aws_alert_msg, 1) 
                        
                    # Prevents the loop from overwhelming the CPU
                    await asyncio.sleep(3)
                    
        except Exception as e:
            # If the ESP32 disconnects, wait 5 seconds and try to reconnect
            print(f"[{mac_address}] Disconnected or out of range. Retrying in 5s...")
            await asyncio.sleep(5)

# ==========================================
# 4. SYSTEM BOOTSTRAP
# ==========================================
async def main():
    print(f"Starting GateGuard Edge Gateway...")
    print(f"Loaded {len(TRUSTED_DEVICES)} trusted devices. Engaging Zero-Trust Protocols.")
    
    # Create a list of independent tasks for every device in the config file
    tasks = []
    for mac, topic in TRUSTED_DEVICES.items():
        tasks.append(connect_to_device(mac, topic))
        
    # Launch all concurrent workers simultaneously
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    # Boot the async event loop
    asyncio.run(main())