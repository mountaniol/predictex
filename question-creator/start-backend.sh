#!/bin/bash

# Start script for Question Creator Backend
# Reads configuration from config.toml

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CONFIG_FILE="$SCRIPT_DIR/config.toml"

echo "==================================="
echo "Starting Question Creator Backend"
echo "==================================="

# Check if config exists
if [ -f "$CONFIG_FILE" ]; then
    echo "✅ Found config.toml"
    # Try to extract host and port using Python with toml
    if python3 -c "import toml" 2>/dev/null; then
        HOST=$(python3 -c "import toml; print(toml.load(open('$CONFIG_FILE'))['backend']['host'])" 2>/dev/null || echo "0.0.0.0")
        PORT=$(python3 -c "import toml; print(toml.load(open('$CONFIG_FILE'))['backend']['port'])" 2>/dev/null || echo "3004")
        echo "📍 Backend will run on: $HOST:$PORT"
    else
        echo "⚠️ toml module not available, using defaults"
        HOST="0.0.0.0"
        PORT="3004"
    fi
else
    # Check for legacy JSON config
    CONFIG_JSON="$SCRIPT_DIR/config.json.legacy"
    if [ -f "$CONFIG_JSON" ]; then
        echo "📋 Using legacy JSON config"
        HOST=$(python3 -c "import json; print(json.load(open('$CONFIG_JSON'))['backend']['host'])" 2>/dev/null || echo "0.0.0.0")
        PORT=$(python3 -c "import json; print(json.load(open('$CONFIG_JSON'))['backend']['port'])" 2>/dev/null || echo "3004")
    else
        echo "⚠️ No config found, using defaults"
        HOST="0.0.0.0"
        PORT="3004"
    fi
    echo "📍 Backend will run on: $HOST:$PORT"
fi

# Activate virtual environment if it exists
VENV_PATH="$SCRIPT_DIR/../venv"
if [ -d "$VENV_PATH" ]; then
    echo "✅ Activating virtual environment"
    source "$VENV_PATH/bin/activate"
    
    # Ensure toml is installed
    pip install toml >/dev/null 2>&1
else
    echo "⚠️  No virtual environment found, using system Python"
    echo "📦 Installing toml module globally..."
    pip install --user toml >/dev/null 2>&1 || pip install toml >/dev/null 2>&1
fi

# Start the backend
cd "$SCRIPT_DIR/backend"
echo ""
echo "🚀 Starting backend server..."
echo "==================================="

# Check if we're in virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  WARNING: Virtual environment not activated!"
    echo "🔄 Trying to activate it now..."
    if [ -d "$VENV_PATH" ]; then
        source "$VENV_PATH/bin/activate"
        python server.py
    else
        echo "❌ Cannot find virtual environment. Please install toml:"
        echo "   sudo apt-get install python3-toml"
        echo "   OR"
        echo "   Create venv: python3 -m venv ../venv"
        echo "   Activate: source ../venv/bin/activate"
        echo "   Install: pip install toml flask flask-cors requests"
        exit 1
    fi
else
    python server.py
fi