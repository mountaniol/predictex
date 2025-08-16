#!/bin/bash

# Setup script for Cloudflare Tunnel with Question Creator
# This script helps configure Cloudflare Tunnel to properly proxy both frontend and backend

echo "==================================="
echo "Cloudflare Tunnel Setup for Question Creator"
echo "==================================="
echo ""

# Check if cloudflared is installed
if ! command -v cloudflared &> /dev/null; then
    echo "❌ cloudflared is not installed."
    echo "Please install it first: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/"
    exit 1
fi

echo "✅ cloudflared is installed"
echo ""

# Get current directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Create config directory if not exists
CONFIG_DIR="$HOME/.cloudflared"
mkdir -p "$CONFIG_DIR"

echo "📝 Creating Cloudflare Tunnel configuration..."
echo ""
echo "Please provide your domain name (e.g., example.com):"
read -r DOMAIN

# Create the config file
CONFIG_FILE="$CONFIG_DIR/config-question-creator.yml"

cat > "$CONFIG_FILE" << EOF
# Cloudflare Tunnel Configuration for Question Creator
# Generated on $(date)

# Uncomment and add your tunnel credentials
# tunnel: YOUR-TUNNEL-ID
# credentials-file: $CONFIG_DIR/YOUR-TUNNEL-CREDS.json

ingress:
  # Question Creator Backend API
  - hostname: $DOMAIN
    path: /api-creator
    service: http://localhost:3004
    originRequest:
      noTLSVerify: true
      connectTimeout: 30s
      
  # Main QnA Evaluator API (if needed)
  - hostname: $DOMAIN
    path: /api
    service: http://localhost:3001
    originRequest:
      noTLSVerify: true
      connectTimeout: 30s
      
  # Question Creator Frontend (and everything else)
  - hostname: $DOMAIN
    service: http://localhost:3003
    originRequest:
      noTLSVerify: true
      
  # 404 for unmatched routes
  - service: http_status:404
EOF

echo "✅ Configuration created at: $CONFIG_FILE"
echo ""

# Create .env file if it doesn't exist
ENV_FILE="$SCRIPT_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
    echo "📝 Creating .env file..."
    cat > "$ENV_FILE" << EOF
# Question Creator Environment Variables
# Generated for Cloudflare Tunnel setup

# Use proxy path for API when accessed via HTTPS
REACT_APP_API_BASE_URL=/api-creator

# Frontend port
PORT=3003

# Your domain (for reference)
# DOMAIN=$DOMAIN
EOF
    echo "✅ .env file created"
else
    echo "ℹ️  .env file already exists, skipping..."
fi

echo ""
echo "📝 Creating start script..."

# Create start script
START_SCRIPT="$SCRIPT_DIR/start-with-tunnel.sh"
cat > "$START_SCRIPT" << 'EOF'
#!/bin/bash

# Start script for Question Creator with Cloudflare Tunnel

echo "Starting Question Creator with Cloudflare Tunnel..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down services...${NC}"
    kill $(jobs -p) 2>/dev/null
    exit
}

trap cleanup EXIT INT TERM

# Start backend
echo -e "${GREEN}Starting backend server on port 3004...${NC}"
cd "$SCRIPT_DIR/backend"
python server.py &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Check if backend is running
if ! curl -s http://localhost:3004/api/providers > /dev/null; then
    echo -e "${RED}Backend failed to start!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Backend is running${NC}"

# Start frontend
echo -e "${GREEN}Starting frontend on port 3003...${NC}"
cd "$SCRIPT_DIR"

# Check if we should use production build
if [ -d "build" ] && [ "$1" == "production" ]; then
    echo "Using production build..."
    npx serve -s build -l 3003 &
else
    echo "Using development mode..."
    npm start &
fi
FRONTEND_PID=$!

# Wait for frontend to start
sleep 5

echo -e "${GREEN}✅ Frontend is running${NC}"

# Instructions for Cloudflare Tunnel
echo ""
echo "==================================="
echo -e "${GREEN}Services are running!${NC}"
echo ""
echo "Backend API: http://localhost:3004"
echo "Frontend: http://localhost:3003"
echo ""
echo -e "${YELLOW}To start Cloudflare Tunnel, run in another terminal:${NC}"
echo "cloudflared tunnel run --config ~/.cloudflared/config-question-creator.yml"
echo ""
echo "Or if you have a named tunnel:"
echo "cloudflared tunnel run YOUR-TUNNEL-NAME"
echo "==================================="
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for all background jobs
wait
EOF

chmod +x "$START_SCRIPT"
echo "✅ Start script created at: $START_SCRIPT"

echo ""
echo "==================================="
echo "✅ Setup Complete!"
echo "==================================="
echo ""
echo "Next steps:"
echo ""
echo "1. If you haven't created a tunnel yet:"
echo "   cloudflared tunnel create question-creator"
echo ""
echo "2. Update the config file with your tunnel ID:"
echo "   Edit: $CONFIG_FILE"
echo "   Add your tunnel ID and credentials file path"
echo ""
echo "3. Route your domain to the tunnel:"
echo "   cloudflared tunnel route dns question-creator $DOMAIN"
echo ""
echo "4. Start everything:"
echo "   $START_SCRIPT"
echo ""
echo "5. In another terminal, run the tunnel:"
echo "   cloudflared tunnel run --config $CONFIG_FILE"
echo ""
echo "6. Access your app at: https://$DOMAIN"
echo ""
echo "==================================="