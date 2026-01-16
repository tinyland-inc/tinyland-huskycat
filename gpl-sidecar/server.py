#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
#
# GPL-licensed IPC server for HuskyCat sidecar
# This file is GPL because it directly executes GPL-licensed tools
#
# Architecture:
# - Listens on Unix socket for JSON-RPC 2.0 requests
# - Executes GPL tools (shellcheck, hadolint, yamllint)
# - Returns results in structured format
# - Single-threaded, sequential execution model

import argparse
import json
import logging
import os
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger(__name__)


class GPLToolExecutor:
    """Executes GPL-licensed validation tools."""

    SUPPORTED_TOOLS = {
        "shellcheck": "/usr/bin/shellcheck",
        "hadolint": "/usr/bin/hadolint",
        "yamllint": "/usr/bin/yamllint",
    }

    @classmethod
    def execute(cls, tool: str, args: List[str], cwd: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute a GPL tool and return results.

        Args:
            tool: Tool name (shellcheck, hadolint, yamllint)
            args: Command-line arguments for the tool
            cwd: Working directory (default: /workspace)

        Returns:
            Dict with keys: success, stdout, stderr, exit_code
        """
        if tool not in cls.SUPPORTED_TOOLS:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Unsupported tool: {tool}",
                "exit_code": 127,
            }

        tool_path = cls.SUPPORTED_TOOLS[tool]
        if not os.path.exists(tool_path):
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Tool not found: {tool_path}",
                "exit_code": 127,
            }

        cmd = [tool_path] + args
        working_dir = cwd or "/workspace"

        logger.info(f"Executing: {' '.join(cmd)} (cwd={working_dir})")

        try:
            result = subprocess.run(
                cmd,
                cwd=working_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
                text=True,
            )

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Tool execution timed out after 30s",
                "exit_code": 124,
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Execution error: {str(e)}",
                "exit_code": 1,
            }


class JSONRPCServer:
    """JSON-RPC 2.0 server over Unix socket."""

    def __init__(self, socket_path: str):
        self.socket_path = socket_path
        self.executor = GPLToolExecutor()

    def handle_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle JSON-RPC 2.0 request.

        Supported methods:
        - execute: Execute a GPL tool
        - list_tools: List available tools
        - health: Health check

        Args:
            request_data: JSON-RPC 2.0 request dict

        Returns:
            JSON-RPC 2.0 response dict
        """
        request_id = request_data.get("id")
        method = request_data.get("method")
        params = request_data.get("params", {})

        logger.info(f"Request: method={method}, id={request_id}")

        # Validate JSON-RPC 2.0 format
        if "jsonrpc" not in request_data or request_data["jsonrpc"] != "2.0":
            return self._error_response(request_id, -32600, "Invalid JSON-RPC version")

        if not method:
            return self._error_response(request_id, -32600, "Missing method")

        # Route to method handler
        if method == "execute":
            return self._handle_execute(request_id, params)
        elif method == "list_tools":
            return self._handle_list_tools(request_id)
        elif method == "health":
            return self._handle_health(request_id)
        else:
            return self._error_response(request_id, -32601, f"Method not found: {method}")

    def _handle_execute(self, request_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle 'execute' method."""
        tool = params.get("tool")
        args = params.get("args", [])
        cwd = params.get("cwd")

        if not tool:
            return self._error_response(request_id, -32602, "Missing 'tool' parameter")

        if not isinstance(args, list):
            return self._error_response(request_id, -32602, "'args' must be a list")

        result = self.executor.execute(tool, args, cwd)

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result,
        }

    def _handle_list_tools(self, request_id: Any) -> Dict[str, Any]:
        """Handle 'list_tools' method."""
        tools = []
        for tool_name, tool_path in GPLToolExecutor.SUPPORTED_TOOLS.items():
            exists = os.path.exists(tool_path)
            version = "unknown"

            if exists:
                try:
                    result = subprocess.run(
                        [tool_path, "--version"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=5,
                        text=True,
                    )
                    version = result.stdout.strip().split("\n")[0]
                except Exception:
                    pass

            tools.append({
                "name": tool_name,
                "path": tool_path,
                "available": exists,
                "version": version,
            })

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"tools": tools},
        }

    def _handle_health(self, request_id: Any) -> Dict[str, Any]:
        """Handle 'health' method."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"status": "healthy", "server": "huskycat-gpl-sidecar"},
        }

    def _error_response(self, request_id: Any, code: int, message: str) -> Dict[str, Any]:
        """Create JSON-RPC 2.0 error response."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message,
            },
        }

    def start(self):
        """Start the Unix socket server."""
        # Remove stale socket
        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)

        # Create socket
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.bind(self.socket_path)
        sock.listen(5)

        # Set socket permissions
        os.chmod(self.socket_path, 0o666)

        logger.info(f"Server listening on {self.socket_path}")

        try:
            while True:
                conn, _ = sock.accept()
                try:
                    self._handle_connection(conn)
                finally:
                    conn.close()
        except KeyboardInterrupt:
            logger.info("Server shutting down")
        finally:
            sock.close()
            if os.path.exists(self.socket_path):
                os.unlink(self.socket_path)

    def _handle_connection(self, conn: socket.socket):
        """Handle a single client connection."""
        # Read request (max 1MB)
        data = b""
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            data += chunk
            if len(data) > 1024 * 1024:
                logger.warning("Request too large, dropping connection")
                return

        if not data:
            return

        try:
            request = json.loads(data.decode("utf-8"))
            response = self.handle_request(request)
            response_bytes = json.dumps(response).encode("utf-8")
            conn.sendall(response_bytes)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {e}")
            error = self._error_response(None, -32700, "Parse error")
            conn.sendall(json.dumps(error).encode("utf-8"))
        except Exception as e:
            logger.error(f"Request handling error: {e}")
            error = self._error_response(None, -32603, f"Internal error: {str(e)}")
            conn.sendall(json.dumps(error).encode("utf-8"))


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="HuskyCat GPL-licensed tools IPC server"
    )
    parser.add_argument(
        "--socket",
        default="/ipc/huskycat-gpl.sock",
        help="Unix socket path (default: /ipc/huskycat-gpl.sock)",
    )
    args = parser.parse_args()

    # Create IPC directory if needed
    socket_dir = os.path.dirname(args.socket)
    if socket_dir:
        os.makedirs(socket_dir, exist_ok=True)

    logger.info(f"Starting HuskyCat GPL Sidecar Server")
    logger.info(f"License: GPL-3.0-only")
    logger.info(f"Socket: {args.socket}")

    server = JSONRPCServer(args.socket)
    server.start()


if __name__ == "__main__":
    main()
