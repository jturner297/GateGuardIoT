#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEServer.h>
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_MPU6050.h>

// Match these to the UUIDs in your partner's hub.py
#define SERVICE_UUID        "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define CHARACTERISTIC_UUID "beb5483e-36e1-4688-b7f5-ea07361b26a8"

Adafruit_MPU6050 mpu;
BLECharacteristic *pCharacteristic;
bool deviceConnected = false;

class MyServerCallbacks: public BLEServerCallbacks {
    void onConnect(BLEServer* pServer) { deviceConnected = true; }
    void onDisconnect(BLEServer* pServer) { deviceConnected = false; }
};

void setup() {
  Serial.begin(115200);

  // 1. Initialize MPU6050
  if (!mpu.begin()) {
    Serial.println("MPU6050 Error!");
    while (1);
  }

  // 2. Initialize BLE
  BLEDevice::init("SecureEdge_Node_1");
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
  BLEDevice::startAdvertising();
  Serial.println("SecureEdge Node 1 is Advertising...");
}

void loop() {
  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp);

  // Package Accel X, Y, Z into a proper JSON string
  String dataString = "{\"x\":" + String(a.acceleration.x) + ",\"y\":" + String(a.acceleration.y) + ",\"z\":" + String(a.acceleration.z) + "}";
  
  pCharacteristic->setValue(dataString.c_str());
  if (deviceConnected) {
    pCharacteristic->notify();
    Serial.println("Pushing Validated Telemetry: " + dataString);
  }
  delay(3000); 
}