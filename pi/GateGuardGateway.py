# asyncio allows the script to handle multiple background tasks (like checking different sensors) at the same time without locking up the CPU
import asyncio
# json handles converting Python dictionaries to string formats that AWS and local MQTT can read
import json
# os lets the script navigate the file system to find the config file, no matter where you run the script from
import os
# paho.mqtt.client is what the Pi uses to talk to the local Mosquitto broker for the zero-latency dashboard
import paho.mqtt.client as mqtt
# AWSIoTPythonSDK manages the secure handshake to get through Amazon's firewall using our specific certificates
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
# bleak handles the physical Bluetooth Low Energy (BLE) radio connections to the ESP32 nodes
from bleak import BleakClient
# datetime and timezone generate exact UTC time records so our database stays perfectly sorted
from datetime import datetime, timezone # Ensure timezone is imported


# 1. Dynamic configuration

# Check the current folder first, then the parent folder just in case the script is run from a different directory
config_path = 'config.json'
if not os.path.exists(config_path):
    config_path = '../config.json'

# Load all the environment variables so we don't have to hardcode IPs or MAC addresses in the main logic
with open(config_path, 'r') as f:
    config = json.load(f)

# Figure out the exact absolute path to the config file so the certificate paths don't break
base_dir = os.path.dirname(os.path.abspath(config_path))

# Pull local network and Bluetooth parameters
TRUSTED_DEVICES = config["trusted_devices"]
DATA_CHAR_UUID = config["ble"]["data_char_uuid"]
LOCAL_BROKER = config["mqtt"]["broker"]
LOCAL_PORT = config["mqtt"]["port"]
ALERT_TOPIC = config["alert_topics"][0]

# Pull AWS endpoint and dynamically build the absolute paths to the security certificates
AWS_ENDPOINT = config["aws"]["endpoint"]
PATH_TO_ROOT = os.path.join(base_dir, config["aws"]["root_ca"])
PATH_TO_KEY = os.path.join(base_dir, config["aws"]["private_key"])
PATH_TO_CERT = os.path.join(base_dir, config["aws"]["device_cert"])
CLIENT_ID = config["aws"]["client_id"]
AWS_TOPIC_TELEMETRY = config["aws"]["cloud_telemetry_topic"]
AWS_TOPIC_ALERTS = config["aws"]["cloud_alert_topic"]


# 2. Cloud and local connections

print("Initializing AWS IoT Core connection...")
# Create the AWS client instance and feed it the certificates to authenticate
aws_client = AWSIoTMQTTClient(CLIENT_ID)
aws_client.configureEndpoint(AWS_ENDPOINT, 8883)
aws_client.configureCredentials(PATH_TO_ROOT, PATH_TO_KEY, PATH_TO_CERT)

# Configure the connection to queue messages and auto-reconnect if the Pi temporarily loses WiFi
aws_client.configureOfflinePublishQueueing(-1)
aws_client.configureDrainingFrequency(2)
aws_client.configureConnectDisconnectTimeout(10)
aws_client.configureMQTTOperationTimeout(5)
aws_client.connect()
print("SUCCESS: Connected to AWS Cloud.")

# Create and connect the local client for the dashboard UI
local_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1) 
local_client.connect(LOCAL_BROKER, LOCAL_PORT)


# 3. Edge processing

# This asynchronous function handles the connection and routing for a single ESP32 node
async def connect_to_device(mac_address, local_topic):
    print(f"[{mac_address}] Scanning...")
    
    # Outer infinite loop ensures the gateway never gives up if a sensor dies or goes out of range
    while True: 
        try:
            # Attempt to establish a physical BLE link with the target MAC address
            async with BleakClient(mac_address) as client:
                print(f"[{mac_address}] Connected.")
                
                # Inner loop runs continuously while the Bluetooth connection is active
                while True:
                    # Pull the raw bytes from the ESP32's Bluetooth characteristic and decode it to text
                    raw_data = await client.read_gatt_char(DATA_CHAR_UUID)
                    payload_str = raw_data.decode('utf-8')
                    
                    try:
                        # 1. Parse raw data from ESP32
                        json_data = json.loads(payload_str)
                        
                        # 2. Metadata injection
                        # Stamping the payload so the database knows exactly which piece of hardware sent it
                        json_data["mac_address"] = mac_address
                        
                        # Adds timestamp to data 
                        # Ensures all events have a unified UTC clock reference for the AWS data lake
                        json_data["timestamp"] = datetime.now(timezone.utc).isoformat()
                        
                        # 3. Repackage
                        # Turn the enriched dictionary back into a JSON string for transmission
                        enriched_payload = json.dumps(json_data)
                        
                        # 4. Route
                        # Fire the payload down both pipes simultaneously (Hot storage/UI + Cold storage)
                        local_client.publish(local_topic, enriched_payload)
                        aws_client.publish(AWS_TOPIC_TELEMETRY, enriched_payload, 1)
                        
                        print(f"ROUTED: {enriched_payload}")
                        
                  # Triggers if the incoming data isn't perfect JSON
                    except json.JSONDecodeError:
                        error_msg = f"Invalid JSON from {mac_address}"
                        timestamp_now = datetime.now(timezone.utc).isoformat()
                        
                        # 1. Package the alert as JSON for the Local Dashboard
                        local_alert_msg = json.dumps({
                            "message": error_msg,
                            "timestamp": timestamp_now
                        })
                        
                        # 2. Package the alert as JSON for AWS SNS Email
                        aws_alert_msg = json.dumps({
                            "default": f"GATEGUARD ALERT: {error_msg}",
                            "timestamp": timestamp_now
                        })
                        
                        # 3. Route to both systems
                        local_client.publish(ALERT_TOPIC, local_alert_msg)
                        aws_client.publish(AWS_TOPIC_ALERTS, aws_alert_msg, 1)
                        
                    # Brief pause prevents the while loop from eating up 100% of the Raspberry Pi's CPU
                    await asyncio.sleep(3)
                    
        # If the BLE connection drops, catch the error, wait 5 seconds, and try scanning again
        except Exception as e:
            await asyncio.sleep(5)


# 4. STARTUP

# The main function that orchestrates the concurrent workers
async def main():
    print(f"Starting GateGuard Edge Gateway...")
    
    # Create an independent connection task for every trusted device found in the config file
    tasks = [connect_to_device(mac, topic) for mac, topic in TRUSTED_DEVICES.items()]
    
    # Launch all tasks at the exact same time
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    # Boot up the Python asynchronous event loop
    asyncio.run(main())