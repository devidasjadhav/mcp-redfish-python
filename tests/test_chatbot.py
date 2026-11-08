"""Chatbot dispatch tests with no live model or Redfish target."""

import os
import subprocess
import sys
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, patch

from src.redfish_mcp import chatbot

REPO_ROOT = Path(__file__).resolve().parents[1]


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

        with patch.object(
            chatbot, "_build_model_with_tools", return_value=model
        ):
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

    def test_import_does_not_require_api_key(self):
        """Importing the module must not prompt, even without a TTY or key."""
        env = os.environ.copy()
        env["ANTHROPIC_API_KEY"] = ""
        result = subprocess.run(
            [sys.executable, "-c", "import src.redfish_mcp.chatbot"],
            cwd=REPO_ROOT,
            env=env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=120,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(
            "Enter your Anthropic API key", result.stdout + result.stderr
        )

    def test_run_chatbot_requires_api_key(self):
        """Starting the chatbot without a key reports a configuration error."""
        with patch.object(chatbot.config, "ANTHROPIC_API_KEY", None):
            with self.assertRaisesRegex(ValueError, "ANTHROPIC_API_KEY"):
                chatbot.run_chatbot()


if __name__ == "__main__":
    unittest.main()
