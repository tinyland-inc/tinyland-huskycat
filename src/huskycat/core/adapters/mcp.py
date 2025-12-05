"""
MCP Mode Adapter.

Optimized for AI assistant integration:
- JSON-RPC 2.0 protocol
- stdio transport
- Tool registration for Claude Code
"""

from .base import AdapterConfig, ModeAdapter, OutputFormat


class MCPAdapter(ModeAdapter):
    """
    Adapter for MCP (Model Context Protocol) mode.

    Requirements:
    - JSON-RPC protocol: stdio transport
    - Tool registration: Expose validators as tools
    - Context-aware: Understand project structure
    - No terminal output: Pure protocol
    - Stateless requests: Each call independent
    - Error responses: JSON-RPC error format
    """

    @property
    def name(self) -> str:
        return "mcp"

    @property
    def config(self) -> AdapterConfig:
        return AdapterConfig(
            output_format=OutputFormat.JSONRPC,  # JSON-RPC 2.0
            interactive=False,  # Never prompt
            fail_fast=True,  # Per-request handling
            color=False,  # No ANSI
            progress=False,  # No UI
            tools="all",  # All available tools
            transport="stdio",  # stdin/stdout
        )

    def format_output(self, results, summary):
        """
        MCP mode: JSON-RPC response format.

        Note: The actual JSON-RPC wrapper is handled by the MCP server.
        This formats the content portion of the response.
        """
        import json

        return json.dumps({
            "content": [
                {
                    "type": "text",
                    "text": self._format_mcp_text(results, summary),
                }
            ],
            "isError": summary.get("total_errors", 0) > 0,
        })

    def _format_mcp_text(self, results, summary):
        """Format results as readable text for MCP response."""
        lines = []

        total_errors = summary.get("total_errors", 0)
        total_warnings = summary.get("total_warnings", 0)
        files_checked = summary.get("files_checked", 0)

        if total_errors == 0 and total_warnings == 0:
            lines.append(f"✓ Validation passed ({files_checked} files)")
        else:
            lines.append(f"Validation: {total_errors} errors, {total_warnings} warnings")

            for filepath, file_results in results.items():
                for result in file_results:
                    errors = getattr(result, "errors", [])
                    warnings = getattr(result, "warnings", [])

                    if errors:
                        tool = getattr(result, "tool", "validator")
                        for error in errors:
                            lines.append(f"  {filepath} [{tool}]: {error}")

                    if warnings:
                        tool = getattr(result, "tool", "validator")
                        for warning in warnings:
                            lines.append(f"  {filepath} [{tool}] (warning): {warning}")

        return "\n".join(lines)

    def wrap_jsonrpc_response(self, request_id, result):
        """
        Wrap result in JSON-RPC 2.0 response format.

        Args:
            request_id: The JSON-RPC request ID
            result: The result content

        Returns:
            Complete JSON-RPC response dict
        """
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result,
        }

    def wrap_jsonrpc_error(self, request_id, code, message, data=None):
        """
        Wrap error in JSON-RPC 2.0 error response format.

        Args:
            request_id: The JSON-RPC request ID
            code: Error code (e.g., -32600 for invalid request)
            message: Error message
            data: Optional additional error data

        Returns:
            Complete JSON-RPC error response dict
        """
        error = {
            "code": code,
            "message": message,
        }
        if data:
            error["data"] = data

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": error,
        }
