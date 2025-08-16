# Cloudflare Tunnel Setup for Question Creator

## Problem
When using Cloudflare Tunnel to access your local machine, the Question Creator frontend (served via HTTPS through Cloudflare) cannot reach the backend API (HTTP on port 3004) due to Mixed Content restrictions.

## Solution: Configure Cloudflare Tunnel for Both Services

### Option 1: Tunnel Both Frontend and Backend (Recommended)

#### 1. Update Cloudflare Tunnel Configuration

Edit your `config.yml` or `config.yaml` file:

```yaml
tunnel: your-tunnel-id
credentials-file: /path/to/credentials.json

ingress:
  # Frontend - Question Creator UI
  - hostname: your-domain.com
    service: http://localhost:3003
    
  # Backend API - Question Creator Backend
  - hostname: your-domain.com
    path: /api-creator
    service: http://localhost:3004
    
  # Main QnA Evaluator API (if needed)
  - hostname: your-domain.com
    path: /api
    service: http://localhost:3001
    
  # Catch-all rule (required)
  - service: http_status:404
```

#### 2. Set Environment Variable

Create `.env` file in question-creator directory:

```bash
# Tell the app to use the proxied API path
REACT_APP_API_BASE_URL=/api-creator
```

#### 3. Rebuild the Application

```bash
cd /media/AI/predictex/qna-evaluator/question-creator
npm run build
```

### Option 2: Use Subdomain for API

If you prefer separate subdomains:

```yaml
ingress:
  # Frontend
  - hostname: app.your-domain.com
    service: http://localhost:3003
    
  # Backend API
  - hostname: api.your-domain.com
    service: http://localhost:3004
    
  - service: http_status:404
```

Then set:
```bash
REACT_APP_API_BASE_URL=https://api.your-domain.com
```

### Option 3: Path-Based Routing (Current Setup)

If you want to keep the current dynamic configuration, ensure your Cloudflare Tunnel config includes:

```yaml
ingress:
  # Main app
  - hostname: your-domain.com
    service: http://localhost:3003
    
  # API proxy path
  - hostname: your-domain.com
    path: /api-creator
    service: http://localhost:3004
    originRequest:
      noTLSVerify: true
    
  - service: http_status:404
```

## Quick Fix: Direct Configuration

### 1. Stop Current Services

```bash
# Stop if running
pkill -f "server.py"
```

### 2. Update Frontend Config

Edit `/media/AI/predictex/qna-evaluator/question-creator/src/config.ts`:

```typescript
export const getApiBaseUrl = (): string => {
  // For Cloudflare Tunnel, always use the proxied path
  if (window.location.hostname.includes('your-domain.com')) {
    return '/api-creator';
  }
  
  // ... rest of existing logic
};
```

### 3. Start Services

```bash
# Terminal 1: Start backend
cd /media/AI/predictex/qna-evaluator/question-creator/backend
python server.py

# Terminal 2: Start frontend (development)
cd /media/AI/predictex/qna-evaluator/question-creator
npm start

# Or serve production build
npm run build
npx serve -s build -l 3003
```

### 4. Restart Cloudflare Tunnel

```bash
# If using cloudflared service
sudo systemctl restart cloudflared

# Or if running manually
cloudflared tunnel run
```

## Testing

### 1. Verify Tunnel Status

```bash
# Check if tunnel is running
cloudflared tunnel list
cloudflared tunnel info your-tunnel-name
```

### 2. Test API Endpoint

```bash
# From outside (through Cloudflare)
curl https://your-domain.com/api-creator/api/providers

# Should return JSON with AI providers
```

### 3. Check Browser Console

Open https://your-domain.com and check console:
- Should show API URL as `/api-creator` or `https://your-domain.com/api-creator`
- No Mixed Content errors
- API calls should succeed

## Troubleshooting

### "Failed to fetch" Errors

1. **Check Cloudflare Tunnel logs**:
```bash
sudo journalctl -u cloudflared -f
# or
cloudflared tunnel run --loglevel debug
```

2. **Verify services are running**:
```bash
# Check backend
curl http://localhost:3004/api/providers

# Check frontend
curl http://localhost:3003
```

### Mixed Content Still Appears

Make sure the app is using the correct API URL:

1. **Force the URL via environment**:
```bash
export REACT_APP_API_BASE_URL=/api-creator
npm run build
```

2. **Or hardcode for Cloudflare** in `src/config.ts`:
```typescript
// At the top of getApiBaseUrl function
if (protocol === 'https:') {
  return '/api-creator';  // Always use proxy path for HTTPS
}
```

### Path Stripping Issues

If the backend receives `/api-creator/api/providers` instead of `/api/providers`, you need to strip the path:

**Option 1: Configure in Cloudflare Tunnel**:
```yaml
- hostname: your-domain.com
  path: /api-creator
  service: http://localhost:3004
  originRequest:
    noTLSVerify: true
    # This might help with path handling
    httpHostHeader: "localhost:3004"
```

**Option 2: Handle in Backend** (server.py):
```python
@app.route('/api-creator/<path:path>', methods=['GET', 'POST', 'OPTIONS'])
def proxy_api(path):
    # Forward to the actual route
    return handle_request('/' + path)
```

## Cloudflare-Specific Headers

The backend might need to handle Cloudflare headers:

```python
# In server.py, update CORS to handle Cloudflare
@app.after_request
def after_request(response):
    origin = request.headers.get('Origin')
    if origin:
        response.headers['Access-Control-Allow-Origin'] = origin
    else:
        response.headers['Access-Control-Allow-Origin'] = '*'
    
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    
    # Handle Cloudflare headers
    if request.headers.get('CF-Connecting-IP'):
        response.headers['X-Real-IP'] = request.headers.get('CF-Connecting-IP')
    
    return response
```

## Complete Working Example

### config.yml for Cloudflare Tunnel:
```yaml
tunnel: your-tunnel-id
credentials-file: ~/.cloudflared/cert.json

ingress:
  # API routes first (more specific)
  - hostname: your-domain.com
    path: /api-creator
    service: http://localhost:3004
    
  # Then frontend (catch-all for domain)
  - hostname: your-domain.com
    service: http://localhost:3003
    
  # 404 for everything else
  - service: http_status:404
```

### .env file:
```bash
REACT_APP_API_BASE_URL=/api-creator
PORT=3003
```

### Start everything:
```bash
# Terminal 1
cd backend && python server.py

# Terminal 2
cd .. && npm start

# Terminal 3
cloudflared tunnel run
```

This should resolve the Mixed Content issue when using Cloudflare Tunnel!