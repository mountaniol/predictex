#!/bin/bash

# Start development servers for QNA Evaluator
echo "🚀 Starting QNA Evaluator development servers..."

# Start backend server
echo "📡 Starting backend server on port 5000..."
cd backend
node server.js &
BACKEND_PID=$!
cd ..

# Wait a moment for backend to start
sleep 2

# Start frontend server
echo "🌐 Starting frontend server on port 3000..."
npm start &
FRONTEND_PID=$!

echo "✅ Both servers started!"
echo "📡 Backend: http://localhost:5000"
echo "🌐 Frontend: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop both servers"

# Wait for user to stop
wait 