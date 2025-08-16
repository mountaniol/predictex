#!/bin/bash

# Debug version of server starter with auto-restart

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_PATH="$SCRIPT_DIR/../../../venv"
LOG_FILE="/tmp/creator-backend-debug.log"

echo "🔍 DEBUG: Starting Question Creator Backend with monitoring..."
echo "📝 Log file: $LOG_FILE"

# Set environment variables for OpenAI
export OPENAI_API_KEY="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"
export REACT_APP_GPT_KEY="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"
export REACT_APP_PROJECT_ID="proj_1hNKc2pZ058vN4dqwCDO9o9T"

# Activate virtual environment
if [ -d "$VENV_PATH" ]; then
    source "$VENV_PATH/bin/activate"
else
    echo "❌ Virtual environment not found!"
    exit 1
fi

# Install dependencies
echo "📦 Ensuring dependencies..."
pip install -q flask flask-cors requests toml openai 2>/dev/null

# Function to start server
start_server() {
    echo "[$(date)] 🚀 Starting server..." | tee -a $LOG_FILE
    
    # Run Python with unbuffered output for better debugging
    python -u server.py 2>&1 | while read line; do
        echo "[$(date)] $line" | tee -a $LOG_FILE
    done
    
    EXIT_CODE=$?
    echo "[$(date)] ❌ Server exited with code: $EXIT_CODE" | tee -a $LOG_FILE
    return $EXIT_CODE
}

# Main loop with auto-restart
RESTART_COUNT=0
MAX_RESTARTS=10

while [ $RESTART_COUNT -lt $MAX_RESTARTS ]; do
    echo "[$(date)] 🔄 Starting attempt $((RESTART_COUNT + 1))/$MAX_RESTARTS" | tee -a $LOG_FILE
    
    start_server
    EXIT_CODE=$?
    
    if [ $EXIT_CODE -eq 0 ]; then
        echo "[$(date)] ✅ Server exited normally" | tee -a $LOG_FILE
        break
    else
        echo "[$(date)] ⚠️ Server crashed! Exit code: $EXIT_CODE" | tee -a $LOG_FILE
        RESTART_COUNT=$((RESTART_COUNT + 1))
        
        if [ $RESTART_COUNT -lt $MAX_RESTARTS ]; then
            echo "[$(date)] ⏳ Waiting 5 seconds before restart..." | tee -a $LOG_FILE
            sleep 5
        else
            echo "[$(date)] ❌ Maximum restart attempts reached!" | tee -a $LOG_FILE
            exit 1
        fi
    fi
done