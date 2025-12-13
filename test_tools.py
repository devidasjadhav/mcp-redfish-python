#!/usr/bin/env python3

"""
Simple test script to verify chatbot functionality without AI
"""

import sys
import os
sys.path.append('.')

from src.redfish_mcp.redfish_tool import list_endpoints, get_endpoint_data, patch_resource, post_action

def test_redfish_tools():
    """Test all Redfish tools directly"""
    print("Testing Redfish MCP Tools")
    print("=" * 40)

    # Test list_endpoints
    print("\n1. Testing list_endpoints...")
    try:
        result = list_endpoints.invoke({})
        print("✓ list_endpoints: SUCCESS")
        print(f"   Found endpoints: {len(result.split('- ')) - 1}")
    except Exception as e:
        print(f"✗ list_endpoints: FAILED - {e}")

    # Test get_endpoint_data
    print("\n2. Testing get_endpoint_data...")
    try:
        result = get_endpoint_data.invoke({"endpoint_url": "/Systems"})
        print("✓ get_endpoint_data: SUCCESS")
        print(f"   Response length: {len(result)} characters")
    except Exception as e:
        print(f"✗ get_endpoint_data: FAILED - {e}")

    # Test get_endpoint_data with invalid endpoint
    print("\n3. Testing get_endpoint_data (invalid endpoint)...")
    try:
        result = get_endpoint_data.invoke({"endpoint_url": "/InvalidEndpoint"})
        print("✓ get_endpoint_data (error handling): SUCCESS")
        print(f"   Error response: {result[:100]}...")
    except Exception as e:
        print(f"✗ get_endpoint_data (error handling): FAILED - {e}")

    print("\n" + "=" * 40)
    print("Redfish MCP Tools Test Complete!")

if __name__ == "__main__":
    test_redfish_tools()