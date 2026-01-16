#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
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
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from dataclasses import asdict

from .core.process_manager import ProcessManager, ValidationRun
from .core.task_manager import TaskManager, TaskStatus, get_task_manager
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
        self.process_manager = ProcessManager()
        self.task_manager = get_task_manager()
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
                "protocolVersion": "2024-11-05",
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

        # Add result query tools
        tools.append(
            {
                "name": "get_last_run",
                "description": "Get the most recent validation run with results. Returns run metadata including success status, error count, and tools used.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            }
        )

        tools.append(
            {
                "name": "get_run_history",
                "description": "Get recent validation run history. Returns a list of previous runs with their status and results summary.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of runs to return",
                            "default": 10,
                        },
                    },
                },
            }
        )

        tools.append(
            {
                "name": "get_run_results",
                "description": "Get detailed results for a specific validation run by run_id.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "run_id": {
                            "type": "string",
                            "description": "The run_id to get results for (e.g., 20241219_114200_123456)",
                        },
                    },
                    "required": ["run_id"],
                },
            }
        )

        tools.append(
            {
                "name": "get_running_validations",
                "description": "Check if any validations are currently in progress. Returns list of running validation processes.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            }
        )

        # Async validation tools - for long-running validations
        tools.append(
            {
                "name": "validate_async",
                "description": "Start an asynchronous validation and return immediately with a task_id. "
                "Use this for long-running validations (mypy: 10-30s, CI schema: 5-15s) to avoid blocking. "
                "Poll with get_task_status to check progress and get results.",
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

        tools.append(
            {
                "name": "get_task_status",
                "description": "Get the status of an async validation task. "
                "Returns task status (pending, running, completed, failed), progress, and results when complete.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "The task_id returned from validate_async",
                        },
                    },
                    "required": ["task_id"],
                },
            }
        )

        tools.append(
            {
                "name": "list_async_tasks",
                "description": "List all async validation tasks. "
                "Optionally filter by status (pending, running, completed, failed).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "description": "Filter by task status",
                            "enum": ["pending", "running", "completed", "failed", "cancelled"],
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of tasks to return",
                            "default": 20,
                        },
                    },
                },
            }
        )

        tools.append(
            {
                "name": "cancel_async_task",
                "description": "Cancel a running async validation task.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "The task_id to cancel",
                        },
                    },
                    "required": ["task_id"],
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
            elif tool_name == "get_last_run":
                result = self._get_last_run(arguments)
            elif tool_name == "get_run_history":
                result = self._get_run_history(arguments)
            elif tool_name == "get_run_results":
                result = self._get_run_results(arguments)
            elif tool_name == "get_running_validations":
                result = self._get_running_validations(arguments)
            elif tool_name == "validate_async":
                result = self._validate_async(arguments)
            elif tool_name == "get_task_status":
                result = self._get_task_status(arguments)
            elif tool_name == "list_async_tasks":
                result = self._list_async_tasks(arguments)
            elif tool_name == "cancel_async_task":
                result = self._cancel_async_task(arguments)
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

    def _get_last_run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get the most recent validation run with results.

        Checks both the last_run tracking file and recent run history
        to provide the most recent validation result.
        """
        # First try check_previous_run which returns failed runs
        run = self.process_manager.check_previous_run()

        # If no failed run, check the last_run file directly for any run
        if run is None:
            last_run_file = self.process_manager.last_run_file
            if last_run_file.exists():
                try:
                    import json
                    data = json.loads(last_run_file.read_text())
                    run = ValidationRun(**data)
                except (json.JSONDecodeError, TypeError, ValueError) as e:
                    logger.warning(f"Could not parse last run file: {e}")

        # If still no run found, try getting the most recent from history
        if run is None:
            history = self.process_manager.get_run_history(limit=1)
            if history:
                run = history[0]

        if run is None:
            return {
                "found": False,
                "message": "No validation runs found. Run 'huskycat validate' to create a validation record.",
            }

        # Load detailed results if available
        run_results_file = self.process_manager.cache_dir / f"{run.run_id}_results.json"
        detailed_results = None
        if run_results_file.exists():
            try:
                import json
                detailed_results = json.loads(run_results_file.read_text())
            except Exception as e:
                logger.warning(f"Could not load detailed results: {e}")

        # Load log file content if available
        log_file = self.process_manager.logs_dir / f"{run.run_id}.log"
        log_content = None
        if log_file.exists():
            try:
                log_content = log_file.read_text()
                # Truncate if too long
                if len(log_content) > 5000:
                    log_content = log_content[-5000:] + "\n... [truncated, showing last 5000 chars]"
            except Exception as e:
                logger.warning(f"Could not load log file: {e}")

        return {
            "found": True,
            "run": asdict(run),
            "detailed_results": detailed_results,
            "log_content": log_content,
        }

    def _get_run_history(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get recent validation run history."""
        limit = arguments.get("limit", 10)

        # Ensure limit is reasonable
        limit = min(max(1, limit), 100)

        runs = self.process_manager.get_run_history(limit=limit)

        return {
            "count": len(runs),
            "limit": limit,
            "runs": [asdict(r) for r in runs],
        }

    def _get_run_results(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed results for a specific validation run."""
        run_id = arguments.get("run_id")

        if not run_id:
            raise ValueError("run_id is required")

        # Look for the run file
        run_file = self.process_manager.cache_dir / f"{run_id}.json"
        if not run_file.exists():
            return {
                "found": False,
                "run_id": run_id,
                "message": f"No validation run found with ID: {run_id}",
            }

        try:
            import json
            run_data = json.loads(run_file.read_text())
            run = ValidationRun(**run_data)
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            raise ValueError(f"Could not parse run file: {e}")

        # Load detailed results if available
        results_file = self.process_manager.cache_dir / f"{run_id}_results.json"
        detailed_results = None
        if results_file.exists():
            try:
                detailed_results = json.loads(results_file.read_text())
            except Exception as e:
                logger.warning(f"Could not load detailed results: {e}")

        # Load log file content if available
        log_file = self.process_manager.logs_dir / f"{run_id}.log"
        log_content = None
        if log_file.exists():
            try:
                log_content = log_file.read_text()
                # Truncate if too long
                if len(log_content) > 10000:
                    log_content = log_content[-10000:] + "\n... [truncated, showing last 10000 chars]"
            except Exception as e:
                logger.warning(f"Could not load log file: {e}")

        return {
            "found": True,
            "run": asdict(run),
            "detailed_results": detailed_results,
            "log_content": log_content,
        }

    def _get_running_validations(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Check if any validations are currently in progress."""
        # Cleanup zombies first to ensure accurate status
        self.process_manager.cleanup_zombies()

        running = self.process_manager.get_running_validations()

        return {
            "count": len(running),
            "running": len(running) > 0,
            "validations": running,
        }

    # ==========================================================================
    # Async Validation Tools
    # ==========================================================================

    def _validate_async(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Start async validation, return task ID immediately.

        This allows long-running validations (mypy: 10-30s, CI schema: 5-15s)
        to run without blocking the MCP client. Use get_task_status to poll
        for results.
        """
        path_str = arguments.get("path", ".")
        fix = arguments.get("fix", False)

        # Create task
        task_id = self.task_manager.create_task(
            tool_name="validate",
            arguments={"path": path_str, "fix": fix},
        )

        # Start validation in background thread
        thread = threading.Thread(
            target=self._run_async_validation,
            args=(task_id, arguments),
            daemon=True,
            name=f"async-validate-{task_id}",
        )
        thread.start()

        logger.info(f"Started async validation task {task_id} for path: {path_str}")

        return {
            "task_id": task_id,
            "status": "started",
            "poll_tool": "get_task_status",
            "message": f"Validation started for '{path_str}'. Poll get_task_status with task_id='{task_id}' to check progress.",
        }

    def _run_async_validation(self, task_id: str, arguments: Dict[str, Any]) -> None:
        """Run validation in background thread, update task manager with results.

        This method runs in a daemon thread and should not raise exceptions
        that could crash the server.
        """
        try:
            path_str = arguments.get("path", ".")

            # Update task to running
            self.task_manager.update_progress(
                task_id, 0, 100, f"Starting validation for {path_str}..."
            )

            # Run the actual validation (this may take 10-30s)
            self.task_manager.update_progress(
                task_id, 10, 100, "Running validators..."
            )

            result = self._validate(arguments)

            # Update progress to 90% before completion
            self.task_manager.update_progress(
                task_id, 90, 100, "Processing results..."
            )

            # Complete the task with results
            self.task_manager.complete_task(task_id, result)
            logger.info(f"Async validation task {task_id} completed successfully")

        except Exception as e:
            logger.error(f"Async validation task {task_id} failed: {e}")
            self.task_manager.fail_task(task_id, str(e))

    def _get_task_status(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get async task status and results.

        Returns task status including progress and results when complete.
        """
        task_id = arguments.get("task_id")

        if not task_id:
            raise ValueError("task_id is required")

        task = self.task_manager.get_task(task_id)

        if task is None:
            return {
                "found": False,
                "task_id": task_id,
                "error": f"Task not found: {task_id}",
                "message": "The task may have expired or never existed. Use list_async_tasks to see available tasks.",
            }

        # Build response based on task state
        response: Dict[str, Any] = {
            "found": True,
            "task_id": task.task_id,
            "status": task.status.value,
            "progress": task.progress,
            "total": task.total,
            "progress_percent": task.progress_percent,
            "message": task.message,
            "started": task.started,
            "completed": task.completed,
            "tool_name": task.tool_name,
        }

        # Include result for completed tasks
        if task.status == TaskStatus.COMPLETED:
            response["result"] = task.result
            response["message"] = "Validation completed successfully. See 'result' for details."

        # Include error for failed tasks
        if task.status == TaskStatus.FAILED:
            response["error"] = task.error
            response["message"] = f"Validation failed: {task.error}"

        # Include reason for cancelled tasks
        if task.status == TaskStatus.CANCELLED:
            response["error"] = task.error
            response["message"] = f"Task was cancelled: {task.error}"

        return response

    def _list_async_tasks(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List all async validation tasks, optionally filtered by status."""
        status_filter = arguments.get("status")
        limit = arguments.get("limit", 20)

        # Ensure limit is reasonable
        limit = min(max(1, limit), 100)

        # Convert status string to enum if provided
        status_enum = None
        if status_filter:
            try:
                status_enum = TaskStatus(status_filter)
            except ValueError:
                raise ValueError(
                    f"Invalid status filter: {status_filter}. "
                    f"Valid values: pending, running, completed, failed, cancelled"
                )

        tasks = self.task_manager.list_tasks(status=status_enum, limit=limit)

        return {
            "count": len(tasks),
            "filter": status_filter,
            "limit": limit,
            "tasks": [task.to_dict() for task in tasks],
        }

    def _cancel_async_task(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Cancel a running async validation task."""
        task_id = arguments.get("task_id")

        if not task_id:
            raise ValueError("task_id is required")

        task = self.task_manager.get_task(task_id)

        if task is None:
            return {
                "success": False,
                "task_id": task_id,
                "error": f"Task not found: {task_id}",
            }

        if task.is_complete:
            return {
                "success": False,
                "task_id": task_id,
                "error": f"Task already {task.status.value}, cannot cancel",
                "status": task.status.value,
            }

        # Cancel the task
        cancelled = self.task_manager.cancel_task(task_id, reason="Cancelled via MCP")

        if cancelled:
            return {
                "success": True,
                "task_id": task_id,
                "message": "Task cancelled successfully",
                "status": "cancelled",
            }
        else:
            return {
                "success": False,
                "task_id": task_id,
                "error": "Failed to cancel task",
            }

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
