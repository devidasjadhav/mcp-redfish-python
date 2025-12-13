"""
Custom exceptions for Redfish MCP operations
"""

from typing import Optional, Dict, Any


class RedfishError(Exception):
    """Base exception for all Redfish-related errors."""

    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details or {}


class RedfishConnectionError(RedfishError):
    """Raised when unable to connect to Redfish server."""
    pass


class RedfishAuthenticationError(RedfishError):
    """Raised when authentication fails."""
    pass


class RedfishTimeoutError(RedfishError):
    """Raised when requests timeout."""
    pass


class RedfishServerError(RedfishError):
    """Raised when server returns 5xx errors."""
    pass


class RedfishClientError(RedfishError):
    """Raised when client sends invalid requests (4xx errors)."""
    pass


class RedfishValidationError(RedfishError):
    """Raised when request/response validation fails."""
    pass


class RedfishCircuitBreakerError(RedfishError):
    """Raised when circuit breaker is open."""
    pass