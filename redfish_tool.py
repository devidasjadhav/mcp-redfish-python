from langchain.tools import tool

@tool
def list_endpoints() -> str:
    """List available Redfish endpoints."""
    # Mock implementation - in real use, this would query actual Redfish servers
    return """
Available Redfish endpoints:
- Server1: https://server1.example.com/redfish/v1
- Server2: https://server2.example.com/redfish/v1

Each endpoint provides access to hardware information, sensors, and management features.
"""

@tool
def get_endpoint_data(endpoint_url: str) -> str:
    """Get data from a specific Redfish endpoint.

    Args:
        endpoint_url: The URL of the Redfish endpoint to query
    """
    # Mock implementation - in real use, this would make HTTP requests to the endpoint
    mock_data = {
        "https://server1.example.com/redfish/v1": {
            "Systems": "/redfish/v1/Systems",
            "Chassis": "/redfish/v1/Chassis",
            "Managers": "/redfish/v1/Managers",
            "MAC Addresses": ["00:11:22:33:44:55", "AA:BB:CC:DD:EE:FF"]
        },
        "https://server1.example.com/redfish/v1/Systems": {
            "Members": [{"@odata.id": "/redfish/v1/Systems/1"}]
        },
        "https://server1.example.com/redfish/v1/Systems/1": {
            "Name": "Server1",
            "Model": "PowerEdge R750",
            "SerialNumber": "ABC123",
            "Status": {"State": "Enabled", "Health": "OK"}
        }
    }

    return str(mock_data.get(endpoint_url, f"No data available for endpoint: {endpoint_url}"))