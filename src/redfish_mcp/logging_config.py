"""
Logging configuration for Redfish MCP
"""

import logging
import sys
from typing import Optional, TextIO


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    format_string: Optional[str] = None,
    console_stream: Optional[TextIO] = None
) -> logging.Logger:
    """
    Set up logging configuration for the application.

    The MCP stdio transport reserves stdout for JSON-RPC messages, so
    console logging defaults to stderr.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
        format_string: Optional custom format string
        console_stream: Optional stream for console output (defaults to
            stderr, keeping stdout free for MCP framing)

    Returns:
        Configured logger instance
    """
    # Convert string level to logging level
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Default format
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Configure formatter
    formatter = logging.Formatter(format_string)

    # Get or create logger
    logger = logging.getLogger("redfish_mcp")
    logger.setLevel(numeric_level)

    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Console handler (stderr by default so stdout stays clean for MCP)
    console_handler = logging.StreamHandler(
        console_stream if console_stream is not None else sys.stderr
    )
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(numeric_level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except (OSError, IOError) as e:
            # Use print since logger might not be fully set up yet; stderr
            # keeps stdout free for MCP framing.
            print(
                f"Warning: Could not create log file {log_file}: {e}",
                file=sys.stderr,
            )

    return logger


# Global logger instance (will be reconfigured when config is loaded)
logger = setup_logging(
    level="INFO",  # Default level until config is loaded
    log_file=None
)


def reconfigure_logging_from_config():
    """
    Reconfigure logging using the loaded configuration.
    This should be called after config is loaded.
    """
    try:
        # Import here to avoid circular imports
        from .config import config
        global logger
        logger = setup_logging(
            level=config.LOG_LEVEL,
            log_file=config.LOG_FILE
        )
    except ImportError:
        # Config not loaded yet, keep default logger
        pass