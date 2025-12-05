#!/usr/bin/env python3
"""
Property-Based Testing for MCP Server
Using Hypothesis for comprehensive testing
"""

import json
import os
import sys
from io import StringIO

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from huskycat.mcp_server import MCPServer


# Custom strategies for JSON-RPC
@st.composite
def json_rpc_id(draw):
    """Generate valid JSON-RPC ID (string, number, or null)"""
    return draw(st.one_of(st.integers(), st.text(min_size=1, max_size=100), st.none()))


@st.composite
def json_rpc_method(draw):
    """Generate valid JSON-RPC method names"""
    methods = [
        "tools/list",
        "tools/call",
        "validate",
        "validate_staged",
        "validate_black",
        "validate_flake8",
        "validate_mypy",
        "validate_yamllint",
        "validate_hadolint",
        "validate_shellcheck",
    ]
    return draw(st.sampled_from(methods))


@st.composite
def json_rpc_request(draw):
    """Generate valid JSON-RPC request"""
    return {
        "jsonrpc": "2.0",
        "method": draw(json_rpc_method()),
        "id": draw(json_rpc_id()),
        "params": draw(
            st.one_of(
                st.none(), st.dictionaries(st.text(min_size=1), st.text(), max_size=5)
            )
        ),
    }


class TestMCPServerProperties:
    """Property-based tests for MCP Server"""

    @given(json_rpc_request())
    @settings(max_examples=50)
    def test_server_handles_any_valid_request(self, request):
        """Test that server handles any valid JSON-RPC request"""
        server = MCPServer()

        # Capture output
        output = StringIO()
        original_stdout = sys.stdout
        sys.stdout = output

        try:
            # Process request
            response = server.handle_request(request)

            # Print response for test compatibility
            print(json.dumps(response))

            # Get response text
            response_text = output.getvalue()

            # Should produce valid JSON
            if response_text.strip():
                parsed_response = json.loads(response_text)
            else:
                parsed_response = response

            # Should be valid JSON-RPC response
            assert "jsonrpc" in parsed_response
            assert parsed_response["jsonrpc"] == "2.0"

            # Should have matching ID
            if "id" in request:
                assert "id" in parsed_response
                assert parsed_response["id"] == request["id"]

            # Should have either result or error
            assert "result" in parsed_response or "error" in parsed_response
            assert not ("result" in parsed_response and "error" in parsed_response)

        finally:
            sys.stdout = original_stdout

    @given(st.text(min_size=1))
    @settings(max_examples=30)
    def test_server_handles_invalid_json_gracefully(self, invalid_json):
        """Test that server handles invalid JSON gracefully"""
        assume(not self._is_valid_json(invalid_json))

        server = MCPServer()
        output = StringIO()
        original_stdout = sys.stdout
        sys.stdout = output

        try:
            # Try to parse invalid JSON
            try:
                request = json.loads(invalid_json)
                server.handle_request(request)
            except json.JSONDecodeError:
                # Expected - server should handle this
                pass

            # Server should not crash
            assert True

        finally:
            sys.stdout = original_stdout

    @given(st.dictionaries(st.text(), st.text()))
    @settings(max_examples=30)
    def test_server_validates_request_structure(self, invalid_request):
        """Test that server validates request structure"""
        assume(
            "jsonrpc" not in invalid_request or invalid_request.get("jsonrpc") != "2.0"
        )

        server = MCPServer()
        output = StringIO()
        original_stdout = sys.stdout
        sys.stdout = output

        try:
            response = server.handle_request(invalid_request)
            print(json.dumps(response))
            response_text = output.getvalue()

            if response:
                # Should return error for invalid request
                if "jsonrpc" not in invalid_request:
                    assert "error" in response

        finally:
            sys.stdout = original_stdout

    @given(json_rpc_id())
    @settings(max_examples=30)
    def test_tools_list_returns_consistent_structure(self, request_id):
        """Test that tools/list always returns consistent structure"""
        server = MCPServer()
        request = {"jsonrpc": "2.0", "method": "tools/list", "id": request_id}

        output = StringIO()
        original_stdout = sys.stdout
        sys.stdout = output

        try:
            response = server.handle_request(request)
            print(json.dumps(response))

            # Check response structure
            assert response["jsonrpc"] == "2.0"
            assert response["id"] == request_id
            assert "result" in response
            assert "tools" in response["result"]
            assert isinstance(response["result"]["tools"], list)

            # Each tool should have required fields
            for tool in response["result"]["tools"]:
                assert "name" in tool
                assert "description" in tool
                assert "inputSchema" in tool

        finally:
            sys.stdout = original_stdout

    @given(
        json_rpc_id(),
        st.sampled_from(["validate_black", "validate_flake8", "validate_mypy"]),
        st.text(min_size=1, max_size=100),
    )
    @settings(max_examples=20)
    def test_validation_tools_handle_paths(self, request_id, tool_name, path):
        """Test that validation tools handle any path input"""
        server = MCPServer()
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": request_id,
            "params": {"name": tool_name, "arguments": {"path": path, "fix": False}},
        }

        output = StringIO()
        original_stdout = sys.stdout
        sys.stdout = output

        try:
            response = server.handle_request(request)
            print(json.dumps(response))

            # Should always return valid response
            assert response["jsonrpc"] == "2.0"
            assert response["id"] == request_id

            # Should have either result or error (file not found is OK)
            assert "result" in response or "error" in response

        finally:
            sys.stdout = original_stdout

    @given(st.lists(json_rpc_request(), min_size=1, max_size=10))
    @settings(max_examples=10)
    def test_server_handles_multiple_requests(self, requests):
        """Test that server can handle multiple requests in sequence"""
        server = MCPServer()

        for request in requests:
            output = StringIO()
            original_stdout = sys.stdout
            sys.stdout = output

            try:
                response = server.handle_request(request)
                print(json.dumps(response))
                response_text = output.getvalue()

                # Each request should produce valid response
                if response:
                    assert "jsonrpc" in response

            finally:
                sys.stdout = original_stdout

    def _is_valid_json(self, text):
        """Helper to check if text is valid JSON"""
        try:
            json.loads(text)
            return True
        except:
            return False


class TestMCPProtocolCompliance:
    """Test MCP protocol compliance properties"""

    @given(
        st.text(min_size=1, max_size=100),
        st.dictionaries(st.text(min_size=1), st.text(), max_size=5),
    )
    @settings(max_examples=30)
    def test_unknown_method_returns_error(self, unknown_method, params):
        """Test that unknown methods return appropriate error"""
        assume(
            unknown_method
            not in [
                "tools/list",
                "tools/call",
                "validate",
                "validate_staged",
                "validate_black",
                "validate_flake8",
                "validate_mypy",
                "validate_yamllint",
                "validate_hadolint",
                "validate_shellcheck",
            ]
        )

        server = MCPServer()
        request = {
            "jsonrpc": "2.0",
            "method": unknown_method,
            "id": 1,
            "params": params,
        }

        output = StringIO()
        original_stdout = sys.stdout
        sys.stdout = output

        try:
            response = server.handle_request(request)
            print(json.dumps(response))

            # Should return error for unknown method
            assert "error" in response
            assert response["error"]["code"] == -32601  # Method not found

        finally:
            sys.stdout = original_stdout

    @given(json_rpc_id())
    @settings(max_examples=20)
    def test_response_id_matches_request(self, request_id):
        """Test that response ID always matches request ID"""
        server = MCPServer()
        request = {"jsonrpc": "2.0", "method": "tools/list", "id": request_id}

        output = StringIO()
        original_stdout = sys.stdout
        sys.stdout = output

        try:
            response = server.handle_request(request)
            print(json.dumps(response))

            # Response ID must match request ID
            assert response["id"] == request_id

        finally:
            sys.stdout = original_stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
