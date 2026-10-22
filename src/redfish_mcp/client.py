"""
Redfish Client - Shared HTTP client for Redfish operations
"""

import requests
from typing import Any, Dict, Mapping, Optional, Tuple
from urllib.parse import urljoin, urlparse

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
        circuit_breaker: Optional[CircuitBreaker] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        max_response_bytes: int = 1024 * 1024,
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
        self.max_response_bytes = max_response_bytes
        self._origin = self._url_origin(self.base_url)
        self._service_path = urlparse(self.base_url).path.rstrip("/")

        self.session = requests.Session()
        if username:
            self.session.auth = (username, password or "")

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
        if endpoint.startswith(("http://", "https://")):
            url = endpoint
        elif endpoint == self._service_path or endpoint.startswith(
            self._service_path + "/"
        ):
            parsed = urlparse(self.base_url)
            url = urljoin(f"{parsed.scheme}://{parsed.netloc}", endpoint)
        else:
            url = urljoin(self.base_url + "/", endpoint.lstrip("/"))
        if self._url_origin(url) != self._origin:
            raise RedfishClientError(
                f"Refusing off-origin Redfish URI: {url}"
            )
        return url

    @staticmethod
    def _url_origin(url: str) -> Tuple[str, str, int]:
        parsed = urlparse(url)
        default_port = 443 if parsed.scheme == "https" else 80
        return parsed.scheme.lower(), (parsed.hostname or "").lower(), parsed.port or default_port

    def _validate_response_size(self, response: requests.Response) -> None:
        response_headers = getattr(response, "headers", {})
        content_length = (
            response_headers.get("Content-Length")
            if isinstance(response_headers, Mapping)
            else None
        )
        if content_length and int(content_length) > self.max_response_bytes:
            raise RedfishClientError(
                f"Response exceeds {self.max_response_bytes} byte limit"
            )
        content = getattr(response, "content", b"")
        if isinstance(content, (bytes, bytearray)) and len(content) > self.max_response_bytes:
            raise RedfishClientError(
                f"Response exceeds {self.max_response_bytes} byte limit"
            )

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
            self._validate_response_size(response)
            response.raise_for_status()
            if response.status_code == 204 or not getattr(response, "content", True):
                return {}
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
                current_url = self._build_url(url)
                for _ in range(4):
                    response = self.session.request(
                        method,
                        current_url,
                        timeout=self.timeout,
                        verify=self.verify_ssl,
                        allow_redirects=False,
                        **kwargs
                    )
                    if response.status_code not in (301, 302, 303, 307, 308):
                        return response
                    location = response.headers.get("Location")
                    if not location:
                        return response
                    redirected_url = urljoin(current_url, location)
                    if self._url_origin(redirected_url) != self._origin:
                        raise RedfishClientError(
                            f"Refusing off-origin redirect to {redirected_url}"
                        )
                    current_url = redirected_url
                raise RedfishClientError("Too many Redfish redirects")
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

    def get_with_headers(
        self, endpoint: str
    ) -> Tuple[Dict[str, Any], Mapping[str, str], int]:
        """GET a resource and retain headers needed for Redfish preconditions."""
        url = self._build_url(endpoint)
        logger.debug(f"GET request to {url}")

        @retry_with_backoff(self.retry_config)
        def _get_with_retry():
            response = self._execute_request("GET", url)
            result = self._handle_response(response)
            return result, response.headers, response.status_code

        if self.enable_retry:
            return _get_with_retry()
        response = self._execute_request("GET", url)
        return self._handle_response(response), response.headers, response.status_code

    def get(self, endpoint: str) -> Dict[str, Any]:
        """
        Perform GET request to Redfish endpoint with resilience features.

        Args:
            endpoint: Endpoint path

        Returns:
            JSON response data
        """
        try:
            result, _, _ = self.get_with_headers(endpoint)
            return result
        except Exception as e:
            logger.error(f"GET {endpoint} failed: {e}")
            raise

    def patch_with_status(
        self,
        endpoint: str,
        data: Dict[str, Any],
        headers: Optional[Mapping[str, str]] = None,
    ) -> Tuple[Dict[str, Any], int]:
        """PATCH a resource and return its body and HTTP status."""
        url = self._build_url(endpoint)

        @retry_with_backoff(self.retry_config)
        def _patch_with_retry():
            response = self._execute_request("PATCH", url, json=data, headers=headers)
            return self._handle_response(response), response.status_code

        if self.enable_retry:
            return _patch_with_retry()
        response = self._execute_request("PATCH", url, json=data, headers=headers)
        return self._handle_response(response), response.status_code

    def patch(
        self,
        endpoint: str,
        data: Dict[str, Any],
        headers: Optional[Mapping[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Perform PATCH request to update Redfish resource with resilience features.

        Args:
            endpoint: Endpoint path
            data: JSON data to patch

        Returns:
            JSON response data (may be empty for 204 responses)
        """
        result, _ = self.patch_with_status(endpoint, data, headers)
        return result

    def post_with_status(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> Tuple[Dict[str, Any], int]:
        """POST an action and return its body and HTTP status."""
        url = self._build_url(endpoint)

        response = self._execute_request("POST", url, json=data, headers=headers)
        return self._handle_response(response), response.status_code

    def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Perform POST request to execute Redfish action with resilience features.

        Args:
            endpoint: Endpoint path
            data: JSON data for POST body (optional)

        Returns:
            JSON response data
        """
        result, _ = self.post_with_status(endpoint, data, headers)
        return result

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
