# 🔧 Fix for Creator Frontend when accessed via Cloudflare

## Problem
When users access `creator.predictex.ai` from external computers, the frontend cannot connect to backend because it tries to use internal IP `192.168.1.50:3004` which is not accessible from outside.

## Solution Implemented

### 1. Updated Frontend Configuration (`src/config.ts`)
Added `creator.predictex.ai` to the list of recognized Cloudflare domains:

```typescript
if (protocol === 'https:' && (
  hostname.includes('.trycloudflare.com') ||
  hostname.includes('.cloudflareaccess.com') ||
  hostname === 'creator.predictex.ai' ||        // ← ADDED
  hostname === 'www.predictex.ai' ||            // ← ADDED
  // ...
)) {
  debugLog('Cloudflare Tunnel detected, using proxy path');
  return config.api.proxyPath;  // Returns '/api-creator'
}
```

### 2. How It Works Now

**When accessed locally (http://localhost:3003):**
- Frontend uses `http://localhost:3004` for API

**When accessed via network (http://192.168.1.50:3003):**
- Frontend uses `http://192.168.1.50:3004` for API

**When accessed via Cloudflare (https://creator.predictex.ai):**
- Frontend detects HTTPS + domain name
- Uses `/api-creator` as API path
- Full URL becomes `https://creator.predictex.ai/api-creator/api/*`
- Cloudflare proxies `/api-creator/*` → `http://192.168.1.50:3004/*`

### 3. Required Cloudflare Configuration

Your Cloudflare Tunnel config must have these rules (in this order):

```yaml
ingress:
  # API Backend for Question Creator (MUST BE FIRST!)
  - hostname: creator.predictex.ai
    path: /api-creator
    service: http://192.168.1.50:3004
    originRequest:
      httpHostHeader: 192.168.1.50:3004
      noTLSVerify: true

  # Frontend for Question Creator
  - hostname: creator.predictex.ai
    service: http://192.168.1.50:3003
    originRequest:
      httpHostHeader: 192.168.1.50:3003

  # Catch-all
  - service: http_status:404
```

### 4. Deployment Steps

1. **Build the frontend with new configuration:**
```bash
npm run build
```

2. **Serve the production build:**
```bash
npx serve -s build -p 3003
# OR use the existing npm start for development
```

3. **Ensure backend is running:**
```bash
./start-backend.sh
```

4. **Test from external computer:**
- Open `https://creator.predictex.ai`
- Check browser console for API calls
- Should see requests to `https://creator.predictex.ai/api-creator/api/*`

### 5. Debugging

If it still doesn't work, check:

1. **Browser Console (F12):**
   - Look for `[Question Creator]` debug messages
   - Check what API URL is being used
   - Look for CORS or connection errors

2. **Test API directly:**
```bash
# From external computer
curl https://creator.predictex.ai/api-creator/api/health

# Should return:
{
  "status": "healthy",
  "service": "Question Creator Backend",
  "port": 3004,
  "timestamp": "..."
}
```

3. **Check Cloudflare Tunnel logs:**
```bash
sudo journalctl -u cloudflared -f
```

4. **Verify Cloudflare config:**
```bash
cat ~/.cloudflared/config.yml
# Ensure the ingress rules are in correct order
```

## Summary

The fix ensures that when accessed via HTTPS on `creator.predictex.ai`, the frontend correctly uses the proxied API path `/api-creator` instead of trying to reach the internal IP directly. This allows external users to use the application properly through Cloudflare Tunnel.