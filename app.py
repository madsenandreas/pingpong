#!/usr/bin/env python3

from flask import Flask, render_template_string, jsonify
from gpiozero import Button
from time import time, sleep
import threading

app = Flask(__name__)

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

def monitor_reset():
    global reset_active
    while True:
        if white_button.is_pressed and black_button.is_pressed:
            # Ensure the reset hasn't been activated yet
            if not reset_active:
                current_time = time()
                white_press_time = press_times.get(white_button.pin.number)
                black_press_time = press_times.get(black_button.pin.number)
                if white_press_time and black_press_time:
                    # Calculate press durations
                    white_duration = current_time - white_press_time
                    black_duration = current_time - black_press_time
                    # Check if both are pressed long enough
                    if white_duration >= RESET_THRESHOLD and black_duration >= RESET_THRESHOLD:
                        reset_scores()
                        reset_active = True
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
    </style>
</head>
<body>
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
    <script src="./jquery.min.js"></script>
    <script>
        $(document).ready(function() {
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
