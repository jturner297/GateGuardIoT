# Flask creates web server, render_template serves HTML file
# SocketIO allows for real time communication between server and browser
# Paho.mqtt.client allows Pi to connect to Mosquitto broker and receive messages
from flask import Flask, render_template
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt

# Creates instances of respective services
app = Flask(__name__)

# FIX: Explicitly set async_mode to 'threading'. 
# This forces SocketIO to listen to the MQTT background thread so the data actually escapes the Pi.
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Fixes the DeprecationWarning
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)

# Function that essentially allows for data to be separated into topics such as sensor data
def on_message(client, userdata, message):
    # Converts raw bytes from MQTT into readable string
    data = message.payload.decode('utf-8')
    
    # Check for either 'accel' or 'telemetry' just in case you bounce between hub scripts
    if message.topic == "secureedge/node1/telemetry" or message.topic == "secureedge/node2/telemetry":
        # Broadcasts the payload to the frontend
        socketio.emit('sensor_data', {'data': data})
        print(f"Pushed to UI: {data}")
        
    elif message.topic == "secureedge/node1/blockedattempts":
        # Sends blocked attempt data to browser 
        socketio.emit('blocked_attempts', {'data': data})
        print(f"Pushed Alert to UI: {data}")

# Instance of MQTT running locally via port 1883
mqtt_client.connect("localhost", 1883)
mqtt_client.on_message = on_message

# Subscribe to both nodes so you never miss data regardless of which ESP32 you use
mqtt_client.subscribe("secureedge/node1/telemetry")
mqtt_client.subscribe("secureedge/node2/telemetry")
mqtt_client.subscribe("secureedge/node1/blockedattempts")

mqtt_client.loop_start()

# Will be used for future html file rendering
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    print("Starting GateGuardIoT Web Server on Port 5000...")
    # HOST 0.0.0.0 IS REQUIRED TO VIEW DASHBOARD FROM YOUR DESKTOP
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
