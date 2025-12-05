#!/usr/bin/env python3
"""Pytest configuration and shared fixtures for HuskyCats testing."""

import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterator

import hypothesis
import pytest
from hypothesis import strategies as st

# Add src directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Configure Hypothesis profiles
# CI profile: Reduced examples to avoid timeouts
hypothesis.settings.register_profile(
    "ci",
    max_examples=10,  # Reduced from 1000 to prevent timeouts
    deadline=None,
    suppress_health_check=[hypothesis.HealthCheck.too_slow],
)
# Dev profile: Moderate testing for local development
hypothesis.settings.register_profile("dev", max_examples=50, deadline=200)
# Load appropriate profile based on environment
hypothesis.settings.load_profile("ci" if os.getenv("CI") else "dev")


@pytest.fixture(scope="session")
def temp_project_dir() -> Iterator[Path]:
    """Create a temporary project directory for testing."""
    temp_dir = tempfile.mkdtemp(prefix="huskycats_test_")
    try:
        yield Path(temp_dir)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="function")
def isolated_dir(temp_project_dir: Path) -> Iterator[Path]:
    """Create an isolated directory for each test."""
    test_dir = temp_project_dir / f"test_{os.getpid()}"
    test_dir.mkdir(exist_ok=True)
    original_cwd = os.getcwd()
    try:
        os.chdir(test_dir)
        yield test_dir
    finally:
        os.chdir(original_cwd)


@pytest.fixture
def sample_python_code() -> str:
    """Provide sample Python code for testing."""
    return '''#!/usr/bin/env python3
"""Sample module for testing."""
from typing import List, Optional

def calculate_sum(numbers: List[int]) -> int:
    """Calculate sum of numbers."""
    return sum(numbers)

def process_data(data: Optional[List[str]]) -> List[str]:
    """Process string data."""
    if data is None:
        return []
    return [item.strip().upper() for item in data if item.strip()]

class DataProcessor:
    """Sample data processor."""
    
    def __init__(self, name: str) -> None:
        self.name = name
    
    def process(self, items: List[int]) -> List[int]:
        """Process integer items."""
        return [x * 2 for x in items if x > 0]
'''


@pytest.fixture
def bad_python_code() -> str:
    """Provide bad Python code for testing validation tools."""
    return """#!/usr/bin/env python3

def calculate_sum(numbers):
    sum=0
    for i in range(len(numbers)):
        sum+=numbers[i]
    return sum

def process_data(  data  ):
    if data==None:
        return []
    processed=[]
    for item in data:
        if item>0: processed.append(item*2)
    return processed

class DataProcessor:
    def __init__(self,name):
        self.name=name
    def process(self,data):
        return [x**2 for x in data if x%2==0]

# Security issue
def unsafe_calc(expr):
    return eval(expr)

def concatenate(a,b):
    return str(a)+str(b)
"""


@pytest.fixture
def mcp_server_config() -> Dict[str, Any]:
    """Provide MCP server test configuration."""
    return {
        "server": {
            "host": "localhost",
            "port": 8080,
            "token": "test-token-123",
        },
        "tools": {
            "python-black": {"enabled": True},
            "python-flake8": {"enabled": True},
            "python-mypy": {"enabled": True},
            "security_bandit_scan": {"enabled": True},
        },
        "validation": {
            "timeout": 30,
            "max_file_size": 1024 * 1024,  # 1MB
        },
    }


@pytest.fixture
def container_test_config() -> Dict[str, Any]:
    """Provide container testing configuration."""
    return {
        "image_name": "huskycats-test",
        "dockerfile_path": "./ContainerFile",
        "test_commands": [
            "which python3",
            "python3 --version",
            "pip list",
            "black --version",
            "flake8 --version",
            "mypy --version",
        ],
        "environment": {
            "PYTHONPATH": "/app",
            "NODE_PATH": "/usr/local/lib/node_modules",
        },
    }


@pytest.fixture
def git_hook_test_repo(isolated_dir: Path) -> Path:
    """Create a test git repository with hooks."""
    repo_dir = isolated_dir / "test_repo"
    repo_dir.mkdir()

    # Initialize git repo
    os.system(f"cd {repo_dir} && git init")
    os.system(f"cd {repo_dir} && git config user.email 'test@example.com'")
    os.system(f"cd {repo_dir} && git config user.name 'Test User'")

    # Create .husky directory
    husky_dir = repo_dir / ".husky"
    husky_dir.mkdir()

    # Create sample pre-commit hook
    pre_commit = husky_dir / "pre-commit"
    pre_commit.write_text(
        """#!/usr/bin/env sh
. "$(dirname -- "$0")/_/husky.sh"

echo "Running pre-commit validation..."
exit 0
"""
    )
    pre_commit.chmod(0o755)

    return repo_dir


# Hypothesis strategies for property-based testing
@st.composite
def python_code_strategy(draw) -> str:
    """Generate valid Python code structures."""
    function_name = draw(
        st.text(
            min_size=3,
            max_size=20,
            alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd", "_")),
        )
    )
    if not function_name[0].isalpha():
        function_name = "f" + function_name

    parameters = draw(
        st.lists(
            st.text(
                min_size=1,
                max_size=10,
                alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd", "_")),
            ),
            min_size=0,
            max_size=3,
        )
    )
    parameters = [p for p in parameters if p.isidentifier()]

    param_str = ", ".join(parameters) if parameters else ""
    return f"def {function_name}({param_str}):\n    return None"


@st.composite
def file_content_strategy(draw) -> str:
    """Generate file content for testing."""
    lines = draw(st.lists(st.text(max_size=100), min_size=1, max_size=50))
    return "\n".join(lines)


@st.composite
def validation_config_strategy(draw) -> Dict[str, Any]:
    """Generate validation configuration objects."""
    return {
        "max_line_length": draw(st.integers(min_value=80, max_value=120)),
        "indent_size": draw(st.integers(min_value=2, max_value=8)),
        "enforce_typing": draw(st.booleans()),
        "check_security": draw(st.booleans()),
        "exclude_patterns": draw(st.lists(st.text(max_size=20), max_size=5)),
    }


# Markers for test categorization
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "security: Security-focused tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "property: Property-based tests")
    config.addinivalue_line("markers", "container: Container tests")
    config.addinivalue_line("markers", "slow: Slow-running tests")


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on filename patterns."""
    for item in items:
        # Mark property-based tests
        if "property" in item.nodeid or "hypothesis" in str(item.function):
            item.add_marker(pytest.mark.property)

        # Mark container tests
        if "container" in item.nodeid or "docker" in item.nodeid:
            item.add_marker(pytest.mark.container)

        # Mark slow tests
        if "slow" in item.nodeid:
            item.add_marker(pytest.mark.slow)

        # Mark security tests
        if "security" in item.nodeid or "bandit" in item.nodeid:
            item.add_marker(pytest.mark.security)


@pytest.fixture(autouse=True)
def test_environment_setup():
    """Set up test environment variables."""
    original_env = os.environ.copy()

    # Set test-specific environment variables
    os.environ.update(
        {
            "TESTING": "true",
            "LOG_LEVEL": "DEBUG",
            "MCP_SERVER_URL": "http://localhost:8080",
            "MCP_SERVER_TOKEN": "test-token-123",
        }
    )

    try:
        yield
    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)


# E2E fixtures removed - see docs/future-roadmap.md for future plans


# Custom assertion helpers
def assert_valid_python_code(code: str) -> None:
    """Assert that given code is valid Python."""
    try:
        compile(code, "<test>", "exec")
    except SyntaxError as e:
        pytest.fail(f"Invalid Python code: {e}")


def assert_no_security_issues(code: str) -> None:
    """Assert that code has no obvious security issues."""
    dangerous_patterns = ["eval(", "exec(", "__import__", "open("]
    for pattern in dangerous_patterns:
        assert pattern not in code, f"Potentially dangerous pattern found: {pattern}"


def assert_follows_style(code: str, max_line_length: int = 88) -> None:
    """Assert that code follows basic style guidelines."""
    lines = code.split("\n")
    for i, line in enumerate(lines, 1):
        assert (
            len(line) <= max_line_length
        ), f"Line {i} exceeds max length: {len(line)} > {max_line_length}"


def assert_test_quality(test_function) -> None:
    """Assert that a test function meets quality standards."""
    import inspect

    # Check for docstring
    assert (
        test_function.__doc__ is not None
    ), f"Test {test_function.__name__} missing docstring"

    # Check for proper naming
    assert test_function.__name__.startswith(
        "test_"
    ), f"Test {test_function.__name__} doesn't follow naming convention"

    # Check function signature for proper typing (if annotations exist)
    sig = inspect.signature(test_function)
    for param_name, param in sig.parameters.items():
        if param.annotation != inspect.Parameter.empty:
            # Parameter has type annotation - good practice
            pass


def assert_e2e_environment_ready() -> bool:
    """Assert that E2E testing environment is properly configured."""
    required_packages = ["playwright", "requests", "docker"]
    missing_packages = []

    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        pytest.skip(f"E2E environment not ready, missing packages: {missing_packages}")

    return True
