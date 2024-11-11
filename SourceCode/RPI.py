import asyncio
from bleak import BleakClient, BleakError
import pyrebase

#Firebase configuration
firebaseConfig = {
    "apiKey": "AIzaSyBhty7aB9lirwmq4VUcB8TIF1bohg8JFag",
    "authDomain": "envirosync-7c7b5.firebaseapp.com",
    "databaseURL": "https://envirosync-7c7b5-default-rtdb.firebaseio.com",
    "projectId": "envirosync-7c7b5",
    "storageBucket": "envirosync-7c7b5.appspot.com",
    "messagingSenderId": "645755185917",
    "appId": "1:645755185917:web:5a364e74be3eedbfd4ec94",
    "measurementId": "G-ZHCJ67WJB6"
}

#Initialize Firebase
firebase = pyrebase.initialize_app(firebaseConfig)
db = firebase.database()

#Arduino BLE address and UUIDs
arduino_address = "40:91:51:A4:0F:02"
SERVICE_UUID_CONTROL = "180D"
CHARACTERISTIC_UUID_CONTROL = "2A58"
SERVICE_UUID_ENVIRONMENT = "180C"
CHARACTERISTIC_UUID_ENVIRONMENT = "2A57"

#Queue for storing commands from Firebase
command_queue = asyncio.Queue()

def firebase_listener():
    """
    Firebase listener function that adds commands to the asyncio queue.
    This function is called synchronously by Pyrebase.
    """
    def stream_handler(message):
        data = message["data"]

        #Process command and enqueue it
        if isinstance(data, dict):
            if "AC" in data:
                command = "AC_ON" if data["AC"] else "AC_OFF"
                asyncio.run_coroutine_threadsafe(command_queue.put(command), loop)
                print(f"Received Firebase command: {command}")

            if "Heater" in data:
                command = "HEATER_ON" if data["Heater"] else "HEATER_OFF"
                asyncio.run_coroutine_threadsafe(command_queue.put(command), loop)
                print(f"Received Firebase command: {command}")

        elif isinstance(data, bool):
            last_device = message["path"].strip("/")
            if last_device == "AC":
                command = "AC_ON" if data else "AC_OFF"
                asyncio.run_coroutine_threadsafe(command_queue.put(command), loop)
                print(f"Received Firebase command: {command}")
            elif last_device == "Heater":
                command = "HEATER_ON" if data else "HEATER_OFF"
                asyncio.run_coroutine_threadsafe(command_queue.put(command), loop)
                print(f"Received Firebase command: {command}")

    #Start the Firebase stream
    db.child("EnviroSync").stream(stream_handler)
    
async def process_commands(client):
    """
    Processes commands from the queue and sends them to the Arduino.
    """
    while True:
        command = await command_queue.get()  #Wait for command
        if client.is_connected:
            await client.write_gatt_char(CHARACTERISTIC_UUID_CONTROL, command.encode())
            print(f"Command '{command}' successfully sent to Arduino.")
        command_queue.task_done()
        
async def main():
    """
    Main loop to connect to Arduino, start command processing, and handle sensor data.
    """
    #Start Firebase listener in a separate thread
    firebase_listener()

    while True:
        try:
            #Connect to Arduino
            async with BleakClient(arduino_address, timeout=30.0) as client:
                print("Connected to Arduino.")

                # Start processing commands in the background
                asyncio.create_task(process_commands(client))

                #Notification handler for BLE updates from Arduino
                def notification_handler(sender, data):
                    try:
                        data_str = data.decode("utf-8")
                        temperature, humidity = data_str.split(",")
                        print(f"Received from Arduino - Temperature: {temperature}, Humidity: {humidity}")

                        #Update Firebase with new readings
                        db.child("EnviroSync").update({
                            "temperature": float(temperature),
                            "humidity": float(humidity)
                        })
                    except Exception as e:
                        print("Error decoding notification:", e)

                #Subscribe to notifications from Arduino
                await client.start_notify(CHARACTERISTIC_UUID_ENVIRONMENT, notification_handler)

                #Keep the connection alive
                while client.is_connected:
                    await asyncio.sleep(1)

        except (BleakError, TimeoutError) as e:
            print(f"Connection failed: {e}. Retrying in 5 seconds...") #Fail safe Mechanism
            await asyncio.sleep(5)

# Start the main event loop
loop = asyncio.get_event_loop()
loop.run_until_complete(main())
