#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEServer.h>
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_MPU6050.h>

// Match these to the UUIDs in your config.json / hub script
#define SERVICE_UUID        "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define CHARACTERISTIC_UUID "beb5483e-36e1-4688-b7f5-ea07361b26a8"

Adafruit_MPU6050 mpu;
BLECharacteristic *pCharacteristic;
bool deviceConnected = false;

// Callback to track if the Pi has connected to us and handle disconnects
class MyServerCallbacks: public BLEServerCallbacks {
    void onConnect(BLEServer* pServer) { 
        deviceConnected = true; 
    };
    
    void onDisconnect(BLEServer* pServer) { 
        deviceConnected = false; 
     
        // Restarts advertising when the Pi disconnects or reboots
        delay(500); // Give the Bluetooth radio a half-second to reset
        pServer->startAdvertising(); 
        Serial.println("Connection dropped! Restarting BLE Advertising...");
    }
};

void setup() {
  Serial.begin(115200);

  // 1. Initialize MPU6050
  if (!mpu.begin()) {
    Serial.println("MPU6050 Error! Check wiring.");
    while (1);
  }
  
  // Optional: Set MPU ranges for better kinematic data capture
  mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
  mpu.setGyroRange(MPU6050_RANGE_500_DEG);
  mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);

  // 2. Initialize BLE
  BLEDevice::init("MPU6050_SensorNode"); // Updated to differentiate from BME node
  BLEServer *pServer = BLEDevice::createServer();
  pServer->setCallbacks(new MyServerCallbacks());

  // 3. Create Service and Characteristic
  BLEService *pService = pServer->createService(SERVICE_UUID);
  pCharacteristic = pService->createCharacteristic(
                        CHARACTERISTIC_UUID,
                        BLECharacteristic::PROPERTY_READ |
                        BLECharacteristic::PROPERTY_NOTIFY
                      );
  pService->start();

  // 4. Start Advertising
  BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pAdvertising->setScanResponse(true);
  pAdvertising->setMinPreferred(0x06);  
  pAdvertising->setMinPreferred(0x12);
  BLEDevice::startAdvertising();
  Serial.println("SecureEdge Node (MPU6050) is Advertising...");
}

void loop() {
  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp);

  
  // Added the "sensor":"MPU6050" key to match the BME280 format
  String dataString = "{\"sensor\":\"MPU6050\", \"x\":" + String(a.acceleration.x) + ", \"y\":" + String(a.acceleration.y) + ", \"z\":" + String(a.acceleration.z) + "}";
  
  pCharacteristic->setValue(dataString.c_str());
  

  // Only push data to the Bluetooth stack if the gateway is actively listening
  if (deviceConnected) {
    pCharacteristic->notify();
    Serial.println("Pushing Validated Telemetry: " + dataString);
  } else {
    Serial.println("Waiting for Edge Hub to connect...");
  }
  
  delay(3000); 
}