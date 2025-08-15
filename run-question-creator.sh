#!/bin/bash

# Question Creator Services Runner
# This script starts both Question Creator frontend (3003) and backend (3004)

echo "🚀 Starting Question Creator services..."

# Function to kill processes on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down Question Creator..."
    pkill -f "question-creator.*server.py"
    pkill -f "question-creator.*react-scripts"
    exit 0
}

# Set up cleanup on exit
trap cleanup SIGINT SIGTERM

# Check if we're in the right directory
if [ ! -d "question-creator" ]; then
    echo "❌ Error: question-creator directory not found!"
    echo "   Make sure you're running this from the main project directory."
    exit 1
fi

cd question-creator

# Check and setup virtual environment for backend
if [ ! -d "backend/venv" ]; then
    echo "📦 Creating Python virtual environment for Question Creator backend..."
    cd backend
    python3 -m venv venv
    source venv/bin/activate
    pip install flask flask-cors requests
    cd ..
fi

# Start backend (port 3004)
echo "🐍 Starting Question Creator backend on port 3004..."
cd backend
source venv/bin/activate
python server.py &
BACKEND_PID=$!
cd ..

# Wait for backend to start
sleep 3

# Start frontend (port 3003) on 0.0.0.0
echo "⚛️  Starting Question Creator frontend on 0.0.0.0:3003..."
HOST=0.0.0.0 PORT=3003 npm start &
FRONTEND_PID=$!

# Wait for processes
echo ""
echo "✅ Question Creator services started:"
echo "   Frontend: http://0.0.0.0:3003"
echo "   Backend:  http://localhost:3004"
echo ""

# Keep script running
wait $BACKEND_PID $FRONTEND_PID