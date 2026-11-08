"""Tests that MCP stdio servers keep stdout clean for JSON-RPC framing."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from src.redfish_mcp.logging_config import setup_logging


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestLoggingStreams(unittest.TestCase):
    """Console logging and log-file warnings must not write to stdout."""

    def tearDown(self):
        # Restore the module logger to a real stream after patched tests.
        setup_logging()

    def test_console_handler_writes_to_stderr(self):
        with patch("sys.stdout", new_callable=StringIO) as stdout:
            with patch("sys.stderr", new_callable=StringIO) as stderr:
                logger = setup_logging(level="INFO")
                logger.info("Validating configuration...")

        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("Validating configuration...", stderr.getvalue())

    def test_log_file_warning_writes_to_stderr(self):
        # A directory can never be opened as a log file, so FileHandler fails.
        with tempfile.TemporaryDirectory() as directory:
            with patch("sys.stdout", new_callable=StringIO) as stdout:
                with patch("sys.stderr", new_callable=StringIO) as stderr:
                    setup_logging(log_file=directory)

        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("Warning: Could not create log file", stderr.getvalue())


class TestStdioServerStdout(unittest.TestCase):
    """The stdio server must never emit plaintext on stdout."""

    @staticmethod
    def _is_json_rpc_line(line):
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            return False
        return isinstance(message, dict) and message.get("jsonrpc") == "2.0"

    def test_stdout_has_no_plaintext_startup_output(self):
        with tempfile.TemporaryDirectory() as directory:
            env = dict(os.environ)
            env["PYTHONPATH"] = os.pathsep.join(
                path for path in (str(REPO_ROOT), env.get("PYTHONPATH")) if path
            )
            env["CONTRACT_SQLITE_PATH"] = str(
                Path(directory) / "contracts.sqlite3"
            )
            env["LOG_LEVEL"] = "INFO"
            env["MCP_TRANSPORT"] = "stdio"
            env.pop("LOG_FILE", None)

            completed = subprocess.run(
                [sys.executable, "-m", "src.redfish_mcp.redfish_mcp_server"],
                cwd=str(REPO_ROOT),
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=120,
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)

        non_json_lines = [
            line
            for line in completed.stdout.splitlines()
            if line.strip() and not self._is_json_rpc_line(line)
        ]
        self.assertEqual(
            non_json_lines,
            [],
            "stdio server wrote non-JSON-RPC text to stdout: "
            f"{non_json_lines!r}",
        )

        self.assertIn("Validating configuration...", completed.stderr)
        self.assertIn(
            "Configuration validated successfully", completed.stderr
        )


if __name__ == "__main__":
    unittest.main()
