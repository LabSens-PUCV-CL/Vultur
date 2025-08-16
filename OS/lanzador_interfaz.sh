#!/bin/bash

# Description:
# This script waits for the X11 graphical environment to be ready (DISPLAY=:0)
# and then launches the main Python GUI interface (interfaz.py).
# It ensures that the display and authentication variables are set correctly
# so the interface can be shown on screen even when launched on startup.

# Export required environment variables for GUI execution
export DISPLAY=:0
export XAUTHORITY=/home/vultur04/.Xauthority

echo "Waiting for graphical environment (DISPLAY=:0)..."

# Wait for X11 to become available (max 10 seconds)
for i in {1..20}; do
  if xset q > /dev/null 2>&1; then
    echo "Graphical environment available. Launching interface..."
    break
  fi 
  sleep 0.5
done

# Execute the main interface
exec /usr/bin/python3 /home/vultur04/interfaz.py
