"""
Redfish Tools - LangChain tools for Redfish operations
"""

from typing import Any, Dict, Optional

from langchain.tools import tool
from .capability_service import create_capability_service

_service = create_capability_service()

@tool
def list_endpoints() -> str:
    """List available Redfish endpoints by querying the root service."""
    return _service.list_endpoints()

@tool
def get_endpoint_data(endpoint_url: str) -> str:
    """Get data from a specific Redfish endpoint.

    Args:
        endpoint_url: The relative path of the Redfish endpoint (e.g., '/Systems')
    """
    return _service.get_endpoint_data(endpoint_url)

@tool
def find_capabilities(
    query: str, selector: Optional[Dict[str, str]] = None
) -> str:
    """Find writable properties/actions and matching resources.

    Args:
        query: Property or action name to find.
        selector: Optional context filters such as Name, Id, endpoint, type,
            interface kind, or ancestor path.
    """
    return _service.find_capabilities(query, selector)

@tool
def set_properties(
    updates: Dict[str, Any],
    selector: Optional[Dict[str, str]] = None,
    candidate_id: Optional[str] = None,
) -> str:
    """Set properties using the learned contract; never construct raw PATCH.

    Args:
        updates: Values keyed by writable property path.
        selector: Contextual resource filters.
        candidate_id: Candidate returned by an ambiguous result.
    """
    return _service.set_properties(updates, selector, candidate_id)

@tool
def invoke_action(
    action_name: str,
    arguments: Optional[Dict[str, Any]] = None,
    selector: Optional[Dict[str, str]] = None,
    candidate_id: Optional[str] = None,
) -> str:
    """Invoke a contract-validated Redfish action."""
    return _service.invoke_action(
        action_name, arguments, selector, candidate_id
    )