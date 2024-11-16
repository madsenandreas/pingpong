#!/usr/bin/env python3

from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import threading
from time import time, sleep
from team_names import team_names
import random

app = Flask(__name__, template_folder='templates')
socketio = SocketIO(app, async_mode='gevent')  # Initialize SocketIO

# Game state object to track all game variables
DEFAULT_GAME_STATE = {
    'white': 0,
    'black': 0,
    'current_set': 1,
    'black_set_wins': 0,
    'white_set_wins': 0,
    'swapped_sides': False,
    'white_start': 0,
    'black_start': 0,
    'debug': False,
    'started': False,
    'starting_server': None,
    'current_server': None,
    'serves_remaining': 2,
    'current_white_name': None,
    'current_black_name': None,
    'theme': None,
    'game_won': False,
    'winning_side': None
}
game_state = DEFAULT_GAME_STATE.copy()

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
    game_state['debug'] = True

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

# PI Functions

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
                # Update serves after each point
                game_state['serves_remaining'] -= 1
                if game_state['serves_remaining'] == 0:
                    # Switch the server
                    game_state['current_server'] = 'black' if game_state['current_server'] == 'white' else 'white'

                    # Check for deuce (both sides 10 or more points)
                    if game_state['white'] >= 10 and game_state['black'] >= 10:
                        game_state['serves_remaining'] = 1  # One serve per side
                    else:
                        game_state['serves_remaining'] = 2  # Standard two serves per side

                # Emit updated state to all clients
                emit_game_state()


# Gamestate functions

def emit_game_state():
    global game_state
    if game_state['swapped_sides']:
        socketio.emit('game_state', {
            'count_white': game_state['black'],
            'count_black': game_state['white'],
            'current_server': game_state['current_server'],
            'serves_remaining': game_state['serves_remaining'],
            'started': game_state['started'],
            'current_white_name': game_state['current_black_name'],
            'current_black_name': game_state['current_white_name'],
            'black_set_wins': game_state['white_set_wins'],
            'white_set_wins': game_state['black_set_wins'],
            'game_won': game_state['game_won'],
            'winning_side': game_state['winning_side']
        })
    else:
        socketio.emit('game_state', {
            'count_white': game_state['white'],
            'count_black': game_state['black'],
            'current_server': game_state['current_server'],
            'serves_remaining': game_state['serves_remaining'],
            'started': game_state['started'],
            'current_white_name': game_state['current_white_name'],
            'current_black_name': game_state['current_black_name'],
            'black_set_wins': game_state['black_set_wins'],
            'white_set_wins': game_state['white_set_wins'],
            'game_won': game_state['game_won'],
            'winning_side': game_state['winning_side']
        })

def end_set(winner):
    game_state['current_set'] += 1
    game_state['serves_remaining'] = 2
    game_state['swapped_sides'] = game_state['current_set'] % 2 == 0
    game_state['swapped_sides'] = not game_state['swapped_sides']

    if winner == 'white':
        game_state['white_set_wins'] += 1
    else:
        game_state['black_set_wins'] += 1

    if game_state['current_set'] % 2 == 0:
        game_state['current_server'] = game_state['starting_server']
    else:
        if game_state['starting_server'] == 'white':
            game_state['current_server'] = 'black'
        else:
            game_state['current_server'] = 'white'

    if game_state['swapped_sides']:
        if game_state['white_set_wins'] == 2:
            game_state['game_won'] = 'black'
        elif game_state['black_set_wins'] == 2:
            game_state['game_won'] = 'white'
    else:
        if game_state['white_set_wins'] == 2:
            game_state['game_won'] = 'white'
        elif game_state['black_set_wins'] == 2:
            game_state['game_won'] = 'black'
    if not game_state['game_won']:
        game_state['black'] = 0
        game_state['white'] = 0
        game_state['swapped_sides'] = not game_state['swapped_sides']
    emit_game_state()

def check_set_winner():
    white_score = game_state['white']
    black_score = game_state['black']

    # Check if either player has at least 11 points and a 2 point lead
    if white_score >= 11 and white_score - black_score >= 2:
        return 'white'
    elif black_score >= 11 and black_score - white_score >= 2:
        return 'black'

    return None

def select_starting_server():
    global game_state
    game_state['current_server'] = random.choice(['white', 'black'])
    game_state['starting_server'] = game_state['current_server']

def select_team_names():
    selected_team = random.choice(team_names)
    game_state['current_white_name'] = selected_team['white']
    game_state['current_black_name'] = selected_team['black']
    game_state['theme'] = selected_team['franchise']

def decrement_server():
    game_state['serves_remaining'] -= 1
    if game_state['serves_remaining'] == 0:
        game_state['current_server'] = 'black' if game_state['current_server'] == 'white' else 'white'

    # Check if the deuce condition (both scores >= 10) is still true
    if game_state['white'] >= 10 and game_state['black'] >= 10:
        game_state['serves_remaining'] = 1  # Maintain single serve
    else:
        game_state['serves_remaining'] = 2  # Reset to normal two serves if not in deuce

def increment_server():
    game_state['serves_remaining'] += 1
    if game_state['serves_remaining'] >= 3:
        game_state['current_server'] = 'black' if game_state['current_server'] == 'white' else 'white'
        game_state['serves_remaining'] = 1

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

def start_game():
    global game_state
    game_state['started'] = True
    select_starting_server()
    select_team_names()

def reset_scores():
    global game_state, DEFAULT_GAME_STATE
    debug_mode = game_state['debug']
    game_state = DEFAULT_GAME_STATE.copy()
    game_state['debug'] = debug_mode
    socketio.emit('reset', True)
    emit_game_state()

def white_increment():
    global game_state

    if not game_state['started']:
        start_game()
    else:
        if game_state['swapped_sides']:
            game_state['black'] += 1
        else:
            game_state['white'] += 1
        decrement_server()
    winner = check_set_winner()
    if winner:
        end_set(winner)
    emit_game_state()

def black_increment():
    global game_state
    if not game_state['started']:
        start_game()
    else:
        if game_state['swapped_sides']:
            game_state['white'] += 1
        else:
            game_state['black'] += 1
        decrement_server()
    winner = check_set_winner()
    if winner:
        end_set(winner)
    emit_game_state()

def white_decrement():
    global game_state
    if game_state['swapped_sides']:
        if game_state['black'] > 0:
            game_state['black'] -= 1
    else:
        if game_state['white'] > 0:
            game_state['white'] -= 1

    # Reassess serve logic
    decrement_server()
    emit_game_state()

def black_decrement():
    global game_state
    if game_state['swapped_sides']:
        if game_state['white'] > 0:
            game_state['white'] -= 1
    else:
        if game_state['black'] > 0:
            game_state['black'] -= 1

    # Reassess serve logic
    decrement_server()
    emit_game_state()

@socketio.on('debug_request')
def handle_debug_request():
    global game_state
    socketio.emit('debug_response', {'debug': game_state['debug']})

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
    return render_template('index.html', white=game_state['white'], black=game_state['black'])

white_button.when_pressed = lambda: handle_press(white_button)
white_button.when_released = lambda: handle_release(white_button, white_increment, white_decrement)

black_button.when_pressed = lambda: handle_press(black_button)
black_button.when_released = lambda: handle_release(black_button, black_increment, black_decrement)

reset_thread = threading.Thread(target=monitor_reset, daemon=True)
reset_thread.start()

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5001)

