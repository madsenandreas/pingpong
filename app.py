#!/usr/bin/env python3

from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import threading
from time import time, sleep

app = Flask(__name__, template_folder='templates')
socketio = SocketIO(app)  # Initialize SocketIO

white_start = 0
black_start = 0

# Initial count for white and black button presses
white = 0
black = 0
DEBUG = False
started = False
current_server = 'white'  # Track current server (white or black)
serves_remaining = 2      # Track serves remaining before switch

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
def decrement_server():
    global serves_remaining, current_server
    serves_remaining -= 1
    if serves_remaining == 0:
        current_server = 'black' if current_server == 'white' else 'white'
        serves_remaining = 2

def increment_server():
    global serves_remaining, current_server
    serves_remaining += 1
    if serves_remaining >= 3:
        current_server = 'black' if current_server == 'white' else 'white'
        serves_remaining = 1

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
    global white, black, current_server, serves_remaining, started
    started = False
    white = 0
    black = 0
    current_server = 'white'
    serves_remaining = 2
    emit_game_state()

def handle_press(button):
    press_times[button.pin.number] = time()

def handle_release(button, increment, decrement):
    global reset_active, serves_remaining, current_server
    if not reset_active:
        start_time = press_times.pop(button.pin.number, None)
        if start_time:
            duration = time() - start_time
            if duration >= LONG_PRESS_THRESHOLD:
                decrement()
            else:
                increment()
                # Update serves after each point
                serves_remaining -= 1
                if serves_remaining == 0:
                    current_server = 'black' if current_server == 'white' else 'white'
                    serves_remaining = 2
                # Emit updated state to all clients
                emit_game_state()

def white_increment():
    global white, started
    if not started:
        started = True
    else:
        white += 1
        decrement_server()
    emit_game_state()

def white_decrement():
    global white
    if white > 0:
        white -= 1
        increment_server()
        emit_game_state()

def black_increment():
    global black, started
    if not started:
        started = True
    else:
        black += 1
        decrement_server()
    emit_game_state()

def black_decrement():
    global black
    if black > 0:
        black -= 1
        increment_server()
        emit_game_state()

white_button.when_pressed = lambda: handle_press(white_button)
white_button.when_released = lambda: handle_release(white_button, white_increment, white_decrement)

black_button.when_pressed = lambda: handle_press(black_button)
black_button.when_released = lambda: handle_release(black_button, black_increment, black_decrement)

reset_thread = threading.Thread(target=monitor_reset, daemon=True)
reset_thread.start()

def emit_game_state():
    global started, current_server, serves_remaining, white, black
    socketio.emit('game_state', {
        'count_white': white,
        'count_black': black,
        'current_server': current_server,
        'serves_remaining': serves_remaining,
        'started': started
    })


@socketio.on('debug_request')
def handle_debug_request():
    socketio.emit('debug_response', {'debug': DEBUG})

@socketio.on('connect')
def handle_connect():
    emit_game_state()

@socketio.on('button_press')
def handle_button_press(data):
    button_color = data.get('button')
    if button_color == 'white':
        white_increment()
    elif button_color == 'black':
        black_increment()
    elif button_color == 'white_decrement':
        white_decrement()
    elif button_color == 'black_decrement':
        black_decrement()

@socketio.on('reset_request')
def handle_reset_request():
    reset_scores()

@app.route('/')
def index():
    return render_template('index.html', white=white, black=black)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
