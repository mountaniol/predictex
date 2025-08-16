# Configuration Management for Question Creator

## Central Configuration File: `config.json`

All network and service configuration is now centralized in `config.json`:

```json
{
  "backend": {
    "host": "192.168.1.50",    // Backend server IP
    "port": 3004                // Backend server port
  },
  "frontend": {
    "host": "192.168.1.50",    // Frontend server IP
    "port": 3003                // Frontend server port
  },
  "cloudflare": {
    "tunnel": {
      "hostname": "creator.predictex.ai",
      "apiPath": "/api-creator"
    }
  }
}
```

## How to Change Backend Address/Port

### 1. Edit `config.json`

```bash
nano /media/AI/predictex/qna-evaluator/question-creator/config.json
```

Change the backend host and port:
```json
"backend": {
  "host": "YOUR_IP_ADDRESS",
  "port": YOUR_PORT
}
```

### 2. Regenerate Configurations

Run the configuration generator:
```bash
cd /media/AI/predictex/qna-evaluator/question-creator
python3 cloudflare-config-generator.py
```

This will:
- Generate new Cloudflare Tunnel configuration
- Update `.env` file with correct API URL
- Show you the commands to run

### 3. Update Cloudflare Tunnel

Copy the generated configuration to your Cloudflare config:
```bash
# View generated config
cat generated-cloudflare-config.yml

# Edit your Cloudflare config
nano ~/.cloudflared/config.yml

# Restart Cloudflare
sudo systemctl restart cloudflared
```

### 4. Restart Services

```bash
# Stop current services
pkill -f server.py

# Start backend with new config
./start-backend.sh

# Rebuild and start frontend
npm run build
npm start
```

## Configuration Files Overview

| File | Purpose | Generated |
|------|---------|-----------|
| `config.json` | Master configuration | Manual |
| `.env` | Frontend environment variables | Auto-generated |
| `generated-cloudflare-config.yml` | Cloudflare Tunnel rules | Auto-generated |
| `start-backend.sh` | Backend startup script | Uses config.json |

## Quick Commands

### Change Backend to Different Port
```bash
# Edit config.json
nano config.json
# Change port from 3004 to 3005

# Regenerate configs
python3 cloudflare-config-generator.py

# Restart backend
./start-backend.sh
```

### Change Backend to Different Host
```bash
# Edit config.json
nano config.json
# Change host from 192.168.1.50 to 192.168.1.100

# Regenerate configs
python3 cloudflare-config-generator.py

# Update Cloudflare and restart
sudo systemctl restart cloudflared
```

### Test Configuration
```bash
# Test backend directly
curl http://$(python3 -c "import json; c=json.load(open('config.json')); print(f\"{c['backend']['host']}:{c['backend']['port']}\")")/api/providers

# Test through Cloudflare
curl https://creator.predictex.ai/api-creator/api/providers
```

## Environment Variables

The following environment variables are automatically set based on `config.json`:

- `REACT_APP_API_BASE_URL` - Full API URL for frontend
- `PORT` - Frontend development server port

## Backend Configuration Usage

The backend (`server.py`) automatically reads from `config.json`:

```python
# Loads automatically on startup
with open(CONFIG_FILE, 'r') as f:
    config = json.load(f)
    BACKEND_HOST = config['backend']['host']
    BACKEND_PORT = config['backend']['port']
```

## Frontend Configuration Usage

The frontend uses the `.env` file (auto-generated from `config.json`):

```javascript
// Automatically uses REACT_APP_API_BASE_URL from .env
const API_BASE_URL = getApiBaseUrl();
```

## Troubleshooting

### Backend won't start on configured port
- Check if port is already in use: `lsof -i :PORT`
- Kill existing process: `kill PID`
- Verify config.json syntax: `python3 -m json.tool config.json`

### Frontend can't connect to backend
- Regenerate .env: `python3 cloudflare-config-generator.py`
- Rebuild frontend: `npm run build`
- Check backend is running: `curl http://BACKEND_HOST:BACKEND_PORT/api/providers`

### Cloudflare Tunnel not working
- Verify ingress rules order (API path must be FIRST)
- Check tunnel is running: `sudo systemctl status cloudflared`
- Test API path: `curl https://YOUR_DOMAIN/api-creator/api/providers`