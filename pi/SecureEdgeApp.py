# Flask creates web server, render_template serves HTML file
# SocketIO allows for real time communication between server and browser
# Paho.mqtt.client allows Pi to connect to Mosquitto broker and receive messages
from flask import Flask, render_template
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt

# Creates instances of respective services
app = Flask(__name__)
socketio= SocketIO(app)
mqtt_client = mqtt.Client()

# Function that essentially allows for data to be seperated into topics such as sensor data
def on_message(client, userdata, message):
	# Converts raw bytes from MQTT into readable string
	data = message.payload.decode('utf-8')
	if message.topic == "secureedge/node1/accel":
		# Sends valid data to browser
		socketio.emit('sensor_data', data)
	else:
		# Sends blocked attempt data to browser 
		socketio.emit('blocked_attempts', data)

# Instance of MQTT running locally via port 1883 utilizing function on_message, subscribes to topics while running continuously via loop
mqtt_client.connect("localhost", 1883)
mqtt_client.on_message = on_message
mqtt_client.subscribe("secureedge/node1/accel")
mqtt_client.subscribe("secureedge/node1/blockedattempts")
mqtt_client.loop_start()

# Will be used for future html file rendering
@app.route('/')
def index():
	return render_template('index.html')

socketio.run(app)





