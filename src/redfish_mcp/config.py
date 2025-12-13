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

    # Authentication (future enhancement)
    REDFISH_USERNAME: Optional[str] = os.getenv("REDFISH_USERNAME")
    REDFISH_PASSWORD: Optional[str] = os.getenv("REDFISH_PASSWORD")

    # Anthropic API settings
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022")

    # Logging settings (future enhancement)
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: Optional[str] = os.getenv("LOG_FILE")


# Global configuration instance
config = Config()