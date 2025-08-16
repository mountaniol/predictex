#!/bin/bash

# Question Creator Services Runner (Production Mode)
# This script starts both Question Creator frontend (3003) and backend (3004)
# Uses production build with serve instead of npm start

echo "🚀 Starting Question Creator services (Production Mode)..."

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Function to kill processes on specific port
kill_port() {
    local port=$1
    echo "Checking port $port..."
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "  Killing process on port $port..."
        lsof -Pi :$port -sTCP:LISTEN -t | xargs kill -9 2>/dev/null || true
        sleep 1
    fi
}

# Function to kill processes on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down Question Creator..."
    
    # Kill backend
    if [ -f /tmp/qc-backend.pid ]; then
        kill $(cat /tmp/qc-backend.pid) 2>/dev/null || true
        rm /tmp/qc-backend.pid
    fi
    
    # Kill frontend
    if [ -f /tmp/qc-frontend.pid ]; then
        kill $(cat /tmp/qc-frontend.pid) 2>/dev/null || true
        rm /tmp/qc-frontend.pid
    fi
    
    # Additional cleanup
    pkill -f "question-creator.*server.py" 2>/dev/null || true
    pkill -f "serve.*3003" 2>/dev/null || true
    pkill -f "npx serve" 2>/dev/null || true
    
    exit 0
}

# Set up cleanup on exit
trap cleanup SIGINT SIGTERM EXIT

# Check if we're in the right directory
if [ ! -d "question-creator" ]; then
    echo "❌ Error: question-creator directory not found!"
    echo "   Make sure you're running this from the main project directory."
    exit 1
fi

cd question-creator

# Clean up any existing processes
echo "🧹 Cleaning up existing processes..."
kill_port 3003
kill_port 3004
pkill -f "serve.*3003" 2>/dev/null || true
pkill -f "npx serve" 2>/dev/null || true
pkill -f "question-creator.*server.py" 2>/dev/null || true

# Check for virtual environment
VENV_PATH="$SCRIPT_DIR/../venv"
if [ ! -d "$VENV_PATH" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv "$VENV_PATH"
fi

# Activate virtual environment
echo "🐍 Activating virtual environment..."
source "$VENV_PATH/bin/activate"

# Install Python dependencies
echo "📦 Checking Python dependencies..."
pip install -q flask flask-cors requests toml 2>/dev/null

# Build frontend if needed
if [ ! -d "build" ] || [ "src/config.ts" -nt "build/index.html" ] 2>/dev/null; then
    echo "🔨 Building Question Creator frontend..."
    npm run build
fi

# Start backend (port 3004)
echo "🐍 Starting Question Creator backend on port 3004..."
(
    cd backend
    if [ -f "start-server.sh" ]; then
        ./start-server.sh > /tmp/qc-backend.log 2>&1 &
    else
        python server.py > /tmp/qc-backend.log 2>&1 &
    fi
    echo $! > /tmp/qc-backend.pid
)

# Wait for backend to start
sleep 2

# Verify backend started
if [ -f /tmp/qc-backend.pid ] && kill -0 $(cat /tmp/qc-backend.pid) 2>/dev/null; then
    echo "  ✅ Backend started (PID: $(cat /tmp/qc-backend.pid))"
else
    echo "  ❌ Failed to start backend"
    echo "  Check logs: tail -f /tmp/qc-backend.log"
    exit 1
fi

# Double-check port 3003 is free
if lsof -Pi :3003 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Port 3003 still in use, forcing cleanup..."
    lsof -Pi :3003 -sTCP:LISTEN -t | xargs kill -9 2>/dev/null || true
    sleep 2
fi

# Start frontend using serve (port 3003)
echo "⚛️  Starting Question Creator frontend on port 3003..."
(
    npx serve -s build -l 3003 --no-clipboard > /tmp/qc-frontend.log 2>&1 &
    echo $! > /tmp/qc-frontend.pid
)

# Wait for frontend to start
sleep 2

# Verify frontend started
if [ -f /tmp/qc-frontend.pid ] && kill -0 $(cat /tmp/qc-frontend.pid) 2>/dev/null; then
    echo "  ✅ Frontend started (PID: $(cat /tmp/qc-frontend.pid))"
else
    echo "  ❌ Failed to start frontend"
    echo "  Check logs: tail -f /tmp/qc-frontend.log"
    exit 1
fi

# Show status
echo ""
echo "========================================="
echo "✅ Question Creator services started:"
echo "   Frontend: http://localhost:3003"
echo "   Backend:  http://localhost:3004"
echo ""
echo "📋 Logs:"
echo "   Frontend: tail -f /tmp/qc-frontend.log"
echo "   Backend:  tail -f /tmp/qc-backend.log"
echo ""
echo "Press Ctrl+C to stop all services"
echo "========================================="

# Keep script running
while true; do
    sleep 1
    
    # Check if services are still running
    if [ -f /tmp/qc-backend.pid ] && ! kill -0 $(cat /tmp/qc-backend.pid) 2>/dev/null; then
        echo "⚠️  Backend stopped unexpectedly"
        cleanup
    fi
    
    if [ -f /tmp/qc-frontend.pid ] && ! kill -0 $(cat /tmp/qc-frontend.pid) 2>/dev/null; then
        echo "⚠️  Frontend stopped unexpectedly"
        cleanup
    fi
done