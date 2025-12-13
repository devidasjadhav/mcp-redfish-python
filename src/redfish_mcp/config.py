"""
Configuration management for Redfish MCP
"""

import os
from typing import Optional


class Config:
    """Configuration settings loaded from environment variables."""

    # Redfish server settings
    REDFISH_BASE_URL: str = os.getenv("REDFISH_BASE_URL", "http://127.0.0.1:8000/redfish/v1")
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))
    VERIFY_SSL: bool = os.getenv("VERIFY_SSL", "true").lower() == "true"

    # Resilience settings
    ENABLE_RETRY: bool = os.getenv("ENABLE_RETRY", "true").lower() == "true"
    ENABLE_CIRCUIT_BREAKER: bool = os.getenv("ENABLE_CIRCUIT_BREAKER", "true").lower() == "true"
    MAX_RETRY_ATTEMPTS: int = int(os.getenv("MAX_RETRY_ATTEMPTS", "3"))
    RETRY_BASE_DELAY: float = float(os.getenv("RETRY_BASE_DELAY", "1.0"))
    RETRY_MAX_DELAY: float = float(os.getenv("RETRY_MAX_DELAY", "30.0"))
    CIRCUIT_BREAKER_THRESHOLD: int = int(os.getenv("CIRCUIT_BREAKER_THRESHOLD", "5"))
    CIRCUIT_BREAKER_TIMEOUT: float = float(os.getenv("CIRCUIT_BREAKER_TIMEOUT", "60.0"))

    # Authentication (future enhancement)
    REDFISH_USERNAME: Optional[str] = os.getenv("REDFISH_USERNAME")
    REDFISH_PASSWORD: Optional[str] = os.getenv("REDFISH_PASSWORD")

    # Anthropic API settings
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022")

    # Logging settings
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: Optional[str] = os.getenv("LOG_FILE")


# Global configuration instance
config = Config()