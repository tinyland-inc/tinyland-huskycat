#!/usr/bin/env python3
"""
HuskyCat MCP Server
Simple stdio-based MCP server for Claude Code integration
Uses the unified validation engine

Protocol Version: 2025-11-25
- Implements isError flag pattern for tool errors (enables LLM self-correction)
- Token tracking with configurable limits
- Recovery suggestions for error responses
"""

import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .unified_validation import ValidationEngine

# Token limits for output management
MAX_TOKENS = int(os.environ.get("MAX_MCP_OUTPUT_TOKENS", "25000"))
WARN_TOKENS = 10000

# Configure logging to stderr so it doesn't interfere with stdio
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


class MCPServer:
    """Simple MCP stdio server for validation tools

    Protocol Version: 2025-11-25
    - Tool errors return successful JSON-RPC with isError: true
    - Token tracking prevents context overflow
    - Recovery suggestions help LLM self-correct
    """

    def __init__(self) -> None:
        # Container-only mode - check if container runtime is available
        self.container_available = self._detect_container_available()
        self.engine = ValidationEngine(auto_fix=False)
        self.request_id = 0

        logger.info(
            f"MCP Server initialized (container-only mode): {self.container_available}"
        )

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation: ~4 chars per token

        This is a conservative estimate. Actual tokenization varies by model,
        but 4 chars/token is a reasonable approximation for code/text.
        """
        return len(text) // 4

    def _truncate_if_needed(self, text: str) -> tuple[str, int, bool]:
        """Truncate text if it exceeds MAX_TOKENS, return (text, token_count, was_truncated)"""
        token_count = self._estimate_tokens(text)

        if token_count > WARN_TOKENS:
            logger.warning(f"Tool output exceeds {WARN_TOKENS} tokens: {token_count}")

        if token_count > MAX_TOKENS:
            truncated_text = text[: MAX_TOKENS * 4] + "\n... [truncated - output exceeded token limit]"
            logger.warning(f"Output truncated from {token_count} to ~{MAX_TOKENS} tokens")
            return truncated_text, token_count, True

        return text, token_count, False

    def _get_recovery_suggestions(self, error: Exception, context: Optional[str] = None) -> List[str]:
        """Generate context-aware recovery suggestions for errors"""
        suggestions = []
        error_str = str(error).lower()

        # File/path related errors
        if "no such file" in error_str or "not found" in error_str or "path" in error_str:
            suggestions.extend([
                "Verify the file path is correct and exists",
                "Check for typos in the path",
                "Use absolute paths instead of relative paths",
            ])

        # Permission errors
        if "permission" in error_str or "access denied" in error_str:
            suggestions.extend([
                "Check file permissions (chmod)",
                "Verify you have read/write access to the file",
                "Try running with appropriate privileges",
            ])

        # Container runtime errors
        if "container" in error_str or "podman" in error_str or "docker" in error_str:
            suggestions.extend([
                "Verify container runtime is available (podman or docker)",
                "Check if the huskycat:local image exists",
                "Try pulling the image: podman pull huskycat:local",
            ])

        # Timeout errors
        if "timeout" in error_str:
            suggestions.extend([
                "The operation took too long - try a smaller scope",
                "Check for infinite loops or large files",
                "Consider increasing timeout limits",
            ])

        # Validation tool errors
        if "validator" in error_str or "validation" in error_str:
            suggestions.extend([
                "Check if the required validation tool is installed",
                "Verify the file type matches the validator",
                "Try running with --fix to auto-fix issues",
            ])

        # Generic suggestions if none matched
        if not suggestions:
            suggestions = [
                "Check the error message for specific details",
                "Verify all required dependencies are installed",
                "Try running the command manually for more details",
            ]

        return suggestions

    def _detect_container_available(self) -> bool:
        """Detect if we're in a container or have container runtime available"""
        # First check if we're running inside a container
        if self._is_running_in_container():
            logger.info("Running inside container - direct tool execution available")
            return True

        # If not in container, check for container runtime
        try:
            # Try podman first (preferred), then docker
            for runtime in ["podman", "docker"]:
                result = subprocess.run(
                    [runtime, "--version"], capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    logger.info(f"Container runtime detected: {runtime}")
                    return True
        except (
            subprocess.SubprocessError,
            FileNotFoundError,
            subprocess.TimeoutExpired,
        ):
            pass

        logger.warning("No container runtime detected - validation may fail")
        return False

    def _is_running_in_container(self) -> bool:
        """Detect if we're running inside a container (same logic as Validator class)"""
        import os

        # Check for container-specific environment indicators
        return (
            os.path.exists("/.dockerenv")  # Docker
            or bool(os.environ.get("container"))  # Podman
            or os.path.exists("/run/.containerenv")  # Podman
        )

    def _run_container_validation(
        self, command_args: list, cwd: str = "."
    ) -> Dict[str, Any]:
        """Run validation - directly if in container, via container runtime if on host"""
        try:
            # If we're already inside a container, execute commands directly
            if self._is_running_in_container():
                logger.info(
                    f"Running direct validation (inside container): {' '.join(command_args)}"
                )

                result = subprocess.run(
                    command_args, cwd=cwd, capture_output=True, text=True, timeout=60
                )

                return {
                    "success": result.returncode == 0,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                    "runtime": "direct",
                }

            # If on host, try to run via container runtime
            for runtime in ["podman", "docker"]:
                try:
                    cmd = [
                        runtime,
                        "run",
                        "--rm",
                        "-v",
                        f"{cwd}:/workspace",
                        "huskycat:local",
                    ] + command_args

                    logger.info(f"Running container validation: {' '.join(cmd)}")

                    result = subprocess.run(
                        cmd, cwd=cwd, capture_output=True, text=True, timeout=60
                    )

                    return {
                        "success": result.returncode == 0,
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "returncode": result.returncode,
                        "runtime": runtime,
                    }

                except subprocess.SubprocessError as e:
                    logger.warning(f"Container runtime {runtime} failed: {e}")
                    continue

            # If no runtime worked
            raise RuntimeError("No container runtime available")

        except Exception as e:
            logger.error(f"Container validation failed: {e}")
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1,
                "runtime": "none",
            }

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a JSON-RPC request"""
        method = request.get("method", "")
        params = request.get("params", {})
        request_id = request.get("id")

        logger.info(f"Handling request: {method}")

        try:
            if method == "initialize":
                return self._handle_initialize(request_id)
            elif method == "tools/list":
                return self._handle_list_tools(request_id)
            elif method == "tools/call":
                return self._handle_tool_call(params, request_id)
            else:
                # Method not found is a protocol-level error
                return self._error_response(
                    request_id, -32601, f"Method not found: {method}"
                )
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            # For tools/call, return tool error with isError flag
            # For other methods, use protocol-level error
            if method == "tools/call":
                return self._tool_error_response(request_id, e, context=f"method:{method}")
            return self._error_response(request_id, -32603, str(e))

    def _handle_initialize(self, request_id: Any) -> Dict[str, Any]:
        """Handle initialization request"""
        # Include execution mode in server info (always container-only now)
        execution_mode = "container-only"
        tool_count = len(self.engine.validators)

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2025-11-25",
                "capabilities": {"tools": {}, "prompts": {}},
                "serverInfo": {
                    "name": "huskycat-mcp",
                    "version": "2.0.0",
                    "executionMode": execution_mode,
                    "containerAvailable": self.container_available,
                    "toolCount": tool_count,
                },
            },
        }

    def _handle_list_tools(self, request_id: Any) -> Dict[str, Any]:
        """List available validation tools"""
        tools = []

        # Add validate tool
        tools.append(
            {
                "name": "validate",
                "description": "Validate code files with appropriate linters",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "File or directory path to validate",
                        },
                        "fix": {
                            "type": "boolean",
                            "description": "Auto-fix issues where possible",
                            "default": False,
                        },
                    },
                    "required": ["path"],
                },
            }
        )

        # Add validate_staged tool
        tools.append(
            {
                "name": "validate_staged",
                "description": "Validate files staged for git commit",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "fix": {
                            "type": "boolean",
                            "description": "Auto-fix issues where possible",
                            "default": False,
                        }
                    },
                },
            }
        )

        # Add individual tool validators
        for validator in self.engine.validators:
            tools.append(
                {
                    "name": f"validate_{validator.name}",
                    "description": f"Run {validator.name} on specified files",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "File path to validate",
                            },
                            "fix": {
                                "type": "boolean",
                                "description": "Auto-fix issues where possible",
                                "default": False,
                            },
                        },
                        "required": ["path"],
                    },
                }
            )

        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": tools}}

    def _handle_tool_call(
        self, params: Dict[str, Any], request_id: Any
    ) -> Dict[str, Any]:
        """Handle a tool call request"""
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        logger.info(f"Calling tool: {tool_name} with args: {arguments}")

        try:
            if tool_name == "validate":
                result = self._validate(arguments)
            elif tool_name == "validate_staged":
                result = self._validate_staged(arguments)
            elif tool_name.startswith("validate_"):
                # Individual validator
                validator_name = tool_name.replace("validate_", "")
                result = self._validate_with_specific_tool(validator_name, arguments)
            else:
                return self._error_response(
                    request_id, -32602, f"Unknown tool: {tool_name}"
                )

            # Serialize and check token count
            result_text = json.dumps(result, indent=2)
            result_text, token_count, was_truncated = self._truncate_if_needed(result_text)

            response_content = {
                "content": [{"type": "text", "text": result_text}],
            }

            # Add metadata about truncation if it occurred
            if was_truncated:
                response_content["metadata"] = {
                    "truncated": True,
                    "original_tokens": token_count,
                    "max_tokens": MAX_TOKENS,
                }

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": response_content,
            }
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            # Return tool error with isError flag (NOT protocol-level error)
            # This enables LLM self-correction by keeping it in the tool result flow
            return self._tool_error_response(request_id, e, context=f"tool:{tool_name}")

    def _validate(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Validate files or directories"""
        path_str = arguments.get("path", ".")
        fix = arguments.get("fix", False)

        # Container-only execution mode
        if self.container_available:
            # Build container command
            cmd_args = ["validate"]
            if fix:
                cmd_args.append("--fix")
            if path_str != ".":
                cmd_args.append(path_str)

            # Run in container
            result = self._run_container_validation(cmd_args, cwd=".")

            # Parse container output and return structured result
            return {
                "summary": f"Container validation ({'success' if result['success'] else 'failed'})",
                "container_output": result["stdout"],
                "container_errors": result["stderr"],
                "success": result["success"],
                "runtime": result["runtime"],
            }

        # Fallback to local engine execution
        # Update engine settings
        self.engine.auto_fix = fix

        # Validate
        path = Path(path_str)
        if path.is_file():
            results = self.engine.validate_file(path)
            validation_results = {str(path): results} if results else {}
        else:
            validation_results = self.engine.validate_directory(path)

        # Generate summary
        summary = self.engine.get_summary(validation_results)

        return {
            "summary": summary,
            "results": {
                filepath: [r.to_dict() for r in file_results]
                for filepath, file_results in validation_results.items()
            },
        }

    def _validate_staged(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Validate staged files"""
        fix = arguments.get("fix", False)

        # Container-only execution mode
        if self.container_available:
            # Build container command
            cmd_args = ["validate", "--staged"]
            if fix:
                cmd_args.append("--fix")

            # Run in container
            result = self._run_container_validation(cmd_args, cwd=".")

            # Parse container output and return structured result
            return {
                "summary": f"Container staged validation ({'success' if result['success'] else 'failed'})",
                "container_output": result["stdout"],
                "container_errors": result["stderr"],
                "success": result["success"],
                "runtime": result["runtime"],
            }

        # Fallback to local engine execution
        # Update engine settings
        self.engine.auto_fix = fix

        # Validate staged files
        validation_results = self.engine.validate_staged_files()

        # Generate summary
        summary = self.engine.get_summary(validation_results)

        return {
            "summary": summary,
            "results": {
                filepath: [r.to_dict() for r in file_results]
                for filepath, file_results in validation_results.items()
            },
        }

    def _validate_with_specific_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate with a specific tool"""
        path_str = arguments.get("path", ".")
        fix = arguments.get("fix", False)

        # Use container execution if enabled - specific tools through general validate
        if self.container_available:
            # Container mode: run general validation (comprehensive)
            cmd_args = ["validate"]
            if fix:
                cmd_args.append("--fix")
            if path_str != ".":
                cmd_args.append(path_str)

            # Run in container
            result = self._run_container_validation(cmd_args, cwd=".")

            # Parse container output and return structured result
            return {
                "tool": f"{tool_name} (via container)",
                "summary": f"Container {tool_name} validation ({'success' if result['success'] else 'failed'})",
                "container_output": result["stdout"],
                "container_errors": result["stderr"],
                "success": result["success"],
                "runtime": result["runtime"],
            }

        # Fallback to local engine execution
        # Find the validator
        validator = None
        for v in self.engine.validators:
            if v.name == tool_name:
                validator = v
                break

        if not validator:
            raise ValueError(f"Validator not found: {tool_name}")

        # Update settings
        validator.auto_fix = fix

        # Validate
        path = Path(path_str)
        validation_result = validator.validate(path)

        return {"tool": tool_name, "result": validation_result.to_dict()}

    def _tool_error_response(
        self, request_id: Any, error: Exception, context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a tool error response with isError flag

        Per MCP protocol 2025-11-25: Tool errors should return successful JSON-RPC
        response with isError: true in the result. This enables LLM self-correction
        by keeping errors in the tool result flow rather than breaking it with
        protocol-level errors.
        """
        error_message = f"Error: {error}"
        recovery_suggestions = self._get_recovery_suggestions(error, context)

        error_content = {
            "error": str(error),
            "error_type": type(error).__name__,
            "recovery_suggestions": recovery_suggestions,
        }

        if context:
            error_content["context"] = context

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [
                    {"type": "text", "text": error_message},
                    {"type": "text", "text": json.dumps(error_content, indent=2)},
                ],
                "isError": True,
            },
        }

    def _error_response(
        self, request_id: Any, code: int, message: str
    ) -> Dict[str, Any]:
        """Create a protocol-level error response

        Note: For tool execution errors, use _tool_error_response instead.
        Protocol-level errors should only be used for:
        - Method not found (-32601)
        - Invalid request (-32600)
        - Parse error (-32700)
        """
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": code, "message": message},
        }

    def run(self) -> None:
        """Run the MCP server"""
        logger.info("HuskyCat MCP Server starting...")

        while True:
            try:
                # Read a line from stdin
                line = sys.stdin.readline()
                if not line:
                    break

                # Parse JSON-RPC request
                try:
                    request = json.loads(line.strip())
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON: {e}")
                    continue

                # Handle the request
                response = self.handle_request(request)

                # Send response
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()

            except KeyboardInterrupt:
                logger.info("Server interrupted")
                break
            except Exception as e:
                logger.error(f"Server error: {e}")
                continue

        logger.info("HuskyCat MCP Server stopped")


def main() -> None:
    """Main entry point"""
    server = MCPServer()
    server.run()


if __name__ == "__main__":
    main()
