"""
Redfish MCP Server - FastMCP server exposing Redfish tools
"""

import sys
from typing import Any, Dict, Optional

from fastmcp import FastMCP
from .capability_service import create_capability_service
from .config import config
from .logging_config import logger, reconfigure_logging_from_config

# Reconfigure logging with loaded config
reconfigure_logging_from_config()

# Validate configuration on startup
logger.info("Validating configuration...")
validation_errors = config.validate(require_anthropic=False)
if validation_errors:
    logger.error("Configuration validation failed:")
    for error in validation_errors:
        logger.error(f"  - {error}")
    logger.error("Please check your .env file or environment variables")
    sys.exit(1)

logger.info("Configuration validated successfully")
logger.debug(f"Configuration: {config.to_dict()}")

app = FastMCP(config.MCP_SERVER_NAME)

_service = create_capability_service()

@app.tool()
def list_endpoints() -> str:
    """List available Redfish endpoints by querying the root service."""
    return _service.list_endpoints()

@app.tool()
def get_endpoint_data(endpoint_url: str) -> str:
    """Get data from a specific Redfish endpoint.

    Args:
        endpoint_url: The relative path of the Redfish endpoint (e.g., '/Systems')
    """
    return _service.get_endpoint_data(endpoint_url)

@app.tool()
def find_capabilities(
    query: str, selector: Optional[Dict[str, str]] = None
) -> str:
    """Find writable Redfish properties or actions without exposing discovery state.

    Args:
        query: Property or action name to find.
        selector: Optional contextual filters such as endpoint, resource_type,
            Id, Name, interface_kind, or ancestor_path.
    """
    return _service.find_capabilities(query, selector)

@app.tool()
def set_properties(
    updates: Dict[str, Any],
    selector: Optional[Dict[str, str]] = None,
    candidate_id: Optional[str] = None,
) -> str:
    """Set validated properties on one contract-resolved Redfish resource.

    Args:
        updates: Values keyed by contract property paths.
        selector: Contextual resource filters. Use conversation context first.
        candidate_id: Candidate returned after unresolved ambiguity.
    """
    return _service.set_properties(updates, selector, candidate_id)

@app.tool()
def invoke_action(
    action_name: str,
    arguments: Optional[Dict[str, Any]] = None,
    selector: Optional[Dict[str, str]] = None,
    candidate_id: Optional[str] = None,
) -> str:
    """Invoke a validated action on one contract-resolved Redfish resource."""
    return _service.invoke_action(
        action_name, arguments, selector, candidate_id
    )

if __name__ == "__main__":
    app.run()