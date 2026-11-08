"""Test environment defaults shared by every test module.

The configuration singleton in ``redfish_mcp.config`` reads its values when it
is first imported.  Pytest imports the root-level ``test_tools.py`` before it
loads ``tests/conftest.py``, so these defaults live at the repository root to
keep test collection order from changing behavior.
"""

import os

os.environ.setdefault("ANTHROPIC_API_KEY", "dummy_key_for_testing")
os.environ.setdefault("CONTRACT_SQLITE_PATH", ":memory:")
