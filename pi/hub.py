import asyncio
import json
import paho.mqtt.client as mqtt
from bleak import BleakClient
from datetime import datetime

# --- LOAD CONFIGURATION ---
with open('config.json', 'r') as f:
    config = json.load(f)

MQTT_BROKER = config["mqtt"]["broker"]
MQTT_PORT = config["mqtt"]["port"]
DATA_CHAR_UUID = config["ble"]["data_char_uuid"]
TRUSTED_DEVICES = config["trusted_devices"]
ALERT_TOPIC = config["alert_topics"][0]

mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1) 
mqtt_client.connect(MQTT_BROKER, MQTT_PORT)

# --- THE CONCURRENT WORKER ---
# This function runs independently for every MAC address in your config
async def connect_to_device(mac_address, target_topic):
    print(f"[{mac_address}] Scanning for node...")
    
    while True: # Infinite retry loop in case the sensor loses power
        try:
            async with BleakClient(mac_address) as client:
                print(f"[{mac_address}] ALLOWED: Connected to Verified Device.")
                
                while True:
                    raw_data = await client.read_gatt_char(DATA_CHAR_UUID)
                    payload_str = raw_data.decode('utf-8')
                    
                    try:
                        # 1. Parse the raw JSON
                        json_data = json.loads(payload_str)
                        
                        # 2. METADATA STAMPING: Inject the MAC address into the payload for AWS
                        json_data["mac_address"] = mac_address
                        
                        # 3. Repackage the enriched JSON
                        enriched_payload = json.dumps(json_data)
                        
                        # 4. Ship it to the specific MQTT topic
                        mqtt_client.publish(target_topic, enriched_payload)
                        
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        print(f"[{timestamp}] [{mac_address}] FORWARDED: {enriched_payload}")
                        
                    except json.JSONDecodeError:
                        print(f"[{mac_address}] BLOCKED: Malformed payload detected.")
                        error_msg = f"Invalid JSON from {mac_address}"
                        mqtt_client.publish(ALERT_TOPIC, error_msg)
                        
                    await asyncio.sleep(3)
                    
        except Exception as e:
            # If it disconnects, wait 5 seconds and try to reconnect
            print(f"[{mac_address}] Disconnected or out of range. Retrying in 5s...")
            await asyncio.sleep(5)

async def main():
    print(f"Starting SecureEdge Hub in Multi-Node Mode...")
    print(f"Loaded {len(TRUSTED_DEVICES)} trusted devices from config.")
    
    # Create a list of independent tasks for every device in the config file
    tasks = []
    for mac, topic in TRUSTED_DEVICES.items():
        tasks.append(connect_to_device(mac, topic))
        
    # Launch all workers simultaneously
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())