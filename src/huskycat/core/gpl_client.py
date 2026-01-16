# SPDX-License-Identifier: Apache-2.0
"""IPC client for GPL sidecar communication.

This module provides a client for communicating with the GPL-licensed tool
sidecar via Unix socket using JSON-RPC 2.0 protocol.

Architecture:
- Connects to GPL sidecar via Unix socket
- Sends JSON-RPC 2.0 requests (execute, list_tools, health)
- Handles connection errors gracefully
- Auto-detects socket path from environment or default

The sidecar executes GPL tools (shellcheck, hadolint, yamllint) in isolation
to maintain Apache-2.0 licensing for the main HuskyCat codebase.
"""

import json
import logging
import os
import socket
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Default socket path (host-side)
DEFAULT_SOCKET_PATH = f"/tmp/huskycat-gpl-{os.getuid()}.sock"


@dataclass
class GPLToolResult:
    """Result from GPL tool execution."""

    tool: str
    exit_code: int
    stdout: str
    stderr: str
    success: bool
    duration_ms: float


class GPLSidecarError(Exception):
    """Base exception for GPL sidecar errors."""

    pass


class GPLSidecarConnectionError(GPLSidecarError):
    """Sidecar connection error."""

    pass


class GPLSidecarTimeoutError(GPLSidecarError):
    """Sidecar request timeout."""

    pass


class GPLSidecarClient:
    """Client for communicating with GPL sidecar via IPC.

    Example:
        client = GPLSidecarClient()
        if client.is_available():
            result = client.execute("shellcheck", ["script.sh"])
            print(result.stdout)
    """

    def __init__(self, socket_path: Optional[str] = None):
        """Initialize GPL sidecar client.

        Args:
            socket_path: Unix socket path (default: from env or /tmp/huskycat-gpl-{uid}.sock)
        """
        self.socket_path = socket_path or os.environ.get(
            "HUSKYCAT_GPL_SOCKET", DEFAULT_SOCKET_PATH
        )
        self._request_id = 0

    def _next_request_id(self) -> int:
        """Get next JSON-RPC request ID."""
        self._request_id += 1
        return self._request_id

    def _send_request(
        self, method: str, params: Optional[Dict[str, Any]] = None, timeout: float = 30.0
    ) -> Dict[str, Any]:
        """Send JSON-RPC 2.0 request to sidecar.

        Args:
            method: JSON-RPC method name
            params: Method parameters (optional)
            timeout: Socket timeout in seconds

        Returns:
            JSON-RPC result dict

        Raises:
            GPLSidecarConnectionError: Connection failed
            GPLSidecarTimeoutError: Request timed out
            GPLSidecarError: RPC error or invalid response
        """
        request = {
            "jsonrpc": "2.0",
            "id": self._next_request_id(),
            "method": method,
        }
        if params is not None:
            request["params"] = params

        try:
            # Connect to Unix socket
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(timeout)

            try:
                sock.connect(self.socket_path)
            except FileNotFoundError:
                raise GPLSidecarConnectionError(
                    f"Socket not found: {self.socket_path}. Is the sidecar running?"
                )
            except ConnectionRefusedError:
                raise GPLSidecarConnectionError(
                    f"Connection refused: {self.socket_path}"
                )
            except socket.timeout:
                raise GPLSidecarTimeoutError(
                    f"Connection timeout: {self.socket_path}"
                )

            # Send request
            request_bytes = json.dumps(request).encode("utf-8")
            sock.sendall(request_bytes)

            # Shutdown write side to signal end of request
            sock.shutdown(socket.SHUT_WR)

            # Receive response (max 1MB)
            response_data = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response_data += chunk
                if len(response_data) > 1024 * 1024:
                    raise GPLSidecarError("Response too large (>1MB)")

            if not response_data:
                raise GPLSidecarError("Empty response from sidecar")

            # Parse JSON-RPC response
            response = json.loads(response_data.decode("utf-8"))

            # Check for JSON-RPC error
            if "error" in response:
                error = response["error"]
                code = error.get("code", -32603)
                message = error.get("message", "Unknown error")
                raise GPLSidecarError(f"RPC error {code}: {message}")

            # Return result
            if "result" not in response:
                raise GPLSidecarError("Invalid JSON-RPC response: missing 'result'")

            return response["result"]

        except socket.timeout:
            raise GPLSidecarTimeoutError(f"Request timeout after {timeout}s")
        except json.JSONDecodeError as e:
            raise GPLSidecarError(f"Invalid JSON response: {e}")
        except GPLSidecarError:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            raise GPLSidecarError(f"Unexpected error: {e}")
        finally:
            sock.close()

    def is_available(self) -> bool:
        """Check if sidecar is running and accessible.

        Returns:
            True if sidecar is healthy, False otherwise
        """
        try:
            result = self.health_check()
            return result
        except Exception as e:
            logger.debug(f"GPL sidecar not available: {e}")
            return False

    def execute(
        self,
        tool: str,
        args: List[str],
        cwd: Optional[str] = None,
        stdin: Optional[str] = None,
        timeout_ms: int = 30000,
    ) -> GPLToolResult:
        """Execute a GPL tool via sidecar.

        Args:
            tool: Tool name (shellcheck, hadolint, yamllint)
            args: Command-line arguments
            cwd: Working directory (default: /workspace in container)
            stdin: Optional stdin input (not yet implemented in server)
            timeout_ms: Execution timeout in milliseconds

        Returns:
            GPLToolResult with execution results

        Raises:
            GPLSidecarError: Execution failed or sidecar unavailable
        """
        start_time = time.time()

        params: Dict[str, Any] = {
            "tool": tool,
            "args": args,
        }
        if cwd is not None:
            params["cwd"] = cwd
        # Note: stdin not yet supported by server, but included for future

        # Convert timeout to seconds for socket timeout
        socket_timeout = timeout_ms / 1000.0

        try:
            result = self._send_request("execute", params, timeout=socket_timeout)
        except GPLSidecarTimeoutError:
            # Convert to result with timeout exit code
            duration_ms = (time.time() - start_time) * 1000
            return GPLToolResult(
                tool=tool,
                exit_code=124,
                stdout="",
                stderr=f"Tool execution timed out after {timeout_ms}ms",
                success=False,
                duration_ms=duration_ms,
            )
        except GPLSidecarError as e:
            # Convert other errors to result
            duration_ms = (time.time() - start_time) * 1000
            return GPLToolResult(
                tool=tool,
                exit_code=1,
                stdout="",
                stderr=f"Sidecar error: {e}",
                success=False,
                duration_ms=duration_ms,
            )

        duration_ms = (time.time() - start_time) * 1000

        return GPLToolResult(
            tool=tool,
            exit_code=result.get("exit_code", 1),
            stdout=result.get("stdout", ""),
            stderr=result.get("stderr", ""),
            success=result.get("success", False),
            duration_ms=duration_ms,
        )

    def list_tools(self) -> Dict[str, str]:
        """Get available tools and versions from sidecar.

        Returns:
            Dict mapping tool name to version string

        Raises:
            GPLSidecarError: Request failed
        """
        result = self._send_request("list_tools", timeout=5.0)

        tools_dict = {}
        for tool_info in result.get("tools", []):
            name = tool_info.get("name")
            version = tool_info.get("version", "unknown")
            available = tool_info.get("available", False)

            if name and available:
                tools_dict[name] = version

        return tools_dict

    def health_check(self) -> bool:
        """Check sidecar health.

        Returns:
            True if sidecar is healthy, False otherwise
        """
        try:
            result = self._send_request("health", timeout=2.0)
            status = result.get("status")
            return status == "healthy"
        except Exception:
            return False


def get_default_client() -> GPLSidecarClient:
    """Get default GPL sidecar client instance.

    Returns:
        GPLSidecarClient configured with default socket path
    """
    return GPLSidecarClient()


# Convenience module-level functions
def is_sidecar_available() -> bool:
    """Check if GPL sidecar is available.

    Returns:
        True if sidecar is running and healthy
    """
    client = get_default_client()
    return client.is_available()


def execute_gpl_tool(
    tool: str,
    args: List[str],
    cwd: Optional[str] = None,
    timeout_ms: int = 30000,
) -> GPLToolResult:
    """Execute a GPL tool via sidecar (convenience function).

    Args:
        tool: Tool name
        args: Command-line arguments
        cwd: Working directory
        timeout_ms: Timeout in milliseconds

    Returns:
        GPLToolResult with execution results
    """
    client = get_default_client()
    return client.execute(tool, args, cwd=cwd, timeout_ms=timeout_ms)
