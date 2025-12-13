from fastmcp import FastMCP
import requests

app = FastMCP("Redfish MCP Server")

REDFISH_BASE = "http://localhost:8000/redfish/v1"

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

if __name__ == "__main__":
    app.run()