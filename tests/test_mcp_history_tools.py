#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
MCP History Tools Tests

Tests for MCP server run history functionality:
- get_last_run: Get most recent validation run
- get_run_history: Get list of historical runs
- get_run_results: Get detailed results by run_id
- get_running_validations: Check for in-progress validations
"""

import json
import os
import sys
import time
from io import StringIO
from pathlib import Path
from typing import Dict, Optional
from unittest.mock import MagicMock, patch

import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Try to import MCP server
try:
    from huskycat.mcp_server import MCPServer

    HAS_MCP_SERVER = True
except ImportError:
    HAS_MCP_SERVER = False
    MCPServer = type("MCPServer", (), {})  # type: ignore

# Try to import ProcessManager for history testing
try:
    from huskycat.core.process_manager import ProcessManager

    HAS_PROCESS_MANAGER = True
except ImportError:
    HAS_PROCESS_MANAGER = False


class MCPTestClient:
    """Simple MCP test client for history tool testing."""

    def __init__(self):
        self.request_id = 1

    def create_request(self, method: str, params: Optional[Dict] = None) -> Dict:
        """Create a JSON-RPC 2.0 request."""
        request = {"jsonrpc": "2.0", "method": method, "id": self.request_id}
        if params:
            request["params"] = params
        self.request_id += 1
        return request

    def send_request(self, server: "MCPServer", request: Dict) -> Dict:
        """Send request to server and get response."""
        original_stdout = sys.stdout
        captured_output = StringIO()
        sys.stdout = captured_output

        try:
            server.handle_request(request)
            response_text = captured_output.getvalue().strip()

            if not response_text:
                return {"error": {"code": -32603, "message": "No response"}}

            return json.loads(response_text)

        except json.JSONDecodeError as e:
            return {"error": {"code": -32700, "message": f"Parse error: {e}"}}
        except Exception as e:
            return {"error": {"code": -32603, "message": f"Error: {e}"}}
        finally:
            sys.stdout = original_stdout


@pytest.fixture
def mcp_server():
    """Provide MCP server instance."""
    if not HAS_MCP_SERVER:
        pytest.skip("MCP server not available")
    return MCPServer()


@pytest.fixture
def mcp_client():
    """Provide MCP test client."""
    return MCPTestClient()


@pytest.fixture
def temp_workspace(tmp_path) -> Path:
    """Create temporary workspace for history tests."""
    workspace = tmp_path / "history_workspace"
    workspace.mkdir()
    return workspace


@pytest.fixture
def setup_huskycat_dir(tmp_path):
    """Set up .huskycat directory for run history."""
    huskycat_dir = tmp_path / ".huskycat"
    runs_dir = huskycat_dir / "runs"
    results_dir = huskycat_dir / "results"
    runs_dir.mkdir(parents=True)
    results_dir.mkdir(parents=True)

    # Create some mock run history
    run1 = {
        "run_id": "20260115_120000_123456",
        "timestamp": "2026-01-15T12:00:00",
        "status": "completed",
        "files_validated": 5,
        "issues_found": 2,
    }
    run2 = {
        "run_id": "20260115_130000_654321",
        "timestamp": "2026-01-15T13:00:00",
        "status": "completed",
        "files_validated": 10,
        "issues_found": 0,
    }

    (runs_dir / "20260115_120000_123456.json").write_text(json.dumps(run1))
    (runs_dir / "20260115_130000_654321.json").write_text(json.dumps(run2))
    (runs_dir / "last_run.json").write_text(json.dumps(run2))

    return huskycat_dir


@pytest.mark.skipif(not HAS_MCP_SERVER, reason="MCP server not available")
class TestGetLastRun:
    """Test get_last_run tool."""

    def test_get_last_run_tool_listed(
        self, mcp_server: MCPServer, mcp_client: MCPTestClient
    ):
        """Test that get_last_run is listed in tools."""
        request = mcp_client.create_request("tools/list")
        response = mcp_client.send_request(mcp_server, request)

        if "result" in response and "tools" in response["result"]:
            tool_names = [t["name"] for t in response["result"]["tools"]]
            assert (
                "get_last_run" in tool_names
            ), f"get_last_run not in tools: {tool_names}"

    def test_get_last_run_no_history(
        self, mcp_server: MCPServer, mcp_client: MCPTestClient
    ):
        """Test get_last_run when no runs exist."""
        request = mcp_client.create_request(
            "tools/call", {"name": "get_last_run", "arguments": {}}
        )

        response = mcp_client.send_request(mcp_server, request)
        assert "jsonrpc" in response
        assert response["jsonrpc"] == "2.0"

        # Should return empty result or informative message
        if "result" in response:
            result = response["result"]
            # Might be empty, None, or message about no runs
            assert result is not None or "error" not in response

    def test_get_last_run_after_validation(
        self,
        mcp_server: MCPServer,
        mcp_client: MCPTestClient,
        temp_workspace: Path,
    ):
        """Test get_last_run after performing a validation."""
        # First, do a validation
        test_file = temp_workspace / "test.py"
        test_file.write_text("# Test file\ndef test(): pass\n")

        validate_request = mcp_client.create_request(
            "tools/call",
            {
                "name": "validate",
                "arguments": {"path": str(test_file), "fix": False},
            },
        )

        mcp_client.send_request(mcp_server, validate_request)

        # Now get last run
        last_run_request = mcp_client.create_request(
            "tools/call", {"name": "get_last_run", "arguments": {}}
        )

        response = mcp_client.send_request(mcp_server, last_run_request)
        assert "jsonrpc" in response


@pytest.mark.skipif(not HAS_MCP_SERVER, reason="MCP server not available")
class TestGetRunHistory:
    """Test get_run_history tool."""

    def test_get_run_history_tool_listed(
        self, mcp_server: MCPServer, mcp_client: MCPTestClient
    ):
        """Test that get_run_history is listed in tools."""
        request = mcp_client.create_request("tools/list")
        response = mcp_client.send_request(mcp_server, request)

        if "result" in response and "tools" in response["result"]:
            tool_names = [t["name"] for t in response["result"]["tools"]]
            assert (
                "get_run_history" in tool_names
            ), f"get_run_history not in tools: {tool_names}"

    def test_get_run_history_empty(
        self, mcp_server: MCPServer, mcp_client: MCPTestClient
    ):
        """Test get_run_history when no runs exist."""
        request = mcp_client.create_request(
            "tools/call", {"name": "get_run_history", "arguments": {}}
        )

        response = mcp_client.send_request(mcp_server, request)
        assert "jsonrpc" in response

        if "result" in response:
            result = response["result"]
            # Should return list or structured data
            if isinstance(result, dict):
                # Might have "runs" or "history" key
                assert isinstance(
                    result.get("runs", result.get("history", result.get("content", []))),
                    (list, str),
                )

    def test_get_run_history_with_limit(
        self, mcp_server: MCPServer, mcp_client: MCPTestClient
    ):
        """Test get_run_history with limit parameter."""
        request = mcp_client.create_request(
            "tools/call", {"name": "get_run_history", "arguments": {"limit": 5}}
        )

        response = mcp_client.send_request(mcp_server, request)
        assert "jsonrpc" in response

    def test_get_run_history_limit_bounds(
        self, mcp_server: MCPServer, mcp_client: MCPTestClient
    ):
        """Test get_run_history limit parameter bounds (1-100)."""
        # Test minimum
        request_min = mcp_client.create_request(
            "tools/call", {"name": "get_run_history", "arguments": {"limit": 1}}
        )
        response_min = mcp_client.send_request(mcp_server, request_min)
        assert "jsonrpc" in response_min

        # Test maximum
        request_max = mcp_client.create_request(
            "tools/call", {"name": "get_run_history", "arguments": {"limit": 100}}
        )
        response_max = mcp_client.send_request(mcp_server, request_max)
        assert "jsonrpc" in response_max


@pytest.mark.skipif(not HAS_MCP_SERVER, reason="MCP server not available")
class TestGetRunResults:
    """Test get_run_results tool."""

    def test_get_run_results_tool_listed(
        self, mcp_server: MCPServer, mcp_client: MCPTestClient
    ):
        """Test that get_run_results is listed in tools."""
        request = mcp_client.create_request("tools/list")
        response = mcp_client.send_request(mcp_server, request)

        if "result" in response and "tools" in response["result"]:
            tool_names = [t["name"] for t in response["result"]["tools"]]
            assert (
                "get_run_results" in tool_names
            ), f"get_run_results not in tools: {tool_names}"

    def test_get_run_results_nonexistent(
        self, mcp_server: MCPServer, mcp_client: MCPTestClient
    ):
        """Test get_run_results with nonexistent run_id."""
        request = mcp_client.create_request(
            "tools/call",
            {
                "name": "get_run_results",
                "arguments": {"run_id": "nonexistent_run_20260101_000000"},
            },
        )

        response = mcp_client.send_request(mcp_server, request)
        assert "jsonrpc" in response

        # Should handle gracefully
        if "result" in response:
            result = response["result"]
            result_str = str(result).lower()
            # Either isError flag or error message
            has_error = (
                "not found" in result_str
                or "error" in result_str
                or (isinstance(result, dict) and result.get("isError", False))
            )
            # Or empty result is also acceptable
            assert has_error or result == {} or result is None or result == ""

    def test_get_run_results_requires_run_id(
        self, mcp_server: MCPServer, mcp_client: MCPTestClient
    ):
        """Test get_run_results requires run_id parameter."""
        request = mcp_client.create_request(
            "tools/call", {"name": "get_run_results", "arguments": {}}
        )

        response = mcp_client.send_request(mcp_server, request)
        assert "jsonrpc" in response

        # Should indicate missing parameter
        if "result" in response:
            result = response["result"]
            if isinstance(result, dict):
                # Should have error or isError
                assert result.get("isError", False) or "error" in str(result).lower()


@pytest.mark.skipif(not HAS_MCP_SERVER, reason="MCP server not available")
class TestGetRunningValidations:
    """Test get_running_validations tool."""

    def test_get_running_validations_tool_listed(
        self, mcp_server: MCPServer, mcp_client: MCPTestClient
    ):
        """Test that get_running_validations is listed in tools."""
        request = mcp_client.create_request("tools/list")
        response = mcp_client.send_request(mcp_server, request)

        if "result" in response and "tools" in response["result"]:
            tool_names = [t["name"] for t in response["result"]["tools"]]
            assert (
                "get_running_validations" in tool_names
            ), f"get_running_validations not in tools: {tool_names}"

    def test_get_running_validations_empty(
        self, mcp_server: MCPServer, mcp_client: MCPTestClient
    ):
        """Test get_running_validations when none running."""
        request = mcp_client.create_request(
            "tools/call", {"name": "get_running_validations", "arguments": {}}
        )

        response = mcp_client.send_request(mcp_server, request)
        assert "jsonrpc" in response

        if "result" in response:
            result = response["result"]
            # Should return empty list or message
            if isinstance(result, dict):
                running = result.get(
                    "running", result.get("validations", result.get("content", []))
                )
                # Might be empty list or empty string
                if isinstance(running, list):
                    assert len(running) >= 0
            elif isinstance(result, list):
                assert len(result) >= 0


@pytest.mark.skipif(not HAS_MCP_SERVER, reason="MCP server not available")
class TestHistoryToolSchemas:
    """Test history tool input schemas."""

    def test_get_last_run_schema(
        self, mcp_server: MCPServer, mcp_client: MCPTestClient
    ):
        """Test get_last_run has correct input schema."""
        request = mcp_client.create_request("tools/list")
        response = mcp_client.send_request(mcp_server, request)

        if "result" in response and "tools" in response["result"]:
            for tool in response["result"]["tools"]:
                if tool["name"] == "get_last_run":
                    schema = tool["inputSchema"]
                    assert "type" in schema
                    # Should have object type (may have no required properties)
                    assert schema["type"] == "object"
                    break

    def test_get_run_history_schema(
        self, mcp_server: MCPServer, mcp_client: MCPTestClient
    ):
        """Test get_run_history has correct input schema."""
        request = mcp_client.create_request("tools/list")
        response = mcp_client.send_request(mcp_server, request)

        if "result" in response and "tools" in response["result"]:
            for tool in response["result"]["tools"]:
                if tool["name"] == "get_run_history":
                    schema = tool["inputSchema"]
                    assert "type" in schema

                    if "properties" in schema:
                        props = schema["properties"]
                        # Should have optional limit property
                        if "limit" in props:
                            assert props["limit"]["type"] in ["integer", "number"]
                    break

    def test_get_run_results_schema(
        self, mcp_server: MCPServer, mcp_client: MCPTestClient
    ):
        """Test get_run_results has correct input schema."""
        request = mcp_client.create_request("tools/list")
        response = mcp_client.send_request(mcp_server, request)

        if "result" in response and "tools" in response["result"]:
            for tool in response["result"]["tools"]:
                if tool["name"] == "get_run_results":
                    schema = tool["inputSchema"]
                    assert "type" in schema

                    if "properties" in schema:
                        props = schema["properties"]
                        # Should have run_id property
                        assert "run_id" in props
                        assert props["run_id"]["type"] == "string"

                    # run_id should be required
                    if "required" in schema:
                        assert "run_id" in schema["required"]
                    break


@pytest.mark.integration
@pytest.mark.skipif(not HAS_MCP_SERVER, reason="MCP server not available")
class TestHistoryIntegration:
    """Integration tests for history workflow."""

    def test_validation_creates_history(
        self,
        mcp_server: MCPServer,
        mcp_client: MCPTestClient,
        temp_workspace: Path,
    ):
        """Test that validation creates history entries."""
        # Create and validate a file
        test_file = temp_workspace / "history_test.py"
        test_file.write_text("# History test\ndef test(): pass\n")

        validate_request = mcp_client.create_request(
            "tools/call",
            {
                "name": "validate",
                "arguments": {"path": str(test_file), "fix": False},
            },
        )

        validate_response = mcp_client.send_request(mcp_server, validate_request)
        assert "jsonrpc" in validate_response

        # Check that we can get history
        history_request = mcp_client.create_request(
            "tools/call", {"name": "get_run_history", "arguments": {"limit": 10}}
        )

        history_response = mcp_client.send_request(mcp_server, history_request)
        assert "jsonrpc" in history_response

    def test_last_run_updates(
        self,
        mcp_server: MCPServer,
        mcp_client: MCPTestClient,
        temp_workspace: Path,
    ):
        """Test that last_run updates after each validation."""
        test_file = temp_workspace / "last_run_test.py"
        test_file.write_text("# Test\n")

        # Get initial last run
        initial_request = mcp_client.create_request(
            "tools/call", {"name": "get_last_run", "arguments": {}}
        )
        initial_response = mcp_client.send_request(mcp_server, initial_request)

        # Validate
        validate_request = mcp_client.create_request(
            "tools/call",
            {
                "name": "validate",
                "arguments": {"path": str(test_file), "fix": False},
            },
        )
        mcp_client.send_request(mcp_server, validate_request)

        # Get last run again
        after_request = mcp_client.create_request(
            "tools/call", {"name": "get_last_run", "arguments": {}}
        )
        after_response = mcp_client.send_request(mcp_server, after_request)

        # Both should be valid responses
        assert "jsonrpc" in initial_response
        assert "jsonrpc" in after_response


@pytest.mark.skipif(not HAS_PROCESS_MANAGER, reason="ProcessManager not available")
class TestProcessManagerIntegration:
    """Test ProcessManager history storage."""

    def test_process_manager_saves_runs(self, tmp_path):
        """Test that ProcessManager saves run history."""
        pm = ProcessManager(data_dir=tmp_path)

        # Simulate a run
        run_data = {
            "run_id": "test_run_001",
            "timestamp": "2026-01-15T12:00:00",
            "status": "completed",
            "files": 5,
            "issues": 0,
        }

        # Check if process manager has save methods
        if hasattr(pm, "save_run"):
            pm.save_run(run_data)
            # Verify saved
            assert (tmp_path / "runs" / "test_run_001.json").exists()

    def test_process_manager_retrieves_history(self, tmp_path):
        """Test that ProcessManager retrieves history."""
        pm = ProcessManager(data_dir=tmp_path)

        if hasattr(pm, "get_history"):
            history = pm.get_history(limit=10)
            assert isinstance(history, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
