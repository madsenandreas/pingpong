#!/usr/bin/bash
# Delay to allow the graphical environment to fully load
sleep 30
# Start Firefox and open the specified URL
#DISPLAY=:0 firefox -url http://127.0.0.1:5000/ &
DISPLAY=:0 firefox &
# Wait for Firefox to fully load
sleep 20
# Use xdotool to simulate pressing F11 to enter fullscreen mode
DISPLAY=:0 xdotool search --sync --onlyvisible --class "Firefox" windowactivate
DISPLAY=:0 xdotool search --sync --onlyvisible --class "Firefox" windowfocus
DISPLAY=:0 xdotool key F11
