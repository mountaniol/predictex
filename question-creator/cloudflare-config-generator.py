#!/usr/bin/env python3
"""
Generate Cloudflare Tunnel configuration from config.toml
"""

import toml
import yaml
import sys
import os

def generate_cloudflare_config():
    """Generate Cloudflare Tunnel configuration based on config.toml"""
    
    # Load config.toml
    config_file = os.path.join(os.path.dirname(__file__), 'config.toml')
    
    try:
        with open(config_file, 'r') as f:
            config = toml.load(f)
    except FileNotFoundError:
        print(f"❌ Error: config.toml not found at {config_file}")
        sys.exit(1)
    except toml.TomlDecodeError as e:
        print(f"❌ Error parsing config.toml: {e}")
        sys.exit(1)
    
    # Extract configuration
    backend_host = config['backend']['host']
    backend_port = config['backend']['port']
    frontend_host = config['frontend']['host']
    frontend_port = config['frontend']['port']
    hostname = config['cloudflare']['tunnel']['hostname']
    api_path = config['cloudflare']['tunnel']['api_path']
    # Use backend_service from cloudflare.tunnel if specified, otherwise construct from backend
    backend_service = config['cloudflare']['tunnel'].get('backend_service', f"http://{backend_host}:{backend_port}")
    frontend_service = config['cloudflare']['tunnel'].get('frontend_service', f"http://{frontend_host}:{frontend_port}")
    
    # Generate Cloudflare ingress rules
    print("\n" + "="*60)
    print("📋 CLOUDFLARE TUNNEL CONFIGURATION")
    print("="*60)
    print("\nAdd these rules to your Cloudflare Tunnel config:")
    print("(Usually in ~/.cloudflared/config.yml)")
    print("\n" + "-"*60)
    print("```yaml")
    
    ingress_config = f"""ingress:
  # API Backend for Question Creator (MUST BE FIRST!)
  - hostname: {hostname}
    path: {api_path}
    service: {backend_service}
    originRequest:
      noTLSVerify: true

  # Frontend for Question Creator
  - hostname: {hostname}
    service: {frontend_service}

  # Your other rules...
  # - hostname: www.predictex.ai
  #   service: http://127.0.0.1:3000
  #   ...
  
  # Catch-all (required)
  - service: http_status:404"""
    
    print(ingress_config)
    print("```")
    print("-"*60)
    
    # Generate environment variables for frontend
    print("\n📋 FRONTEND ENVIRONMENT CONFIGURATION")
    print("="*60)
    print("\nCreate or update .env file in question-creator directory:")
    print("-"*60)
    
    env_config = f"""# Question Creator Environment Variables
# Generated from config.toml

# API URL for production (HTTPS via Cloudflare)
REACT_APP_API_BASE_URL=https://{hostname}{api_path}

# Frontend port
PORT={frontend_port}

# Backend configuration (for reference)
# Backend runs on {backend_host}:{backend_port}"""
    
    print(env_config)
    print("-"*60)
    
    # Commands to run
    print("\n📋 COMMANDS TO RUN")
    print("="*60)
    print()
    print("1. Update Cloudflare Tunnel configuration:")
    print("   nano ~/.cloudflared/config.yml")
    print()
    print("2. Restart Cloudflare Tunnel:")
    print("   sudo systemctl restart cloudflared")
    print("   # or")
    print("   cloudflared tunnel run")
    print()
    print("3. Start Backend:")
    print(f"   cd {os.path.dirname(__file__)}")
    print("   ./start-backend.sh")
    print()
    print("4. Start Frontend:")
    print(f"   cd {os.path.dirname(__file__)}")
    print("   npm start")
    print("   # or for production:")
    print("   npm run build && npx serve -s build -p " + str(frontend_port))
    print()
    print("5. Test:")
    print(f"   curl http://{backend_host}:{backend_port}/api/providers")
    print(f"   curl https://{hostname}{api_path}/api/providers")
    print()
    print("="*60)
    
    # Save to file
    output_file = os.path.join(os.path.dirname(__file__), 'generated-cloudflare-config.yml')
    with open(output_file, 'w') as f:
        f.write("# Generated Cloudflare Tunnel Configuration\n")
        f.write("# Copy this to your Cloudflare config file\n")
        f.write("# Generated from config.toml\n\n")
        f.write(ingress_config)
    
    print(f"\n✅ Configuration saved to: {output_file}")
    
    # Update .env file
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    with open(env_file, 'w') as f:
        f.write(env_config)
    
    print(f"✅ Environment file updated: {env_file}")
    print()
    
    # Show current configuration
    print("📋 CURRENT CONFIGURATION (from config.toml)")
    print("="*60)
    print(f"Backend:    {backend_host}:{backend_port}")
    print(f"Frontend:   {frontend_host}:{frontend_port}")
    print(f"Cloudflare: {hostname}")
    print(f"API Path:   {api_path}")
    print("="*60)

if __name__ == "__main__":
    generate_cloudflare_config()