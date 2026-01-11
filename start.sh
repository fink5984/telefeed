#!/bin/bash
# Start script for Railway - runs both UI and telefeed

# Start telefeed in background
python telefeed_multi.py &

# Start web UI in foreground
python web_ui.py
