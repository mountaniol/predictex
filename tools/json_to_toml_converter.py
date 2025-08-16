#!/usr/bin/env python3
"""
JSON to TOML Configuration Converter
Converts app.config.json to app.config.toml format
"""

import json
import toml
import os
import sys
from typing import Dict, Any
from datetime import datetime
import shutil


def load_json_config(json_path: str) -> Dict[str, Any]:
    """Load JSON configuration file"""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_toml_config(config: Dict[str, Any], toml_path: str):
    """Save configuration as TOML file with comments"""
    
    # Create header comment
    header = f"""# QnA Evaluator Configuration
# Generated from app.config.json on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# Format: TOML v1.0.0
# Documentation: https://toml.io/

"""
    
    # Convert to TOML string
    toml_content = toml.dumps(config)
    
    # Add section comments
    toml_content = toml_content.replace('[Generic]', '# General application settings\n[Generic]')
    toml_content = toml_content.replace('[Frontend]', '\n# Frontend configuration\n[Frontend]')
    toml_content = toml_content.replace('[Backend]', '\n# Backend server configuration\n[Backend]')
    toml_content = toml_content.replace('[Backend.ollama]', '\n  # Ollama AI provider settings\n  [Backend.ollama]')
    toml_content = toml_content.replace('[Backend.openai]', '\n  # OpenAI provider settings\n  [Backend.openai]')
    toml_content = toml_content.replace('[Backend.retry_logic]', '\n  # Retry logic for API calls\n  [Backend.retry_logic]')
    toml_content = toml_content.replace('[Backend.web_search]', '\n  # Web search configuration\n  [Backend.web_search]')
    toml_content = toml_content.replace('[Backend.web_search.classification]', '\n    # Query classification settings\n    [Backend.web_search.classification]')
    toml_content = toml_content.replace('[Backend.web_search.providers.duckduckgo]', '\n    # DuckDuckGo search provider\n    [Backend.web_search.providers.duckduckgo]')
    toml_content = toml_content.replace('[Backend.web_search.providers.wikipedia]', '\n    # Wikipedia search provider\n    [Backend.web_search.providers.wikipedia]')
    toml_content = toml_content.replace('[Backend.web_search.providers.rss]', '\n    # RSS feed provider\n    [Backend.web_search.providers.rss]')
    toml_content = toml_content.replace('[Backend.web_search.cache]', '\n    # Search cache settings\n    [Backend.web_search.cache]')
    toml_content = toml_content.replace('[Backend.web_search.rate_limiting]', '\n    # Rate limiting configuration\n    [Backend.web_search.rate_limiting]')
    toml_content = toml_content.replace('[Backend.ai_web_search_integration]', '\n  # AI-powered web search integration\n  [Backend.ai_web_search_integration]')
    
    # Add inline comments for important fields
    toml_content = toml_content.replace('ai_provider = "ollama"', 'ai_provider = "ollama"  # Options: "ollama" or "openai"')
    toml_content = toml_content.replace('ai_provider = "openai"', 'ai_provider = "openai"  # Options: "ollama" or "openai"')
    toml_content = toml_content.replace('local_api_port = 3001', 'local_api_port = 3001  # Backend API port')
    toml_content = toml_content.replace('enabled = true', 'enabled = true  # Enable/disable this feature')
    toml_content = toml_content.replace('enabled = false', 'enabled = false  # Enable/disable this feature')
    
    # Write to file
    with open(toml_path, 'w', encoding='utf-8') as f:
        f.write(header + toml_content)


def create_backup(file_path: str) -> str:
    """Create a backup of the original file"""
    backup_path = file_path + '.backup'
    
    # If backup already exists, add timestamp
    if os.path.exists(backup_path):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = f"{file_path}.backup.{timestamp}"
    
    shutil.copy2(file_path, backup_path)
    return backup_path


def convert_json_to_toml(json_path: str, toml_path: str = None, create_backup_file: bool = True):
    """
    Convert JSON config to TOML format
    
    Args:
        json_path: Path to input JSON file
        toml_path: Path to output TOML file (optional)
        create_backup_file: Whether to create a backup of the original JSON
    """
    
    # Check if JSON file exists
    if not os.path.exists(json_path):
        print(f"❌ Error: JSON file not found: {json_path}")
        return False
    
    # Set default TOML path if not provided
    if toml_path is None:
        toml_path = json_path.replace('.json', '.toml')
    
    try:
        # Create backup if requested
        if create_backup_file:
            backup_path = create_backup(json_path)
            print(f"✅ Created backup: {backup_path}")
        
        # Load JSON config
        print(f"📖 Loading JSON config from: {json_path}")
        config = load_json_config(json_path)
        
        # Save as TOML
        print(f"💾 Saving TOML config to: {toml_path}")
        save_toml_config(config, toml_path)
        
        # Verify the conversion
        print(f"🔍 Verifying conversion...")
        loaded_toml = toml.load(toml_path)
        
        # Basic verification - check if main sections exist
        if all(key in loaded_toml for key in ['Generic', 'Frontend', 'Backend']):
            print(f"✅ Successfully converted {json_path} to {toml_path}")
            
            # Show file sizes
            json_size = os.path.getsize(json_path)
            toml_size = os.path.getsize(toml_path)
            print(f"📊 File sizes: JSON={json_size} bytes, TOML={toml_size} bytes")
            
            return True
        else:
            print(f"❌ Error: TOML file missing required sections")
            return False
            
    except Exception as e:
        print(f"❌ Error during conversion: {e}")
        return False


def main():
    """Main function for CLI usage"""
    
    # Default paths
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    json_path = os.path.join(project_root, 'public', 'app.config.json')
    toml_path = os.path.join(project_root, 'public', 'app.config.toml')
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        json_path = sys.argv[1]
    if len(sys.argv) > 2:
        toml_path = sys.argv[2]
    
    print("🔄 JSON to TOML Configuration Converter")
    print("=" * 50)
    
    # Perform conversion
    success = convert_json_to_toml(json_path, toml_path)
    
    if success:
        print("\n✨ Conversion completed successfully!")
        print(f"\nNext steps:")
        print(f"1. Review the generated TOML file: {toml_path}")
        print(f"2. Test the application with the new config")
        print(f"3. Update code to use TOML loader")
    else:
        print("\n❌ Conversion failed. Please check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()