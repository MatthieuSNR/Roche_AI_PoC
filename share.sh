#!/bin/bash
# Share the dashboard from this Mac through an ngrok tunnel (prototype only).
# The data stays on this Mac; the app is reachable only while this script runs.
# Requires APP_PASSWORD in .env (otherwise anyone with the link sees the data).
# Usage (from the project root):  ./share.sh      Stop: Ctrl+C

cd "$(dirname "$0")"
if ! grep -qE '^APP_PASSWORD=.+' .env; then
    echo "Set APP_PASSWORD in .env before sharing the app."; exit 1
fi

venv/bin/streamlit run scripts/app.py --server.headless true --server.port 8505 > /dev/null 2>&1 &
STREAMLIT_PID=$!
trap 'kill $STREAMLIT_PID 2>/dev/null' EXIT
caffeinate -i ngrok http 8505   # caffeinate: the Mac does not go to sleep while sharing
