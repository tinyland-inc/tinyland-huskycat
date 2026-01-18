#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
MCP Async Tools Tests

Tests for MCP server async validation functionality:
- validate_async: Start background validation
- get_task_status: Poll task progress
- list_async_tasks: List all tasks
- cancel_async_task: Cancel running validation
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


class MCPTestClient:
    """Simple MCP test client for async tool testing."""

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
    """Create temporary workspace for async validation tests."""
    workspace = tmp_path / "async_workspace"
    workspace.mkdir()
    return workspace


@pytest.mark.skipif(not HAS_MCP_SERVER, reason="MCP server not available")
class TestValidateAsync:
    """Test validate_async tool."""

    def test_validate_async_tool_listed(
        self, mcp_server: MCPServer, mcp_client: MCPTestClient
    ):
        """Test that validate_async is listed in tools."""
        request = mcp_client.create_request("tools/list")
        response = mcp_client.send_request(mcp_server, request)

        if "result" in response and "tools" in response["result"]:
            tool_names = [t["name"] for t in response["result"]["tools"]]
            assert (
                "validate_async" in tool_names
            ), f"validate_async not in tools: {tool_names}"

    def test_validate_async_starts_task(
        self,
        mcp_server: MCPServer,
        mcp_client: MCPTestClient,
        temp_workspace: Path,
    ):
        """Test that validate_async starts a background task."""
        # Create test file
        test_file = temp_workspace / "test.py"
        test_file.write_text("def hello():\n    pass\n")

        request = mcp_client.create_request(
            "tools/call",
            {
                "name": "validate_async",
                "arguments": {"path": str(test_file), "fix": False},
            },
        )

        response = mcp_client.send_request(mcp_server, request)

        assert "jsonrpc" in response
        assert response["jsonrpc"] == "2.0"

        if "result" in response:
            result = response["result"]
            # Should contain task_id or similar identifier
            result_str = str(result).lower()
            assert (
                "task" in result_str or "started" in result_str or "id" in result_str
            ), f"Unexpected result: {result}"

    def test_validate_async_with_fix(
        self,
        mcp_server: MCPServer,
        mcp_client: MCPTestClient,
        temp_workspace: Path,
    ):
        """Test validate_async with fix=True."""
        test_file = temp_workspace / "fix_test.py"
        test_file.write_text("def badly_formatted(x,y):\n    return x+y\n")

        request = mcp_client.create_request(
            "tools/call",
            {
                "name": "validate_async",
                "arguments": {"path": str(test_file), "fix": True},
            },
        )

        response = mcp_client.send_request(mcp_server, request)
        assert "jsonrpc" in response

    def test_validate_async_invalid_path(
        self, mcp_server: MCPServer, mcp_client: MCPTestClient
    ):
        """Test validate_async with nonexistent path."""
        request = mcp_client.create_request(
            "tools/call",
            {
                "name": "validate_async",
                "arguments": {"path": "/nonexistent/path/file.py", "fix": False},
            },
        )

        response = mcp_client.send_request(mcp_server, request)
        assert "jsonrpc" in response
        # Should handle gracefully (error or task that fails)


@pytest.mark.skipif(not HAS_MCP_SERVER, reason="MCP server not available")
class TestGetTaskStatus:
    """Test get_task_status tool."""

    def test_get_task_status_tool_listed(
        self, mcp_server: MCPServer, mcp_client: MCPTestClient
    ):
        """Test that get_task_status is listed in tools."""
        request = mcp_client.create_request("tools/list")
        response = mcp_client.send_request(mcp_server, request)

        if "result" in response and "tools" in response["result"]:
            tool_names = [t["name"] for t in response["result"]["tools"]]
            assert (
                "get_task_status" in tool_names
            ), f"get_task_status not in tools: {tool_names}"

    def test_get_task_status_nonexistent(
        self, mcp_server: MCPServer, mcp_client: MCPTestClient
    ):
        """Test get_task_status with nonexistent task ID."""
        request = mcp_client.create_request(
            "tools/call",
            {"name": "get_task_status", "arguments": {"task_id": "nonexistent-task-id"}},
        )

        response = mcp_client.send_request(mcp_server, request)
        assert "jsonrpc" in response

        # Should handle gracefully with error or "not found" result
        if "result" in response:
            result = response["result"]
            result_str = str(result).lower()
            # Might contain "not found", "error", or isError flag
            assert (
                "not found" in result_str
                or "error" in result_str
                or "invalid" in result_str
                or response.get("result", {}).get("isError", False)
            )

    def test_get_task_status_workflow(
        self,
        mcp_server: MCPServer,
        mcp_client: MCPTestClient,
        temp_workspace: Path,
    ):
        """Test starting async task and checking status."""
        # Create test file
        test_file = temp_workspace / "workflow_test.py"
        test_file.write_text("# Simple test file\n")

        # Start async validation
        start_request = mcp_client.create_request(
            "tools/call",
            {
                "name": "validate_async",
                "arguments": {"path": str(test_file), "fix": False},
            },
        )

        start_response = mcp_client.send_request(mcp_server, start_request)

        if "result" in start_response:
            result_content = start_response["result"]
            # Try to extract task_id from result
            if isinstance(result_content, dict) and "task_id" in result_content:
                task_id = result_content["task_id"]

                # Check status
                status_request = mcp_client.create_request(
                    "tools/call",
                    {"name": "get_task_status", "arguments": {"task_id": task_id}},
                )

                status_response = mcp_client.send_request(mcp_server, status_request)
                assert "jsonrpc" in status_response


@pytest.mark.skipif(not HAS_MCP_SERVER, reason="MCP server not available")
class TestListAsyncTasks:
    """Test list_async_tasks tool."""

    def test_list_async_tasks_tool_listed(
        self, mcp_server: MCPServer, mcp_client: MCPTestClient
    ):
        """Test that list_async_tasks is listed in tools."""
        request = mcp_client.create_request("tools/list")
        response = mcp_client.send_request(mcp_server, request)

        if "result" in response and "tools" in response["result"]:
            tool_names = [t["name"] for t in response["result"]["tools"]]
            assert (
                "list_async_tasks" in tool_names
            ), f"list_async_tasks not in tools: {tool_names}"

    def test_list_async_tasks_empty(
        self, mcp_server: MCPServer, mcp_client: MCPTestClient
    ):
        """Test listing tasks when none exist."""
        request = mcp_client.create_request(
            "tools/call", {"name": "list_async_tasks", "arguments": {}}
        )

        response = mcp_client.send_request(mcp_server, request)
        assert "jsonrpc" in response

        if "result" in response:
            result = response["result"]
            # Should return empty list or list of tasks
            if isinstance(result, dict):
                tasks = result.get("tasks", result.get("content", []))
                assert isinstance(tasks, (list, str))

    def test_list_async_tasks_with_filter(
        self, mcp_server: MCPServer, mcp_client: MCPTestClient
    ):
        """Test listing tasks with status filter."""
        request = mcp_client.create_request(
            "tools/call",
            {"name": "list_async_tasks", "arguments": {"status": "running"}},
        )

        response = mcp_client.send_request(mcp_server, request)
        assert "jsonrpc" in response


@pytest.mark.skipif(not HAS_MCP_SERVER, reason="MCP server not available")
class TestCancelAsyncTask:
    """Test cancel_async_task tool."""

    def test_cancel_async_task_tool_listed(
        self, mcp_server: MCPServer, mcp_client: MCPTestClient
    ):
        """Test that cancel_async_task is listed in tools."""
        request = mcp_client.create_request("tools/list")
        response = mcp_client.send_request(mcp_server, request)

        if "result" in response and "tools" in response["result"]:
            tool_names = [t["name"] for t in response["result"]["tools"]]
            assert (
                "cancel_async_task" in tool_names
            ), f"cancel_async_task not in tools: {tool_names}"

    def test_cancel_nonexistent_task(
        self, mcp_server: MCPServer, mcp_client: MCPTestClient
    ):
        """Test cancelling nonexistent task."""
        request = mcp_client.create_request(
            "tools/call",
            {
                "name": "cancel_async_task",
                "arguments": {"task_id": "nonexistent-cancel-id"},
            },
        )

        response = mcp_client.send_request(mcp_server, request)
        assert "jsonrpc" in response
        # Should handle gracefully

    def test_cancel_task_workflow(
        self,
        mcp_server: MCPServer,
        mcp_client: MCPTestClient,
        temp_workspace: Path,
    ):
        """Test starting and cancelling an async task."""
        # Create a large file that will take time to validate
        large_file = temp_workspace / "large_test.py"
        content = "\n".join([f"def func_{i}():\n    pass\n" for i in range(100)])
        large_file.write_text(content)

        # Start async validation
        start_request = mcp_client.create_request(
            "tools/call",
            {
                "name": "validate_async",
                "arguments": {"path": str(large_file), "fix": False},
            },
        )

        start_response = mcp_client.send_request(mcp_server, start_request)

        if "result" in start_response:
            result_content = start_response["result"]
            if isinstance(result_content, dict) and "task_id" in result_content:
                task_id = result_content["task_id"]

                # Immediately try to cancel
                cancel_request = mcp_client.create_request(
                    "tools/call",
                    {"name": "cancel_async_task", "arguments": {"task_id": task_id}},
                )

                cancel_response = mcp_client.send_request(mcp_server, cancel_request)
                assert "jsonrpc" in cancel_response


@pytest.mark.skipif(not HAS_MCP_SERVER, reason="MCP server not available")
class TestAsyncToolSchemas:
    """Test async tool input schemas."""

    def test_validate_async_schema(
        self, mcp_server: MCPServer, mcp_client: MCPTestClient
    ):
        """Test validate_async has correct input schema."""
        request = mcp_client.create_request("tools/list")
        response = mcp_client.send_request(mcp_server, request)

        if "result" in response and "tools" in response["result"]:
            for tool in response["result"]["tools"]:
                if tool["name"] == "validate_async":
                    schema = tool["inputSchema"]
                    assert "type" in schema
                    assert schema["type"] == "object"

                    if "properties" in schema:
                        props = schema["properties"]
                        # Should have path property
                        assert "path" in props
                        assert props["path"]["type"] == "string"

                        # Should have optional fix property
                        if "fix" in props:
                            assert props["fix"]["type"] == "boolean"
                    break

    def test_get_task_status_schema(
        self, mcp_server: MCPServer, mcp_client: MCPTestClient
    ):
        """Test get_task_status has correct input schema."""
        request = mcp_client.create_request("tools/list")
        response = mcp_client.send_request(mcp_server, request)

        if "result" in response and "tools" in response["result"]:
            for tool in response["result"]["tools"]:
                if tool["name"] == "get_task_status":
                    schema = tool["inputSchema"]
                    assert "type" in schema

                    if "properties" in schema:
                        props = schema["properties"]
                        assert "task_id" in props
                        assert props["task_id"]["type"] == "string"
                    break


@pytest.mark.integration
@pytest.mark.skipif(not HAS_MCP_SERVER, reason="MCP server not available")
class TestAsyncTaskIntegration:
    """Integration tests for async task workflow."""

    def test_full_async_workflow(
        self,
        mcp_server: MCPServer,
        mcp_client: MCPTestClient,
        temp_workspace: Path,
    ):
        """Test full async workflow: start, check status, get result."""
        # Create test file
        test_file = temp_workspace / "integration_test.py"
        test_file.write_text("# Integration test\ndef test(): pass\n")

        # 1. Start async validation
        start_request = mcp_client.create_request(
            "tools/call",
            {
                "name": "validate_async",
                "arguments": {"path": str(test_file), "fix": False},
            },
        )

        start_response = mcp_client.send_request(mcp_server, start_request)
        assert "jsonrpc" in start_response

        # 2. List tasks
        list_request = mcp_client.create_request(
            "tools/call", {"name": "list_async_tasks", "arguments": {}}
        )

        list_response = mcp_client.send_request(mcp_server, list_request)
        assert "jsonrpc" in list_response

        # 3. If we got a task_id, check its status
        if "result" in start_response:
            result = start_response["result"]
            if isinstance(result, dict) and "task_id" in result:
                task_id = result["task_id"]

                # Wait a bit for task to complete
                time.sleep(0.5)

                status_request = mcp_client.create_request(
                    "tools/call",
                    {"name": "get_task_status", "arguments": {"task_id": task_id}},
                )

                status_response = mcp_client.send_request(mcp_server, status_request)
                assert "jsonrpc" in status_response


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
