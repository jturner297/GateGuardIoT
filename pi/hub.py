import asyncio
import json
import paho.mqtt.client as mqtt
from bleak import BleakClient
from datetime import datetime

# Creates MQTT client instance
mqtt_client = mqtt.Client() 
mqtt_client.connect("localhost", 1883)

# --- Trusted Devices Config ---
TRUSTED_DEVICES = {
    "68:FE:71:86:C0:66": "secureedge/node1/telemetry",
    "b0:cb:d8:cc:91:ca": "secureedge/node2/telemetry" 
}

DATA_CHAR_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a8"
# We will just connect to the first device in our list for this demo
TARGET_MAC = list(TRUSTED_DEVICES.keys())[1]

async def main():
    print(f"Starting SecureEdge Sensor-Agnostic Hub...")
    print(f"Scanning for Trusted Device: {TARGET_MAC}...")
    
    try:
        async with BleakClient(TARGET_MAC) as client:
            print(f"ALLOWED: Connected to Verified Device {TARGET_MAC}")
            
            while True:
                raw_data = await client.read_gatt_char(DATA_CHAR_UUID)
                payload_str = raw_data.decode('utf-8')
                
                # --- DATA SANITIZATION & GENERIC ROUTING ---
                try:
                    # 1. Try to parse it as JSON. If it's malicious garbage, it will fail here.
                    json_data = json.loads(payload_str)
                    
                    # 2. Get the correct MQTT topic for this specific MAC address
                    target_topic = TRUSTED_DEVICES[TARGET_MAC]
                    
                    # 3. Publish the generic JSON directly to the broker
                    mqtt_client.publish(target_topic, payload_str)
                    
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    print(f"[{timestamp}] FORWARDED VALID PAYLOAD: {payload_str}")
                    
                except json.JSONDecodeError:
                    # If a hacker tries to inject malformed code, drop it.
                    print("BLOCKED: Malformed payload detected. Dropping packet.")
                
                await asyncio.sleep(3)
                
    except Exception as e:
        print(f"BLOCKED/ERROR: Connection failed or device out of range.")
        print(f"    Reason: {e}")

if __name__ == "__main__":
    asyncio.run(main())