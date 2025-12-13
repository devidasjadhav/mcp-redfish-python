#!/usr/bin/env python3

"""
Unit tests for configuration management
"""

import unittest
import os
import tempfile
from unittest.mock import patch, mock_open
from src.redfish_mcp.config import Config


class TestConfig(unittest.TestCase):
    """Test configuration management functionality."""

    def setUp(self):
        """Set up test environment."""
        # Clear any existing environment variables for clean testing
        env_vars_to_clear = [
            'REDFISH_BASE_URL', 'REQUEST_TIMEOUT', 'VERIFY_SSL',
            'ENABLE_RETRY', 'ENABLE_CIRCUIT_BREAKER', 'ANTHROPIC_API_KEY',
            'LOG_LEVEL', 'MCP_SERVER_NAME'
        ]
        for var in env_vars_to_clear:
            os.environ.pop(var, None)

    def test_default_config(self):
        """Test default configuration values."""
        config = Config()

        # Test default values
        self.assertEqual(config.REDFISH_BASE_URL, "http://127.0.0.1:8000/redfish/v1")
        self.assertEqual(config.REQUEST_TIMEOUT, 30)
        self.assertTrue(config.VERIFY_SSL)
        self.assertTrue(config.ENABLE_RETRY)
        self.assertTrue(config.ENABLE_CIRCUIT_BREAKER)
        self.assertEqual(config.MAX_RETRY_ATTEMPTS, 3)
        self.assertEqual(config.ANTHROPIC_MODEL, "claude-3-5-haiku-20241022")
        self.assertEqual(config.LOG_LEVEL, "INFO")
        self.assertEqual(config.MCP_SERVER_NAME, "Redfish MCP Server")

    def test_env_override(self):
        """Test environment variable overrides."""
        with patch.dict(os.environ, {
            'REDFISH_BASE_URL': 'http://test-server:9000/redfish/v1',
            'REQUEST_TIMEOUT': '60',
            'VERIFY_SSL': 'false',
            'ENABLE_RETRY': 'false',
            'LOG_LEVEL': 'DEBUG',
            'MCP_SERVER_NAME': 'Test Server'
        }):
            config = Config()
            self.assertEqual(config.REDFISH_BASE_URL, "http://test-server:9000/redfish/v1")
            self.assertEqual(config.REQUEST_TIMEOUT, 60)
            self.assertFalse(config.VERIFY_SSL)
            self.assertFalse(config.ENABLE_RETRY)
            self.assertEqual(config.LOG_LEVEL, "DEBUG")
            self.assertEqual(config.MCP_SERVER_NAME, "Test Server")

    def test_validation_valid_config(self):
        """Test validation with valid configuration."""
        with patch.dict(os.environ, {
            'ANTHROPIC_API_KEY': 'test-key',
            'REDFISH_BASE_URL': 'http://valid-url'
        }):
            config = Config()
            errors = config.validate()
            self.assertEqual(len(errors), 0)

    def test_validation_missing_required(self):
        """Test validation with missing required fields."""
        config = Config()
        # Clear required fields
        config.ANTHROPIC_API_KEY = None
        config.REDFISH_BASE_URL = ""

        errors = config.validate()
        self.assertIn("ANTHROPIC_API_KEY is required for chatbot functionality", errors)
        self.assertIn("REDFISH_BASE_URL is required", errors)

    def test_validation_invalid_values(self):
        """Test validation with invalid values."""
        with patch.dict(os.environ, {
            'ANTHROPIC_API_KEY': 'test-key',
            'REQUEST_TIMEOUT': '-1',
            'MAX_RETRY_ATTEMPTS': '-5',
            'RETRY_BASE_DELAY': '0',
            'RETRY_MAX_DELAY': '0.5',  # Less than base delay
            'LOG_LEVEL': 'INVALID'
        }):
            config = Config()
            errors = config.validate()

            self.assertIn("REQUEST_TIMEOUT must be positive", errors)
            self.assertIn("MAX_RETRY_ATTEMPTS cannot be negative", errors)
            self.assertIn("RETRY_BASE_DELAY must be positive", errors)
            self.assertIn("RETRY_MAX_DELAY must be greater than RETRY_BASE_DELAY", errors)
            self.assertIn("LOG_LEVEL must be one of", errors)

    def test_to_dict_masks_sensitive_data(self):
        """Test that to_dict masks sensitive information."""
        with patch.dict(os.environ, {
            'ANTHROPIC_API_KEY': 'secret-key',
            'REDFISH_PASSWORD': 'secret-password',
            'REDFISH_USERNAME': 'test-user'
        }):
            config = Config()
            config_dict = config.to_dict()

            # Sensitive data should be masked
            self.assertEqual(config_dict['ANTHROPIC_API_KEY'], "***masked***")
            self.assertEqual(config_dict['REDFISH_PASSWORD'], "***masked***")

            # Non-sensitive data should be visible
            self.assertEqual(config_dict['REDFISH_USERNAME'], 'test-user')
            self.assertEqual(config_dict['REQUEST_TIMEOUT'], 30)

    def test_dotenv_loading(self):
        """Test that dotenv.load_dotenv is available."""
        # Just test that the Config class can be instantiated
        # dotenv.load_dotenv is called at module level
        config = Config()
        self.assertIsInstance(config, Config)


if __name__ == '__main__':
    unittest.main()