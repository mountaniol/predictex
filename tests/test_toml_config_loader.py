#!/usr/bin/env python3
"""
Test suite for TOML configuration loader
"""

import os
import sys
import unittest
import tempfile
import toml
from unittest.mock import patch, MagicMock

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.backend.config_loader import ConfigLoader, get_config_loader, load_app_config, get_config_value


class TestConfigLoader(unittest.TestCase):
    """Test cases for TOML configuration loader"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a temporary TOML config file for testing
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False)
        self.test_config = {
            'Generic': {
                'question_set_file': 'test.json',
                'ai_prompt_file': 'test-prompt.txt'
            },
            'Frontend': {
                'api_base_url': '/api',
                'final_report_initial_rows': 30,
                'request_send_delay': 1000
            },
            'Backend': {
                'local_api_port': 3001,
                'ai_provider': 'ollama',
                'ollama': {
                    'base_url': 'http://localhost:11434',
                    'model': 'test-model',
                    'default_temperature': 0.3
                },
                'openai': {
                    'model': 'gpt-4',
                    'default_temperature': 0.3
                }
            }
        }
        
        # Write test config to temp file
        toml.dump(self.test_config, self.temp_file)
        self.temp_file.close()
        
        # Create loader instance
        self.loader = ConfigLoader(self.temp_file.name)
    
    def tearDown(self):
        """Clean up test fixtures"""
        # Remove temporary file
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)
    
    def test_load_config(self):
        """Test loading TOML configuration"""
        config = self.loader.load_config()
        
        self.assertIsNotNone(config)
        self.assertIn('Generic', config)
        self.assertIn('Backend', config)
        self.assertEqual(config['Generic']['question_set_file'], 'test.json')
        self.assertEqual(config['Backend']['ai_provider'], 'ollama')
    
    def test_config_caching(self):
        """Test that config is cached and not reloaded unnecessarily"""
        # Load config first time
        config1 = self.loader.load_config()
        
        # Load config second time (should use cache)
        with patch('builtins.open', MagicMock()) as mock_open:
            config2 = self.loader.load_config()
            # open() should not be called since config is cached
            mock_open.assert_not_called()
        
        self.assertEqual(config1, config2)
    
    def test_force_reload(self):
        """Test force reload of configuration"""
        # Load config first time
        config1 = self.loader.load_config()
        
        # Modify the config file
        self.test_config['Generic']['new_field'] = 'new_value'
        with open(self.temp_file.name, 'w') as f:
            toml.dump(self.test_config, f)
        
        # Force reload
        config2 = self.loader.load_config(force_reload=True)
        
        self.assertIn('new_field', config2['Generic'])
        self.assertEqual(config2['Generic']['new_field'], 'new_value')
    
    def test_get_value_by_path(self):
        """Test getting configuration value by dot-notation path"""
        self.loader.load_config()
        
        # Test valid paths
        value = self.loader.get('Backend.ai_provider')
        self.assertEqual(value, 'ollama')
        
        value = self.loader.get('Backend.ollama.model')
        self.assertEqual(value, 'test-model')
        
        # Test invalid path with default
        value = self.loader.get('Invalid.Path', default='default_value')
        self.assertEqual(value, 'default_value')
    
    def test_get_section(self):
        """Test getting entire configuration section"""
        self.loader.load_config()
        
        backend_section = self.loader.get_section('Backend')
        self.assertIsNotNone(backend_section)
        self.assertIn('ai_provider', backend_section)
        self.assertIn('ollama', backend_section)
        
        # Test non-existent section
        invalid_section = self.loader.get_section('NonExistent')
        self.assertEqual(invalid_section, {})
    
    def test_validate_config(self):
        """Test configuration validation"""
        # Valid config should pass
        is_valid = self.loader.validate_config()
        self.assertTrue(is_valid)
        
        # Create invalid config (missing required fields)
        invalid_config = {'Frontend': {'api_base_url': '/api'}}
        invalid_file = tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False)
        toml.dump(invalid_config, invalid_file)
        invalid_file.close()
        
        invalid_loader = ConfigLoader(invalid_file.name)
        is_valid = invalid_loader.validate_config()
        self.assertFalse(is_valid)
        
        # Clean up
        os.unlink(invalid_file.name)
    
    def test_file_not_found(self):
        """Test handling of missing configuration file"""
        loader = ConfigLoader('/non/existent/file.toml')
        
        with self.assertRaises(FileNotFoundError):
            loader.load_config()
    
    def test_invalid_toml_format(self):
        """Test handling of invalid TOML format"""
        # Create a file with invalid TOML
        invalid_file = tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False)
        invalid_file.write("This is not valid TOML format [[[")
        invalid_file.close()
        
        loader = ConfigLoader(invalid_file.name)
        
        with self.assertRaises(toml.TomlDecodeError):
            loader.load_config()
        
        # Clean up
        os.unlink(invalid_file.name)
    
    def test_global_functions(self):
        """Test global convenience functions"""
        # Test get_config_loader
        loader1 = get_config_loader(self.temp_file.name)
        loader2 = get_config_loader(self.temp_file.name)
        self.assertEqual(loader1, loader2)  # Should return same instance
        
        # Test load_app_config
        config = load_app_config(self.temp_file.name)
        self.assertIsNotNone(config)
        self.assertIn('Generic', config)
        
        # Test get_config_value
        value = get_config_value('Backend.ai_provider')
        self.assertEqual(value, 'ollama')
    
    def test_default_config_path(self):
        """Test that default config path is set correctly"""
        loader = ConfigLoader()
        expected_path = os.path.join(PROJECT_ROOT, 'public', 'app.config.toml')
        self.assertEqual(loader.config_path, expected_path)


class TestConfigIntegration(unittest.TestCase):
    """Integration tests for config loader with actual app.config.toml"""
    
    def test_load_actual_config(self):
        """Test loading the actual app.config.toml file if it exists"""
        config_path = os.path.join(PROJECT_ROOT, 'public', 'app.config.toml')
        
        if os.path.exists(config_path):
            loader = ConfigLoader(config_path)
            config = loader.load_config()
            
            # Verify structure matches expected format
            self.assertIn('Generic', config)
            self.assertIn('Backend', config)
            self.assertIn('Frontend', config)
            
            # Validate configuration
            is_valid = loader.validate_config()
            self.assertTrue(is_valid, "Actual app.config.toml should be valid")
            
            print(f"✅ Successfully loaded actual config from {config_path}")
        else:
            self.skipTest(f"app.config.toml not found at {config_path}")


if __name__ == '__main__':
    unittest.main(verbosity=2)