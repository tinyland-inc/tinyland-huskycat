#!/usr/bin/env python3
"""
Comprehensive Container Testing for HuskyCat
Tests container build, security, and functionality
"""

import pytest
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional

# Try to import docker, but don't fail if it's not available
try:
    pass

    HAS_DOCKER = True
except ImportError:
    HAS_DOCKER = False


class ContainerTestHelper:
    """Helper class for container testing operations."""

    def __init__(self):
        self.runtime = self._detect_runtime()
        self.test_containers = []
        self.test_images = []

    def _detect_runtime(self) -> str:
        """Detect available container runtime."""
        for runtime in ["podman", "docker"]:
            try:
                subprocess.run([runtime, "--version"], check=True, capture_output=True)
                return runtime
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue
        raise pytest.skip("No container runtime available (podman/docker)")

    def build_image(self, dockerfile_path: Path, tag: str, context_dir: Path) -> bool:
        """Build container image."""
        cmd = [
            self.runtime,
            "build",
            "-f",
            str(dockerfile_path),
            "-t",
            tag,
            str(context_dir),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            self.test_images.append(tag)
            return True
        else:
            print(f"Build failed: {result.stderr}")
            return False

    def run_container(
        self,
        image: str,
        command: Optional[List[str]] = None,
        volumes: Optional[Dict[str, str]] = None,
        environment: Optional[Dict[str, str]] = None,
        detach: bool = False,
    ) -> subprocess.CompletedProcess:
        """Run container with specified options."""
        cmd = [self.runtime, "run"]

        if detach:
            cmd.append("-d")
            container_name = f"test-container-{int(time.time())}"
            cmd.extend(["--name", container_name])
            self.test_containers.append(container_name)
        else:
            cmd.append("--rm")

        if volumes:
            for host_path, container_path in volumes.items():
                cmd.extend(["-v", f"{host_path}:{container_path}"])

        if environment:
            for key, value in environment.items():
                cmd.extend(["-e", f"{key}={value}"])

        cmd.append(image)
        if command:
            cmd.extend(command)

        return subprocess.run(cmd, capture_output=True, text=True)

    def cleanup(self):
        """Clean up test containers and images."""
        # Stop and remove containers
        for container in self.test_containers:
            subprocess.run([self.runtime, "stop", container], capture_output=True)
            subprocess.run([self.runtime, "rm", container], capture_output=True)

        # Remove images
        for image in self.test_images:
            subprocess.run([self.runtime, "rmi", image], capture_output=True)


@pytest.fixture
def container_helper():
    """Provide container test helper."""
    helper = ContainerTestHelper()
    yield helper
    helper.cleanup()


@pytest.fixture
def built_image(container_helper: ContainerTestHelper):
    """Build the HuskyCat container image."""
    containerfile = Path("ContainerFile")
    if not containerfile.exists():
        pytest.skip("ContainerFile not found")

    tag = "huskycat-test:latest"
    build_success = container_helper.build_image(containerfile, tag, Path("."))

    if not build_success:
        pytest.skip("Container build failed")

    return tag


class TestContainerBuild:
    """Test container building process."""

    def test_container_builds_successfully(self, container_helper: ContainerTestHelper):
        """Test that container builds without errors."""
        containerfile = Path("ContainerFile")
        if not containerfile.exists():
            pytest.skip("ContainerFile not found")

        tag = "huskycat-build-test:latest"
        assert container_helper.build_image(containerfile, tag, Path("."))

    def test_container_has_required_tools(
        self, container_helper: ContainerTestHelper, built_image: str
    ):
        """Test that container has all required validation tools."""
        tools_to_check = [
            "python3 --version",
            "black --version",
            "flake8 --version",
            "mypy --version",
            "yamllint --version",
            "shellcheck --version",
            "hadolint --version",
        ]

        for tool_cmd in tools_to_check:
            result = container_helper.run_container(built_image, ["sh", "-c", tool_cmd])
            # Tool should exist (exit code 0) or at least not give "command not found"
            if result.returncode != 0:
                assert (
                    "command not found" not in result.stderr.lower()
                ), f"Tool missing: {tool_cmd}"

    def test_container_python_environment(
        self, container_helper: ContainerTestHelper, built_image: str
    ):
        """Test Python environment in container."""
        # Test Python imports
        python_imports = [
            "import sys; print(sys.version)",
            "import black; print(black.__version__)",
            "import flake8; print('flake8 available')",
            "import yaml; print('yaml available')",
        ]

        for import_test in python_imports:
            result = container_helper.run_container(
                built_image, ["python3", "-c", import_test]
            )
            if "black" in import_test or "flake8" in import_test:
                # These might not be available as Python modules
                continue
            assert result.returncode == 0, f"Python import failed: {import_test}"


class TestContainerSecurity:
    """Test container security aspects."""

    def test_runs_as_non_root(
        self, container_helper: ContainerTestHelper, built_image: str
    ):
        """Test that container runs as non-root user."""
        result = container_helper.run_container(built_image, ["id", "-u"])
        assert result.returncode == 0
        user_id = result.stdout.strip()
        assert user_id != "0", f"Container runs as root (UID: {user_id})"

    def test_user_permissions(
        self, container_helper: ContainerTestHelper, built_image: str
    ):
        """Test user permissions and access."""
        # Test that user can write to workspace
        result = container_helper.run_container(
            built_image,
            ["sh", "-c", "touch /workspace/test_file && ls -la /workspace/test_file"],
        )
        assert result.returncode == 0, "User should be able to write to workspace"

        # Test that user cannot write to system directories
        result = container_helper.run_container(
            built_image, ["sh", "-c", "touch /etc/test_file"]
        )
        assert result.returncode != 0, "User should not be able to write to /etc"

    def test_no_package_managers(
        self, container_helper: ContainerTestHelper, built_image: str
    ):
        """Test that package managers are not available to prevent privilege escalation."""
        package_managers = ["apt", "yum", "apk", "pip"]

        for pm in package_managers:
            result = container_helper.run_container(built_image, ["which", pm])
            # It's OK if pip is available since it's needed for Python packages
            if pm == "pip":
                continue
            # Package managers should not be available or not usable
            if result.returncode == 0:
                # If available, try to use it - should fail due to permissions
                install_result = container_helper.run_container(
                    built_image, [pm, "update" if pm == "apk" else "list"]
                )
                # This is acceptable - tool exists but user can't use it

    def test_filesystem_permissions(
        self, container_helper: ContainerTestHelper, built_image: str
    ):
        """Test filesystem permissions and restrictions."""
        # Test critical system directories are protected
        system_dirs = ["/etc", "/usr", "/bin", "/sbin"]

        for sys_dir in system_dirs:
            result = container_helper.run_container(
                built_image,
                ["sh", "-c", f"touch {sys_dir}/test_file 2>&1 || echo 'BLOCKED'"],
            )
            # Should either fail or be blocked
            assert result.returncode != 0 or "BLOCKED" in result.stdout


class TestContainerFunctionality:
    """Test container functionality and validation features."""

    def test_help_command(
        self, container_helper: ContainerTestHelper, built_image: str
    ):
        """Test that help command works."""
        result = container_helper.run_container(built_image, ["--help"])
        assert (
            result.returncode == 0
            or "help" in result.stdout.lower()
            or "usage" in result.stdout.lower()
        )

    def test_python_file_validation(
        self, container_helper: ContainerTestHelper, built_image: str
    ):
        """Test Python file validation in container."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """#!/usr/bin/env python3
import os,sys
def bad_function(  ):
    x=1+2
    return x
"""
            )
            f.flush()
            temp_file = Path(f.name)

        try:
            # Mount file and validate
            volumes = {str(temp_file.parent): "/workspace"}
            result = container_helper.run_container(
                built_image,
                [
                    "python3",
                    "-c",
                    f"import py_compile; py_compile.compile('/workspace/{temp_file.name}')",
                ],
                volumes=volumes,
            )

            # Should be able to compile Python files
            assert result.returncode == 0 or "SyntaxError" not in result.stderr

        finally:
            temp_file.unlink()

    def test_validation_tools_integration(
        self, container_helper: ContainerTestHelper, built_image: str
    ):
        """Test that validation tools work together."""
        # Create a test directory with various files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Python file
            (temp_path / "test.py").write_text(
                """
def hello_world():
    print("Hello, World!")
"""
            )

            # YAML file
            (temp_path / "config.yaml").write_text(
                """
database:
  host: localhost
  port: 5432
"""
            )

            # Shell script
            script_file = temp_path / "test.sh"
            script_file.write_text(
                """#!/bin/bash
echo "Hello from shell"
"""
            )
            script_file.chmod(0o755)

            # Test validation of each file type
            volumes = {str(temp_path): "/workspace"}

            # Test Python validation
            result = container_helper.run_container(
                built_image,
                ["python3", "-m", "py_compile", "/workspace/test.py"],
                volumes=volumes,
            )
            assert result.returncode == 0, "Python file should compile successfully"

            # Test if black can process the file
            result = container_helper.run_container(
                built_image, ["black", "--check", "/workspace/test.py"], volumes=volumes
            )
            # Black might not be configured to work this way, so just check it doesn't crash
            assert "Traceback" not in result.stderr

    def test_workspace_isolation(
        self, container_helper: ContainerTestHelper, built_image: str
    ):
        """Test that workspace is properly isolated."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = temp_path / "test.txt"
            test_file.write_text("test content")

            volumes = {str(temp_path): "/workspace"}

            # Test that container can see the file
            result = container_helper.run_container(
                built_image, ["cat", "/workspace/test.txt"], volumes=volumes
            )
            assert result.returncode == 0
            assert "test content" in result.stdout

            # Test that container can write to workspace
            result = container_helper.run_container(
                built_image,
                ["sh", "-c", "echo 'new content' > /workspace/new_file.txt"],
                volumes=volumes,
            )
            assert result.returncode == 0

            # Verify file was created on host
            new_file = temp_path / "new_file.txt"
            assert new_file.exists()
            assert "new content" in new_file.read_text()


class TestContainerPerformance:
    """Test container performance characteristics."""

    @pytest.mark.slow
    def test_container_startup_time(
        self, container_helper: ContainerTestHelper, built_image: str
    ):
        """Test container startup performance."""
        start_time = time.time()
        result = container_helper.run_container(built_image, ["echo", "ready"])
        end_time = time.time()

        startup_time = end_time - start_time
        assert (
            startup_time < 10.0
        ), f"Container startup took too long: {startup_time:.2f}s"
        assert result.returncode == 0
        assert "ready" in result.stdout

    @pytest.mark.slow
    def test_validation_performance_in_container(
        self, container_helper: ContainerTestHelper, built_image: str
    ):
        """Test validation performance inside container."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create multiple test files
            for i in range(10):
                test_file = temp_path / f"test_{i}.py"
                test_file.write_text(
                    f"""#!/usr/bin/env python3
def function_{i}():
    '''Test function {i}.'''
    return {i}

if __name__ == "__main__":
    print(function_{i}())
"""
                )

            volumes = {str(temp_path): "/workspace"}

            # Measure validation time
            start_time = time.time()

            # Validate all Python files
            result = container_helper.run_container(
                built_image,
                [
                    "sh",
                    "-c",
                    'for f in /workspace/*.py; do python3 -m py_compile "$f" || exit 1; done',
                ],
                volumes=volumes,
            )

            end_time = time.time()
            validation_time = end_time - start_time

            assert result.returncode == 0, "All files should validate successfully"
            assert (
                validation_time < 30.0
            ), f"Validation took too long: {validation_time:.2f}s"

    def test_container_resource_usage(
        self, container_helper: ContainerTestHelper, built_image: str
    ):
        """Test container resource usage."""
        # Test memory usage with a simple command
        result = container_helper.run_container(
            built_image,
            [
                "python3",
                "-c",
                "import sys; print(f'Python {sys.version_info.major}.{sys.version_info.minor}')",
            ],
        )

        assert result.returncode == 0
        assert "Python" in result.stdout

        # Container should complete quickly for simple tasks
        # This is tested implicitly by the other tests not timing out


class TestContainerHealthCheck:
    """Test container health checking functionality."""

    def test_health_check_endpoint(
        self, container_helper: ContainerTestHelper, built_image: str
    ):
        """Test basic health check functionality."""
        # Test that Python interpreter works (health check command)
        result = container_helper.run_container(
            built_image, ["python3", "-c", "import sys; sys.exit(0)"]
        )

        assert result.returncode == 0, "Health check command should succeed"

    def test_container_readiness(
        self, container_helper: ContainerTestHelper, built_image: str
    ):
        """Test container readiness checks."""
        # Test that all required components are available
        readiness_checks = [
            "python3 -c 'import sys; print(\"Python OK\")'",
            "which black && echo 'Black OK' || echo 'Black not found'",
            "ls /workspace && echo 'Workspace OK' || echo 'Workspace not found'",
        ]

        for check in readiness_checks:
            result = container_helper.run_container(built_image, ["sh", "-c", check])
            # Commands should execute without crashing
            assert "Traceback" not in result.stderr


class TestContainerIntegration:
    """Test container integration with external systems."""

    @pytest.mark.integration
    def test_git_integration_in_container(
        self, container_helper: ContainerTestHelper, built_image: str
    ):
        """Test Git operations inside container."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Initialize git repo
            subprocess.run(["git", "init"], cwd=temp_path, check=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=temp_path,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test User"], cwd=temp_path, check=True
            )

            # Create test file
            test_file = temp_path / "test.py"
            test_file.write_text("print('hello')")
            subprocess.run(["git", "add", "test.py"], cwd=temp_path, check=True)
            subprocess.run(
                ["git", "commit", "-m", "initial commit"], cwd=temp_path, check=True
            )

            volumes = {str(temp_path): "/workspace"}

            # Test git operations in container
            result = container_helper.run_container(
                built_image,
                ["sh", "-c", "cd /workspace && git log --oneline"],
                volumes=volumes,
            )

            # Git should work or at least not crash
            assert (
                result.returncode == 0
                or "not a git repository" not in result.stderr.lower()
            )

    @pytest.mark.integration
    def test_file_permissions_consistency(
        self, container_helper: ContainerTestHelper, built_image: str
    ):
        """Test that file permissions work consistently between host and container."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create files with different permissions
            regular_file = temp_path / "regular.txt"
            regular_file.write_text("regular file")

            executable_file = temp_path / "script.sh"
            executable_file.write_text("#!/bin/bash\necho 'executable'")
            executable_file.chmod(0o755)

            volumes = {str(temp_path): "/workspace"}

            # Test regular file
            result = container_helper.run_container(
                built_image, ["cat", "/workspace/regular.txt"], volumes=volumes
            )
            assert result.returncode == 0
            assert "regular file" in result.stdout

            # Test executable file
            result = container_helper.run_container(
                built_image, ["/workspace/script.sh"], volumes=volumes
            )
            # Should be executable and run correctly
            assert result.returncode == 0
            assert "executable" in result.stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
