import asyncio
import socket
from bleak import BleakClient, BleakError
import pyrebase
import threading

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

# Arduino BLE address and UUIDs
arduino_address = "40:91:51:A4:0F:02"
SERVICE_UUID_CONTROL = "180D"
CHARACTERISTIC_UUID_CONTROL = "2A58"
SERVICE_UUID_ENVIRONMENT = "180C"
CHARACTERISTIC_UUID_ENVIRONMENT = "2A57"

# IP address and port for socket communication
IP_ADDRESS = '192.168.31.71'
PORT = 5000

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

    #Start Firebase stream
    db.child("EnviroSync").stream(stream_handler)

async def process_commands(client=None, socket_connection=None):
    """
    Processes commands from the queue and sends them to the Arduino via BLE or socket.
    """
    while True:
        command = await command_queue.get()  #Wait for command
        try:
            if client and client.is_connected:
                #Send command via Bluetooth
                await client.write_gatt_char(CHARACTERISTIC_UUID_CONTROL, command.encode())
                print(f"Command '{command}' sent to Arduino via Bluetooth.")
            elif socket_connection:
                #Send command via IP socket
                socket_connection.sendall(command.encode())
                print(f"Command '{command}' sent to Arduino via IP socket.")
        except Exception as e:
            print(f"Error sending command '{command}': {e}")
        command_queue.task_done()

async def bluetooth_connection():
    """
    Connect to the Arduino via Bluetooth and process commands.
    """
    try:
        async with BleakClient(arduino_address, timeout=30.0) as client:
            print("Connected to Arduino via Bluetooth.")

            # Start processing commands in the background
            asyncio.create_task(process_commands(client=client))

            # Notification handler for BLE updates from Arduino
            def notification_handler(sender, data):
                try:
                    data_str = data.decode("utf-8")
                    temperature, humidity = data_str.split(",")
                    print(f"Received from Arduino - Temperature: {temperature}, Humidity: {humidity}")

                    # Update Firebase with new readings
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
        print(f"Bluetooth connection failed: {e}. Retrying in 5 seconds...")
        await asyncio.sleep(5)
        return False  #Indicate Bluetooth failure

async def socket_connection():
    """
    Connect to the Arduino via IP (Socket) and process commands.
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((IP_ADDRESS, PORT))
        print("Connected to Arduino via IP socket.")

        # Start processing commands with socket connection
        asyncio.create_task(process_commands(socket_connection=sock))

        # Keep the connection alive
        while True:
            await asyncio.sleep(1)

    except Exception as e:
        print(f"Error with socket connection: {e}")
        return False

async def main():
    """
    Main loop to start Bluetooth connection and fallback to socket if necessary.
    """
    #Start Firebase listener in a separate thread
    threading.Thread(target=firebase_listener, daemon=True).start()

    while True:
        #First attempt Bluetooth connection
        bluetooth_success = await bluetooth_connection()

        if not bluetooth_success:
            #If Bluetooth fails, try IP socket connection
            print("Switching to IP socket communication...")
            await socket_connection()

        await asyncio.sleep(1)

# Start the main event loop
loop = asyncio.get_event_loop()
loop.run_until_complete(main())
