#!/bin/bash

# Simple wrapper to ALWAYS run server.py with virtual environment
# This ensures all dependencies are available

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_PATH="$SCRIPT_DIR/../../../venv"

# Check if virtual environment exists
if [ ! -d "$VENV_PATH" ]; then
    echo "❌ Virtual environment not found at: $VENV_PATH"
    echo "Creating it now..."
    python3 -m venv "$VENV_PATH"
fi

# Activate virtual environment
source "$VENV_PATH/bin/activate"

# Ensure dependencies are installed
echo "📦 Checking Python dependencies..."
pip install -q flask flask-cors requests toml 2>/dev/null

# Run the server
echo "🚀 Starting Question Creator Backend with venv Python..."
exec python server.py