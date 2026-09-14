from flask import Flask, render_template
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt
import json

# --- LOAD CONFIGURATION ---
with open('config.json', 'r') as f:
    config = json.load(f)

app = Flask(__name__)
socketio = SocketIO(app, async_mode='threading')
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)

# Extract telemetry topics from the trusted_devices dictionary values
TELEMETRY_TOPICS = list(config["trusted_devices"].values())
ALERT_TOPICS = config["alert_topics"]

def on_message(client, userdata, message):
    data = message.payload.decode('utf-8')
    
    if message.topic in TELEMETRY_TOPICS:
        socketio.emit('sensor_data', {'data': data})
        print(f"Pushed to UI: {data}")
    elif message.topic in ALERT_TOPICS:
        socketio.emit('blocked_attempts', {'data': data})
        print(f"Pushed Alert to UI: {data}")

mqtt_client.connect(config["mqtt"]["broker"], config["mqtt"]["port"])
mqtt_client.on_message = on_message

# Dynamically subscribe to all valid topics
for topic in TELEMETRY_TOPICS + ALERT_TOPICS:
    mqtt_client.subscribe(topic)

mqtt_client.loop_start()

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    port = config["flask"]["port"]
    host = config["flask"]["host"]
    print(f"Starting Flask Web Server on Port {port}...")
    socketio.run(app, host=host, port=port, debug=True)