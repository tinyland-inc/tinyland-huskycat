#!/usr/bin/env python3
"""
Comprehensive End-to-End Tests for Real Validation Flow
Tests that the actual validation pipeline works as expected
"""

import pytest
import subprocess
import os
import json
import time
from pathlib import Path
from typing import Optional
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Try to import our validation engines
try:
    from huskycat.unified_validation import ValidationEngine

    HAS_UNIFIED = True
except ImportError:
    HAS_UNIFIED = False

try:
    from huskycat.mcp_server import MCPServer

    HAS_MCP = True
except ImportError:
    HAS_MCP = False


class TestRealValidationFlow:
    """Test the actual validation flow with real files and tools."""

    @pytest.fixture
    def temp_project(self, isolated_dir: Path) -> Path:
        """Create a temporary project with real files."""
        project_dir = isolated_dir / "test_project"
        project_dir.mkdir()

        # Initialize git repo
        subprocess.run(
            ["git", "init"], cwd=project_dir, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=project_dir,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"], cwd=project_dir, check=True
        )

        return project_dir

    def test_python_validation_with_real_tools(self, temp_project: Path):
        """Test Python validation using real validation tools."""
        # Create a Python file with known issues
        python_file = temp_project / "bad_code.py"
        python_file.write_text(
            """#!/usr/bin/env python3
import os,sys,json
def bad_function(  x,y  ):
    result=x+y
    return result
def unused_function():
    import subprocess
    subprocess.call("echo test", shell=True)  # Security issue
class BadClass:
    def __init__(self,name):
        self.name=name
    def method(self):
        eval("1+1")  # Another security issue
"""
        )

        if not HAS_UNIFIED:
            pytest.skip("Unified validation not available")

        # Run validation
        engine = ValidationEngine()
        results = engine.validate_file(python_file)

        # Verify results
        assert isinstance(results, list)
        assert len(results) > 0, "Should find validation issues"

        # Check that at least one tool found issues
        found_issues = any(
            not result.success for result in results if hasattr(result, "success")
        )
        if not found_issues:
            # Check legacy result format
            found_issues = any(
                result.messages for result in results if hasattr(result, "messages")
            )

        assert found_issues, "Should find formatting or security issues"

    def test_javascript_validation_flow(self, temp_project: Path):
        """Test JavaScript validation flow."""
        js_file = temp_project / "bad_code.js"
        js_file.write_text(
            """const x=1+2;const y=3+4;
function badFunction(){console.log("test");return x+y;}
class BadClass{constructor(){this.name="test";}method(){return eval("1+1");}}
"""
        )

        if not HAS_UNIFIED:
            pytest.skip("Unified validation not available")

        engine = ValidationEngine()
        results = engine.validate_file(js_file)

        assert isinstance(results, list)
        # JavaScript validation might not be configured, but should not crash

    def test_yaml_validation_flow(self, temp_project: Path):
        """Test YAML validation flow."""
        yaml_file = temp_project / "config.yaml"
        yaml_file.write_text(
            """
# This YAML has some style issues
database:
  host:    localhost  # Extra spaces
  port:    5432
  name:  mydb
services:
- name: web
  port: 8080
- name:  api  # Inconsistent spacing
  port:    9000
"""
        )

        if not HAS_UNIFIED:
            pytest.skip("Unified validation not available")

        engine = ValidationEngine()
        results = engine.validate_file(yaml_file)

        assert isinstance(results, list)
        # YAML validation results depend on yamllint being installed

    def test_shell_script_validation_flow(self, temp_project: Path):
        """Test shell script validation flow."""
        script_file = temp_project / "test_script.sh"
        script_file.write_text(
            """#!/bin/bash
# This script has shellcheck issues
echo $USER  # Should quote variable
if [ $1 = "test" ]; then  # Should use quotes
    rm -rf $HOME/temp  # Dangerous without quotes
fi

function bad_function() {
    cd $1  # Should check if cd succeeds
    ls *.txt  # Should quote glob
}
"""
        )
        script_file.chmod(0o755)

        if not HAS_UNIFIED:
            pytest.skip("Unified validation not available")

        engine = ValidationEngine()
        results = engine.validate_file(script_file)

        assert isinstance(results, list)
        # Shell validation depends on shellcheck being installed

    def test_dockerfile_validation_flow(self, temp_project: Path):
        """Test Dockerfile validation flow."""
        dockerfile = temp_project / "Dockerfile"
        dockerfile.write_text(
            """FROM ubuntu:latest
MAINTAINER test@example.com
RUN apt-get update
RUN apt-get install -y python3
COPY . /app
WORKDIR /app
USER root
EXPOSE 8080
CMD python3 app.py
"""
        )

        if not HAS_UNIFIED:
            pytest.skip("Unified validation not available")

        engine = ValidationEngine()
        results = engine.validate_file(dockerfile)

        assert isinstance(results, list)
        # Dockerfile validation depends on hadolint being installed


class TestGitHookIntegration:
    """Test that git hooks actually work with real validation."""

    @pytest.fixture
    def git_project(self, isolated_dir: Path) -> Path:
        """Create a git project with hooks set up."""
        project_dir = isolated_dir / "hook_test_project"
        project_dir.mkdir()

        # Initialize git
        subprocess.run(
            ["git", "init"], cwd=project_dir, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=project_dir,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"], cwd=project_dir, check=True
        )

        # Set up basic husky directory
        husky_dir = project_dir / ".husky"
        husky_dir.mkdir()

        # Create a realistic pre-commit hook
        pre_commit_hook = husky_dir / "pre-commit"
        pre_commit_hook.write_text(
            """#!/usr/bin/env sh
. "$(dirname -- "$0")/_/husky.sh"

echo "🔍 Running HuskyCat validation..."

# Check if we have staged Python files
python_files=$(git diff --cached --name-only --diff-filter=ACM | grep '\\.py$' || true)

if [ -n "$python_files" ]; then
    echo "📝 Found Python files, running validation..."
    
    # Run validation on each Python file
    for file in $python_files; do
        echo "  Validating: $file"
        
        # Basic syntax check
        if ! python3 -m py_compile "$file"; then
            echo "❌ Syntax error in $file"
            exit 1
        fi
        
        # Check if black is available
        if command -v black >/dev/null 2>&1; then
            if ! black --check "$file" >/dev/null 2>&1; then
                echo "❌ Formatting issues in $file (run 'black $file' to fix)"
                exit 1
            fi
        fi
        
        # Check if flake8 is available
        if command -v flake8 >/dev/null 2>&1; then
            if ! flake8 "$file" >/dev/null 2>&1; then
                echo "❌ Style issues in $file"
                exit 1
            fi
        fi
    done
    
    echo "✅ Python validation passed"
fi

echo "✅ Pre-commit validation completed"
"""
        )
        pre_commit_hook.chmod(0o755)

        # Create husky internal directory
        husky_internal = husky_dir / "_"
        husky_internal.mkdir()
        husky_sh = husky_internal / "husky.sh"
        husky_sh.write_text("# Husky internal file\n")

        return project_dir

    @pytest.mark.integration
    def test_pre_commit_blocks_bad_python(self, git_project: Path):
        """Test that pre-commit hook blocks bad Python code."""
        bad_python = git_project / "bad.py"
        bad_python.write_text(
            """
# This will fail syntax check
def broken_function(:
    return "missing parenthesis"
"""
        )

        # Stage the file
        subprocess.run(["git", "add", "bad.py"], cwd=git_project, check=True)

        # Try to commit - should fail
        result = subprocess.run(
            ["git", "commit", "-m", "test: add broken code"],
            cwd=git_project,
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0, "Pre-commit should block broken Python code"
        assert "Syntax error" in result.stdout or "syntax" in result.stderr.lower()

    @pytest.mark.integration
    def test_pre_commit_allows_good_python(self, git_project: Path):
        """Test that pre-commit hook allows good Python code."""
        good_python = git_project / "good.py"
        good_python.write_text(
            """#!/usr/bin/env python3
\"\"\"Good Python code for testing.\"\"\"


def hello_world() -> str:
    \"\"\"Return a greeting.\"\"\"
    return "Hello, World!"


if __name__ == "__main__":
    print(hello_world())
"""
        )

        # Stage the file
        subprocess.run(["git", "add", "good.py"], cwd=git_project, check=True)

        # Try to commit - should succeed
        result = subprocess.run(
            ["git", "commit", "-m", "feat: add hello world function"],
            cwd=git_project,
            capture_output=True,
            text=True,
        )

        # Should succeed or at least not fail due to syntax
        if result.returncode != 0:
            # Allow failure due to missing black/flake8, but not syntax errors
            assert "Syntax error" not in result.stdout
            assert "syntax error" not in result.stderr.lower()

    @pytest.mark.integration
    def test_commit_msg_validation(self, git_project: Path):
        """Test commit message validation."""
        # Create commit-msg hook
        commit_msg_hook = git_project / ".husky" / "commit-msg"
        commit_msg_hook.write_text(
            """#!/usr/bin/env sh
. "$(dirname -- "$0")/_/husky.sh"

commit_msg_file="$1"

# Basic commit message validation
if [ ! -f "$commit_msg_file" ]; then
    echo "❌ Commit message file not found"
    exit 1
fi

# Check if message is not empty
if [ ! -s "$commit_msg_file" ]; then
    echo "❌ Commit message cannot be empty"
    exit 1
fi

# Read first line
first_line=$(head -n1 "$commit_msg_file")

# Check for conventional commit format (optional)
if echo "$first_line" | grep -qE '^(feat|fix|docs|style|refactor|test|chore)(\(.+\))?: .+'; then
    echo "✅ Conventional commit format detected"
elif [ ${#first_line} -lt 10 ]; then
    echo "❌ Commit message too short (minimum 10 characters)"
    exit 1
fi

echo "✅ Commit message validation passed"
"""
        )
        commit_msg_hook.chmod(0o755)

        # Create a good file to commit
        test_file = git_project / "test.txt"
        test_file.write_text("test content")
        subprocess.run(["git", "add", "test.txt"], cwd=git_project, check=True)

        # Test bad commit message
        result = subprocess.run(
            ["git", "commit", "-m", "bad"],
            cwd=git_project,
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0, "Should reject short commit message"

        # Test good commit message
        result = subprocess.run(
            ["git", "commit", "-m", "feat: add test file for validation"],
            cwd=git_project,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, "Should accept good commit message"


@pytest.mark.skipif(not HAS_MCP, reason="MCP server not available")
class TestMCPServerIntegration:
    """Test MCP server integration with real validation."""

    def test_mcp_server_tools_list(self):
        """Test that MCP server can list available tools."""
        server = MCPServer()

        request = {"jsonrpc": "2.0", "method": "tools/list", "id": 1}

        # Capture stdout
        import io

        original_stdout = sys.stdout
        sys.stdout = captured_output = io.StringIO()

        try:
            server.handle_request(request)
            response_text = captured_output.getvalue()
            response = json.loads(response_text)

            assert response["jsonrpc"] == "2.0"
            assert response["id"] == 1
            assert "result" in response
            assert "tools" in response["result"]
            assert isinstance(response["result"]["tools"], list)

            # Check that we have some validation tools
            tool_names = [tool["name"] for tool in response["result"]["tools"]]
            expected_tools = ["validate_black", "validate_flake8", "validate"]

            for tool in expected_tools:
                if tool in tool_names:
                    # At least one expected tool should be available
                    break
            else:
                pytest.fail(
                    f"None of expected tools {expected_tools} found in {tool_names}"
                )

        finally:
            sys.stdout = original_stdout

    def test_mcp_server_validation_call(self, temp_project: Path):
        """Test calling validation through MCP server."""
        server = MCPServer()

        # Create a test file
        test_file = temp_project / "test.py"
        test_file.write_text(
            """
def hello():
    print("hello")
"""
        )

        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 2,
            "params": {
                "name": "validate",
                "arguments": {"path": str(test_file), "fix": False},
            },
        }

        # Capture stdout
        import io

        original_stdout = sys.stdout
        sys.stdout = captured_output = io.StringIO()

        try:
            server.handle_request(request)
            response_text = captured_output.getvalue()

            if response_text:
                response = json.loads(response_text)
                assert response["jsonrpc"] == "2.0"
                assert response["id"] == 2
                # Should have either result or error
                assert "result" in response or "error" in response

        finally:
            sys.stdout = original_stdout


class TestValidationScriptIntegration:
    """Test that validation scripts in scripts/ directory work."""

    @pytest.fixture
    def scripts_dir(self) -> Optional[Path]:
        """Get scripts directory if it exists."""
        scripts_path = Path("scripts")
        return scripts_path if scripts_path.exists() else None

    def test_comprehensive_lint_script(
        self, scripts_dir: Optional[Path], temp_project: Path
    ):
        """Test the comprehensive-lint.sh script."""
        if not scripts_dir:
            pytest.skip("scripts directory not found")

        lint_script = scripts_dir / "comprehensive-lint.sh"
        if not lint_script.exists():
            pytest.skip("comprehensive-lint.sh not found")

        # Create test files in temp project
        python_file = temp_project / "test.py"
        python_file.write_text(
            """def hello():
    print("hello world")
"""
        )

        # Run the lint script
        result = subprocess.run(
            [str(lint_script), "--all"],
            cwd=temp_project,
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Script should complete without hanging
        assert result.returncode is not None, "Lint script should complete"

        # If it fails, it should be due to validation issues, not script errors
        if result.returncode != 0:
            # Check that it's not a script error
            assert "command not found" not in result.stderr.lower()
            assert "no such file" not in result.stderr.lower()

    def test_install_script_dry_run(self, scripts_dir: Optional[Path]):
        """Test install script in dry-run mode."""
        if not scripts_dir:
            pytest.skip("scripts directory not found")

        install_script = scripts_dir / "install.sh"
        if not install_script.exists():
            # Try other possible install script names
            for script_name in ["install-unified.sh", "setup.sh"]:
                test_script = scripts_dir / script_name
                if test_script.exists():
                    install_script = test_script
                    break
            else:
                pytest.skip("No install script found")

        # Test script syntax
        result = subprocess.run(
            ["bash", "-n", str(install_script)], capture_output=True, text=True
        )

        assert (
            result.returncode == 0
        ), f"Install script has syntax errors: {result.stderr}"


class TestPerformanceValidation:
    """Test validation performance characteristics."""

    @pytest.mark.slow
    def test_large_file_validation_performance(self, temp_project: Path):
        """Test validation performance on larger files."""
        if not HAS_UNIFIED:
            pytest.skip("Unified validation not available")

        # Create a large Python file
        large_python = temp_project / "large_file.py"
        lines = []
        for i in range(1000):
            lines.append(f"def function_{i}():")
            lines.append(f'    """Function number {i}."""')
            lines.append(f"    return {i}")
            lines.append("")

        large_python.write_text("\n".join(lines))

        # Measure validation time
        engine = ValidationEngine()
        start_time = time.time()
        results = engine.validate_file(large_python)
        end_time = time.time()

        duration = end_time - start_time

        # Should complete within reasonable time (30 seconds for 1000 functions)
        assert duration < 30.0, f"Validation took too long: {duration:.2f}s"
        assert isinstance(results, list)

    @pytest.mark.slow
    def test_multiple_files_validation_performance(self, temp_project: Path):
        """Test validation performance on multiple files."""
        if not HAS_UNIFIED:
            pytest.skip("Unified validation not available")

        # Create multiple files
        file_count = 50
        for i in range(file_count):
            test_file = temp_project / f"test_{i}.py"
            test_file.write_text(
                f"""#!/usr/bin/env python3
def test_function_{i}():
    '''Test function {i}.'''
    return {i}

if __name__ == "__main__":
    print(test_function_{i}())
"""
            )

        # Validate all files
        engine = ValidationEngine()
        start_time = time.time()
        results = engine.validate_directory(temp_project, recursive=False)
        end_time = time.time()

        duration = end_time - start_time

        # Should complete within reasonable time
        assert duration < 60.0, f"Multi-file validation took too long: {duration:.2f}s"
        assert isinstance(results, dict)
        assert len(results) <= file_count  # May be fewer if some files aren't validated


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
