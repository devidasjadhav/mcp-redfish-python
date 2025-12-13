#!/usr/bin/env python3

"""
Unit tests for Redfish MCP resilience features
"""

import unittest
import time
from unittest.mock import Mock, patch, MagicMock
import requests

from src.redfish_mcp.exceptions import (
    RedfishError, RedfishConnectionError, RedfishAuthenticationError,
    RedfishTimeoutError, RedfishServerError, RedfishClientError
)
from src.redfish_mcp.circuit_breaker import CircuitBreaker, CircuitBreakerState
from src.redfish_mcp.retry import RetryConfig, retry_with_backoff, calculate_backoff_delay


class TestRedfishExceptions(unittest.TestCase):
    """Test custom Redfish exception classes."""

    def test_redfish_error_creation(self):
        """Test basic RedfishError creation."""
        error = RedfishError("Test error", status_code=404, details={"key": "value"})
        self.assertEqual(str(error), "Test error")
        self.assertEqual(error.status_code, 404)
        self.assertEqual(error.details, {"key": "value"})

    def test_specific_exceptions(self):
        """Test specific exception types."""
        auth_error = RedfishAuthenticationError("Auth failed", status_code=401)
        self.assertIsInstance(auth_error, RedfishError)
        self.assertEqual(auth_error.status_code, 401)

        conn_error = RedfishConnectionError("Connection failed")
        self.assertIsInstance(conn_error, RedfishError)

        timeout_error = RedfishTimeoutError("Timeout occurred")
        self.assertIsInstance(timeout_error, RedfishError)


class TestCircuitBreaker(unittest.TestCase):
    """Test circuit breaker functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.cb = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=1.0,  # Short timeout for testing
            expected_exception=ValueError
        )

    def test_initial_state(self):
        """Test initial circuit breaker state."""
        self.assertEqual(self.cb.state, CircuitBreakerState.CLOSED)
        self.assertEqual(self.cb._failure_count, 0)

    def test_successful_call(self):
        """Test successful call doesn't change state."""
        result = self.cb.call(lambda: "success")
        self.assertEqual(result, "success")
        self.assertEqual(self.cb.state, CircuitBreakerState.CLOSED)
        self.assertEqual(self.cb._failure_count, 0)

    def test_failure_threshold(self):
        """Test circuit opens after failure threshold."""
        with self.assertRaises(ValueError):
            self.cb.call(lambda: (_ for _ in ()).throw(ValueError("test")))

        # Should still be closed after 1 failure
        self.assertEqual(self.cb.state, CircuitBreakerState.CLOSED)
        self.assertEqual(self.cb._failure_count, 1)

        # After threshold failures, should open
        for _ in range(2):
            with self.assertRaises(ValueError):
                self.cb.call(lambda: (_ for _ in ()).throw(ValueError("test")))

        self.assertEqual(self.cb.state, CircuitBreakerState.OPEN)
        self.assertEqual(self.cb._failure_count, 3)

    def test_open_circuit_blocks_calls(self):
        """Test that open circuit blocks new calls."""
        # Force circuit open
        self.cb._failure_count = 3
        self.cb._state = CircuitBreakerState.OPEN

        with self.assertRaises(RedfishError):  # Should raise circuit breaker error
            self.cb.call(lambda: "should not execute")

    def test_half_open_recovery(self):
        """Test circuit recovery from half-open state."""
        # Force circuit open
        self.cb._failure_count = 3
        self.cb._state = CircuitBreakerState.OPEN
        self.cb._last_failure_time = time.time() - 2  # Past recovery timeout

        # Should attempt recovery
        result = self.cb.call(lambda: "recovered")
        self.assertEqual(result, "recovered")
        self.assertEqual(self.cb.state, CircuitBreakerState.CLOSED)
        self.assertEqual(self.cb._failure_count, 0)


class TestRetryLogic(unittest.TestCase):
    """Test retry logic with exponential backoff."""

    def test_calculate_backoff_delay(self):
        """Test backoff delay calculation."""
        delay = calculate_backoff_delay(0)  # First attempt
        self.assertGreaterEqual(delay, 0.5)
        self.assertLessEqual(delay, 1.0)

        delay = calculate_backoff_delay(1)  # Second attempt
        self.assertGreaterEqual(delay, 1.0)
        self.assertLessEqual(delay, 2.0)

    def test_retry_config(self):
        """Test retry configuration."""
        config = RetryConfig(max_attempts=5, base_delay=2.0, max_delay=60.0)
        self.assertEqual(config.max_attempts, 5)
        self.assertEqual(config.base_delay, 2.0)
        self.assertEqual(config.max_delay, 60.0)

    @patch('time.sleep')
    def test_retry_decorator_success(self, mock_sleep):
        """Test retry decorator with eventual success."""
        call_count = 0

        @retry_with_backoff(RetryConfig(max_attempts=3, base_delay=0.1))
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"

        result = flaky_function()
        self.assertEqual(result, "success")
        self.assertEqual(call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)  # 2 retries

    @patch('time.sleep')
    def test_retry_decorator_failure(self, mock_sleep):
        """Test retry decorator with persistent failure."""
        call_count = 0

        @retry_with_backoff(RetryConfig(max_attempts=3, base_delay=0.1))
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ValueError("Persistent failure")

        with self.assertRaises(ValueError):
            always_fails()

        self.assertEqual(call_count, 3)  # All attempts exhausted
        self.assertEqual(mock_sleep.call_count, 2)  # 2 retries


class TestRedfishClient(unittest.TestCase):
    """Test RedfishClient with resilience features."""

    def setUp(self):
        """Set up test fixtures."""
        from src.redfish_mcp.client import RedfishClient
        self.client = RedfishClient(
            base_url="http://test-server/redfish/v1",
            enable_retry=False,  # Disable for unit testing
            enable_circuit_breaker=False
        )

    def test_url_building(self):
        """Test URL building logic."""
        self.assertEqual(
            self.client._build_url("/Systems"),
            "http://test-server/redfish/v1/Systems"
        )
        self.assertEqual(
            self.client._build_url("http://external.com/test"),
            "http://external.com/test"
        )

    @patch('requests.Session.request')
    def test_successful_get(self, mock_request):
        """Test successful GET request."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"test": "data"}
        mock_request.return_value = mock_response

        result = self.client.get("/test")
        self.assertEqual(result, {"test": "data"})
        mock_request.assert_called_once()

    @patch('requests.Session.request')
    def test_error_handling(self, mock_request):
        """Test error response handling."""
        from src.redfish_mcp.exceptions import RedfishServerError

        # Mock server error response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": {"message": "Server error"}}
        mock_request.return_value = mock_response

        with self.assertRaises(RedfishServerError) as cm:
            self.client.get("/test")

        self.assertEqual(cm.exception.status_code, 500)
        self.assertIn("Server error", str(cm.exception))


if __name__ == '__main__':
    unittest.main()