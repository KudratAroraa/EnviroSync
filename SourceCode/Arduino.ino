#include <ArduinoBLE.h>
#include <DHT.h>

//pin configurations
#define DHTPIN 2
#define DHTTYPE DHT22
DHT dht(DHTPIN, DHTTYPE);

#define AC_RELAY_PIN 4
#define HEATER_RELAY_PIN 3

//BLE Service and Characteristics
BLEService enviroService("180C");
BLEStringCharacteristic enviroDataCharacteristic("2A57", BLERead | BLENotify, 20);

BLEService controlService("180D");
BLEStringCharacteristic controlCharacteristic("2A58", BLEWrite, 20);

void setup() 
{
  Serial.begin(9600);

  if (!BLE.begin()) {
    Serial.println("Starting BLE failed!");
    while (1);
  }

  BLE.setLocalName("EnviroSync");

  enviroService.addCharacteristic(enviroDataCharacteristic);
  controlService.addCharacteristic(controlCharacteristic);

  BLE.addService(enviroService);
  BLE.addService(controlService);

  //Advertising the Service  
  BLE.advertise();
  Serial.println("Bluetooth device active, waiting for connections...");

  dht.begin();
  
  //Initialize relay pins
  pinMode(AC_RELAY_PIN, OUTPUT);
  pinMode(HEATER_RELAY_PIN, OUTPUT);

  //setting relay pins to HIGH (off)
  digitalWrite(AC_RELAY_PIN, HIGH);
  digitalWrite(HEATER_RELAY_PIN, HIGH);
}

void loop() 
{
  BLEDevice central = BLE.central();

  if (central) 
  {
    Serial.print("Connected to central: ");
    Serial.println(central.address());

    while (central.connected()) 
    {
      //1. Read and Send Sensor Data
      float temperature = dht.readTemperature();
      float humidity = dht.readHumidity();

      //Sending Data over BLE by writing value in characteristic
      if (!isnan(temperature) && !isnan(humidity)) 
      {
        String data = String(temperature) + "," + String(humidity);
        enviroDataCharacteristic.writeValue(data.c_str());
        Serial.print("Sending --> Temperature: ");
        Serial.print(temperature);
        Serial.print(" C, Humidity: ");
        Serial.println(humidity);
      } else 
      {
        Serial.println("Reading from DHT sensor.");
      }

      //2. Check for Received Commands
      if (controlCharacteristic.written()) 
      {  //only act if a command was received or written in characteristic
        String command = controlCharacteristic.value();
        if (command == "AC_ON") 
        {
          digitalWrite(AC_RELAY_PIN, LOW); //Turn AC ON
          Serial.println("AC is ON");
        } else if (command == "AC_OFF") 
        {
          digitalWrite(AC_RELAY_PIN, HIGH); //Turn AC OFF
          Serial.println("AC is OFF");
        } else if (command == "HEATER_ON") 
        {
          digitalWrite(HEATER_RELAY_PIN, LOW); //Turn Heater ON
          Serial.println("Heater is ON");
        } else if (command == "HEATER_OFF") 
        {
          digitalWrite(HEATER_RELAY_PIN, HIGH); //Turn Heater OFF
          Serial.println("Heater is OFF");
        }
      }

      delay(2000); 
    }
    
    Serial.print("Disconnected from central: ");
    Serial.println(central.address());
  }
}