#!/usr/bin/env python3

from flask import Flask, render_template, jsonify
import threading
from time import time, sleep

app = Flask(__name__, template_folder='templates')

# Initial count for white and black button presses
white = 0
black = 0
DEBUG = False

# Try to import and set up GPIO, fallback to mock implementation if not on Pi
try:
    from gpiozero import Button
    # Define buttons with a debounce time
    white_button = Button(3, bounce_time=0.1)
    black_button = Button(17, bounce_time=0.1)
    ON_RASPBERRY_PI = True

except (ImportError, Exception):
    print("Not running on Raspberry Pi - using mock button implementation")
    ON_RASPBERRY_PI = False
    DEBUG = True
    
    # Mock Button class for development
    class MockButton:
        def __init__(self, pin):
            self.pin = type('obj', (object,), {'number': pin})
            self.is_pressed = False
            self._when_pressed = None
            self._when_released = None
            
        @property
        def when_pressed(self):
            return self._when_pressed
            
        @when_pressed.setter
        def when_pressed(self, func):
            self._when_pressed = func
            
        @property
        def when_released(self):
            return self._when_released
            
        @when_released.setter
        def when_released(self, func):
            self._when_released = func
    
    white_button = MockButton(3)
    black_button = MockButton(17)

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

@app.route('/')
def index():
    return render_template('index.html', white=white, black=black)

@app.route('/counts')
def get_counts():
    return jsonify({'count_white': white, 'count_black': black})

@app.route('/button_white', methods=['POST'])
def button_white_pressed():
    global white
    white += 1
    return jsonify({'count_white': white})

@app.route('/button_black', methods=['POST']) 
def button_black_pressed():
    global black
    black += 1
    return jsonify({'count_black': black})

@app.route('/reset', methods=['POST'])
def reset():
    reset_scores()
    return jsonify({'reset': True})

@app.route('/isDebug')
def is_debug():
    return jsonify({'debug': DEBUG})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
