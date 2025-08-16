#!/usr/bin/env python3
"""
TOML Configuration Loader for QnA Evaluator
Loads configuration from app.config.toml
"""

import os
import toml
from typing import Dict, Any, Optional
from datetime import datetime


class ConfigLoader:
    """Configuration loader for TOML files"""
    
    def __init__(self, config_path: str = None):
        """
        Initialize config loader
        
        Args:
            config_path: Path to TOML config file (optional)
        """
        if config_path is None:
            # Default to app.config.toml in public directory
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            config_path = os.path.join(project_root, 'public', 'app.config.toml')
        
        self.config_path = config_path
        self._config = None
        self._config_mtime = None
    
    def load_config(self, force_reload: bool = False) -> Dict[str, Any]:
        """
        Load configuration from TOML file with caching
        
        Args:
            force_reload: Force reload even if cached
            
        Returns:
            Configuration dictionary
        """
        try:
            # Check if file exists
            if not os.path.exists(self.config_path):
                raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
            
            # Get file modification time
            current_mtime = os.path.getmtime(self.config_path)
            
            # Check if we need to reload (file changed or forced reload)
            if force_reload or self._config is None or current_mtime != self._config_mtime:
                print(f"📖 Loading configuration from: {self.config_path}")
                
                # Load TOML configuration
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self._config = toml.load(f)
                
                self._config_mtime = current_mtime
                print(f"✅ Configuration loaded successfully")
            
            return self._config
            
        except FileNotFoundError as e:
            print(f"❌ Configuration file not found: {e}")
            raise
        except toml.TomlDecodeError as e:
            print(f"❌ Invalid TOML format in {self.config_path}: {e}")
            raise
        except Exception as e:
            print(f"❌ Error loading configuration: {e}")
            raise
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-notation path
        
        Args:
            key_path: Dot-separated path (e.g., "Backend.ai_provider")
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        if self._config is None:
            self.load_config()
        
        keys = key_path.split('.')
        value = self._config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get entire configuration section
        
        Args:
            section: Section name (e.g., "Backend")
            
        Returns:
            Section dictionary or empty dict if not found
        """
        if self._config is None:
            self.load_config()
        
        return self._config.get(section, {})
    
    def validate_config(self) -> bool:
        """
        Validate that all required configuration sections and keys exist
        
        Returns:
            True if configuration is valid
        """
        required_sections = ['Generic', 'Frontend', 'Backend']
        required_keys = {
            'Generic': ['question_set_file', 'ai_prompt_file'],
            'Backend': ['local_api_port', 'ai_provider']
        }
        
        try:
            config = self.load_config()
            
            # Check required sections
            for section in required_sections:
                if section not in config:
                    print(f"❌ Missing required section: {section}")
                    return False
            
            # Check required keys
            for section, keys in required_keys.items():
                for key in keys:
                    if key not in config.get(section, {}):
                        print(f"❌ Missing required key: {section}.{key}")
                        return False
            
            # Validate AI provider configuration
            ai_provider = config['Backend']['ai_provider']
            if ai_provider not in ['openai', 'ollama']:
                print(f"❌ Invalid AI provider: {ai_provider}")
                return False
            
            # Check that provider config exists
            if ai_provider not in config['Backend']:
                print(f"❌ Missing configuration for AI provider: {ai_provider}")
                return False
            
            print("✅ Configuration validation passed")
            return True
            
        except Exception as e:
            print(f"❌ Configuration validation failed: {e}")
            return False


# Global instance for convenience
_config_loader = None


def get_config_loader(config_path: str = None) -> ConfigLoader:
    """
    Get global config loader instance
    
    Args:
        config_path: Path to config file (optional)
        
    Returns:
        ConfigLoader instance
    """
    global _config_loader
    
    if _config_loader is None or (config_path and config_path != _config_loader.config_path):
        _config_loader = ConfigLoader(config_path)
    
    return _config_loader


def load_app_config(config_path: str = None) -> Dict[str, Any]:
    """
    Convenience function to load app configuration
    
    Args:
        config_path: Path to config file (optional)
        
    Returns:
        Configuration dictionary
    """
    loader = get_config_loader(config_path)
    return loader.load_config()


def get_config_value(key_path: str, default: Any = None) -> Any:
    """
    Convenience function to get config value
    
    Args:
        key_path: Dot-separated path
        default: Default value
        
    Returns:
        Configuration value
    """
    loader = get_config_loader()
    return loader.get(key_path, default)