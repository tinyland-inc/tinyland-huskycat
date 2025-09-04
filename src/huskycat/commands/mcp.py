"""
MCP Server command for AI integration.
"""

import sys
import json
from pathlib import Path

from ..core.base import BaseCommand, CommandResult, CommandStatus


class MCPServerCommand(BaseCommand):
    """Command to start MCP server for AI integration."""
    
    @property
    def name(self) -> str:
        return "mcp-server"
    
    @property
    def description(self) -> str:
        return "Start MCP server for AI integration"
    
    def execute(self, port: int = 5000) -> CommandResult:
        """
        Start the MCP server.
        
        Args:
            port: Port to run server on
            
        Returns:
            CommandResult with server status
        """
        try:
            # Import the MCP server
            from ..mcp_server import MCPServer
            
            self.log(f"Starting MCP server on port {port}...")
            
            # Create and run the server
            server = MCPServer()
            
            # For stdio mode (which is what Claude uses)
            if port == 0:  # stdio mode
                self.log("Running in stdio mode for Claude integration")
                server.run_stdio()
            else:
                # This would be for HTTP mode if we implement it
                return CommandResult(
                    status=CommandStatus.WARNING,
                    message="HTTP mode not yet implemented, use stdio mode (port=0)",
                    warnings=["Only stdio mode is currently supported for MCP"]
                )
            
            return CommandResult(
                status=CommandStatus.SUCCESS,
                message="MCP server stopped"
            )
            
        except ImportError as e:
            return CommandResult(
                status=CommandStatus.FAILED,
                message="Failed to import MCP server",
                errors=[str(e), "Make sure mcp package is installed"]
            )
        except Exception as e:
            return CommandResult(
                status=CommandStatus.FAILED,
                message=f"MCP server error: {str(e)}",
                errors=[str(e)]
            )