#!/usr/bin/env python3
"""E2E test fixtures for temporary environments and mock services."""

import pytest
import asyncio
import subprocess
import tempfile
import shutil
import json
import time
import socket
import threading
import signal
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Generator, AsyncGenerator
from contextlib import contextmanager, asynccontextmanager
from unittest.mock import Mock, patch
import requests
from http.server import HTTPServer, SimpleHTTPRequestHandler


class MockGitLabPagesServer:
    """Mock GitLab Pages server for testing."""
    
    def __init__(self, port: int = 8000):
        self.port = port
        self.server = None
        self.thread = None
        self.running = False
    
    def start(self):
        """Start the mock server."""
        handler = self._create_handler()
        self.server = HTTPServer(('localhost', self.port), handler)
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.daemon = True
        self.thread.start()
        self.running = True
        time.sleep(0.5)  # Give server time to start
    
    def stop(self):
        """Stop the mock server."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        if self.thread:
            self.thread.join(timeout=5)
        self.running = False
    
    def _create_handler(self):
        """Create request handler class."""
        class MockPagesHandler(SimpleHTTPRequestHandler):
            def do_GET(self):
                if self.path == '/':
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(b'''
                    <!DOCTYPE html>
                    <html>
                    <head><title>HuskyCat Documentation</title></head>
                    <body>
                        <h1>HuskyCat - Universal Code Validation Platform</h1>
                        <nav>
                            <a href="/installation">Installation</a>
                            <a href="/usage">Usage</a>
                            <a href="/api">API Reference</a>
                        </nav>
                        <div class="main-content">
                            <p>Welcome to HuskyCat documentation</p>
                            <a href="/downloads/huskycat-linux-amd64" class="download-link">Download Linux</a>
                            <a href="/downloads/huskycat-darwin-amd64" class="download-link">Download macOS</a>
                        </div>
                        <input type="search" placeholder="Search docs" class="search-input">
                        <pre><code>pip install huskycat</code></pre>
                    </body>
                    </html>
                    ''')
                elif self.path == '/installation':
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(b'''
                    <html>
                    <head><title>Installation - HuskyCat</title></head>
                    <body>
                        <h1>Installation</h1>
                        <h2>Quick Start</h2>
                        <p>Install using pip:</p>
                        <pre><code>pip install huskycat</code></pre>
                    </body>
                    </html>
                    ''')
                elif self.path.startswith('/downloads/'):
                    # Mock binary download
                    self.send_response(200)
                    self.send_header('Content-type', 'application/octet-stream')
                    self.send_header('Content-Length', '1024')
                    self.end_headers()
                    self.wfile.write(b'x' * 1024)  # Mock binary data
                else:
                    self.send_response(404)
                    self.end_headers()
        
        return MockPagesHandler


class MockMCPServer:
    """Mock MCP server for testing."""
    
    def __init__(self, port: int = 8080):
        self.port = port
        self.process = None
        self.running = False
    
    def start(self):
        """Start the mock MCP server."""
        # Create a simple mock server script
        server_script = tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False)
        server_script.write(f'''
import http.server
import socketserver
import json
from urllib.parse import urlparse, parse_qs

class MockMCPHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {{"status": "ready", "server": "mock-mcp"}}
            self.wfile.write(json.dumps(response).encode())
        
        elif self.path == '/tools':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            tools = [
                {{"name": "python-black", "enabled": True}},
                {{"name": "python-flake8", "enabled": True}},
                {{"name": "python-mypy", "enabled": True}},
                {{"name": "security_bandit_scan", "enabled": True}}
            ]
            self.wfile.write(json.dumps(tools).encode())
        
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        if self.path == '/validate/python':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            # Mock validation results
            result = {{
                "validation_results": {{
                    "python-black": {{"errors": [], "warnings": []}},
                    "python-flake8": {{"errors": ["E302: expected 2 blank lines"], "warnings": []}}
                }}
            }}
            self.wfile.write(json.dumps(result).encode())
        
        elif self.path == '/validate/security':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            result = {{
                "security_issues": [
                    {{"type": "HIGH", "test": "B102", "description": "Use of exec detected"}}
                ]
            }}
            self.wfile.write(json.dumps(result).encode())
        
        else:
            self.send_response(404)
            self.end_headers()

with socketserver.TCPServer(("", {self.port}), MockMCPHandler) as httpd:
    print(f"Mock MCP server running on port {self.port}")
    httpd.serve_forever()
''')
        server_script.close()
        
        # Start the server process
        self.process = subprocess.Popen([
            sys.executable, server_script.name
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        self.running = True
        time.sleep(2)  # Give server time to start
        
        # Clean up script file
        os.unlink(server_script.name)
    
    def stop(self):
        """Stop the mock MCP server."""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
        self.running = False


class MockContainerRegistry:
    """Mock container registry for testing."""
    
    def __init__(self):
        self.images = {}
        self.tags = {}
    
    def push_image(self, image_name: str, tag: str = "latest"):
        """Mock image push."""
        full_name = f"{image_name}:{tag}"
        self.images[full_name] = {
            "name": image_name,
            "tag": tag,
            "size": "100MB",
            "created": "2024-01-01T00:00:00Z"
        }
        return True
    
    def pull_image(self, image_name: str, tag: str = "latest"):
        """Mock image pull."""
        full_name = f"{image_name}:{tag}"
        return self.images.get(full_name)
    
    def list_images(self):
        """Mock image listing."""
        return list(self.images.keys())


class TempGitRepository:
    """Temporary Git repository for testing."""
    
    def __init__(self, repo_dir: Path):
        self.repo_dir = repo_dir
        self.initialized = False
    
    def initialize(self):
        """Initialize the Git repository."""
        subprocess.run(["git", "init"], cwd=self.repo_dir, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.repo_dir, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=self.repo_dir, check=True)
        self.initialized = True
    
    def add_file(self, filename: str, content: str):
        """Add a file to the repository."""
        file_path = self.repo_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w') as f:
            f.write(content)
    
    def commit(self, message: str):
        """Commit changes."""
        subprocess.run(["git", "add", "."], cwd=self.repo_dir, check=True)
        subprocess.run(["git", "commit", "-m", message], cwd=self.repo_dir, check=True)
    
    def create_branch(self, branch_name: str):
        """Create and checkout a new branch."""
        subprocess.run(["git", "checkout", "-b", branch_name], cwd=self.repo_dir, check=True)
    
    def tag_commit(self, tag_name: str):
        """Tag current commit."""
        subprocess.run(["git", "tag", tag_name], cwd=self.repo_dir, check=True)


# Pytest fixtures
@pytest.fixture(scope="session")
def free_port() -> int:
    """Get a free port for testing."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


@pytest.fixture
def mock_pages_server(free_port: int) -> Generator[MockGitLabPagesServer, None, None]:
    """Mock GitLab Pages server fixture."""
    server = MockGitLabPagesServer(port=free_port)
    server.start()
    try:
        yield server
    finally:
        server.stop()


@pytest.fixture
def mock_mcp_server() -> Generator[MockMCPServer, None, None]:
    """Mock MCP server fixture."""
    server = MockMCPServer()
    server.start()
    try:
        yield server
    finally:
        server.stop()


@pytest.fixture
def mock_container_registry() -> MockContainerRegistry:
    """Mock container registry fixture."""
    return MockContainerRegistry()


@pytest.fixture
def temp_project_environment() -> Generator[Path, None, None]:
    """Create a temporary project environment."""
    temp_dir = tempfile.mkdtemp(prefix="huskycats_e2e_")
    project_dir = Path(temp_dir) / "test_project"
    project_dir.mkdir(parents=True)
    
    # Copy essential files for testing
    source_files = [
        "pyproject.toml",
        "package.json", 
        ".gitlab-ci.yml",
        "ContainerFile",
        "Makefile"
    ]
    
    for source_file in source_files:
        if Path(source_file).exists():
            shutil.copy2(source_file, project_dir / source_file)
    
    # Create basic directory structure
    (project_dir / "src").mkdir()
    (project_dir / "tests").mkdir()
    (project_dir / "docs").mkdir()
    
    try:
        yield project_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def temp_git_repo(temp_project_environment: Path) -> TempGitRepository:
    """Create a temporary Git repository."""
    repo = TempGitRepository(temp_project_environment)
    repo.initialize()
    
    # Add initial files
    repo.add_file("README.md", "# Test Project")
    repo.add_file("src/main.py", "def main(): pass")
    repo.commit("Initial commit")
    
    return repo


@pytest.fixture
def mock_ci_environment() -> Dict[str, str]:
    """Mock CI environment variables."""
    return {
        "CI": "true",
        "GITLAB_CI": "true",
        "CI_COMMIT_SHA": "abc123def456",
        "CI_COMMIT_REF_NAME": "main",
        "CI_PROJECT_NAME": "huskycats",
        "CI_PROJECT_URL": "https://gitlab.com/example/huskycats",
        "CI_PIPELINE_ID": "12345",
        "CI_JOB_ID": "67890"
    }


@contextmanager
def isolated_environment(env_vars: Dict[str, str]):
    """Context manager for isolated environment."""
    original_env = os.environ.copy()
    try:
        os.environ.update(env_vars)
        yield
    finally:
        os.environ.clear()
        os.environ.update(original_env)


@pytest.fixture
def isolated_test_environment(mock_ci_environment: Dict[str, str]):
    """Isolated test environment fixture."""
    with isolated_environment(mock_ci_environment):
        yield


@pytest.fixture
def mock_docker_client():
    """Mock Docker client for testing."""
    class MockImage:
        def __init__(self, id: str, tags: List[str]):
            self.id = id
            self.tags = tags
    
    class MockContainer:
        def __init__(self, id: str, status: str = "running"):
            self.id = id
            self.status = status
            self.ports = {"8080/tcp": [{"HostPort": "8080"}]}
        
        def reload(self):
            pass
        
        def stop(self, timeout: int = 10):
            self.status = "stopped"
        
        def remove(self):
            pass
    
    class MockImages:
        def build(self, **kwargs):
            image = MockImage("test-image-id", ["test:latest"])
            build_logs = ["Step 1/5 : FROM python:3.9", "Successfully built test-image-id"]
            return image, build_logs
        
        def remove(self, image_id: str, force: bool = False):
            pass
    
    class MockContainers:
        def run(self, image, **kwargs):
            return MockContainer("test-container-id")
    
    class MockDockerClient:
        def __init__(self):
            self.images = MockImages()
            self.containers = MockContainers()
        
        def ping(self):
            return True
        
        def from_env(self):
            return self
    
    return MockDockerClient()


@pytest.fixture
def sample_validation_files(temp_project_environment: Path) -> Dict[str, Path]:
    """Create sample files for validation testing."""
    files = {}
    
    # Good Python code
    good_python = temp_project_environment / "good_code.py"
    good_python.write_text('''#!/usr/bin/env python3
"""Sample good Python code."""
from typing import List


def calculate_sum(numbers: List[int]) -> int:
    """Calculate sum of numbers."""
    return sum(numbers)


def main() -> None:
    """Main function."""
    result = calculate_sum([1, 2, 3, 4, 5])
    print(f"Sum: {result}")


if __name__ == "__main__":
    main()
''')
    files['good_python'] = good_python
    
    # Bad Python code
    bad_python = temp_project_environment / "bad_code.py"
    bad_python.write_text('''#!/usr/bin/env python3

def calculate_sum(numbers):
    sum=0
    for i in range(len(numbers)):
        sum+=numbers[i]
    return sum

def unsafe_eval(expr):
    return eval(expr)

def main():
    result=calculate_sum([1,2,3])
    print(result)
''')
    files['bad_python'] = bad_python
    
    # Valid YAML
    valid_yaml = temp_project_environment / "valid.yml"
    valid_yaml.write_text('''
version: "3.8"
services:
  web:
    image: nginx:latest
    ports:
      - "80:80"
    environment:
      - DEBUG=false
''')
    files['valid_yaml'] = valid_yaml
    
    # Invalid YAML
    invalid_yaml = temp_project_environment / "invalid.yml"
    invalid_yaml.write_text('''
version: "3.8"
services:
  web:
    image: nginx:latest
    ports:
      - "80:80
    environment:
      - DEBUG=false
''')
    files['invalid_yaml'] = invalid_yaml
    
    return files


@pytest.fixture
def performance_test_data():
    """Generate test data for performance testing."""
    return {
        "small_file": "def hello(): return 'world'\n" * 10,
        "medium_file": "def hello(): return 'world'\n" * 100,
        "large_file": "def hello(): return 'world'\n" * 1000,
        "huge_file": "def hello(): return 'world'\n" * 10000,
    }


@pytest.fixture
async def async_test_client():
    """Async HTTP client for testing."""
    import aiohttp
    
    session = aiohttp.ClientSession()
    try:
        yield session
    finally:
        await session.close()


# Utility functions for testing
def wait_for_server(host: str, port: int, timeout: int = 30) -> bool:
    """Wait for server to be ready."""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except (socket.error, ConnectionRefusedError):
            time.sleep(0.5)
    
    return False


def create_test_dockerfile(directory: Path) -> Path:
    """Create a test Dockerfile."""
    dockerfile = directory / "Dockerfile"
    dockerfile.write_text('''
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["python", "app.py"]
''')
    
    # Create a simple requirements.txt
    requirements = directory / "requirements.txt"
    requirements.write_text("flask==2.0.1\nrequests==2.25.1\n")
    
    # Create a simple app.py
    app_py = directory / "app.py"
    app_py.write_text('''
from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return "Hello, World!"

@app.route('/health')
def health():
    return {"status": "healthy"}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
''')
    
    return dockerfile


def create_test_gitlab_ci(directory: Path) -> Path:
    """Create a test .gitlab-ci.yml file."""
    gitlab_ci = directory / ".gitlab-ci.yml"
    gitlab_ci.write_text('''
stages:
  - test
  - build
  - deploy

variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"

cache:
  paths:
    - .cache/pip
    - venv/

before_script:
  - python -m venv venv
  - source venv/bin/activate
  - pip install -r requirements.txt

test:
  stage: test
  script:
    - python -m pytest tests/ -v
    - python -m flake8 src/
  coverage: '/TOTAL.+ ([0-9]{1,3}%)/'

build:
  stage: build
  script:
    - python -m build
  artifacts:
    paths:
      - dist/

deploy:
  stage: deploy
  script:
    - echo "Deploying to production"
  only:
    - main
''')
    
    return gitlab_ci


@pytest.fixture
def comprehensive_test_environment(temp_project_environment: Path) -> Path:
    """Create a comprehensive test environment with all necessary files."""
    # Create test files
    create_test_dockerfile(temp_project_environment)
    create_test_gitlab_ci(temp_project_environment)
    
    # Create test directories and files
    test_structure = {
        "src/main.py": "def main(): print('Hello, World!')",
        "tests/test_main.py": "def test_main(): assert True",
        "docs/index.md": "# Documentation",
        "config/settings.yml": "debug: true",
        ".env.example": "DEBUG=true\nPORT=8080",
        "scripts/deploy.sh": "#!/bin/bash\necho 'Deploying...'",
    }
    
    for file_path, content in test_structure.items():
        full_path = temp_project_environment / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)
        
        # Make scripts executable
        if file_path.startswith("scripts/") and file_path.endswith(".sh"):
            full_path.chmod(0o755)
    
    return temp_project_environment