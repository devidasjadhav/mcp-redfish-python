"""
Redfish MCP Server - FastMCP server exposing Redfish tools
"""

from fastmcp import FastMCP
from .client import RedfishClient
from .config import config

app = FastMCP("Redfish MCP Server")

# Create shared client instance
_client = RedfishClient(
    base_url=config.REDFISH_BASE_URL,
    timeout=config.REQUEST_TIMEOUT,
    verify_ssl=config.VERIFY_SSL
)

@app.tool()
def list_endpoints() -> str:
    """List available Redfish endpoints by querying the root service."""
    return _client.list_endpoints()

@app.tool()
def get_endpoint_data(endpoint_url: str) -> str:
    """Get data from a specific Redfish endpoint.

    Args:
        endpoint_url: The relative path of the Redfish endpoint (e.g., '/Systems')
    """
    return _client.get_endpoint_data(endpoint_url)

@app.tool()
def patch_resource(endpoint_url: str, patch_data: str) -> str:
    """Update a Redfish resource using PATCH.

    Args:
        endpoint_url: The relative path of the Redfish endpoint (e.g., '/Systems/1')
        patch_data: JSON string of the properties to update (e.g., '{"Description": "Updated"}')
    """
    return _client.patch_resource(endpoint_url, patch_data)

@app.tool()
def post_action(action_url: str, action_data: str) -> str:
    """Execute a Redfish action using POST.

    Args:
        action_url: The full URL of the action endpoint (e.g., '/Systems/1/Actions/ComputerSystem.Reset')
        action_data: JSON string of the action parameters (e.g., '{"ResetType": "GracefulRestart"}')
    """
    return _client.post_action(action_url, action_data)

if __name__ == "__main__":
    app.run()