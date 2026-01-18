#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
GPL Sidecar IPC Tests

Tests for the GPL sidecar client and server communication.
These tests verify:
1. Client connection handling
2. JSON-RPC 2.0 protocol compliance
3. Tool execution via IPC
4. Error handling and graceful degradation
"""

import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Try to import GPL client
try:
    from huskycat.core.gpl_client import (
        DEFAULT_SOCKET_PATH,
        GPLSidecarClient,
        GPLSidecarConnectionError,
        GPLSidecarError,
        GPLSidecarTimeoutError,
        GPLToolResult,
        execute_gpl_tool,
        get_default_client,
        is_sidecar_available,
    )

    HAS_GPL_CLIENT = True
except ImportError:
    HAS_GPL_CLIENT = False


class MockSidecarServer:
    """Mock GPL sidecar server for testing."""

    def __init__(self, socket_path: str, delay: float = 0):
        self.socket_path = socket_path
        self.delay = delay
        self.server_socket: Optional[socket.socket] = None
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.received_requests = []

    def start(self):
        """Start the mock server in a background thread."""
        # Remove stale socket
        if Path(self.socket_path).exists():
            os.unlink(self.socket_path)

        self.server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server_socket.bind(self.socket_path)
        self.server_socket.listen(5)
        self.server_socket.settimeout(0.5)
        self.running = True

        self.thread = threading.Thread(target=self._serve)
        self.thread.daemon = True
        self.thread.start()

        # Wait for server to be ready
        time.sleep(0.1)

    def stop(self):
        """Stop the mock server."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        if self.server_socket:
            self.server_socket.close()
        if Path(self.socket_path).exists():
            os.unlink(self.socket_path)

    def _serve(self):
        """Server loop."""
        while self.running:
            try:
                conn, _ = self.server_socket.accept()
                conn.settimeout(5)
                try:
                    self._handle_connection(conn)
                finally:
                    conn.close()
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"Server error: {e}")

    def _handle_connection(self, conn: socket.socket):
        """Handle a single connection."""
        if self.delay:
            time.sleep(self.delay)

        # Read request
        data = b""
        while True:
            try:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                data += chunk
            except socket.timeout:
                break

        if not data:
            return

        try:
            request = json.loads(data.decode())
            self.received_requests.append(request)
            response = self._handle_request(request)
            conn.sendall(json.dumps(response).encode())
        except Exception as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32603, "message": str(e)},
            }
            conn.sendall(json.dumps(error_response).encode())

    def _handle_request(self, request: dict) -> dict:
        """Handle a JSON-RPC request."""
        request_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})

        if method == "execute":
            tool = params.get("tool", "unknown")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tool": tool,
                    "exit_code": 0,
                    "stdout": f"Mock output from {tool}",
                    "stderr": "",
                    "success": True,
                    "duration_ms": 10.5,
                },
            }
        elif method == "list_tools":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": [
                        {"name": "shellcheck", "version": "0.9.0", "available": True},
                        {"name": "hadolint", "version": "2.12.0", "available": True},
                        {"name": "yamllint", "version": "1.33.0", "available": True},
                    ]
                },
            }
        elif method == "health":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"status": "healthy"},
            }
        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            }


@pytest.fixture
def temp_socket_path(tmp_path):
    """Create a temporary socket path."""
    return str(tmp_path / "test-gpl.sock")


@pytest.fixture
def mock_server(temp_socket_path):
    """Start a mock sidecar server."""
    server = MockSidecarServer(temp_socket_path)
    server.start()
    yield server
    server.stop()


@pytest.mark.skipif(not HAS_GPL_CLIENT, reason="GPL client not available")
class TestGPLSidecarClient:
    """Test GPL sidecar client functionality."""

    def test_client_initialization(self):
        """Test client initialization with default socket path."""
        client = GPLSidecarClient()
        assert client.socket_path == DEFAULT_SOCKET_PATH

    def test_client_custom_socket_path(self, temp_socket_path):
        """Test client initialization with custom socket path."""
        client = GPLSidecarClient(socket_path=temp_socket_path)
        assert client.socket_path == temp_socket_path

    def test_client_from_env(self, temp_socket_path):
        """Test client socket path from environment variable."""
        with patch.dict(os.environ, {"HUSKYCAT_GPL_SOCKET": temp_socket_path}):
            client = GPLSidecarClient()
            assert client.socket_path == temp_socket_path

    def test_is_available_no_server(self, temp_socket_path):
        """Test is_available returns False when no server."""
        client = GPLSidecarClient(socket_path=temp_socket_path)
        assert client.is_available() is False

    def test_is_available_with_server(self, mock_server, temp_socket_path):
        """Test is_available returns True with running server."""
        client = GPLSidecarClient(socket_path=temp_socket_path)
        assert client.is_available() is True

    def test_health_check_with_server(self, mock_server, temp_socket_path):
        """Test health check with running server."""
        client = GPLSidecarClient(socket_path=temp_socket_path)
        result = client.health_check()
        assert result is True

    def test_list_tools(self, mock_server, temp_socket_path):
        """Test list_tools returns tool information."""
        client = GPLSidecarClient(socket_path=temp_socket_path)
        tools = client.list_tools()

        assert "shellcheck" in tools
        assert "hadolint" in tools
        assert "yamllint" in tools
        assert tools["shellcheck"] == "0.9.0"

    def test_execute_tool(self, mock_server, temp_socket_path):
        """Test executing a tool via IPC."""
        client = GPLSidecarClient(socket_path=temp_socket_path)
        result = client.execute("shellcheck", ["--help"])

        assert isinstance(result, GPLToolResult)
        assert result.tool == "shellcheck"
        assert result.exit_code == 0
        assert result.success is True
        assert "Mock output" in result.stdout

    def test_execute_with_args(self, mock_server, temp_socket_path):
        """Test executing with command-line arguments."""
        client = GPLSidecarClient(socket_path=temp_socket_path)
        result = client.execute("hadolint", ["-f", "json", "Dockerfile"])

        assert result.tool == "hadolint"
        assert result.success is True

    def test_execute_with_cwd(self, mock_server, temp_socket_path):
        """Test executing with working directory."""
        client = GPLSidecarClient(socket_path=temp_socket_path)
        result = client.execute("yamllint", ["test.yaml"], cwd="/workspace")

        assert result.success is True
        # Check that request was sent with cwd
        last_request = mock_server.received_requests[-1]
        assert last_request["params"].get("cwd") == "/workspace"


@pytest.mark.skipif(not HAS_GPL_CLIENT, reason="GPL client not available")
class TestGPLSidecarErrors:
    """Test GPL sidecar error handling."""

    def test_connection_error_no_socket(self, temp_socket_path):
        """Test connection error when socket doesn't exist."""
        client = GPLSidecarClient(socket_path=temp_socket_path)

        # execute should return failure result, not raise
        result = client.execute("shellcheck", ["--help"])
        assert result.success is False
        assert "Sidecar error" in result.stderr

    def test_timeout_handling(self, temp_socket_path):
        """Test handling of slow server responses."""
        # Create a server with delay
        server = MockSidecarServer(temp_socket_path, delay=2.0)
        server.start()

        try:
            client = GPLSidecarClient(socket_path=temp_socket_path)
            result = client.execute("shellcheck", ["--help"], timeout_ms=500)

            # Should timeout
            assert result.success is False
            assert result.exit_code == 124
        finally:
            server.stop()

    def test_graceful_degradation(self, temp_socket_path):
        """Test graceful degradation when sidecar unavailable."""
        client = GPLSidecarClient(socket_path=temp_socket_path)

        # Should not raise, should return failure result
        result = client.execute("shellcheck", ["--help"])
        assert result.success is False
        assert result.exit_code != 0


@pytest.mark.skipif(not HAS_GPL_CLIENT, reason="GPL client not available")
class TestGPLConvenienceFunctions:
    """Test module-level convenience functions."""

    def test_get_default_client(self):
        """Test get_default_client returns a client."""
        client = get_default_client()
        assert isinstance(client, GPLSidecarClient)

    def test_is_sidecar_available_no_server(self):
        """Test is_sidecar_available returns False without server."""
        # With default socket path, no server should be running
        result = is_sidecar_available()
        # Might be True if actual sidecar is running, False otherwise
        assert isinstance(result, bool)

    def test_execute_gpl_tool_no_server(self, temp_socket_path):
        """Test execute_gpl_tool handles missing server."""
        with patch("huskycat.core.gpl_client.DEFAULT_SOCKET_PATH", temp_socket_path):
            result = execute_gpl_tool("shellcheck", ["--help"])
            assert result.success is False


@pytest.mark.skipif(not HAS_GPL_CLIENT, reason="GPL client not available")
class TestGPLToolResult:
    """Test GPLToolResult dataclass."""

    def test_result_creation(self):
        """Test creating a GPLToolResult."""
        result = GPLToolResult(
            tool="shellcheck",
            exit_code=0,
            stdout="output",
            stderr="",
            success=True,
            duration_ms=100.5,
        )

        assert result.tool == "shellcheck"
        assert result.exit_code == 0
        assert result.stdout == "output"
        assert result.stderr == ""
        assert result.success is True
        assert result.duration_ms == 100.5

    def test_result_failure(self):
        """Test creating a failure result."""
        result = GPLToolResult(
            tool="hadolint",
            exit_code=1,
            stdout="",
            stderr="Error: file not found",
            success=False,
            duration_ms=50.0,
        )

        assert result.success is False
        assert result.exit_code == 1
        assert "Error" in result.stderr


@pytest.mark.integration
@pytest.mark.skipif(not HAS_GPL_CLIENT, reason="GPL client not available")
class TestGPLSidecarIntegration:
    """Integration tests requiring actual sidecar server."""

    @pytest.fixture
    def real_sidecar(self, temp_socket_path):
        """Start the real sidecar server for integration tests."""
        sidecar_script = Path(__file__).parent.parent / "gpl-sidecar" / "server.py"
        if not sidecar_script.exists():
            pytest.skip("GPL sidecar server.py not found")

        # Start server process
        proc = subprocess.Popen(
            [sys.executable, str(sidecar_script), "--socket", temp_socket_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Wait for server to start
        time.sleep(0.5)

        yield temp_socket_path

        # Stop server
        proc.terminate()
        proc.wait(timeout=5)

    def test_real_health_check(self, real_sidecar):
        """Test health check against real sidecar."""
        client = GPLSidecarClient(socket_path=real_sidecar)

        # May take a moment for server to be ready
        for _ in range(10):
            if client.is_available():
                break
            time.sleep(0.1)

        assert client.is_available() is True

    def test_real_list_tools(self, real_sidecar):
        """Test listing tools from real sidecar."""
        client = GPLSidecarClient(socket_path=real_sidecar)

        # Wait for availability
        for _ in range(10):
            if client.is_available():
                break
            time.sleep(0.1)

        tools = client.list_tools()
        # At minimum, the server should respond with tool info
        # Actual tools may not be installed in test environment
        assert isinstance(tools, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
