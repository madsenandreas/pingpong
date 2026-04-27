#!/usr/bin/env python3

import os
import subprocess
import threading
from flask import Flask, render_template_string, jsonify
from gpiozero import Button
from time import time, sleep

app = Flask(__name__)

# WiFi configuration – set via environment variables or a local config file.
# Example: export PINGPONG_WIFI_SSID="MyNetwork" PINGPONG_WIFI_PASSWORD="secret"
WIFI_SSID = os.environ.get("PINGPONG_WIFI_SSID", "")
WIFI_PASSWORD = os.environ.get("PINGPONG_WIFI_PASSWORD", "")

# Initial count for white and black button presses
white = 0
black = 0

# Define buttons with a debounce time
white_button = Button(3, bounce_time=0.1)
black_button = Button(17, bounce_time=0.1)

# Constants for press duration
LONG_PRESS_THRESHOLD = 1.0  # seconds for increment/decrement
RESET_THRESHOLD = 0.5       # seconds for reset

# Variables to track the press start times and reset check
press_times = {}
reset_active = False

def connect_wifi(ssid, password, retries=10, delay=5):
    for attempt in range(1, retries + 1):
        print(f"WiFi connection attempt {attempt}/{retries}...")
        try:
            result = subprocess.run(
                ["nmcli", "dev", "wifi", "connect", ssid, "password", password],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                print(f"Connected to WiFi: {ssid}")
                return True
            else:
                print(f"Failed: {result.stderr.strip()}")
        except subprocess.TimeoutExpired:
            print("WiFi connection timed out.")
        except FileNotFoundError:
            print("nmcli not found, skipping WiFi setup.")
            return False
        sleep(delay)
    print("Could not connect to WiFi after all retries.")
    return False

def wifi_watchdog(ssid, password, check_interval=30):
    while True:
        sleep(check_interval)
        try:
            result = subprocess.run(
                ["nmcli", "-t", "-f", "TYPE,STATE", "dev", "status"],
                capture_output=True, text=True, timeout=10
            )
            # Each line is "TYPE:STATE"; look for a wifi device that is connected
            connected = any(
                parts[0] == "wifi" and parts[1] == "connected"
                for line in result.stdout.splitlines()
                for parts in (line.split(":", 1),)
                if len(parts) == 2
            )
            if not connected:
                print("WiFi lost, attempting to reconnect...")
                connect_wifi(ssid, password)
        except subprocess.TimeoutExpired:
            print("WiFi watchdog: status check timed out.")
        except FileNotFoundError:
            print("WiFi watchdog: nmcli not found, disabling watchdog.")
            return

# Connect to WiFi on startup and start watchdog (only when credentials are configured)
if WIFI_SSID:
    threading.Thread(target=connect_wifi, args=(WIFI_SSID, WIFI_PASSWORD), daemon=True).start()
    threading.Thread(target=wifi_watchdog, args=(WIFI_SSID, WIFI_PASSWORD), daemon=True).start()

def monitor_reset():
    global reset_active
    while True:
        if white_button.is_pressed and black_button.is_pressed:
            # Mark both-buttons state immediately to suppress individual increments
            # even if released before the reset threshold is reached.
            reset_active = True
            current_time = time()
            white_press_time = press_times.get(white_button.pin.number)
            black_press_time = press_times.get(black_button.pin.number)
            if white_press_time and black_press_time:
                white_duration = current_time - white_press_time
                black_duration = current_time - black_press_time
                if white_duration >= RESET_THRESHOLD and black_duration >= RESET_THRESHOLD:
                    reset_scores()
        else:
            reset_active = False
        sleep(0.1)

def reset_scores():
    global white, black
    white = 0
    black = 0
    print("Scores have been reset.")

def handle_press(button):
    press_times[button.pin.number] = time()

def handle_release(button, increment, decrement):
    global reset_active
    if not reset_active:
        start_time = press_times.pop(button.pin.number, None)
        if start_time:
            duration = time() - start_time
            if duration >= LONG_PRESS_THRESHOLD:
                decrement()
            else:
                increment()

def white_increment():
    global white
    white += 1
    print(f"White button short press. Total presses: {white}")

def white_decrement():
    global white
    if white > 0:
        white -= 1
        print(f"White button long press. Total presses: {white}")

def black_increment():
    global black
    black += 1
    print(f"Black button short press. Total presses: {black}")

def black_decrement():
    global black
    if black > 0:
        black -= 1
        print(f"Black button long press. Total presses: {black}")

# Attach handlers for press and release events
white_button.when_pressed = lambda: handle_press(white_button)
white_button.when_released = lambda: handle_release(white_button, white_increment, white_decrement)

black_button.when_pressed = lambda: handle_press(black_button)
black_button.when_released = lambda: handle_release(black_button, black_increment, black_decrement)

# Start the background thread to monitor for reset condition
reset_thread = threading.Thread(target=monitor_reset, daemon=True)
reset_thread.start()

TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tennis</title>
    <style>
        body {
            margin: 0;
            padding: 0;
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            font-family: Arial, sans-serif;
        }
        .half {
            width: 50%;
            height: 100%;
            display: flex;
            flex-direction: column;
            justify-content: center; /* Center content vertically */
            align-items: center; /* Center content horizontally */
            position: relative; /* Needed for absolute positioning of instructions */
            font-size: 4vw;
        }
        .white-half {
            background-color: white;
            color: black;
        }
        .black-half {
            background-color: black;
            color: white;
        }
        .instructions {
            position: absolute;
            top: 10px; /* Position at the top */
            left: 10px; /* Position at the left */
            text-align: left;
            font-size: 1.5vw; /* Smaller font size for instructions */
            width: auto; /* Auto width to fit content */
            max-width: 50%; /* Max width to prevent too wide */
        }
        .clock {
            position: fixed;
            top: 10px;
            right: 15px;
            font-size: 5vw;
            font-weight: bold;
            color: white;
            background-color: rgba(0, 0, 0, 0.55);
            padding: 4px 18px;
            border-radius: 8px;
            z-index: 100;
            letter-spacing: 0.05em;
        }
    </style>
</head>
<body>
    <div class="clock" id="clock">00:00:00</div>
    <div class="half white-half" id="whiteTeam">
        <div class="instructions">
            Press short to increase value<br>
            Press long to decrease value<br>
            Press both to zero values
        </div>
        WhiteSide: <span id="count_white">{{ white }}</span>
    </div>
    <div class="half black-half" id="blackTeam">
        BlackSide: <span id="count_black">{{ black }}</span>
    </div>
    <script src="{{ url_for('static', filename='jquery.min.js') }}"></script>
    <script>
        $(document).ready(function() {
            function updateClock() {
                var now = new Date();
                var h = String(now.getHours()).padStart(2, '0');
                var m = String(now.getMinutes()).padStart(2, '0');
                var s = String(now.getSeconds()).padStart(2, '0');
                $('#clock').text(h + ':' + m + ':' + s);
            }
            updateClock();
            setInterval(updateClock, 1000);

            function fetchCount_white() {
                $.getJSON('/count_white', function(data) {
                    $('#count_white').text(data.count_white);
                });
            }
            setInterval(fetchCount_white, 100); // Update the white count every second

            function fetchCount_black() {
                $.getJSON('/count_black', function(data) {
                    $('#count_black').text(data.count_black);
                });
            }
            setInterval(fetchCount_black, 100); // Update the black count every second
        });
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    return render_template_string(TEMPLATE, white=white, black=black)

@app.route('/count_white')
def get_count_white():
    return jsonify({'count_white': white})

@app.route('/count_black')
def get_count_black():
    return jsonify({'count_black': black})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
