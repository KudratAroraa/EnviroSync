import { initializeApp } from "https://www.gstatic.com/firebasejs/11.0.1/firebase-app.js";
import { getDatabase, ref, onValue, set } from "https://www.gstatic.com/firebasejs/11.0.1/firebase-database.js";

//Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyBhty7aB9lirwmq4VUcB8TIF1bohg8JFag",
  authDomain: "envirosync-7c7b5.firebaseapp.com",
  databaseURL: "https://envirosync-7c7b5-default-rtdb.firebaseio.com",
  projectId: "envirosync-7c7b5",
  storageBucket: "envirosync-7c7b5.appspot.com",
  messagingSenderId: "645755185917",
  appId: "1:645755185917:web:5a364e74be3eedbfd4ec94",
  measurementId: "G-ZHCJ67WJB6"
};

//Initialize Firebase
const app = initializeApp(firebaseConfig);
const database = getDatabase(app);

let acStatus = false;
let heaterStatus = false;

//Raspberry Pi fixed location and distance threshold (in meters)
const RPI_LOCATION = { lat: 30.7384523, lng: 76.8006375 }; //location of the central hub in a hotel 
const DISTANCE_THRESHOLD = 100; //100 meters for prototype purpose

//Calculating distance using the Haversine formula
function calculateDistance(lat1, lon1, lat2, lon2) 
{
  const R = 6371e3; //Earth radius in meters
  const φ1 = lat1 * (Math.PI / 180);
  const φ2 = lat2 * (Math.PI / 180);
  const Δφ = (lat2 - lat1) * (Math.PI / 180);
  const Δλ = (lon2 - lon1) * (Math.PI / 180);

  const a = Math.sin(Δφ / 2) * Math.sin(Δφ / 2) +
            Math.cos(φ1) * Math.cos(φ2) *
            Math.sin(Δλ / 2) * Math.sin(Δλ / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

  return R * c; //Distance in meters
}

//updating location info and control button availability dynamically
function updateLocationInfo(userLat, userLng) 
{
  const distance = calculateDistance(userLat, userLng, RPI_LOCATION.lat, RPI_LOCATION.lng);
  document.getElementById('coordinates').innerText = `${userLat.toFixed(4)}, ${userLng.toFixed(4)}`;
  document.getElementById('distance').innerText = distance <= DISTANCE_THRESHOLD
    ? `In Range! (${distance.toFixed(0)} m)`
    : `${(distance / 1000).toFixed(2)} km away`;

  //enable controls only if in range or else disable if not
  if (distance <= DISTANCE_THRESHOLD) 
  {
    enableControls();
  } 
  else 
  {
    disableControls(`You are out of range. Controls are Disabled.`);
  }
}

//event listener to get user location periodically for distance updates
async function checkProximity() 
{
  if (navigator.geolocation) {
    navigator.geolocation.watchPosition(position => {
      updateLocationInfo(position.coords.latitude, position.coords.longitude);
    }, () => {
      alert("Unable to access location. Please enable location permissions.");
    });
  } else 
  {
    alert("Geolocation is not supported by this browser.");
  }
}

//enable control buttons
function enableControls() 
{
  document.getElementById('toggleAC').disabled = false;
  document.getElementById('toggleHeater').disabled = false;
  document.getElementById('status').innerText = "You are within range. Controls enabled.";
}

//Disable control buttons
function disableControls(message) 
{
  document.getElementById('toggleAC').disabled = true;
  document.getElementById('toggleHeater').disabled = true;
  document.getElementById('status').innerText = message;
}

//Fetch live temperature and humidity data from firebase
function fetchSensorData() 
{
  const sensorRef = ref(database, 'EnviroSync');
  onValue(sensorRef, (snapshot) => {
    const data = snapshot.val();
    document.getElementById('temp').innerText = data?.temperature !== undefined ? data.temperature : "--";
    document.getElementById('humidity').innerText = data?.humidity !== undefined ? data.humidity : "--";
  }, (error) => {
    console.error("Error fetching sensor data:", error);
  });
}

//update background color based on AC and Heater status
function updateBackgroundColor() 
{
  document.body.classList.remove('body-neutral', 'body-ac-on', 'body-heater-on', 'body-both-on');

  if (acStatus && heaterStatus) {
    document.body.classList.add('body-both-on');
  } else if (acStatus) {
    document.body.classList.add('body-ac-on');
  } else if (heaterStatus) {
    document.body.classList.add('body-heater-on');
  } else {
    document.body.classList.add('body-neutral');
  }
}

//update the status of AC and Heater in Firebase update button styles and background color
function updateDeviceStatus(device, status) 
{
  const deviceRef = ref(database, `EnviroSync/${device}`);
  
  //Set the device status in Firebase and update UI elements based on the new status
  set(deviceRef, status).then(() => {
    
    //Update the local status variables and button text based on the device type
    if (device === 'AC') 
    {
      acStatus = status;
      document.getElementById('toggleAC').innerText = status ? "Turn Off AC" : "Turn On AC";
      document.getElementById('ac-status').innerText = status ? "ON" : "OFF";
      document.getElementById('toggleAC').classList.toggle('ac-on', status);
    } 
    else if (device === 'Heater') 
    {
      heaterStatus = status;
      document.getElementById('toggleHeater').innerText = status ? "Turn Off Heater" : "Turn On Heater";
      document.getElementById('heater-status').innerText = status ? "ON" : "OFF";
      document.getElementById('toggleHeater').classList.toggle('heater-on', status);
    }

    //update background color based on the current statuses
    updateBackgroundColor();
  }).catch((error) => {
    console.error(`Error updating ${device} status:`, error);
  });
}

//initialize interface and event listeners
document.addEventListener('DOMContentLoaded', () => {
  fetchSensorData();
  checkProximity();

  //set up event listeners for the toggle buttons
  document.getElementById('toggleAC').addEventListener('click', () => {
    const currentStatus = !acStatus; //Toggle current AC status
    updateDeviceStatus('AC', currentStatus);
  });

  document.getElementById('toggleHeater').addEventListener('click', () => {
    const currentStatus = !heaterStatus; //Toggle current Heater status
    updateDeviceStatus('Heater', currentStatus);
  });
});