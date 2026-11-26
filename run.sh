#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
echo "Starting Fortivex AI — Autonomous Sales Voice Agent"
echo "Open http://127.0.0.1:8765 in Chrome or Edge"
echo "Press Ctrl+C to stop."
python3 app.py
