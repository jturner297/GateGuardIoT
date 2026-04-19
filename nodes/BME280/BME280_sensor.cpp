#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEServer.h>
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>

// Unique IDs for the BLE Service and Data Characteristic
// Pi will look for these specific IDs
#define SERVICE_UUID        "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define CHARACTERISTIC_UUID "beb5483e-36e1-4688-b7f5-ea07361b26a8"

Adafruit_BME280 bme;
BLECharacteristic *pCharacteristic;
bool deviceConnected = false;

// Callback to track if the Pi has connected to us
class MyServerCallbacks: public BLEServerCallbacks {
    void onConnect(BLEServer* pServer) { deviceConnected = true; };
    void onDisconnect(BLEServer* pServer) { deviceConnected = false; }
};

void setup() {
  Serial.begin(115200);

  // 1. Initialize BME280
  if (!bme.begin(0x76)) {
    Serial.println("BME280 error!");
    while (1);
  }

  // 2. Initialize BLE
  BLEDevice::init("BME280_SensorNode"); // This is the name the Pi will see
  BLEServer *pServer = BLEDevice::createServer();
  pServer->setCallbacks(new MyServerCallbacks());

  // 3. Create the Service and Characteristic
  BLEService *pService = pServer->createService(SERVICE_UUID);
  pCharacteristic = pService->createCharacteristic(
                      CHARACTERISTIC_UUID,
                      BLECharacteristic::PROPERTY_READ |
                      BLECharacteristic::PROPERTY_NOTIFY
                    );

  pService->start();

  // 4. Start Advertising (broadcasting its presence)
  BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pAdvertising->setScanResponse(true);
  pAdvertising->setMinPreferred(0x06);  
  pAdvertising->setMinPreferred(0x12);
  BLEDevice::startAdvertising();
  Serial.println("BLE Server started. Advertising as 'SecureEdge_Node_1'...");
}

void loop() {
  // Read sensor data
  float t = 1.8 * bme.readTemperature() + 32;
  float h = bme.readHumidity();
  float p = bme.readPressure() / 100.0F;

  // Create a data string: "Temp,Hum,Pres"
String dataString = "{\"sensor\":\"BME280\", \"temperature\":" + String(t) + ", \"humidity\":" + String(h) + ", \"pressure\":" + String(p) + "}";
  
  // Update the BLE value
  pCharacteristic->setValue(dataString.c_str());
  pCharacteristic->notify(); // Push data to the Pi if it's listening

  Serial.println("Broadcasting BLE Data: " + dataString);
  delay(3000);
}