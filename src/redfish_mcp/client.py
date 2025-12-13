"""
Redfish Client - Shared HTTP client for Redfish operations
"""

import json
import requests
from typing import Dict, Any, Optional
from urllib.parse import urljoin

from .exceptions import (
    RedfishError, RedfishConnectionError, RedfishAuthenticationError,
    RedfishTimeoutError, RedfishServerError, RedfishClientError
)
from .circuit_breaker import CircuitBreaker
from .retry import RetryConfig, retry_with_backoff
from .logging_config import logger


class RedfishClient:
    """
    Shared HTTP client for Redfish API operations with resilience features.

    Handles common HTTP patterns, error handling, URL building, retry logic,
    and circuit breaker protection used by both LangChain tools and FastMCP server.
    """

    def __init__(
        self,
        base_url: str,
        timeout: int = 30,
        verify_ssl: bool = True,
        enable_retry: bool = True,
        enable_circuit_breaker: bool = True,
        retry_config: Optional[RetryConfig] = None,
        circuit_breaker: Optional[CircuitBreaker] = None
    ):
        """
        Initialize Redfish client with resilience features.

        Args:
            base_url: Base URL for Redfish service (e.g., 'http://127.0.0.1:8000/redfish/v1')
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates
            enable_retry: Whether to enable automatic retry with backoff
            enable_circuit_breaker: Whether to enable circuit breaker protection
            retry_config: Custom retry configuration (optional)
            circuit_breaker: Custom circuit breaker instance (optional)
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.enable_retry = enable_retry
        self.enable_circuit_breaker = enable_circuit_breaker

        self.session = requests.Session()

        # Set default headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })

        # Initialize resilience features
        self.retry_config = retry_config or RetryConfig(
            max_attempts=3,
            base_delay=1.0,
            max_delay=30.0,
            retry_on=(RedfishConnectionError, RedfishTimeoutError, RedfishServerError)
        )

        self.circuit_breaker = circuit_breaker or (
            CircuitBreaker(
                failure_threshold=5,
                recovery_timeout=60.0,
                expected_exception=(RedfishConnectionError, RedfishTimeoutError, RedfishServerError)
            ) if enable_circuit_breaker else None
        )

    def _build_url(self, endpoint: str) -> str:
        """
        Build full URL from endpoint path.

        Args:
            endpoint: Relative endpoint path (e.g., '/Systems')

        Returns:
            Full URL string
        """
        if endpoint.startswith('http'):
            return endpoint
        return urljoin(self.base_url + '/', endpoint.lstrip('/'))

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        Handle HTTP response with appropriate error checking and custom exceptions.

        Args:
            response: HTTP response object

        Returns:
            Parsed JSON response

        Raises:
            RedfishAuthenticationError: For 401/403 responses
            RedfishClientError: For 4xx client errors
            RedfishServerError: For 5xx server errors
        """
        try:
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            # Categorize errors by HTTP status code
            status_code = response.status_code

            # Try to get error details from response
            try:
                error_data = response.json()
                error_msg = error_data.get('error', {}).get('message', str(e))
            except:
                error_msg = str(e)

            # Raise appropriate custom exception
            if status_code in (401, 403):
                raise RedfishAuthenticationError(
                    f"Authentication failed: {error_msg}",
                    status_code=status_code
                ) from e
            elif 400 <= status_code < 500:
                raise RedfishClientError(
                    f"Client error: {error_msg}",
                    status_code=status_code
                ) from e
            elif status_code >= 500:
                raise RedfishServerError(
                    f"Server error: {error_msg}",
                    status_code=status_code
                ) from e
            else:
                raise RedfishError(f"HTTP {status_code}: {error_msg}", status_code=status_code) from e

    def _execute_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        Execute HTTP request with resilience features.

        Args:
            method: HTTP method (GET, POST, PATCH, etc.)
            url: Full URL to request
            **kwargs: Additional arguments for requests

        Returns:
            HTTP response object

        Raises:
            RedfishConnectionError: For connection issues
            RedfishTimeoutError: For timeout issues
        """
        def _make_request():
            try:
                response = self.session.request(
                    method,
                    url,
                    timeout=self.timeout,
                    verify=self.verify_ssl,
                    **kwargs
                )
                return response
            except requests.ConnectionError as e:
                raise RedfishConnectionError(f"Connection failed to {url}: {e}") from e
            except requests.Timeout as e:
                raise RedfishTimeoutError(f"Request timeout to {url}: {e}") from e
            except requests.RequestException as e:
                raise RedfishConnectionError(f"Request failed to {url}: {e}") from e

        # Apply circuit breaker if enabled
        if self.circuit_breaker:
            return self.circuit_breaker.call(_make_request)
        else:
            return _make_request()

    def get(self, endpoint: str) -> Dict[str, Any]:
        """
        Perform GET request to Redfish endpoint with resilience features.

        Args:
            endpoint: Endpoint path

        Returns:
            JSON response data
        """
        url = self._build_url(endpoint)
        logger.debug(f"GET request to {url}")

        @retry_with_backoff(self.retry_config)
        def _get_with_retry():
            response = self._execute_request('GET', url)
            result = self._handle_response(response)
            logger.debug(f"GET {url} successful")
            return result

        try:
            if self.enable_retry:
                return _get_with_retry()
            else:
                response = self._execute_request('GET', url)
                result = self._handle_response(response)
                logger.debug(f"GET {url} successful")
                return result
        except Exception as e:
            logger.error(f"GET {url} failed: {e}")
            raise

    def patch(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform PATCH request to update Redfish resource with resilience features.

        Args:
            endpoint: Endpoint path
            data: JSON data to patch

        Returns:
            JSON response data (may be empty for 204 responses)
        """
        url = self._build_url(endpoint)

        @retry_with_backoff(self.retry_config)
        def _patch_with_retry():
            response = self._execute_request('PATCH', url, json=data)
            if response.status_code == 204:
                return {}
            return self._handle_response(response)

        if self.enable_retry:
            return _patch_with_retry()
        else:
            response = self._execute_request('PATCH', url, json=data)
            if response.status_code == 204:
                return {}
            return self._handle_response(response)

    def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Perform POST request to execute Redfish action with resilience features.

        Args:
            endpoint: Endpoint path
            data: JSON data for POST body (optional)

        Returns:
            JSON response data
        """
        url = self._build_url(endpoint)

        @retry_with_backoff(self.retry_config)
        def _post_with_retry():
            response = self._execute_request('POST', url, json=data)
            return self._handle_response(response)

        if self.enable_retry:
            return _post_with_retry()
        else:
            response = self._execute_request('POST', url, json=data)
            return self._handle_response(response)

    def list_endpoints(self) -> str:
        """
        List available Redfish endpoints by querying the root service.

        Returns:
            Formatted string with available endpoints
        """
        try:
            data = self.get('')
            endpoints = []
            for key, value in data.items():
                if isinstance(value, dict) and "@odata.id" in value:
                    endpoints.append(f"- {key}: {value['@odata.id']}")
            return f"Available Redfish endpoints from {self.base_url}:\n" + "\n".join(endpoints)
        except Exception as e:
            return f"Error querying Redfish service: {e}"

    def get_endpoint_data(self, endpoint_url: str) -> str:
        """
        Get data from a specific Redfish endpoint.

        Args:
            endpoint_url: The relative path of the Redfish endpoint (e.g., '/Systems')

        Returns:
            String representation of JSON response
        """
        try:
            data = self.get(endpoint_url)
            return str(data)
        except Exception as e:
            return f"Error querying endpoint {endpoint_url}: {e}"

    def patch_resource(self, endpoint_url: str, patch_data: str) -> str:
        """
        Update a Redfish resource using PATCH.

        Args:
            endpoint_url: The relative path of the Redfish endpoint (e.g., '/Systems/1')
            patch_data: JSON string of the properties to update

        Returns:
            Success/error message
        """
        try:
            data = json.loads(patch_data)
            result = self.patch(endpoint_url, data)
            return f"Successfully updated resource at {self._build_url(endpoint_url)}"
        except json.JSONDecodeError:
            return "Invalid JSON in patch_data"
        except Exception as e:
            return f"Error updating resource {endpoint_url}: {e}"

    def post_action(self, action_url: str, action_data: str) -> str:
        """
        Execute a Redfish action using POST.

        Args:
            action_url: The full URL of the action endpoint
            action_data: JSON string of the action parameters

        Returns:
            Success/error message
        """
        try:
            data = json.loads(action_data) if action_data else {}
            result = self.post(action_url, data)
            url = self._build_url(action_url)
            return f"Successfully executed action at {url}. Status: {result.get('status', 'completed')}"
        except json.JSONDecodeError:
            return "Invalid JSON in action_data"
        except Exception as e:
            return f"Error executing action {action_url}: {e}"