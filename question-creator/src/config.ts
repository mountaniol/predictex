// Configuration for Question Creator application

interface Config {
  // Backend API configuration
  api: {
    // Override URL if needed (set via environment variable)
    baseUrl?: string;
    // Port for local development
    localPort: number;
    // Path prefix when proxied (for production)
    proxyPath: string;
    // Timeout for API requests (ms)
    timeout: number;
  };
  
  // Feature flags
  features: {
    // Enable debug logging
    debug: boolean;
  };
}

const config: Config = {
  api: {
    // Can be overridden by REACT_APP_API_BASE_URL environment variable
    baseUrl: process.env.REACT_APP_API_BASE_URL,
    localPort: 3004,
    proxyPath: '/api-creator',
    timeout: 30000,
  },
  features: {
    debug: process.env.NODE_ENV === 'development',
  },
};

/**
 * Get the appropriate API base URL based on environment
 */
export const getApiBaseUrl = (): string => {
  // Priority 1: Environment variable override
  if (config.api.baseUrl) {
    debugLog('Using API URL from environment variable:', config.api.baseUrl);
    return config.api.baseUrl;
  }
  
  const hostname = window.location.hostname;
  const protocol = window.location.protocol;
  
  // Priority 2: Cloudflare Tunnel detection
  // Cloudflare Tunnel domains typically use HTTPS and specific patterns
  if (protocol === 'https:' && (
    hostname.includes('.trycloudflare.com') ||  // Cloudflare quick tunnels
    hostname.includes('.cloudflareaccess.com') || // Cloudflare Access
    hostname === 'creator.predictex.ai' ||        // Our custom Cloudflare domain
    hostname === 'www.predictex.ai' ||            // Main domain that might also be used
    window.location.pathname.includes('/cdn-cgi/') || // Cloudflare worker
    // Check for Cloudflare headers (these might be present)
    document.querySelector('meta[name="cf-tunnel"]') !== null
  )) {
    debugLog('Cloudflare Tunnel detected, using proxy path');
    return config.api.proxyPath;
  }
  
  // Priority 3: Local development
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    const url = `http://localhost:${config.api.localPort}`;
    debugLog('Local development mode, using:', url);
    return url;
  }
  
  // Priority 4: Local network access (preserve HTTP for local network)
  if (hostname.match(/^(192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[01])\.)/)) {
    const url = `http://${hostname}:${config.api.localPort}`;
    debugLog('Local network access, using:', url);
    return url;
  }
  
  // Priority 5: Production with HTTPS (general case)
  if (protocol === 'https:') {
    // When accessed via HTTPS, use proxy path to avoid mixed content
    // This works for Cloudflare Tunnel, Nginx proxy, or any reverse proxy
    debugLog('HTTPS detected, using proxy path:', config.api.proxyPath);
    return config.api.proxyPath;
  }
  
  // Priority 6: Default - same protocol and hostname
  const url = `${protocol}//${hostname}:${config.api.localPort}`;
  debugLog('Using default URL:', url);
  return url;
};

/**
 * Log debug messages if debug mode is enabled
 */
export const debugLog = (message: string, data?: any): void => {
  if (config.features.debug) {
    console.log(`[Question Creator] ${message}`, data || '');
  }
};

export default config;