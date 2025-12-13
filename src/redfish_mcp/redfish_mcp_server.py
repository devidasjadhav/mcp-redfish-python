"""
Redfish MCP Server - FastMCP server exposing Redfish tools
"""

import sys
from fastmcp import FastMCP
from .client import RedfishClient
from .config import config
from .logging_config import logger, reconfigure_logging_from_config

# Reconfigure logging with loaded config
reconfigure_logging_from_config()

# Validate configuration on startup
logger.info("Validating configuration...")
validation_errors = config.validate()
if validation_errors:
    logger.error("Configuration validation failed:")
    for error in validation_errors:
        logger.error(f"  - {error}")
    logger.error("Please check your .env file or environment variables")
    sys.exit(1)

logger.info("Configuration validated successfully")
logger.debug(f"Configuration: {config.to_dict()}")

app = FastMCP(config.MCP_SERVER_NAME)

# Create shared client instance with resilience features
_client = RedfishClient(
    base_url=config.REDFISH_BASE_URL,
    timeout=config.REQUEST_TIMEOUT,
    verify_ssl=config.VERIFY_SSL,
    enable_retry=config.ENABLE_RETRY,
    enable_circuit_breaker=config.ENABLE_CIRCUIT_BREAKER
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