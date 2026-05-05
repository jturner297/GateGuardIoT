import paho.mqtt.client as local_mqtt
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import json
import logging
import time

# ==========================================
# CONFIGURATION - UPDATE THESE VALUES
# ==========================================
# 1. You can find this endpoint in AWS IoT Core -> Settings -> "Device data endpoint"
AWS_ENDPOINT = "aom6z3jtu7isf-ats.iot.us-east-2.amazonaws.com"

# 2. Make sure these match the exact filenames you downloaded from AWS
# Note: You need to transfer these files to the Pi and put them in a folder called 'certs'
PATH_TO_CERT = "/home/jesseg25/GateGuardIoT/certs/GateGuardIoT-certificate.pem.crt"
PATH_TO_KEY = "/home/jesseg25/GateGuardIoT/certs/GateGuardIoT-private.pem.key"
PATH_TO_ROOT = "/home/jesseg25/GateGuardIoT/certs/AmazonRootCA1.pem"

CLIENT_ID = "GateGuardIoT_Hub"
AWS_TOPIC = "gateguard/cloud/telemetry"
LOCAL_TOPIC = "secureedge/node2/telemetry" # Listening to the exact topic your hub.py publishes to

# Set up logging for AWS
logger = logging.getLogger("AWSIoTPythonSDK.core")
logger.setLevel(logging.ERROR)
streamHandler = logging.StreamHandler()
logger.addHandler(streamHandler)

# ==========================================
# AWS CLOUD MQTT CLIENT SETUP
# ==========================================
print("Initializing AWS IoT Core connection...")
myAWSIoTMQTTClient = AWSIoTMQTTClient(CLIENT_ID)
myAWSIoTMQTTClient.configureEndpoint(AWS_ENDPOINT, 8883)
myAWSIoTMQTTClient.configureCredentials(PATH_TO_ROOT, PATH_TO_KEY, PATH_TO_CERT)

# AWSIoTMQTTClient connection configuration
myAWSIoTMQTTClient.configureAutoReconnectBackoffTime(1, 32, 20)
myAWSIoTMQTTClient.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
myAWSIoTMQTTClient.configureDrainingFrequency(2)  # Draining: 2 Hz
myAWSIoTMQTTClient.configureConnectDisconnectTimeout(10)  # 10 sec
myAWSIoTMQTTClient.configureMQTTOperationTimeout(5)  # 5 sec

print(f"Connecting to AWS Endpoint: {AWS_ENDPOINT}...")
myAWSIoTMQTTClient.connect()
print("SUCCESS: Connected to AWS Cloud Broker.")

# ==========================================
# LOCAL MQTT CLIENT SETUP (THE BRIDGE)
# ==========================================
def on_local_message(client, userdata, message):
    """
    This function triggers every time your local hub.py validates a BLE packet
    and publishes it to the local Mosquitto broker.
    It grabs that data and immediately forwards it to AWS.
    """
    payload = message.payload.decode('utf-8')
    print(f"[BRIDGE] Intercepted local payload: {payload}")
    
    try:
        # Publish to the cloud
        myAWSIoTMQTTClient.publish(AWS_TOPIC, payload, 1)
        print(f"[BRIDGE] Successfully pushed to AWS IoT Core -> {AWS_TOPIC}")
    except Exception as e:
        print(f"[BRIDGE] ERROR pushing to AWS: {e}")

local_client = local_mqtt.Client(local_mqtt.CallbackAPIVersion.VERSION1)
local_client.on_message = on_local_message

print(f"Connecting to Local Mosquitto Broker...")
local_client.connect("localhost", 1883)
local_client.subscribe(LOCAL_TOPIC)

print(f"Bridge Active. Listening on local topic '{LOCAL_TOPIC}' and forwarding to AWS.")
print("=============================================================================")

# Keep the script running forever
local_client.loop_forever()