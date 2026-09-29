#!/bin/sh
# Start a virtual 1920x1080 display with a window manager, then run the given Python script.
Xvfb :99 -screen 0 1920x1080x24 >/dev/null 2>&1 &
sleep 1
openbox >/dev/null 2>&1 &
sleep 1
exec python "$@"
