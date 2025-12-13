#!/usr/bin/env python3

import os
import sys
from io import StringIO
from unittest.mock import patch

# Set dummy API key for testing
os.environ["ANTHROPIC_API_KEY"] = "dummy_key_for_testing"

# Import after setting env
from chatbot import model_with_tools, list_endpoints, get_endpoint_data, run_chatbot, HumanMessage, ToolMessage

# Mock the model invoke to return test responses
def mock_invoke(messages):
    last_message = messages[-1]
    if hasattr(last_message, 'content'):
        content = last_message.content
        if "list" in content.lower() and "endpoint" in content.lower():
            return type('MockResponse', (), {
                'content': "I'll list the available Redfish endpoints for you.",
                'tool_calls': [{'name': 'list_endpoints', 'args': {}, 'id': 'test1'}]
            })()
        elif "mac" in content.lower():
            return type('MockResponse', (), {
                'content': "Let me check the MAC addresses.",
                'tool_calls': [{'name': 'get_endpoint_data', 'args': {'endpoint_url': 'https://server1.example.com/redfish/v1'}, 'id': 'test2'}]
            })()
        else:
            return type('MockResponse', (), {
                'content': "Hello! I can help with Redfish server management. Try asking about endpoints or MAC addresses.",
                'tool_calls': None
            })()
    else:
        return type('MockResponse', (), {
            'content': "Tool result processed.",
            'tool_calls': None
        })()

# Patch the model
with patch.object(model_with_tools, 'invoke', side_effect=mock_invoke):
    # Test inputs
    test_inputs = [
        "List the available Redfish endpoints",
        "What are the MAC addresses?",
        "quit"
    ]

    # Simulate input
    input_iter = iter(test_inputs)
    with patch('builtins.input', lambda: next(input_iter)):
        # Redirect stdout to capture output
        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()

        try:
            run_chatbot()
        finally:
            sys.stdout = old_stdout

    # Print captured output
    print("Test Output:")
    print(captured_output.getvalue())