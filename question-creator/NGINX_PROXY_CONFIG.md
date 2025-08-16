# Nginx Proxy Configuration for Question Creator

## Problem
When accessing the Question Creator through HTTPS (e.g., via domain name), the browser blocks HTTP requests to the backend API due to Mixed Content security policy.

## Solution
Configure Nginx to proxy API requests from HTTPS to the HTTP backend.

## Nginx Configuration

Add the following location block to your Nginx server configuration:

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;
    
    # Your existing SSL configuration
    ssl_certificate /path/to/certificate.crt;
    ssl_certificate_key /path/to/private.key;
    
    # Proxy for main application (if needed)
    location / {
        proxy_pass http://localhost:3003;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
    
    # Proxy for Question Creator backend API
    location /api-creator/ {
        proxy_pass http://localhost:3004/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # CORS headers (if needed)
        add_header 'Access-Control-Allow-Origin' '*' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'Content-Type' always;
        
        # Handle preflight requests
        if ($request_method = 'OPTIONS') {
            return 204;
        }
    }
}
```

## Alternative: Full Backend Proxy

If you want to proxy all backend services through Nginx:

```nginx
# Main QnA Evaluator backend (port 3001)
location /api/ {
    proxy_pass http://localhost:3001/api/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

# Question Creator backend (port 3004)
location /api-creator/ {
    proxy_pass http://localhost:3004/api/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

## Environment Variables

You can override the API URL using environment variable:

```bash
# In .env file or environment
REACT_APP_API_BASE_URL=https://your-domain.com/api-creator
```

## Testing

1. **Local access** (should use direct HTTP):
   - http://localhost:3003 → http://localhost:3004

2. **Local network access** (should use direct HTTP):
   - http://192.168.1.50:3003 → http://192.168.1.50:3004

3. **HTTPS domain access** (should use proxy):
   - https://your-domain.com → https://your-domain.com/api-creator

## Troubleshooting

1. **Check API URL in browser console**:
   ```javascript
   // Open browser console and check:
   console.log('API URL:', window.API_BASE_URL);
   ```

2. **Test proxy directly**:
   ```bash
   # Test if proxy is working
   curl https://your-domain.com/api-creator/api/providers
   ```

3. **Check Nginx logs**:
   ```bash
   tail -f /var/log/nginx/error.log
   tail -f /var/log/nginx/access.log
   ```

4. **Verify backend is running**:
   ```bash
   # Check if backend is listening
   netstat -tlnp | grep 3004
   
   # Test backend directly
   curl http://localhost:3004/api/providers
   ```

## Security Considerations

1. **Restrict proxy access** if backend should not be publicly accessible:
   ```nginx
   location /api-creator/ {
       # Only allow from specific IPs
       allow 192.168.1.0/24;
       deny all;
       
       proxy_pass http://localhost:3004/;
       # ... rest of proxy config
   }
   ```

2. **Use authentication** if needed:
   ```nginx
   location /api-creator/ {
       auth_basic "Restricted Access";
       auth_basic_user_file /etc/nginx/.htpasswd;
       
       proxy_pass http://localhost:3004/;
       # ... rest of proxy config
   }
   ```

## Apply Configuration

After making changes:

```bash
# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
# or
sudo nginx -s reload
```