# Flask creates web server, render_template serves HTML file
# SocketIO allows for real time communication between server and browser
# Paho.mqtt.client allows Pi to connect to Mosquitto broker and receive messages
from flask import Flask, render_template
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt
import json

# --- LOAD CONFIGURATION ---
with open('config.json', 'r') as f:
    config = json.load(f)

# Creates instances of respective services
app = Flask(__name__)

# FIX: Explicitly set async_mode to 'threading'. 
# This forces SocketIO to listen to the MQTT background thread so the data actually escapes the Pi.
# The cors_allowed_origins="*" allows your external desktop browser to connect.
# Fixes the DeprecationWarning
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)

# Function that essentially allows for data to be separated into topics such as sensor data
# Extract telemetry topics from the trusted_devices dictionary values
TELEMETRY_TOPICS = list(config["trusted_devices"].values())
ALERT_TOPICS = config["alert_topics"]

def on_message(client, userdata, message):
    # Converts raw bytes from MQTT into readable string
    data = message.payload.decode('utf-8')
    
    # Check for either 'accel' or 'telemetry' just in case you bounce between hub scripts
    # Broadcasts the payload to the frontend
    if message.topic in TELEMETRY_TOPICS:
        socketio.emit('sensor_data', {'data': data})
        print(f"Pushed to UI: {data}")
        
    # Sends blocked attempt data to browser 
    elif message.topic in ALERT_TOPICS:
        socketio.emit('blocked_attempts', {'data': data})
        print(f"Pushed Alert to UI: {data}")

# Instance of MQTT running locally via port 1883
# Now dynamically pulls broker and port from config.json
mqtt_client.connect(config["mqtt"]["broker"], config["mqtt"]["port"])
mqtt_client.on_message = on_message

# Subscribe to both nodes so you never miss data regardless of which ESP32 you use
# Dynamically subscribe to all valid topics
for topic in TELEMETRY_TOPICS + ALERT_TOPICS:
    mqtt_client.subscribe(topic)

mqtt_client.loop_start()

# Will be used for future html file rendering
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    port = config["flask"]["port"]
    host = config["flask"]["host"]
    
    print(f"Starting GateGuardIoT Web Server on Port {port}...")
    # HOST 0.0.0.0 IS REQUIRED TO VIEW DASHBOARD FROM YOUR DESKTOP
    socketio.run(app, host=host, port=port, debug=True)