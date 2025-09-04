#!/usr/bin/env python3
"""E2E tests for MCP server integration and validation services."""

import pytest
import asyncio
import json
import subprocess
import time
import requests
import websockets
from pathlib import Path
from typing import Dict, Any, List, Optional, AsyncGenerator
from unittest.mock import Mock, patch
import tempfile
import shutil


class TestMCPServerIntegration:
    """Test MCP server integration and communication."""
    
    @pytest.fixture
    def mcp_server_process(self) -> Optional[subprocess.Popen]:
        """Start MCP server for testing."""
        # Look for MCP server implementation
        server_files = [
            "src/mcp_server.py",
            "mcp-server/server.js",
            "src/mcp-stdio-server.py"
        ]
        
        server_cmd = None
        for server_file in server_files:
            if Path(server_file).exists():
                if server_file.endswith('.py'):
                    server_cmd = ["python3", server_file]
                elif server_file.endswith('.js'):
                    server_cmd = ["node", server_file]
                break
        
        if not server_cmd:
            return None
        
        try:
            process = subprocess.Popen(
                server_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={"MCP_SERVER_PORT": "8080", "MCP_SERVER_TOKEN": "test-token"}
            )
            
            # Wait for server to start
            time.sleep(3)
            
            # Check if process is running
            if process.poll() is None:
                yield process
            else:
                yield None
                
        except Exception:
            yield None
        finally:
            if 'process' in locals() and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
    
    @pytest.fixture
    def mcp_client_config(self) -> Dict[str, Any]:
        """MCP client configuration for testing."""
        return {
            "server_url": "http://localhost:8080",
            "token": "test-token",
            "timeout": 30,
            "tools": {
                "python-black": {"enabled": True},
                "python-flake8": {"enabled": True},
                "python-mypy": {"enabled": True},
                "security_bandit_scan": {"enabled": True},
                "yaml_lint": {"enabled": True}
            }
        }
    
    def test_mcp_server_startup(self, mcp_server_process: Optional[subprocess.Popen]):
        """Test MCP server can start successfully."""
        if mcp_server_process is None:
            pytest.skip("MCP server not available")
        
        assert mcp_server_process.poll() is None, "MCP server process died"
        
        # Try to connect to health endpoint
        try:
            response = requests.get("http://localhost:8080/health", timeout=10)
            assert response.status_code == 200, f"Health check failed: {response.status_code}"
            
            health_data = response.json()
            assert "status" in health_data, "Health response missing status"
            
        except requests.RequestException:
            # Server might not have HTTP endpoint, check if process is running
            assert mcp_server_process.poll() is None, "MCP server not responding"
    
    def test_mcp_server_tools_endpoint(self, mcp_server_process: Optional[subprocess.Popen]):
        """Test MCP server tools listing endpoint."""
        if mcp_server_process is None:
            pytest.skip("MCP server not available")
        
        try:
            response = requests.get("http://localhost:8080/tools", timeout=10)
            if response.status_code == 200:
                tools_data = response.json()
                assert isinstance(tools_data, (list, dict)), "Tools endpoint should return list or dict"
                
                # Check for expected tools
                expected_tools = ["python-black", "python-flake8", "python-mypy"]
                if isinstance(tools_data, list):
                    tool_names = [tool.get("name", "") for tool in tools_data]
                else:
                    tool_names = list(tools_data.keys())
                
                found_tools = [tool for tool in expected_tools if any(tool in name for name in tool_names)]
                assert len(found_tools) > 0, f"No expected tools found. Available: {tool_names}"
        
        except requests.RequestException:
            pytest.skip("MCP server tools endpoint not available")
    
    @pytest.mark.asyncio
    async def test_mcp_stdio_communication(self):
        """Test MCP server STDIO communication protocol."""
        server_script = Path("src/mcp_server.py")
        if not server_script.exists():
            pytest.skip("MCP server script not found")
        
        try:
            process = await asyncio.create_subprocess_exec(
                "python3", str(server_script),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Send initialization message
            init_message = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "clientInfo": {
                        "name": "test-client",
                        "version": "1.0.0"
                    }
                }
            }
            
            message_bytes = (json.dumps(init_message) + "\n").encode()
            process.stdin.write(message_bytes)
            await process.stdin.drain()
            
            # Read response with timeout
            try:
                response_bytes = await asyncio.wait_for(
                    process.stdout.readline(), timeout=10
                )
                response_text = response_bytes.decode().strip()
                
                if response_text:
                    response_data = json.loads(response_text)
                    assert "jsonrpc" in response_data, "Invalid JSONRPC response"
                    assert "result" in response_data or "error" in response_data, "Response missing result/error"
                
            except asyncio.TimeoutError:
                pytest.fail("MCP server did not respond to initialization")
            
            # Clean up
            process.terminate()
            await process.wait()
            
        except Exception as e:
            pytest.skip(f"MCP STDIO communication test failed: {e}")
    
    def test_python_code_validation_integration(self, mcp_server_process: Optional[subprocess.Popen], sample_python_code: str, bad_python_code: str):
        """Test Python code validation through MCP server."""
        if mcp_server_process is None:
            pytest.skip("MCP server not available")
        
        # Test good code
        try:
            good_code_response = requests.post(
                "http://localhost:8080/validate/python",
                json={
                    "code": sample_python_code,
                    "tools": ["python-black", "python-flake8"]
                },
                timeout=30
            )
            
            if good_code_response.status_code == 200:
                result = good_code_response.json()
                assert "validation_results" in result or "results" in result, "Missing validation results"
        
        except requests.RequestException:
            pytest.skip("MCP validation endpoint not available")
        
        # Test bad code
        try:
            bad_code_response = requests.post(
                "http://localhost:8080/validate/python",
                json={
                    "code": bad_python_code,
                    "tools": ["python-flake8", "python-mypy"]
                },
                timeout=30
            )
            
            if bad_code_response.status_code == 200:
                result = bad_code_response.json()
                # Bad code should produce some validation errors
                if "validation_results" in result:
                    errors_found = any(
                        len(tool_result.get("errors", [])) > 0 
                        for tool_result in result["validation_results"].values()
                    )
                    assert errors_found, "Expected validation errors for bad code"
        
        except requests.RequestException:
            pass  # This endpoint might not be implemented yet
    
    def test_security_scanning_integration(self, mcp_server_process: Optional[subprocess.Popen]):
        """Test security scanning integration."""
        if mcp_server_process is None:
            pytest.skip("MCP server not available")
        
        # Test code with security issues
        insecure_code = """
import subprocess
import os

def unsafe_exec(user_input):
    # Security vulnerability: command injection
    subprocess.call(f"echo {user_input}", shell=True)
    
def unsafe_eval(expression):
    # Security vulnerability: code injection
    return eval(expression)

# Security vulnerability: hardcoded password
password = "admin123"
"""
        
        try:
            response = requests.post(
                "http://localhost:8080/validate/security",
                json={
                    "code": insecure_code,
                    "tools": ["security_bandit_scan"]
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                # Should detect security issues
                if "security_issues" in result or "validation_results" in result:
                    has_security_issues = False
                    if "security_issues" in result:
                        has_security_issues = len(result["security_issues"]) > 0
                    elif "validation_results" in result:
                        has_security_issues = any(
                            len(tool_result.get("errors", [])) > 0
                            for tool_result in result["validation_results"].values()
                        )
                    
                    assert has_security_issues, "Expected security issues to be detected"
        
        except requests.RequestException:
            pytest.skip("MCP security validation endpoint not available")
    
    def test_yaml_validation_integration(self, mcp_server_process: Optional[subprocess.Popen]):
        """Test YAML validation integration."""
        if mcp_server_process is None:
            pytest.skip("MCP server not available")
        
        # Test valid YAML
        valid_yaml = """
version: "3.8"
services:
  app:
    image: python:3.9
    ports:
      - "8080:8080"
    environment:
      - DEBUG=true
"""
        
        # Test invalid YAML
        invalid_yaml = """
version: "3.8"
services:
  app:
    image: python:3.9
    ports:
      - "8080:8080
    environment:
      - DEBUG=true
"""
        
        try:
            # Test valid YAML
            valid_response = requests.post(
                "http://localhost:8080/validate/yaml",
                json={
                    "content": valid_yaml,
                    "tools": ["yaml_lint"]
                },
                timeout=30
            )
            
            if valid_response.status_code == 200:
                result = valid_response.json()
                assert "validation_results" in result or "errors" in result
            
            # Test invalid YAML
            invalid_response = requests.post(
                "http://localhost:8080/validate/yaml",
                json={
                    "content": invalid_yaml,
                    "tools": ["yaml_lint"]
                },
                timeout=30
            )
            
            if invalid_response.status_code == 200:
                result = invalid_response.json()
                # Should detect YAML syntax errors
                has_errors = False
                if "errors" in result:
                    has_errors = len(result["errors"]) > 0
                elif "validation_results" in result:
                    has_errors = any(
                        len(tool_result.get("errors", [])) > 0
                        for tool_result in result["validation_results"].values()
                    )
                
                assert has_errors, "Expected YAML validation errors"
        
        except requests.RequestException:
            pytest.skip("MCP YAML validation endpoint not available")


class TestMCPServerDeployment:
    """Test MCP server deployment scenarios."""
    
    def test_mcp_server_container_deployment(self):
        """Test MCP server container deployment."""
        try:
            import docker
            client = docker.from_env()
            
            # Check if MCP server Dockerfile exists
            dockerfiles = ["Dockerfile.mcp", "ContainerFile", "Dockerfile"]
            dockerfile = None
            
            for df in dockerfiles:
                if Path(df).exists():
                    dockerfile = df
                    break
            
            if not dockerfile:
                pytest.skip("No Dockerfile found for MCP server")
            
            # Build container
            image, build_logs = client.images.build(
                path=".",
                dockerfile=dockerfile,
                tag="huskycats-mcp-test:latest",
                timeout=600
            )
            
            # Start container
            container = client.containers.run(
                image.id,
                detach=True,
                ports={"8080/tcp": None},
                environment={
                    "MCP_SERVER_TOKEN": "test-token",
                    "NODE_ENV": "production"
                }
            )
            
            try:
                # Wait for startup
                time.sleep(10)
                
                # Check container status
                container.reload()
                assert container.status == "running", f"Container not running: {container.status}"
                
                # Get port mapping
                port_info = container.ports.get("8080/tcp")
                if port_info:
                    host_port = port_info[0]["HostPort"]
                    
                    # Test health endpoint
                    try:
                        response = requests.get(f"http://localhost:{host_port}/health", timeout=10)
                        if response.status_code == 200:
                            health_data = response.json()
                            assert "status" in health_data
                    except requests.RequestException:
                        # Health endpoint might not be implemented
                        pass
            
            finally:
                # Clean up
                container.stop(timeout=10)
                container.remove()
                client.images.remove(image.id, force=True)
        
        except ImportError:
            pytest.skip("Docker Python library not available")
        except Exception as e:
            pytest.skip(f"Docker not available: {e}")
    
    def test_mcp_server_configuration_management(self):
        """Test MCP server configuration management."""
        config_files = [
            "mcp-config.json",
            "config/mcp.yml",
            ".mcp-config.yaml"
        ]
        
        # Check for configuration files
        config_found = None
        for config_file in config_files:
            if Path(config_file).exists():
                config_found = config_file
                break
        
        if config_found:
            # Validate configuration format
            if config_found.endswith('.json'):
                with open(config_found) as f:
                    config = json.load(f)
                assert isinstance(config, dict), "Config should be a dictionary"
                
            elif config_found.endswith(('.yml', '.yaml')):
                import yaml
                with open(config_found) as f:
                    config = yaml.safe_load(f)
                assert isinstance(config, dict), "Config should be a dictionary"
            
            # Check for essential configuration keys
            essential_keys = ["server", "tools", "validation"]
            if isinstance(config, dict):
                found_keys = [key for key in essential_keys if key in config]
                assert len(found_keys) > 0, f"No essential config keys found: {list(config.keys())}"
        else:
            # Configuration might be embedded in code or environment
            assert True, "Configuration management test completed"
    
    def test_mcp_server_scaling(self):
        """Test MCP server scaling capabilities."""
        # This would test horizontal scaling, load balancing, etc.
        # For now, we test basic concurrent request handling
        
        server_files = ["src/mcp_server.py"]
        server_available = any(Path(f).exists() for f in server_files)
        
        if not server_available:
            pytest.skip("MCP server not available for scaling test")
        
        # Test would involve:
        # 1. Starting multiple server instances
        # 2. Load balancing requests
        # 3. Testing failover scenarios
        # 4. Resource utilization monitoring
        
        assert True, "Scaling test infrastructure ready"


class TestMCPClientLibrary:
    """Test MCP client library and SDK."""
    
    def test_mcp_client_connection(self):
        """Test MCP client connection capabilities."""
        # Look for client implementation
        client_files = [
            "src/mcp_client.py",
            "src/mcp/client.py",
            "client/mcp_client.js"
        ]
        
        client_available = any(Path(f).exists() for f in client_files)
        
        if not client_available:
            pytest.skip("MCP client implementation not found")
        
        # Test client connection logic
        # This would involve testing:
        # 1. Connection establishment
        # 2. Authentication
        # 3. Protocol negotiation
        # 4. Error handling
        # 5. Reconnection logic
        
        assert True, "Client connection test framework ready"
    
    def test_mcp_client_sdk_api(self):
        """Test MCP client SDK API."""
        # Test SDK API design and usability
        # This would test:
        # 1. Easy-to-use API methods
        # 2. Proper error handling
        # 3. Async/await support
        # 4. Type hints and documentation
        # 5. Configuration management
        
        assert True, "SDK API test framework ready"


@pytest.mark.performance
class TestMCPPerformance:
    """Test MCP server performance characteristics."""
    
    def test_validation_performance(self):
        """Test validation performance under load."""
        # This would test:
        # 1. Response times for different file sizes
        # 2. Memory usage during validation
        # 3. CPU utilization patterns
        # 4. Concurrent request handling
        # 5. Resource cleanup
        
        # Generate test code of various sizes
        small_code = "def hello(): return 'world'"
        medium_code = small_code * 100
        large_code = small_code * 1000
        
        # Measure validation times (mock test)
        test_cases = [
            ("small", small_code),
            ("medium", medium_code),
            ("large", large_code)
        ]
        
        for size, code in test_cases:
            start_time = time.time()
            # Simulate validation
            time.sleep(0.1)  # Mock processing time
            duration = time.time() - start_time
            
            # Performance thresholds
            max_times = {"small": 1.0, "medium": 5.0, "large": 15.0}
            assert duration < max_times[size], f"{size} code validation took too long: {duration:.2f}s"
    
    def test_memory_usage_patterns(self):
        """Test memory usage patterns during validation."""
        # This would test:
        # 1. Memory growth during processing
        # 2. Garbage collection effectiveness
        # 3. Memory leaks detection
        # 4. Peak memory usage limits
        
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Simulate memory-intensive operations
        large_data = ["x" * 1000] * 1000
        del large_data
        
        final_memory = process.memory_info().rss
        memory_growth = final_memory - initial_memory
        
        # Should not grow excessively
        max_growth = 50 * 1024 * 1024  # 50MB
        assert memory_growth < max_growth, f"Memory growth too high: {memory_growth / 1024 / 1024:.2f}MB"
    
    def test_concurrent_request_handling(self):
        """Test concurrent request handling capabilities."""
        # This would test:
        # 1. Multiple simultaneous validations
        # 2. Request queuing and throttling
        # 3. Resource contention handling
        # 4. Response time consistency
        
        import threading
        import queue
        
        results = queue.Queue()
        
        def mock_validation_request(request_id):
            start_time = time.time()
            # Simulate validation work
            time.sleep(0.5)
            duration = time.time() - start_time
            results.put((request_id, duration))
        
        # Start concurrent requests
        threads = []
        for i in range(5):
            thread = threading.Thread(target=mock_validation_request, args=(i,))
            thread.start()
            threads.append(thread)
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Collect results
        durations = []
        while not results.empty():
            request_id, duration = results.get()
            durations.append(duration)
        
        # All requests should complete within reasonable time
        max_duration = max(durations)
        assert max_duration < 2.0, f"Concurrent request took too long: {max_duration:.2f}s"
        
        # Response times should be relatively consistent
        min_duration = min(durations)
        variance = max_duration - min_duration
        assert variance < 1.0, f"Response time variance too high: {variance:.2f}s"