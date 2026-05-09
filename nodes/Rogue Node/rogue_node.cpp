#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

// Import our configuration variables
#include "secrets.h"

BLEServer* pServer = NULL;
BLECharacteristic* pCharacteristic = NULL;
bool deviceConnected = false;

// Callbacks to monitor when the Pi connects and disconnects
class MyServerCallbacks: public BLEServerCallbacks {
    void onConnect(BLEServer* pServer) {
      deviceConnected = true;
      Serial.println("Gateway Connected. Commencing attack...");
    };
    void onDisconnect(BLEServer* pServer) {
      deviceConnected = false;
      Serial.println("Gateway Disconnected. Restarting scan beacon...");
      BLEDevice::startAdvertising(); 
    }
};

void setup() {
  Serial.begin(115200);

  // Initialize the BLE device with a suspicious name
  BLEDevice::init("ESP32_ROGUE_NODE");

  // Create the BLE Server and bind the callbacks
  pServer = BLEDevice::createServer();
  pServer->setCallbacks(new MyServerCallbacks());

  // Create the BLE Service
  BLEService *pService = pServer->createService(SERVICE_UUID);

  // Create a BLE Characteristic (Read and Notify permissions)
  pCharacteristic = pService->createCharacteristic(
                      CHARACTERISTIC_UUID,
                      BLECharacteristic::PROPERTY_READ   |
                      BLECharacteristic::PROPERTY_NOTIFY
                    );

  pCharacteristic->addDescriptor(new BLE2902());
  pService->start();

  // Start broadcasting so the Pi can find it
  BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pAdvertising->setScanResponse(false);
  pAdvertising->setMinPreferred(0x0);
  BLEDevice::startAdvertising();
  
  Serial.println("Rogue Node Active.");
  Serial.println("Waiting for Raspberry Pi Gateway to connect...");
}

void loop() {
  if (deviceConnected) {
    // ==========================================
    // THE MALICIOUS PAYLOAD
    // Notice there are no closing quotes or brackets. 
    // This intentionally triggers the JSONDecodeError on the Pi.
    // ==========================================
    String roguePayload = "{MALICIOUS_INJECTION_ATTACK_0x99";

    // Convert the string to standard characters and broadcast it
    pCharacteristic->setValue(roguePayload.c_str());
    pCharacteristic->notify();

    Serial.println("Sent rogue payload: " + roguePayload);
    
    // Fire the bad data every 3 seconds to flood the dashboard
    delay(3000); 
  }
}