"""
MCP Server command for AI integration.
"""

from ..core.base import BaseCommand, CommandResult, CommandStatus


class MCPServerCommand(BaseCommand):
    """Command to start MCP server for AI integration."""

    @property
    def name(self) -> str:
        return "mcp-server"

    @property
    def description(self) -> str:
        return "Start MCP server for AI integration"

    def execute(self) -> CommandResult:
        """
        Start the MCP server in stdio mode for Claude Code integration.

        Returns:
            CommandResult with server status
        """
        try:
            # Import the MCP server
            from ..mcp_server import MCPServer

            # Create server with container support enabled
            server = MCPServer(use_container=True)

            # Always use stdio mode (only supported mode)
            self.log("Starting MCP server in stdio mode for Claude Code integration")
            server.run()

            return CommandResult(
                status=CommandStatus.SUCCESS, message="MCP server stopped"
            )

        except ImportError as e:
            return CommandResult(
                status=CommandStatus.FAILED,
                message="Failed to import MCP server",
                errors=[str(e), "Make sure mcp package is installed"],
            )
        except Exception as e:
            return CommandResult(
                status=CommandStatus.FAILED,
                message=f"MCP server error: {str(e)}",
                errors=[str(e)],
            )
