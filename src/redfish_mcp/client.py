"""
Redfish Client - Shared HTTP client for Redfish operations
"""

import json
import requests
from typing import Dict, Any, Optional
from urllib.parse import urljoin


class RedfishClient:
    """
    Shared HTTP client for Redfish API operations.

    Handles common HTTP patterns, error handling, and URL building
    used by both LangChain tools and FastMCP server.
    """

    def __init__(self, base_url: str, timeout: int = 30, verify_ssl: bool = True):
        """
        Initialize Redfish client.

        Args:
            base_url: Base URL for Redfish service (e.g., 'http://127.0.0.1:8000/redfish/v1')
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.session = requests.Session()

        # Set default headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })

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
        Handle HTTP response with appropriate error checking.

        Args:
            response: HTTP response object

        Returns:
            Parsed JSON response

        Raises:
            requests.HTTPError: For HTTP error status codes
        """
        try:
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            # Try to get error details from response
            try:
                error_data = response.json()
                error_msg = error_data.get('error', {}).get('message', str(e))
            except:
                error_msg = str(e)
            raise requests.HTTPError(f"HTTP {response.status_code}: {error_msg}") from e

    def get(self, endpoint: str) -> Dict[str, Any]:
        """
        Perform GET request to Redfish endpoint.

        Args:
            endpoint: Endpoint path

        Returns:
            JSON response data
        """
        url = self._build_url(endpoint)
        try:
            response = self.session.get(url, timeout=self.timeout, verify=self.verify_ssl)
            return self._handle_response(response)
        except requests.RequestException as e:
            raise requests.RequestException(f"Failed to GET {url}: {e}") from e

    def patch(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform PATCH request to update Redfish resource.

        Args:
            endpoint: Endpoint path
            data: JSON data to patch

        Returns:
            JSON response data (may be empty for 204 responses)
        """
        url = self._build_url(endpoint)
        try:
            response = self.session.patch(
                url,
                json=data,
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            if response.status_code == 204:
                return {}
            return self._handle_response(response)
        except requests.RequestException as e:
            raise requests.RequestException(f"Failed to PATCH {url}: {e}") from e

    def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Perform POST request to execute Redfish action.

        Args:
            endpoint: Endpoint path
            data: JSON data for POST body (optional)

        Returns:
            JSON response data
        """
        url = self._build_url(endpoint)
        try:
            response = self.session.post(
                url,
                json=data,
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            return self._handle_response(response)
        except requests.RequestException as e:
            raise requests.RequestException(f"Failed to POST {url}: {e}") from e

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