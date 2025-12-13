"""
Redfish Tools - LangChain tools for Redfish operations
"""

from langchain.tools import tool
from .client import RedfishClient
from .config import config

# Create shared client instance with resilience features
_client = RedfishClient(
    base_url=config.REDFISH_BASE_URL,
    timeout=config.REQUEST_TIMEOUT,
    verify_ssl=config.VERIFY_SSL,
    enable_retry=config.ENABLE_RETRY,
    enable_circuit_breaker=config.ENABLE_CIRCUIT_BREAKER
)

@tool
def list_endpoints() -> str:
    """List available Redfish endpoints by querying the root service."""
    return _client.list_endpoints()

@tool
def get_endpoint_data(endpoint_url: str) -> str:
    """Get data from a specific Redfish endpoint.

    Args:
        endpoint_url: The relative path of the Redfish endpoint (e.g., '/Systems')
    """
    return _client.get_endpoint_data(endpoint_url)

@tool
def patch_resource(endpoint_url: str, patch_data: str) -> str:
    """Update a Redfish resource using PATCH.

    Args:
        endpoint_url: The relative path of the Redfish endpoint (e.g., '/Systems/1')
        patch_data: JSON string of the properties to update (e.g., '{"Description": "Updated"}')
    """
    return _client.patch_resource(endpoint_url, patch_data)

@tool
def post_action(action_url: str, action_data: str) -> str:
    """Execute a Redfish action using POST.

    Args:
        action_url: The full URL of the action endpoint (e.g., '/Systems/1/Actions/ComputerSystem.Reset')
        action_data: JSON string of the action parameters (e.g., '{"ResetType": "GracefulRestart"}')
    """
    return _client.post_action(action_url, action_data)