#!/bin/bash

# Simple wrapper to run backend with virtual environment
# This ensures toml and other dependencies are available

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_PATH="$SCRIPT_DIR/../venv"

echo "====================================="
echo "Starting Question Creator Backend"
echo "====================================="

# Always use virtual environment
if [ -d "$VENV_PATH" ]; then
    echo "✅ Activating virtual environment..."
    source "$VENV_PATH/bin/activate"
    
    # Ensure dependencies are installed
    echo "📦 Checking dependencies..."
    pip install -q toml flask flask-cors requests 2>/dev/null
    
    # Start backend
    cd "$SCRIPT_DIR/backend"
    echo "🚀 Starting backend server..."
    python server.py
else
    echo "❌ Virtual environment not found at: $VENV_PATH"
    echo ""
    echo "Please create it first:"
    echo "  cd /media/AI/predictex/qna-evaluator"
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install toml flask flask-cors requests openai"
    exit 1
fi