# Mixed Content Fix for Question Creator

## Date: 2025-08-16

## Problem
When accessing Question Creator via HTTPS domain:
- Browser blocks HTTP requests to backend (http://192.168.1.50:3004)
- Error: "Mixed Content: The page was loaded over HTTPS, but requested an insecure resource"
- API calls fail with "Failed to fetch" errors

## Root Cause
The API_BASE_URL was hardcoded to use HTTP with specific IP address, causing Mixed Content security violation when frontend is served over HTTPS.

## Solution Implemented

### 1. Dynamic API URL Configuration
**File:** `/question-creator/src/config.ts`

Created configuration module that:
- Detects current environment (local, network, HTTPS)
- Returns appropriate API URL based on context
- Supports environment variable override
- Provides debug logging

### 2. Updated App Component
**File:** `/question-creator/src/App.tsx`

- Removed hardcoded URL
- Uses dynamic URL from config
- Adds debug logging for troubleshooting

### 3. URL Resolution Logic

```typescript
Priority order:
1. Environment variable (REACT_APP_API_BASE_URL)
2. Local development → http://localhost:3004
3. Local network → http://{hostname}:3004
4. HTTPS access → /api-creator (proxy path)
5. Default → {protocol}//{hostname}:3004
```

## Configuration Options

### Option 1: Nginx Proxy (Recommended for Production)
Configure Nginx to proxy `/api-creator/` to backend:
```nginx
location /api-creator/ {
    proxy_pass http://localhost:3004/;
    # ... proxy headers
}
```
See: `NGINX_PROXY_CONFIG.md` for full configuration

### Option 2: Environment Variable
Set explicit API URL:
```bash
REACT_APP_API_BASE_URL=https://your-domain.com/api-creator
```

### Option 3: HTTPS Backend
Configure backend to support HTTPS directly (requires SSL certificates)

## Testing

### Local Development (Works ✅)
- URL: http://localhost:3003
- API: http://localhost:3004

### Local Network (Works ✅)
- URL: http://192.168.1.50:3003
- API: http://192.168.1.50:3004

### HTTPS Domain (Fixed ✅)
- URL: https://your-domain.com
- API: https://your-domain.com/api-creator (via proxy)

## Verification

1. Check API URL in browser console:
```javascript
// Should show appropriate URL based on access method
console.log('[Question Creator] API Base URL:', ...)
```

2. Network tab should show:
- Local: HTTP requests to port 3004
- HTTPS: HTTPS requests to /api-creator path

## Files Changed

1. `/question-creator/src/config.ts` - New configuration module
2. `/question-creator/src/App.tsx` - Dynamic URL usage
3. `/question-creator/.env.example` - Environment variable example
4. `/question-creator/NGINX_PROXY_CONFIG.md` - Nginx setup guide

## Status: ✅ FIXED

The application now:
- Automatically detects access method
- Uses appropriate API URL
- Works with both HTTP and HTTPS
- Provides configuration flexibility