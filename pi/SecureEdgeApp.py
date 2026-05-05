# Flask creates web server, render_template serves HTML file
# SocketIO allows for real time communication between server and browser
# Paho.mqtt.client allows Pi to connect to Mosquitto broker and receive messages
from flask import Flask, render_template
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt

# Creates instances of respective services
app = Flask(__name__)
socketio = SocketIO(app, async_mode='threading')

# Fixes the DeprecationWarning
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)

# Function that essentially allows for data to be seperated into topics such as sensor data
def on_message(client, userdata, message):
	# Converts raw bytes from MQTT into readable string
    data = message.payload.decode('utf-8')
    
    # Updated to catch Node 2!
    if message.topic == "secureedge/node1/telemetry" or message.topic == "secureedge/node2/telemetry":
		# Sends valid data to browser
        socketio.emit('sensor_data', {'data': data})
        print(f"Pushed to UI: {data}")
    elif message.topic == "secureedge/node1/blockedattempts":
		# Sends blocked attempt data to browser 
        socketio.emit('blocked_attempts', {'data': data})
        print(f"Pushed Alert to UI: {data}")


# Instance of MQTT running locally via port 1883 utilizing function on_message, subscribes to topics while running continuously via loop
mqtt_client.connect("localhost", 1883)
mqtt_client.on_message = on_message

# Subscribe to both nodes so you never miss data regardless of which ESP32 you use
mqtt_client.subscribe("secureedge/node1/telemetry")
mqtt_client.subscribe("secureedge/node2/telemetry")
mqtt_client.subscribe("secureedge/node1/blockedattempts")

mqtt_client.loop_start()

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    print("Starting Flask Web Server on Port 5000...")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)