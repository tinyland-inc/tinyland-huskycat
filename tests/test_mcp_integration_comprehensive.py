#!/usr/bin/env python3
"""
Comprehensive MCP Server Integration Tests
Tests MCP server functionality, protocol compliance, and real-world usage
"""

import json
import os
import subprocess
import sys
import time
from io import StringIO
from pathlib import Path
from typing import Dict, Optional

import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Try to import MCP server components
try:
    from huskycat.mcp_server import MCPServer

    HAS_MCP_SERVER = True
except ImportError:
    HAS_MCP_SERVER = False
    # Define placeholder for type hints
    MCPServer = type("MCPServer", (), {})  # type: ignore

try:

    HAS_VALIDATION = True
except ImportError:
    HAS_VALIDATION = False


class MCPTestClient:
    """Simple MCP test client for integration testing."""

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
        # Capture stdout to get response
        original_stdout = sys.stdout
        captured_output = StringIO()
        sys.stdout = captured_output

        try:
            server.handle_request(request)
            response_text = captured_output.getvalue().strip()

            if not response_text:
                return {"error": {"code": -32603, "message": "No response from server"}}

            return json.loads(response_text)

        except json.JSONDecodeError as e:
            return {"error": {"code": -32700, "message": f"Parse error: {e}"}}

        except Exception as e:
            return {"error": {"code": -32603, "message": f"Internal error: {e}"}}

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
def temp_workspace(isolated_dir: Path) -> Path:
    """Create temporary workspace for validation tests."""
    workspace = isolated_dir / "workspace"
    workspace.mkdir()
    return workspace


@pytest.mark.skipif(not HAS_MCP_SERVER, reason="MCP server not available")
class TestMCPProtocolCompliance:
    """Test MCP protocol compliance and JSON-RPC 2.0 conformance."""

    def test_server_initialization(self, mcp_server: MCPServer):
        """Test that server initializes correctly."""
        assert mcp_server is not None
        # Check that server has required methods
        assert hasattr(mcp_server, "handle_request")

    def test_tools_list_request(self, mcp_server: MCPServer, mcp_client: MCPTestClient):
        """Test tools/list request compliance."""
        request = mcp_client.create_request("tools/list")
        response = mcp_client.send_request(mcp_server, request)

        # Validate JSON-RPC 2.0 response structure
        assert "jsonrpc" in response
        assert response["jsonrpc"] == "2.0"
        assert "id" in response
        assert response["id"] == request["id"]

        # Should have result or error, but not both
        assert ("result" in response) != ("error" in response)

        if "result" in response:
            result = response["result"]
            assert "tools" in result
            assert isinstance(result["tools"], list)

            # Each tool should have required MCP fields
            for tool in result["tools"]:
                assert "name" in tool
                assert "description" in tool
                assert "inputSchema" in tool
                assert isinstance(tool["inputSchema"], dict)

    def test_invalid_method_handling(
        self, mcp_server: MCPServer, mcp_client: MCPTestClient
    ):
        """Test handling of invalid/unknown methods."""
        request = mcp_client.create_request("invalid/method")
        response = mcp_client.send_request(mcp_server, request)

        assert "error" in response
        error = response["error"]
        assert "code" in error
        assert "message" in error
        assert error["code"] == -32601  # Method not found

    def test_invalid_json_handling(self, mcp_server: MCPServer):
        """Test handling of invalid JSON."""
        original_stdout = sys.stdout
        captured_output = StringIO()
        sys.stdout = captured_output

        try:
            # This should not crash the server
            invalid_requests = [
                '{"invalid": json}',
                '{"jsonrpc": "1.0"}',  # Wrong version
                "{}",  # Missing required fields
                "not json at all",
            ]

            for invalid_request in invalid_requests:
                try:
                    parsed = json.loads(invalid_request)
                    mcp_server.handle_request(parsed)
                except json.JSONDecodeError:
                    # Expected for invalid JSON
                    pass

                # Server should not crash
                assert True

        finally:
            sys.stdout = original_stdout

    def test_request_id_echo(self, mcp_server: MCPServer, mcp_client: MCPTestClient):
        """Test that response ID matches request ID."""
        test_ids = [1, "string-id", None, 42.5]

        for test_id in test_ids:
            request = {"jsonrpc": "2.0", "method": "tools/list", "id": test_id}

            response = mcp_client.send_request(mcp_server, request)
            assert response.get("id") == test_id

    def test_error_response_structure(
        self, mcp_server: MCPServer, mcp_client: MCPTestClient
    ):
        """Test error response structure compliance."""
        # Trigger an error with invalid tool call
        request = mcp_client.create_request(
            "tools/call", {"name": "nonexistent_tool", "arguments": {}}
        )

        response = mcp_client.send_request(mcp_server, request)

        if "error" in response:
            error = response["error"]
            assert "code" in error
            assert "message" in error
            assert isinstance(error["code"], int)
            assert isinstance(error["message"], str)


@pytest.mark.skipif(
    not (HAS_MCP_SERVER and HAS_VALIDATION), reason="MCP or validation not available"
)
class TestMCPValidationIntegration:
    """Test MCP server integration with validation tools."""

    def test_validate_tool_python(
        self, mcp_server: MCPServer, mcp_client: MCPTestClient, temp_workspace: Path
    ):
        """Test Python validation through MCP."""
        # Create test Python file
        python_file = temp_workspace / "test.py"
        python_file.write_text(
            """#!/usr/bin/env python3
import os,sys
def bad_function(  x,y  ):
    result=x+y
    return result
"""
        )

        request = mcp_client.create_request(
            "tools/call",
            {"name": "validate", "arguments": {"path": str(python_file), "fix": False}},
        )

        response = mcp_client.send_request(mcp_server, request)

        # Should get a successful response
        if "result" in response:
            result = response["result"]
            # Result should contain validation information
            assert "content" in result or "results" in result or "output" in result
        else:
            # If error, should be informative
            assert "error" in response
            error = response["error"]
            assert "message" in error

    def test_validate_black_tool(
        self, mcp_server: MCPServer, mcp_client: MCPTestClient, temp_workspace: Path
    ):
        """Test Black validation through MCP."""
        python_file = temp_workspace / "format_test.py"
        python_file.write_text(
            """def unformatted(x,y):
    return x+y"""
        )

        request = mcp_client.create_request(
            "tools/call",
            {
                "name": "validate_black",
                "arguments": {"path": str(python_file), "fix": False},
            },
        )

        response = mcp_client.send_request(mcp_server, request)

        # Should handle request even if Black is not installed
        assert "jsonrpc" in response
        assert response["jsonrpc"] == "2.0"

    def test_validate_multiple_files(
        self, mcp_server: MCPServer, mcp_client: MCPTestClient, temp_workspace: Path
    ):
        """Test validating multiple files."""
        # Create multiple test files
        files = []
        for i in range(3):
            test_file = temp_workspace / f"test_{i}.py"
            test_file.write_text(
                f"""
def function_{i}():
    return {i}
"""
            )
            files.append(str(test_file))

        # Test batch validation
        for file_path in files:
            request = mcp_client.create_request(
                "tools/call",
                {"name": "validate", "arguments": {"path": file_path, "fix": False}},
            )

            response = mcp_client.send_request(mcp_server, request)
            # Each request should complete
            assert "jsonrpc" in response

    def test_fix_mode_integration(
        self, mcp_server: MCPServer, mcp_client: MCPTestClient, temp_workspace: Path
    ):
        """Test fix mode through MCP."""
        python_file = temp_workspace / "fix_test.py"
        original_content = """def badly_formatted(x,y):
    return x+y"""
        python_file.write_text(original_content)

        request = mcp_client.create_request(
            "tools/call",
            {
                "name": "validate_black",
                "arguments": {"path": str(python_file), "fix": True},
            },
        )

        response = mcp_client.send_request(mcp_server, request)

        # Should complete without error
        assert "jsonrpc" in response

        # File content might be changed if Black is available
        current_content = python_file.read_text()
        # Either fixed or unchanged (if Black not available)
        assert len(current_content) > 0

    def test_validation_with_syntax_errors(
        self, mcp_server: MCPServer, mcp_client: MCPTestClient, temp_workspace: Path
    ):
        """Test validation of files with syntax errors."""
        broken_file = temp_workspace / "broken.py"
        broken_file.write_text(
            """
def broken_function(:
    return "missing parenthesis"
"""
        )

        request = mcp_client.create_request(
            "tools/call",
            {"name": "validate", "arguments": {"path": str(broken_file), "fix": False}},
        )

        response = mcp_client.send_request(mcp_server, request)

        # Should handle syntax errors gracefully
        assert "jsonrpc" in response

        if "result" in response:
            # Should report the syntax error
            result = response["result"]
            result_str = str(result).lower()
            assert (
                "error" in result_str
                or "syntax" in result_str
                or "invalid" in result_str
            )

    def test_nonexistent_file_handling(
        self, mcp_server: MCPServer, mcp_client: MCPTestClient
    ):
        """Test handling of nonexistent files."""
        request = mcp_client.create_request(
            "tools/call",
            {
                "name": "validate",
                "arguments": {"path": "/nonexistent/path/file.py", "fix": False},
            },
        )

        response = mcp_client.send_request(mcp_server, request)

        # Should handle gracefully with error or empty result
        assert "jsonrpc" in response

        if "error" in response:
            error = response["error"]
            assert (
                "not found" in error["message"].lower()
                or "no such file" in error["message"].lower()
            )


class TestMCPServerRobustness:
    """Test MCP server robustness and error handling."""

    @pytest.mark.skipif(not HAS_MCP_SERVER, reason="MCP server not available")
    def test_concurrent_requests(
        self, mcp_server: MCPServer, mcp_client: MCPTestClient
    ):
        """Test handling concurrent requests."""
        # Create multiple requests
        requests = []
        for i in range(10):
            request = mcp_client.create_request("tools/list")
            requests.append(request)

        # Send requests in sequence (simulating concurrency)
        responses = []
        for request in requests:
            response = mcp_client.send_request(mcp_server, request)
            responses.append(response)

        # All responses should be valid
        assert len(responses) == len(requests)
        for i, response in enumerate(responses):
            assert "jsonrpc" in response
            assert response["id"] == requests[i]["id"]

    @pytest.mark.skipif(not HAS_MCP_SERVER, reason="MCP server not available")
    def test_malformed_requests(self, mcp_server: MCPServer):
        """Test handling of malformed requests."""
        malformed_requests = [
            {"jsonrpc": "2.0"},  # Missing method
            {"jsonrpc": "2.0", "method": ""},  # Empty method
            {"jsonrpc": "1.0", "method": "test"},  # Wrong version
            {"method": "test", "id": 1},  # Missing jsonrpc
            {"jsonrpc": "2.0", "method": 123, "id": 1},  # Invalid method type
        ]

        for bad_request in malformed_requests:
            original_stdout = sys.stdout
            captured_output = StringIO()
            sys.stdout = captured_output

            try:
                mcp_server.handle_request(bad_request)
                response_text = captured_output.getvalue().strip()

                if response_text:
                    try:
                        response = json.loads(response_text)
                        # Should be an error response
                        if "error" in response:
                            assert "code" in response["error"]
                            assert "message" in response["error"]
                    except json.JSONDecodeError:
                        # Server might not respond to invalid requests
                        pass

                # Most importantly, server should not crash
                assert True

            finally:
                sys.stdout = original_stdout

    @pytest.mark.skipif(not HAS_MCP_SERVER, reason="MCP server not available")
    def test_resource_limits(
        self, mcp_server: MCPServer, mcp_client: MCPTestClient, temp_workspace: Path
    ):
        """Test server behavior with resource-intensive requests."""
        # Create a large file
        large_file = temp_workspace / "large.py"
        large_content = []
        for i in range(1000):
            large_content.append(f"def function_{i}():")
            large_content.append(f"    return {i}")
            large_content.append("")

        large_file.write_text("\n".join(large_content))

        request = mcp_client.create_request(
            "tools/call",
            {"name": "validate", "arguments": {"path": str(large_file), "fix": False}},
        )

        # Should handle large files within reasonable time
        start_time = time.time()
        response = mcp_client.send_request(mcp_server, request)
        end_time = time.time()

        duration = end_time - start_time
        assert duration < 30.0, f"Large file validation took too long: {duration:.2f}s"
        assert "jsonrpc" in response


@pytest.mark.skipif(not HAS_MCP_SERVER, reason="MCP server not available")
class TestMCPToolDiscovery:
    """Test MCP tool discovery and metadata."""

    def test_tool_metadata_completeness(
        self, mcp_server: MCPServer, mcp_client: MCPTestClient
    ):
        """Test that all tools have complete metadata."""
        request = mcp_client.create_request("tools/list")
        response = mcp_client.send_request(mcp_server, request)

        if "result" in response and "tools" in response["result"]:
            tools = response["result"]["tools"]

            for tool in tools:
                # Required fields
                assert "name" in tool
                assert "description" in tool
                assert "inputSchema" in tool

                # Validate input schema structure
                schema = tool["inputSchema"]
                assert "type" in schema

                if schema["type"] == "object":
                    # Should have properties for object schemas
                    assert "properties" in schema or "additionalProperties" in schema

                # Tool names should be meaningful
                assert len(tool["name"]) > 0
                assert len(tool["description"]) > 10  # Reasonable description length

    def test_validation_tools_available(
        self, mcp_server: MCPServer, mcp_client: MCPTestClient
    ):
        """Test that expected validation tools are available."""
        request = mcp_client.create_request("tools/list")
        response = mcp_client.send_request(mcp_server, request)

        if "result" in response and "tools" in response["result"]:
            tool_names = [tool["name"] for tool in response["result"]["tools"]]

            # Should have at least some validation tools
            expected_tools = ["validate", "validate_black", "validate_flake8"]

            available_tools = [tool for tool in expected_tools if tool in tool_names]
            assert (
                len(available_tools) > 0
            ), f"No expected validation tools found. Available: {tool_names}"

    def test_tool_input_schemas(self, mcp_server: MCPServer, mcp_client: MCPTestClient):
        """Test that tool input schemas are valid."""
        request = mcp_client.create_request("tools/list")
        response = mcp_client.send_request(mcp_server, request)

        if "result" in response and "tools" in response["result"]:
            for tool in response["result"]["tools"]:
                schema = tool["inputSchema"]

                # Basic schema validation
                if "properties" in schema:
                    properties = schema["properties"]

                    # Common validation tool properties
                    if "path" in properties:
                        path_prop = properties["path"]
                        assert "type" in path_prop
                        assert path_prop["type"] == "string"

                    if "fix" in properties:
                        fix_prop = properties["fix"]
                        assert "type" in fix_prop
                        assert fix_prop["type"] == "boolean"


@pytest.mark.integration
@pytest.mark.skipif(not HAS_MCP_SERVER, reason="MCP server not available")
class TestMCPStdioIntegration:
    """Test MCP server STDIO integration."""

    def test_stdio_server_startup(self):
        """Test that MCP server can start in STDIO mode."""
        # Look for MCP STDIO server script
        mcp_script_paths = [
            Path("src/mcp_server.py"),
            Path("src/mcp-stdio-server.py"),
            Path("mcp_server.py"),
        ]

        mcp_script = None
        for path in mcp_script_paths:
            if path.exists():
                mcp_script = path
                break

        if not mcp_script:
            pytest.skip("MCP STDIO server script not found")

        # Test that script starts without error
        try:
            proc = subprocess.Popen(
                [sys.executable, str(mcp_script)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Send a simple request
            request = (
                json.dumps({"jsonrpc": "2.0", "method": "tools/list", "id": 1}) + "\n"
            )

            stdout, stderr = proc.communicate(input=request, timeout=10)

            # Should get a response
            assert len(stdout) > 0 or len(stderr) > 0

            # If stdout has content, should be valid JSON
            if stdout.strip():
                try:
                    response = json.loads(stdout.strip())
                    assert "jsonrpc" in response
                except json.JSONDecodeError:
                    # Might have multiple responses or other output
                    pass

        except (subprocess.TimeoutExpired, FileNotFoundError):
            pytest.skip("Could not test STDIO server")

        finally:
            if proc.poll() is None:
                proc.terminate()
                proc.wait()

    def test_stdio_protocol_compliance(self):
        """Test STDIO protocol compliance."""
        # This would require a more complex test setup
        # For now, just verify the server script exists and is executable
        mcp_scripts = [Path("src/mcp_server.py"), Path("mcp_server.py")]

        found_script = False
        for script in mcp_scripts:
            if script.exists():
                found_script = True
                # Check if executable
                assert (
                    script.stat().st_mode & 0o111
                ), f"MCP server script {script} is not executable"

        if not found_script:
            pytest.skip("No MCP server script found")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
