"""Chatbot dispatch tests with no live model or Redfish target."""

import os
import unittest
from io import StringIO
from unittest.mock import Mock, patch

os.environ["ANTHROPIC_API_KEY"] = "dummy_key_for_testing"
os.environ["CONTRACT_SQLITE_PATH"] = ":memory:"

from src.redfish_mcp import chatbot


class TestChatbot(unittest.TestCase):
    def test_dispatches_fixed_tool_and_returns_response(self):
        first = Mock(
            content="Checking endpoints",
            tool_calls=[{"name": "list_endpoints", "args": {}, "id": "call-1"}],
        )
        second = Mock(content="Endpoints checked", tool_calls=[])
        model = Mock()
        model.invoke.side_effect = [first, second]
        tool = Mock()
        tool.invoke.return_value = "Available endpoints"

        with patch.object(chatbot, "model_with_tools", model):
            with patch.dict(
                chatbot.TOOL_MAP, {"list_endpoints": tool}, clear=True
            ):
                with patch(
                    "builtins.input", side_effect=["List endpoints", "quit"]
                ):
                    with patch("sys.stdout", new_callable=StringIO) as output:
                        chatbot.run_chatbot()

        tool.invoke.assert_called_once_with({})
        self.assertIn("Endpoints checked", output.getvalue())


if __name__ == "__main__":
    unittest.main()