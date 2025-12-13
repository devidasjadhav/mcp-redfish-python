from fastmcp import FastMCP
import requests
import json

app = FastMCP("Redfish MCP Server")

REDFISH_BASE = "http://127.0.0.1:8000/redfish/v1"

@app.tool()
def list_endpoints() -> str:
    """List available Redfish endpoints by querying the root service."""
    try:
        response = requests.get(REDFISH_BASE)
        if response.status_code == 200:
            data = response.json()
            endpoints = []
            for key, value in data.items():
                if isinstance(value, dict) and "@odata.id" in value:
                    endpoints.append(f"- {key}: {value['@odata.id']}")
            return f"Available Redfish endpoints from {REDFISH_BASE}:\n" + "\n".join(endpoints)
        else:
            return f"Failed to query Redfish service: {response.status_code}"
    except Exception as e:
        return f"Error querying Redfish service: {e}"

@app.tool()
def get_endpoint_data(endpoint_url: str) -> str:
    """Get data from a specific Redfish endpoint.

    Args:
        endpoint_url: The relative path of the Redfish endpoint (e.g., '/Systems')
    """
    try:
        # If it's a relative path, prepend the base
        if not endpoint_url.startswith("http"):
            full_url = f"{REDFISH_BASE}{endpoint_url}"
        else:
            full_url = endpoint_url

        response = requests.get(full_url)
        if response.status_code == 200:
            data = response.json()
            return str(data)
        else:
            return f"Failed to query endpoint {full_url}: {response.status_code}"
    except Exception as e:
        return f"Error querying endpoint {endpoint_url}: {e}"

@app.tool()
def patch_resource(endpoint_url: str, patch_data: str) -> str:
    """Update a Redfish resource using PATCH.

    Args:
        endpoint_url: The relative path of the Redfish endpoint (e.g., '/Systems/1')
        patch_data: JSON string of the properties to update (e.g., '{"Description": "Updated"}')
    """
    try:
        # If it's a relative path, prepend the base
        if not endpoint_url.startswith("http"):
            full_url = f"{REDFISH_BASE}{endpoint_url}"
        else:
            full_url = endpoint_url

        # Parse patch_data as JSON
        data = json.loads(patch_data)

        response = requests.patch(full_url, json=data, headers={'Content-Type': 'application/json'})
        if response.status_code in [200, 204]:
            return f"Successfully updated resource at {full_url}"
        else:
            return f"Failed to update resource {full_url}: {response.status_code} - {response.text}"
    except json.JSONDecodeError:
        return "Invalid JSON in patch_data"
    except Exception as e:
        return f"Error updating resource {endpoint_url}: {e}"

@app.tool()
def post_action(action_url: str, action_data: str) -> str:
    """Execute a Redfish action using POST.

    Args:
        action_url: The full URL of the action endpoint (e.g., '/Systems/1/Actions/ComputerSystem.Reset')
        action_data: JSON string of the action parameters (e.g., '{"ResetType": "GracefulRestart"}')
    """
    try:
        # If it's a relative path, prepend the base
        if not action_url.startswith("http"):
            full_url = f"{REDFISH_BASE}{action_url}"
        else:
            full_url = action_url

        # Parse action_data as JSON
        data = json.loads(action_data) if action_data else {}

        response = requests.post(full_url, json=data, headers={'Content-Type': 'application/json'})
        if response.status_code in [200, 201, 202, 204]:
            return f"Successfully executed action at {full_url}. Status: {response.status_code}"
        else:
            return f"Failed to execute action {full_url}: {response.status_code} - {response.text}"
    except json.JSONDecodeError:
        return "Invalid JSON in action_data"
    except Exception as e:
        return f"Error executing action {action_url}: {e}"

if __name__ == "__main__":
    app.run()