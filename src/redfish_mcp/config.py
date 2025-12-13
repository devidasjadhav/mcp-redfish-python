"""
Configuration management for Redfish MCP
"""

import os
from typing import Optional, List
from dotenv import load_dotenv


# Load .env file if it exists (before defining Config class)
load_dotenv()


class Config:
    """Configuration settings loaded from environment variables and .env files."""

    def __init__(self):
        """Initialize configuration with current environment values."""
        # Redfish server settings
        self.REDFISH_BASE_URL: str = os.getenv("REDFISH_BASE_URL", "http://127.0.0.1:8000/redfish/v1")
        self.REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))
        self.VERIFY_SSL: bool = os.getenv("VERIFY_SSL", "true").lower() == "true"

        # Resilience settings
        self.ENABLE_RETRY: bool = os.getenv("ENABLE_RETRY", "true").lower() == "true"
        self.ENABLE_CIRCUIT_BREAKER: bool = os.getenv("ENABLE_CIRCUIT_BREAKER", "true").lower() == "true"
        self.MAX_RETRY_ATTEMPTS: int = int(os.getenv("MAX_RETRY_ATTEMPTS", "3"))
        self.RETRY_BASE_DELAY: float = float(os.getenv("RETRY_BASE_DELAY", "1.0"))
        self.RETRY_MAX_DELAY: float = float(os.getenv("RETRY_MAX_DELAY", "30.0"))
        self.CIRCUIT_BREAKER_THRESHOLD: int = int(os.getenv("CIRCUIT_BREAKER_THRESHOLD", "5"))
        self.CIRCUIT_BREAKER_TIMEOUT: float = float(os.getenv("CIRCUIT_BREAKER_TIMEOUT", "60.0"))

        # Authentication (future enhancement)
        self.REDFISH_USERNAME: Optional[str] = os.getenv("REDFISH_USERNAME")
        self.REDFISH_PASSWORD: Optional[str] = os.getenv("REDFISH_PASSWORD")

        # Anthropic API settings
        self.ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
        self.ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022")

        # Logging settings
        self.LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
        self.LOG_FILE: Optional[str] = os.getenv("LOG_FILE")

        # MCP Server settings
        self.MCP_SERVER_NAME: str = os.getenv("MCP_SERVER_NAME", "Redfish MCP Server")
        self.MCP_SERVER_VERSION: str = os.getenv("MCP_SERVER_VERSION", "1.0.0")
        self.MCP_TRANSPORT: str = os.getenv("MCP_TRANSPORT", "stdio")

    def validate(self) -> List[str]:
        """
        Validate configuration and return list of error messages.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Required settings
        if not self.REDFISH_BASE_URL:
            errors.append("REDFISH_BASE_URL is required")

        if not self.ANTHROPIC_API_KEY:
            errors.append("ANTHROPIC_API_KEY is required for chatbot functionality")

        # Value validation
        if self.REQUEST_TIMEOUT <= 0:
            errors.append("REQUEST_TIMEOUT must be positive")

        if self.MAX_RETRY_ATTEMPTS < 0:
            errors.append("MAX_RETRY_ATTEMPTS cannot be negative")

        if self.RETRY_BASE_DELAY <= 0:
            errors.append("RETRY_BASE_DELAY must be positive")

        if self.RETRY_MAX_DELAY <= self.RETRY_BASE_DELAY:
            errors.append("RETRY_MAX_DELAY must be greater than RETRY_BASE_DELAY")

        if self.CIRCUIT_BREAKER_THRESHOLD <= 0:
            errors.append("CIRCUIT_BREAKER_THRESHOLD must be positive")

        if self.CIRCUIT_BREAKER_TIMEOUT <= 0:
            errors.append("CIRCUIT_BREAKER_TIMEOUT must be positive")

        # Log level validation
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.LOG_LEVEL.upper() not in valid_log_levels:
            errors.append(f"LOG_LEVEL must be one of: {', '.join(valid_log_levels)}")

        return errors

    def to_dict(self) -> dict:
        """
        Convert configuration to dictionary for debugging/logging.

        Returns:
            Dictionary representation (with sensitive data masked)
        """
        config_dict = {}
        for key, value in self.__dict__.items():
            if not key.startswith('_'):
                if 'PASSWORD' in key or 'API_KEY' in key:
                    config_dict[key] = "***masked***" if value else None
                else:
                    config_dict[key] = value
        return config_dict


# Global configuration instance
config = Config()