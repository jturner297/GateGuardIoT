# flask handles the web server and routing
# flask_socketio allows the server to push real-time updates to your HTML page
# paho.mqtt.client allows this script to listen to the Mosquitto broker fed by your bridge script
# json and os handle the config loading and data parsing
from flask import Flask, render_template
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt
import json
import os


# 1. DYNAMIC CONFIGURATION

# Smart Config Loader: Checks local folder first, then parent folder
config_path = 'config.json'
if not os.path.exists(config_path):
    config_path = '../config.json'

# --- LOAD CONFIGURATION ---
with open(config_path, 'r') as f:
    config = json.load(f)

# Extract Flask parameters from your config
FLASK_HOST = config["flask"]["host"]
FLASK_PORT = config["flask"]["port"]

# Extract Local MQTT parameters
LOCAL_BROKER = config["mqtt"]["broker"]
LOCAL_PORT = config["mqtt"]["port"]

# Extract topics for the dashboard to monitor
TRUSTED_DEVICES = config["trusted_devices"]
TELEMETRY_TOPICS = list(TRUSTED_DEVICES.values()) # ["secureedge/node1/telemetry", ...]
ALERT_TOPIC = config["alert_topics"][0]           # "secureedge/node1/blockedattempts"


# 2. FLASK & SOCKET.IO SETUP

app = Flask(__name__)
app.config['SECRET_KEY'] = 'gateguard_secret!'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

@app.route('/')
def index():
    # This serves your 'index.html' file located in the /templates folder
    return render_template('index.html')


# 3. MQTT SUBSCRIBER (THE LISTENER)


def on_connect(client, userdata, flags, rc):
    print(f"Dashboard connected to Mosquitto at {LOCAL_BROKER} with result code {rc}")
    
    # Subscribe to the telemetry topics for every node in your config
    for topic in TELEMETRY_TOPICS:
        client.subscribe(topic)
        print(f"Subscribing to Telemetry Topic: {topic}")
    
    # Subscribe to the security alert topic
    client.subscribe(ALERT_TOPIC)
    print(f"Subscribing to Alert Topic: {ALERT_TOPIC}")

def on_message(client, userdata, msg):
    # This triggers when the Bridge script publishes data to Mosquitto
    try:
        payload_str = msg.payload.decode('utf-8')
        data = json.loads(payload_str)
        

        # We need to emit the specific event name the HTML script is listening for
        
        if msg.topic == ALERT_TOPIC:
            print(f"ALERT RECEIVED on {msg.topic}")
            # Emits 'blocked_attempts' to match your HTML's socket.on('blocked_attempts')
            socketio.emit('blocked_attempts', {'data': data})
        
        elif msg.topic in TELEMETRY_TOPICS:
            print(f"DATA RECEIVED on {msg.topic}")
            # Emits 'sensor_data' to match your HTML's socket.on('sensor_data')
            socketio.emit('sensor_data', {'data': data})
            
    except Exception as e:
        print(f"Error processing dashboard data: {e}")

# Initialize the MQTT client for the Flask backend
dashboard_mqtt = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
dashboard_mqtt.on_connect = on_connect
dashboard_mqtt.on_message = on_message


# 4. SYSTEM BOOTSTRAP
if __name__ == "__main__":
    # 1. Connect to the local broker
    dashboard_mqtt.connect(LOCAL_BROKER, LOCAL_PORT, 60)
    
    # 2. Start the MQTT loop in a background thread
    dashboard_mqtt.loop_start()
    
    # 3. Launch the Web Server using your config.json values
    print(f"GateGuard Dashboard launching on http://{FLASK_HOST}:{FLASK_PORT}")
    socketio.run(app, host=FLASK_HOST, port=FLASK_PORT, debug=False)