# Question Creator Deployment Guide

## Quick Start

### Development (Local)
```bash
# Start backend
cd backend
python server.py

# Start frontend (different terminal)
npm start
```
Access: http://localhost:3003

### Production Build
```bash
npm run build
# Files will be in build/ directory
```

## HTTPS Deployment

### Problem
When serving the app over HTTPS, browsers block HTTP API calls (Mixed Content).

### Solution: Configure Nginx Proxy

1. **Add to Nginx config** (`/etc/nginx/sites-available/your-site`):
```nginx
# Proxy API requests from HTTPS to HTTP backend
location /api-creator/ {
    proxy_pass http://localhost:3004/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

2. **Test and reload Nginx**:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

3. **Verify**:
- Access https://your-domain.com
- Check browser console for API URL
- Should see requests to `/api-creator/` path

## Environment Configuration

### Using Environment Variables
Create `.env` file:
```bash
# Override API URL if needed
REACT_APP_API_BASE_URL=https://your-domain.com/api-creator

# Development server port
PORT=3003
```

### Dynamic URL Detection
The app automatically detects and uses appropriate API URL:

| Access Method | Frontend URL | API URL |
|--------------|-------------|---------|
| Local Dev | http://localhost:3003 | http://localhost:3004 |
| Local Network | http://192.168.x.x:3003 | http://192.168.x.x:3004 |
| HTTPS Domain | https://domain.com | https://domain.com/api-creator |

## Backend Setup

### Start Backend Server
```bash
cd backend
python server.py
# Runs on port 3004
```

### Backend Requirements
```bash
pip install flask flask-cors requests
```

### Verify Backend
```bash
# Check if running
curl http://localhost:3004/api/providers

# Should return JSON with AI providers
```

## Troubleshooting

### Mixed Content Error
**Symptom**: "Mixed Content: The page was loaded over HTTPS..."

**Solution**: Configure Nginx proxy (see above) or set REACT_APP_API_BASE_URL

### Failed to Connect to Parser Service
**Symptom**: "Failed to connect to parser service"

**Check**:
1. Backend is running: `ps aux | grep server.py`
2. Port is open: `netstat -tlnp | grep 3004`
3. API URL is correct: Check browser console
4. CORS is enabled: Backend should have CORS headers

### API Calls Failing
**Debug Steps**:
1. Open browser Developer Tools
2. Check Console for errors
3. Check Network tab for failed requests
4. Verify API URL in console logs
5. Test API directly: `curl [API_URL]/api/providers`

## Security Notes

1. **Production**: Always use HTTPS for public deployment
2. **API Access**: Consider restricting backend access in Nginx
3. **Authentication**: Add if needed for sensitive deployments
4. **CORS**: Configure appropriately for your domain

## File Structure
```
question-creator/
├── src/
│   ├── App.tsx           # Main app component
│   ├── config.ts         # Configuration and API URL logic
│   └── components/       # React components
├── backend/
│   └── server.py         # Python Flask backend
├── build/               # Production build (after npm run build)
├── .env.example         # Environment variables template
└── NGINX_PROXY_CONFIG.md # Detailed Nginx setup
```

## Support Files
- `MIXED_CONTENT_FIX.md` - Detailed explanation of HTTPS fix
- `NGINX_PROXY_CONFIG.md` - Complete Nginx configuration guide
- `.env.example` - Environment variable template