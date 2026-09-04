# GateGuard IoT
An ethical-by-design edge computing hub that shifts the security responsibility from the edge to the cloud. The system continuously monitors for network intrusions locally, ensuring that only sanitized data utilizes cloud computing for analytics.

**Developed by:** Justin Turner and Jesse Garcia

## Motivation & Problem
* Conventional smart home devices rely too heavily on the Cloud for security.
* Resource-constrained sensors send unencrypted data directly to corporate servers, creating a massive digital attack surface.
* The lack of localized defenses leaves home networks vulnerable to devastating Man-in-the-Middle attacks.

## System Architecture
* **Perception Nodes (ESP32):** Microcontrollers collect raw sensor data and transmit it via local Bluetooth (BLE). They use custom GATT characteristics to establish a stable connection between the sensors and the hub.
* **Zero-Trust Gateway (Raspberry Pi 3B):** Acts as a local firewall and data gatekeeper. The `GateGuardGateway.py` script validates MAC addresses, drops malformed data, and formats raw data into secure, sensor-agnostic JSON payloads.
* **Local Dashboard:** A local Mosquitto MQTT broker feeds a custom Flask/Socket.IO web dashboard (`SecureEdgeApp.py`), providing zero-latency visual monitoring of accepted telemetry and blocked network attacks.
* **Cloud Ingestion:** Verified data is pushed to AWS IoT Core via encrypted MQTT, while rogue payloads at the edge trigger automated AWS SNS security alerts
* **Dual-Tier Storage:** AWS DynamoDB manages high-speed data for real-time querying, while Amazon S3 provides low-cost, long-term archiving
* **Data Visualization:** Grafana directly queries the AWS database to translate raw cloud JSON into dynamic, multi-axis trend charts

## Hardware Nodes
* **BME280 Node:** Captures temperature, humidity, and pressure
* **MPU6050 Node:** Captures accelerometer data 
* **Attack Node:** Runs rogue attack script to simulate attacks and test the gateway's active defenses
