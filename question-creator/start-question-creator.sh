#!/bin/bash

# Question Creator Startup Script
# Starts both frontend (3003) and backend (3004)

echo "🚀 Starting Question Creator System..."

# Check if virtual environment exists
if [ ! -d "backend/venv" ]; then
    echo "📦 Creating Python virtual environment..."
    cd backend
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    cd ..
else
    echo "✅ Virtual environment exists"
fi

# Function to kill processes on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down Question Creator..."
    pkill -f "python.*server.py"
    pkill -f "react-scripts start"
    exit 0
}

# Set up cleanup on exit
trap cleanup SIGINT SIGTERM

# Start backend
echo "🐍 Starting Python backend on port 3004..."
cd backend
source venv/bin/activate
python server.py &
BACKEND_PID=$!
cd ..

# Wait a moment for backend to start
sleep 2

# Start frontend on 0.0.0.0
echo "⚛️  Starting React frontend on 0.0.0.0:3003..."
HOST=0.0.0.0 PORT=3003 npm start &
FRONTEND_PID=$!

# Show startup information
echo ""
echo "📍 Services started:"
echo "   Frontend: http://0.0.0.0:3003 (accessible from any IP)"
echo "   Backend:  http://localhost:3004"
echo ""
echo "🔗 Main QnA Evaluator should be running on:"
echo "   Main App: http://localhost:3000"
echo "   Main API: http://localhost:3001"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID