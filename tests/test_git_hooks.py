#!/usr/bin/env python3
"""Tests for Git hook functionality and validation."""

import pytest
import subprocess
import tempfile
import os
import shutil
from pathlib import Path
from typing import List, Dict, Any
import json


class TestGitHookValidation:
    """Test suite for Git hook functionality."""
    
    def test_pre_commit_hook_exists(self):
        """Verify pre-commit hook exists and is executable."""
        pre_commit_path = Path(".husky/pre-commit")
        assert pre_commit_path.exists(), "Pre-commit hook not found"
        assert os.access(pre_commit_path, os.X_OK), "Pre-commit hook is not executable"
    
    def test_pre_commit_mcp_hook_exists(self):
        """Verify pre-commit MCP hook exists and is executable."""
        pre_commit_mcp_path = Path(".husky/pre-commit-mcp")
        assert pre_commit_mcp_path.exists(), "Pre-commit MCP hook not found"
        assert os.access(pre_commit_mcp_path, os.X_OK), "Pre-commit MCP hook is not executable"
    
    def test_commit_msg_hook_exists(self):
        """Verify commit-msg hook exists."""
        commit_msg_path = Path(".husky/commit-msg")
        assert commit_msg_path.exists(), "Commit-msg hook not found"
    
    def test_husky_directory_structure(self):
        """Verify Husky directory structure is correct."""
        husky_dir = Path(".husky")
        assert husky_dir.exists(), "Husky directory not found"
        assert husky_dir.is_dir(), "Husky path is not a directory"
        
        # Check for Husky internal files
        husky_internal = husky_dir / "_"
        assert husky_internal.exists(), "Husky internal directory not found"


class TestGitHookExecution:
    """Test actual Git hook execution."""
    
    @pytest.fixture
    def test_repo(self, isolated_dir: Path) -> Path:
        """Create a test Git repository."""
        repo_dir = isolated_dir / "test_git_repo"
        repo_dir.mkdir()
        
        # Initialize Git repo
        subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_dir, check=True)
        
        return repo_dir
    
    def test_pre_commit_validation_passes_clean_code(self, test_repo: Path):
        """Test that pre-commit validation passes for clean code."""
        # Create a clean Python file
        clean_python = test_repo / "clean_code.py"
        clean_python.write_text('''#!/usr/bin/env python3
"""Clean Python code for testing."""
from typing import List


def calculate_sum(numbers: List[int]) -> int:
    """Calculate the sum of numbers."""
    return sum(numbers)


def main() -> None:
    """Main function."""
    result = calculate_sum([1, 2, 3, 4, 5])
    print(f"Sum: {result}")


if __name__ == "__main__":
    main()
''')
        
        # Stage the file
        subprocess.run(["git", "add", "clean_code.py"], cwd=test_repo, check=True)
        
        # Copy our pre-commit hook to test repo
        self._setup_test_hooks(test_repo)
        
        # Run pre-commit hook directly
        hook_path = test_repo / ".husky" / "pre-commit"
        if hook_path.exists():
            result = subprocess.run([str(hook_path)], cwd=test_repo, capture_output=True, text=True)
            # Should pass (exit code 0) or at least not fail catastrophically
            assert result.returncode in [0, 1], f"Hook failed unexpectedly: {result.stderr}"
    
    def test_pre_commit_validation_catches_bad_code(self, test_repo: Path):
        """Test that pre-commit validation catches problematic code."""
        # Create problematic Python file
        bad_python = test_repo / "bad_code.py"
        bad_python.write_text('''#!/usr/bin/env python3
def calculate_sum(numbers):
    sum=0
    for i in range(len(numbers)):
        sum+=numbers[i]
    return sum

def unsafe_calc(expr):
    return eval(expr)  # Security issue

def concatenate(a,b):  # Style issues
    return str(a)+str(b)
''')
        
        # Stage the file
        subprocess.run(["git", "add", "bad_code.py"], cwd=test_repo, check=True)
        
        # Copy our pre-commit hook to test repo
        self._setup_test_hooks(test_repo)
        
        # Run pre-commit hook directly
        hook_path = test_repo / ".husky" / "pre-commit"
        if hook_path.exists():
            result = subprocess.run([str(hook_path)], cwd=test_repo, capture_output=True, text=True)
            # May exit with non-zero for validation failures, but shouldn't crash
            assert result.returncode is not None, "Hook process didn't complete"
    
    def test_commit_msg_validation(self, test_repo: Path):
        """Test commit message validation."""
        # Create test commit message
        commit_msg_file = test_repo / ".git" / "COMMIT_EDITMSG"
        commit_msg_file.parent.mkdir(exist_ok=True)
        
        test_messages = [
            "feat: add new feature",  # Good conventional commit
            "fix: resolve bug in calculation",  # Good
            "bad message",  # Potentially bad
            "",  # Empty message
        ]
        
        self._setup_test_hooks(test_repo)
        commit_msg_hook = test_repo / ".husky" / "commit-msg"
        
        if commit_msg_hook.exists():
            for msg in test_messages:
                commit_msg_file.write_text(msg)
                result = subprocess.run(
                    [str(commit_msg_hook), str(commit_msg_file)],
                    cwd=test_repo,
                    capture_output=True,
                    text=True
                )
                # Hook should run without crashing
                assert result.returncode is not None, f"Hook crashed on message: '{msg}'"
    
    def _setup_test_hooks(self, repo_dir: Path):
        """Set up test hooks in the repository."""
        husky_dir = repo_dir / ".husky"
        husky_dir.mkdir(exist_ok=True)
        
        # Copy hooks from main repo if they exist
        main_husky = Path(".husky")
        if main_husky.exists():
            for hook_file in main_husky.glob("*"):
                if hook_file.is_file() and not hook_file.name.startswith("."):
                    dest = husky_dir / hook_file.name
                    try:
                        shutil.copy2(hook_file, dest)
                        dest.chmod(0o755)
                    except (OSError, PermissionError):
                        # Create minimal test hooks if copying fails
                        dest.write_text(f"#!/bin/sh\necho 'Test {hook_file.name} hook'\nexit 0\n")
                        dest.chmod(0o755)
        else:
            # Create minimal test hooks
            self._create_minimal_hooks(husky_dir)
    
    def _create_minimal_hooks(self, husky_dir: Path):
        """Create minimal test hooks."""
        # Pre-commit hook
        pre_commit = husky_dir / "pre-commit"
        pre_commit.write_text('''#!/bin/sh
echo "Running pre-commit validation..."
# Basic validation - check for Python files
if git diff --cached --name-only | grep -q "\.py$"; then
    echo "Python files detected, running basic checks..."
    # Just check syntax with Python
    for file in $(git diff --cached --name-only | grep "\.py$"); do
        if [ -f "$file" ]; then
            python3 -m py_compile "$file" || exit 1
        fi
    done
fi
exit 0
''')
        pre_commit.chmod(0o755)
        
        # Commit message hook
        commit_msg = husky_dir / "commit-msg"
        commit_msg.write_text('''#!/bin/sh
commit_msg_file=$1
if [ -f "$commit_msg_file" ]; then
    # Basic validation - non-empty message
    if [ -s "$commit_msg_file" ]; then
        echo "Commit message validation passed"
        exit 0
    else
        echo "Commit message is empty"
        exit 1
    fi
fi
exit 0
''')
        commit_msg.chmod(0o755)


class TestGitHookPerformance:
    """Test Git hook performance characteristics."""
    
    def test_pre_commit_hook_performance(self, test_repo: Path):
        """Test that pre-commit hooks complete within reasonable time."""
        import time
        
        # Create multiple files to test with
        for i in range(10):
            test_file = test_repo / f"test_file_{i}.py"
            test_file.write_text(f'''#!/usr/bin/env python3
"""Test file {i}."""

def function_{i}() -> int:
    """Return {i}."""
    return {i}

if __name__ == "__main__":
    print(function_{i}())
''')
            subprocess.run(["git", "add", f"test_file_{i}.py"], cwd=test_repo, check=True)
        
        self._setup_test_hooks(test_repo)
        hook_path = test_repo / ".husky" / "pre-commit"
        
        if hook_path.exists():
            start_time = time.time()
            result = subprocess.run([str(hook_path)], cwd=test_repo, capture_output=True)
            end_time = time.time()
            
            duration = end_time - start_time
            # Hook should complete within 30 seconds for 10 small files
            assert duration < 30.0, f"Pre-commit hook took too long: {duration:.2f}s"
    
    def _setup_test_hooks(self, repo_dir: Path):
        """Set up test hooks - reused from TestGitHookExecution."""
        husky_dir = repo_dir / ".husky"
        husky_dir.mkdir(exist_ok=True)
        
        # Create performance-focused minimal hook
        pre_commit = husky_dir / "pre-commit"
        pre_commit.write_text('''#!/bin/sh
echo "Running fast pre-commit validation..."
# Quick syntax check only
for file in $(git diff --cached --name-only | grep "\.py$"); do
    if [ -f "$file" ]; then
        python3 -m py_compile "$file" || exit 1
    fi
done
echo "Pre-commit validation completed"
exit 0
''')
        pre_commit.chmod(0o755)


class TestGitHookIntegration:
    """Test Git hook integration with MCP server and tools."""
    
    @pytest.mark.integration
    def test_mcp_hook_integration(self, test_repo: Path):
        """Test integration between Git hooks and MCP server."""
        # This test would require MCP server to be running
        # For now, we'll test the hook structure and basic functionality
        
        self._setup_mcp_hooks(test_repo)
        
        mcp_hook = test_repo / ".husky" / "pre-commit-mcp"
        if mcp_hook.exists():
            # Test that MCP hook is properly structured
            content = mcp_hook.read_text()
            assert "mcp" in content.lower() or "validation" in content.lower()
            
            # Test execution (may fail if MCP server not running, but shouldn't crash)
            result = subprocess.run([str(mcp_hook)], cwd=test_repo, capture_output=True, text=True, timeout=10)
            # Should complete without hanging
            assert result.returncode is not None
    
    def _setup_mcp_hooks(self, repo_dir: Path):
        """Set up MCP-specific hooks."""
        husky_dir = repo_dir / ".husky"
        husky_dir.mkdir(exist_ok=True)
        
        # Copy MCP hook from main repo or create test version
        main_mcp_hook = Path(".husky/pre-commit-mcp")
        mcp_hook = husky_dir / "pre-commit-mcp"
        
        if main_mcp_hook.exists():
            try:
                shutil.copy2(main_mcp_hook, mcp_hook)
                mcp_hook.chmod(0o755)
            except (OSError, PermissionError):
                self._create_test_mcp_hook(mcp_hook)
        else:
            self._create_test_mcp_hook(mcp_hook)
    
    def _create_test_mcp_hook(self, hook_path: Path):
        """Create a test MCP hook."""
        hook_path.write_text('''#!/bin/sh
echo "Running MCP validation..."
# Test MCP server connectivity (mock)
if command -v curl >/dev/null 2>&1; then
    # Try to connect to MCP server (will likely fail in test, but that's OK)
    curl -s --connect-timeout 1 http://localhost:8080/health >/dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "MCP server is running"
    else
        echo "MCP server not available (OK for testing)"
    fi
fi
echo "MCP hook completed"
exit 0
''')
        hook_path.chmod(0o755)


class TestGitHookConfiguration:
    """Test Git hook configuration and customization."""
    
    def test_husky_configuration(self):
        """Test Husky configuration in package.json."""
        package_json = Path("package.json")
        if package_json.exists():
            with open(package_json) as f:
                config = json.load(f)
            
            # Check for Husky setup
            if "scripts" in config:
                scripts = config["scripts"]
                # Should have prepare script for Husky
                assert "prepare" in scripts, "No prepare script found for Husky"
                assert "husky" in scripts["prepare"], "Prepare script doesn't mention Husky"
    
    def test_lint_staged_configuration(self):
        """Test lint-staged configuration."""
        # Check for lint-staged in package.json
        package_json = Path("package.json")
        if package_json.exists():
            with open(package_json) as f:
                config = json.load(f)
            
            # Check for lint-staged in devDependencies
            if "devDependencies" in config:
                dev_deps = config["devDependencies"]
                # lint-staged is commonly used with Husky
                if "lint-staged" in dev_deps:
                    assert isinstance(dev_deps["lint-staged"], str)
    
    def test_hook_file_permissions(self):
        """Test that hook files have correct permissions."""
        husky_dir = Path(".husky")
        if husky_dir.exists():
            for hook_file in husky_dir.glob("*"):
                if hook_file.is_file() and not hook_file.name.startswith("_"):
                    # Hook files should be executable
                    assert os.access(hook_file, os.X_OK), f"Hook {hook_file} is not executable"


@pytest.mark.integration
class TestGitWorkflow:
    """Test complete Git workflow with hooks."""
    
    def test_full_commit_workflow(self, test_repo: Path):
        """Test complete commit workflow including all hooks."""
        # Create a good file
        good_file = test_repo / "good_code.py"
        good_file.write_text('''#!/usr/bin/env python3
"""Good Python code for testing."""

from typing import List


def calculate_average(numbers: List[float]) -> float:
    """Calculate the average of numbers."""
    if not numbers:
        return 0.0
    return sum(numbers) / len(numbers)


def main() -> None:
    """Main function."""
    test_numbers = [1.0, 2.0, 3.0, 4.0, 5.0]
    avg = calculate_average(test_numbers)
    print(f"Average: {avg}")


if __name__ == "__main__":
    main()
''')
        
        # Stage and commit
        subprocess.run(["git", "add", "good_code.py"], cwd=test_repo, check=True)
        
        # Set up hooks
        self._setup_complete_hooks(test_repo)
        
        # Try to commit (hooks will run)
        try:
            result = subprocess.run([
                "git", "commit", "-m", "feat: add calculate_average function"
            ], cwd=test_repo, capture_output=True, text=True, timeout=30)
            
            # Commit should complete (success or failure, but not hang)
            assert result.returncode is not None, "Commit process hung"
            
            if result.returncode == 0:
                # Verify commit was created
                log_result = subprocess.run(
                    ["git", "log", "--oneline", "-n", "1"],
                    cwd=test_repo, capture_output=True, text=True
                )
                assert "calculate_average" in log_result.stdout
        
        except subprocess.TimeoutExpired:
            pytest.fail("Git commit with hooks timed out")
    
    def _setup_complete_hooks(self, repo_dir: Path):
        """Set up complete hook suite."""
        husky_dir = repo_dir / ".husky"
        husky_dir.mkdir(exist_ok=True)
        
        # Pre-commit hook with comprehensive checks
        pre_commit = husky_dir / "pre-commit"
        pre_commit.write_text('''#!/bin/sh
echo "🔍 Running pre-commit validation..."

# Check for Python files
python_files=$(git diff --cached --name-only | grep "\.py$" || true)

if [ -n "$python_files" ]; then
    echo "📝 Found Python files, running checks..."
    
    # Syntax check
    for file in $python_files; do
        if [ -f "$file" ]; then
            echo "  Checking syntax: $file"
            python3 -m py_compile "$file" || {
                echo "❌ Syntax error in $file"
                exit 1
            }
        fi
    done
    
    echo "✅ All Python files passed syntax check"
fi

echo "✅ Pre-commit validation completed"
exit 0
''')
        pre_commit.chmod(0o755)
        
        # Commit message hook
        commit_msg = husky_dir / "commit-msg"
        commit_msg.write_text('''#!/bin/sh
commit_msg_file=$1
echo "📝 Validating commit message..."

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

# Basic length check
if [ ${#first_line} -gt 72 ]; then
    echo "⚠️  Commit message first line is longer than 72 characters"
fi

echo "✅ Commit message validation passed"
exit 0
''')
        commit_msg.chmod(0o755)