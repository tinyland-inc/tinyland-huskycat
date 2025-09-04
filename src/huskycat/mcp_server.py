#!/usr/bin/env python3
"""
HuskyCat MCP Server
Simple stdio-based MCP server for Claude Code integration
Uses the unified validation engine
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

from .unified_validation import ValidationEngine

# Configure logging to stderr so it doesn't interfere with stdio
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


class MCPServer:
    """Simple MCP stdio server for validation tools"""

    def __init__(self):
        self.engine = ValidationEngine(auto_fix=False, use_container=False)
        self.request_id = 0

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
                return self._error_response(
                    request_id, -32601, f"Method not found: {method}"
                )
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return self._error_response(request_id, -32603, str(e))

    def _handle_initialize(self, request_id: Any) -> Dict[str, Any]:
        """Handle initialization request"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}, "prompts": {}},
                "serverInfo": {"name": "huskycat-mcp", "version": "2.0.0"},
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

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
                },
            }
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            return self._error_response(request_id, -32603, str(e))

    def _validate(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Validate files or directories"""
        path_str = arguments.get("path", ".")
        fix = arguments.get("fix", False)

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
        result = validator.validate(path)

        return {"tool": tool_name, "result": result.to_dict()}

    def _error_response(
        self, request_id: Any, code: int, message: str
    ) -> Dict[str, Any]:
        """Create an error response"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": code, "message": message},
        }

    def run(self):
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


def main():
    """Main entry point"""
    server = MCPServer()
    server.run()


if __name__ == "__main__":
    main()
