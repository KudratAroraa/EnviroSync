#include <ArduinoBLE.h>
#include <DHT.h>
#include <WiFi.h>
#include <WiFiClient.h>

#define DHTPIN 2
#define DHTTYPE DHT22
DHT dht(DHTPIN, DHTTYPE);

#define AC_RELAY_PIN 4
#define HEATER_RELAY_PIN 3

//Wi-Fi Configuration
const char *ssid = "iQOO"; 
const char *password = "yay44444";  

//Socket Configuration
const char *server_ip = "192.168.31.71";  // Raspberry Pi's IP
const int server_port = 5000;  //Port for communication

WiFiServer server(server_port);
WiFiClient socketClient;

//BLE Service and Characteristics
BLEService enviroService("180C");
BLEStringCharacteristic enviroDataCharacteristic("2A57", BLERead | BLENotify, 20);

BLEService controlService("180D");
BLEStringCharacteristic controlCharacteristic("2A58", BLEWrite, 20);

void setup() {
  Serial.begin(9600);
  while (!Serial);

  //Start Wi-Fi connection
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.print(".");
  }
  Serial.println("Connected to Wi-Fi!");

  //Start Wi-Fi server
  server.begin();
  Serial.println("Wi-Fi server started.");

  //Initialize BLE
  if (!BLE.begin()) {
    Serial.println("Starting BLE failed!");
    while (1);
  }

  BLE.setLocalName("EnviroSync");

  enviroService.addCharacteristic(enviroDataCharacteristic);
  controlService.addCharacteristic(controlCharacteristic);

  BLE.addService(enviroService);
  BLE.addService(controlService);

  BLE.advertise();
  Serial.println("Bluetooth device active, waiting for connections...");

  dht.begin();

  //Initialize relay pins
  pinMode(AC_RELAY_PIN, OUTPUT);
  pinMode(HEATER_RELAY_PIN, OUTPUT);

  //Set relay pins to HIGH (off)
  digitalWrite(AC_RELAY_PIN, HIGH);
  digitalWrite(HEATER_RELAY_PIN, HIGH);
}

void loop() {
  //Check for BLE connection
  BLEDevice central = BLE.central();

  if (central) {
    Serial.print("Connected to central: ");
    Serial.println(central.address());

    while (central.connected()) {
      //Read and send sensor data over BLE
      float temperature = dht.readTemperature();
      float humidity = dht.readHumidity();

      if (!isnan(temperature) && !isnan(humidity)) {
        String data = String(temperature) + "," + String(humidity);
        enviroDataCharacteristic.writeValue(data.c_str());
        Serial.print("Sending --> Temperature: ");
        Serial.print(temperature);
        Serial.print(" C, Humidity: ");
        Serial.println(humidity);
      } else {
        Serial.println("Reading from DHT sensor.");
      }

      //Check for incoming BLE commands
      if (controlCharacteristic.written()) {
        String command = controlCharacteristic.value();
        handleCommand(command);
      }
      delay(2000);
    }

    Serial.print("Disconnected from central: ");
    Serial.println(central.address());
  }

  //Handle Socket Communication (if BLE fails)
  if (WiFi.status() == WL_CONNECTED) {
    if (!socketClient.connected()) {
      Serial.println("Connecting to Raspberry Pi server...");
      socketClient.connect(server_ip, server_port);
      if (socketClient.connected()) {
        Serial.println("Connected to Raspberry Pi server!");
      } else {
        Serial.println("Failed to connect to Raspberry Pi server.");
      }
    }

    if (socketClient.connected()) {
      //Send sensor data over socket
      float temperature = dht.readTemperature();
      float humidity = dht.readHumidity();

      if (!isnan(temperature) && !isnan(humidity)) {
        String data = String(temperature) + "," + String(humidity);
        socketClient.println(data);
        Serial.print("Sending data over socket --> Temperature: ");
        Serial.print(temperature);
        Serial.print(" C, Humidity: ");
        Serial.println(humidity);
      } else {
        Serial.println("Error reading sensor data.");
      }

      //Check for incoming socket commands
      if (socketClient.available()) {
        String command = socketClient.readStringUntil('\n');
        handleCommand(command);
      }
    }
  }
}

void handleCommand(String command) {
  if (command == "AC_ON") {
    digitalWrite(AC_RELAY_PIN, LOW); //Turn AC ON
    Serial.println("AC is ON");
  } else if (command == "AC_OFF") {
    digitalWrite(AC_RELAY_PIN, HIGH); //Turn AC OFF
    Serial.println("AC is OFF");
  } else if (command == "HEATER_ON") {
    digitalWrite(HEATER_RELAY_PIN, LOW); //Turn Heater ON
    Serial.println("Heater is ON");
  } else if (command == "HEATER_OFF") {
    digitalWrite(HEATER_RELAY_PIN, HIGH); //Turn Heater OFF
    Serial.println("Heater is OFF");
  }
}
