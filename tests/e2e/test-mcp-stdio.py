#!/usr/bin/env python3
"""
E2E Test for MCP Stdio Server
Tests the complete MCP protocol implementation
"""

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, Any, Optional
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

class MCPTestClient:
    """Test client for MCP stdio server"""
    
    def __init__(self, server_path: str = "src/mcp-stdio-server.py"):
        self.server_path = server_path
        self.process = None
        self.request_id = 0
        
    def start(self):
        """Start the MCP server process"""
        self.process = subprocess.Popen(
            ["python3", self.server_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=0
        )
        time.sleep(0.5)  # Give server time to start
        
    def stop(self):
        """Stop the MCP server process"""
        if self.process:
            self.process.terminate()
            self.process.wait(timeout=5)
            
    def send_request(self, method: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Send a JSON-RPC request and get response"""
        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": self.request_id
        }
        
        # Send request
        request_line = json.dumps(request) + "\n"
        self.process.stdin.write(request_line)
        self.process.stdin.flush()
        
        # Read response
        response_line = self.process.stdout.readline()
        if not response_line:
            raise Exception("No response from server")
            
        return json.loads(response_line)


def test_initialize():
    """Test MCP initialization"""
    print("Testing MCP initialization...")
    
    client = MCPTestClient()
    client.start()
    
    try:
        # Send initialize request
        response = client.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0.0"}
        })
        
        # Check response
        assert "result" in response
        assert response["result"]["protocolVersion"] == "2024-11-05"
        assert "capabilities" in response["result"]
        assert "serverInfo" in response["result"]
        assert response["result"]["serverInfo"]["name"] == "huskycat-mcp"
        
        print("✓ Initialization successful")
        
    finally:
        client.stop()


def test_tools_list():
    """Test listing available tools"""
    print("Testing tools list...")
    
    client = MCPTestClient()
    client.start()
    
    try:
        # Initialize first
        client.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {}
        })
        
        # List tools
        response = client.send_request("tools/list")
        
        assert "result" in response
        assert "tools" in response["result"]
        tools = response["result"]["tools"]
        
        # Check we have expected tools
        tool_names = [t["name"] for t in tools]
        assert "python-black" in tool_names
        assert "python-flake8" in tool_names
        assert "js-eslint" in tool_names
        assert "yaml-yamllint" in tool_names
        assert "validate_project" in tool_names
        
        print(f"✓ Found {len(tools)} tools")
        
    finally:
        client.stop()


def test_validate_python_file():
    """Test validating a Python file"""
    print("Testing Python file validation...")
    
    client = MCPTestClient()
    client.start()
    
    try:
        # Initialize
        client.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {}
        })
        
        # Create test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("x=1+2\ny=3+4\n")  # Badly formatted
            test_file = f.name
        
        # Validate file
        response = client.send_request("tools/call", {
            "name": "python-black",
            "arguments": {
                "filepath": test_file,
                "fix": False
            }
        })
        
        assert "result" in response
        result_text = response["result"]["content"][0]["text"]
        result_data = json.loads(result_text)
        
        # Black should report formatting issues
        assert "success" in result_data
        
        print("✓ Python validation working")
        
        # Cleanup
        Path(test_file).unlink()
        
    finally:
        client.stop()


def test_batch_validation():
    """Test batch validation of multiple files"""
    print("Testing batch validation...")
    
    client = MCPTestClient()
    client.start()
    
    try:
        # Initialize
        client.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {}
        })
        
        # Create test files
        test_files = []
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("print('hello')\n")
            test_files.append(f.name)
            
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write("console.log('hello');\n")
            test_files.append(f.name)
        
        # Batch validate
        response = client.send_request("tools/call", {
            "name": "batch_validate",
            "arguments": {
                "files": test_files,
                "fix": False
            }
        })
        
        assert "result" in response
        result_text = response["result"]["content"][0]["text"]
        result_data = json.loads(result_text)
        
        assert "results" in result_data
        assert len(result_data["results"]) >= 1
        
        print("✓ Batch validation working")
        
        # Cleanup
        for file in test_files:
            Path(file).unlink()
        
    finally:
        client.stop()


def test_project_validation():
    """Test full project validation"""
    print("Testing project validation...")
    
    client = MCPTestClient()
    client.start()
    
    try:
        # Initialize
        client.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {}
        })
        
        # Create test directory
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create some test files
            Path(tmpdir, "test.py").write_text("print('hello')\n")
            Path(tmpdir, "test.js").write_text("console.log('hello');\n")
            Path(tmpdir, "test.yaml").write_text("key: value\n")
            
            # Validate project
            response = client.send_request("tools/call", {
                "name": "validate_project",
                "arguments": {
                    "path": tmpdir
                }
            })
            
            assert "result" in response
            result_text = response["result"]["content"][0]["text"]
            result_data = json.loads(result_text)
            
            assert result_data["success"] == True
            assert "results" in result_data
            
            print("✓ Project validation working")
        
    finally:
        client.stop()


def test_resources_list():
    """Test listing resources"""
    print("Testing resources list...")
    
    client = MCPTestClient()
    client.start()
    
    try:
        # Initialize
        client.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {}
        })
        
        # List resources
        response = client.send_request("resources/list")
        
        assert "result" in response
        assert "resources" in response["result"]
        
        print(f"✓ Found {len(response['result']['resources'])} resources")
        
    finally:
        client.stop()


def test_prompts_list():
    """Test listing prompts"""
    print("Testing prompts list...")
    
    client = MCPTestClient()
    client.start()
    
    try:
        # Initialize
        client.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {}
        })
        
        # List prompts
        response = client.send_request("prompts/list")
        
        assert "result" in response
        assert "prompts" in response["result"]
        
        print(f"✓ Found {len(response['result']['prompts'])} prompts")
        
    finally:
        client.stop()


def test_error_handling():
    """Test error handling"""
    print("Testing error handling...")
    
    client = MCPTestClient()
    client.start()
    
    try:
        # Send invalid method
        response = client.send_request("invalid/method")
        
        assert "error" in response
        assert response["error"]["code"] == -32601
        assert "not found" in response["error"]["message"].lower()
        
        print("✓ Error handling working")
        
    finally:
        client.stop()


def main():
    """Run all E2E tests"""
    print("=" * 50)
    print("HuskyCat MCP Stdio Server E2E Tests")
    print("=" * 50)
    
    # Create logs directory
    Path("logs").mkdir(exist_ok=True)
    
    # Log file
    log_file = f"logs/e2e-mcp-stdio-{time.strftime('%Y%m%d-%H%M%S')}.log"
    
    tests = [
        test_initialize,
        test_tools_list,
        test_validate_python_file,
        test_batch_validation,
        test_project_validation,
        test_resources_list,
        test_prompts_list,
        test_error_handling
    ]
    
    failed = []
    
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed.append(test.__name__)
            
            # Log error
            with open(log_file, 'a') as f:
                f.write(f"{test.__name__} failed: {e}\n")
    
    print("=" * 50)
    
    if failed:
        print(f"✗ {len(failed)} tests failed: {', '.join(failed)}")
        sys.exit(1)
    else:
        print("✓ All tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()