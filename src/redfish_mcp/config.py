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

        # Learned contract settings
        self.CONTRACT_SQLITE_PATH: str = os.getenv(
            "CONTRACT_SQLITE_PATH", ".redfish_contracts.sqlite3"
        )
        self.REDIS_URL: Optional[str] = os.getenv("REDIS_URL")
        self.CONTRACT_PROBE_TTL_SECONDS: int = int(
            os.getenv("CONTRACT_PROBE_TTL_SECONDS", "30")
        )
        self.CONTRACT_REFRESH_TTL_SECONDS: int = int(
            os.getenv("CONTRACT_REFRESH_TTL_SECONDS", "300")
        )
        self.CANDIDATE_TTL_SECONDS: int = int(
            os.getenv("CANDIDATE_TTL_SECONDS", "300")
        )
        self.EXPLORE_MAX_RESOURCES: int = int(
            os.getenv("EXPLORE_MAX_RESOURCES", "200")
        )
        self.EXPLORE_MAX_DEPTH: int = int(os.getenv("EXPLORE_MAX_DEPTH", "8"))
        self.EXPLORE_MAX_ACTIONS: int = int(os.getenv("EXPLORE_MAX_ACTIONS", "16"))
        self.MAX_RESPONSE_BYTES: int = int(os.getenv("MAX_RESPONSE_BYTES", "1048576"))

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

    def validate(self, require_anthropic: bool = True) -> List[str]:
        """
        Validate configuration and return list of error messages.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Required settings
        if not self.REDFISH_BASE_URL:
            errors.append("REDFISH_BASE_URL is required")

        if require_anthropic and not self.ANTHROPIC_API_KEY:
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

        if self.CONTRACT_PROBE_TTL_SECONDS < 0:
            errors.append("CONTRACT_PROBE_TTL_SECONDS cannot be negative")

        if self.CONTRACT_REFRESH_TTL_SECONDS <= 0:
            errors.append("CONTRACT_REFRESH_TTL_SECONDS must be positive")

        if self.CANDIDATE_TTL_SECONDS <= 0:
            errors.append("CANDIDATE_TTL_SECONDS must be positive")

        if self.EXPLORE_MAX_RESOURCES <= 0:
            errors.append("EXPLORE_MAX_RESOURCES must be positive")

        if self.EXPLORE_MAX_DEPTH <= 0:
            errors.append("EXPLORE_MAX_DEPTH must be positive")

        if self.EXPLORE_MAX_ACTIONS <= 0:
            errors.append("EXPLORE_MAX_ACTIONS must be positive")

        if self.MAX_RESPONSE_BYTES <= 0:
            errors.append("MAX_RESPONSE_BYTES must be positive")

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