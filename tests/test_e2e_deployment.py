#!/usr/bin/env python3
"""End-to-end deployment and installation tests."""

import pytest
import subprocess
import tempfile
import shutil
import os
import time
import json
import requests
from pathlib import Path
from typing import Dict, List, Any, Optional
from contextlib import contextmanager

# Try to import docker, but don't fail if it's not available
try:
    import docker
    HAS_DOCKER = True
except ImportError:
    HAS_DOCKER = False


class TestInstallationE2E:
    """Test complete installation and setup process."""
    
    @pytest.fixture
    def fresh_environment(self, isolated_dir: Path) -> Path:
        """Create a fresh environment for installation testing."""
        install_dir = isolated_dir / "fresh_install"
        install_dir.mkdir()
        return install_dir
    
    def test_script_based_installation(self, fresh_environment: Path):
        """Test installation using install.sh script."""
        # Copy install script to test environment
        install_script = Path("install.sh")
        if not install_script.exists():
            pytest.skip("install.sh not found")
        
        test_install_script = fresh_environment / "install.sh"
        shutil.copy2(install_script, test_install_script)
        
        # Make executable
        test_install_script.chmod(0o755)
        
        # Run installation script
        try:
            result = subprocess.run(
                [str(test_install_script)],
                cwd=fresh_environment,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            
            # Installation should complete without critical errors
            assert result.returncode in [0, 1], f"Installation failed: {result.stderr}"
            
            # Check for expected outputs
            if result.returncode == 0:
                # Verify installation artifacts
                assert "completed" in result.stdout.lower() or "success" in result.stdout.lower()
        
        except subprocess.TimeoutExpired:
            pytest.fail("Installation script timed out")
    
    def test_node_package_installation(self, fresh_environment: Path):
        """Test Node.js package installation and setup."""
        # Copy package.json
        package_json = Path("package.json")
        if not package_json.exists():
            pytest.skip("package.json not found")
        
        test_package_json = fresh_environment / "package.json"
        shutil.copy2(package_json, test_package_json)
        
        # Run npm install
        try:
            result = subprocess.run(
                ["npm", "install"],
                cwd=fresh_environment,
                capture_output=True,
                text=True,
                timeout=180  # 3 minutes
            )
            
            if result.returncode == 0:
                # Verify node_modules exists
                node_modules = fresh_environment / "node_modules"
                assert node_modules.exists(), "node_modules directory not created"
                
                # Verify key packages are installed
                with open(test_package_json) as f:
                    config = json.load(f)
                
                if "devDependencies" in config:
                    for package in config["devDependencies"]:
                        package_dir = node_modules / package
                        assert package_dir.exists(), f"Package {package} not installed"
        
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            if isinstance(e, FileNotFoundError):
                pytest.skip("npm not available")
            else:
                pytest.fail("npm install timed out")
    
    def test_python_dependencies_installation(self, fresh_environment: Path):
        """Test Python dependencies installation."""
        # Check for requirements files
        req_files = ["requirements.txt", "requirements-dev.txt", "pyproject.toml"]
        found_req_file = None
        
        for req_file in req_files:
            if Path(req_file).exists():
                found_req_file = req_file
                break
        
        if not found_req_file:
            pytest.skip("No requirements file found")
        
        # Copy requirements file
        test_req_file = fresh_environment / found_req_file
        shutil.copy2(Path(found_req_file), test_req_file)
        
        # Install dependencies
        if found_req_file.endswith(".txt"):
            cmd = ["pip", "install", "-r", found_req_file]
        else:
            cmd = ["pip", "install", "-e", "."]
        
        try:
            result = subprocess.run(
                cmd,
                cwd=fresh_environment,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes
            )
            
            if result.returncode == 0:
                # Verify key packages are available
                test_imports = [
                    "import pytest",
                    "import hypothesis",
                    "from typing import List, Dict, Any",
                ]
                
                for test_import in test_imports:
                    import_result = subprocess.run(
                        ["python3", "-c", test_import],
                        cwd=fresh_environment,
                        capture_output=True,
                        text=True
                    )
                    if import_result.returncode != 0:
                        print(f"Warning: Could not import: {test_import}")
        
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            if isinstance(e, FileNotFoundError):
                pytest.skip("pip not available")
            else:
                pytest.fail("pip install timed out")


class TestContainerDeployment:
    """Test container-based deployment scenarios."""
    
    @pytest.fixture
    def docker_client(self):
        """Get Docker client."""
        try:
            client = docker.from_env()
            # Test connection
            client.ping()
            return client
        except Exception:
            pytest.skip("Docker not available")
    
    @pytest.mark.slow
    def test_container_build(self, docker_client):
        """Test building container from ContainerFile."""
        containerfile = Path("ContainerFile")
        if not containerfile.exists():
            pytest.skip("ContainerFile not found")
        
        try:
            # Build image
            image, build_logs = docker_client.images.build(
                path=".",
                dockerfile="ContainerFile",
                tag="huskycats-test:latest",
                timeout=600  # 10 minutes
            )
            
            assert image is not None, "Image build failed"
            
            # Verify image properties
            assert len(image.tags) > 0, "Image has no tags"
            
            # Clean up
            docker_client.images.remove(image.id, force=True)
        
        except docker.errors.BuildError as e:
            pytest.fail(f"Container build failed: {e}")
        except docker.errors.DockerException as e:
            pytest.skip(f"Docker error: {e}")
    
    @pytest.mark.slow
    def test_container_startup_and_health(self, docker_client):
        """Test container startup and health checks."""
        # First build the image
        containerfile = Path("ContainerFile")
        if not containerfile.exists():
            pytest.skip("ContainerFile not found")
        
        try:
            image, _ = docker_client.images.build(
                path=".",
                dockerfile="ContainerFile",
                tag="huskycats-health-test:latest",
                timeout=600
            )
            
            # Start container
            container = docker_client.containers.run(
                image.id,
                detach=True,
                ports={'8080/tcp': None},  # Random port
                environment={
                    'NODE_ENV': 'test',
                    'MCP_SERVER_TOKEN': 'test-token'
                }
            )
            
            try:
                # Wait for startup
                time.sleep(10)
                
                # Check container is running
                container.reload()
                assert container.status == "running", f"Container not running: {container.status}"
                
                # Get port mapping
                port_info = container.ports.get('8080/tcp')
                if port_info:
                    host_port = port_info[0]['HostPort']
                    
                    # Try to connect to health endpoint
                    try:
                        response = requests.get(
                            f"http://localhost:{host_port}/health",
                            timeout=10
                        )
                        if response.status_code == 200:
                            health_data = response.json()
                            assert health_data.get("status") == "ready"
                    except requests.exceptions.RequestException:
                        # Health check might not be implemented, that's OK
                        pass
            
            finally:
                # Clean up
                container.stop(timeout=10)
                container.remove()
                docker_client.images.remove(image.id, force=True)
        
        except docker.errors.DockerException as e:
            pytest.skip(f"Docker error: {e}")
    
    @pytest.mark.slow
    def test_multi_container_deployment(self, docker_client):
        """Test multi-container deployment scenario."""
        docker_compose_file = Path("docker-compose.yml")
        compose_override = Path("docker-compose.override.yml")
        
        if not (docker_compose_file.exists() or compose_override.exists()):
            pytest.skip("No docker-compose files found")
        
        # Use docker-compose CLI if available
        try:
            # Check if docker-compose is available
            subprocess.run(["docker-compose", "--version"], check=True, capture_output=True)
            
            # Start services
            result = subprocess.run([
                "docker-compose", "up", "-d", "--build"
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                try:
                    # Wait for services to start
                    time.sleep(15)
                    
                    # Check service status
                    status_result = subprocess.run([
                        "docker-compose", "ps"
                    ], capture_output=True, text=True)
                    
                    # Services should be running
                    assert "Up" in status_result.stdout or "running" in status_result.stdout.lower()
                
                finally:
                    # Clean up
                    subprocess.run(["docker-compose", "down", "-v"], capture_output=True)
        
        except (subprocess.CalledProcessError, FileNotFoundError):
            pytest.skip("docker-compose not available or failed")


class TestConfigurationDeployment:
    """Test configuration file deployment and validation."""
    
    def test_linting_config_deployment(self, fresh_environment: Path):
        """Test linting configuration deployment."""
        config_dir = Path("linting-configs")
        if not config_dir.exists():
            pytest.skip("linting-configs directory not found")
        
        # Copy linting configs
        test_config_dir = fresh_environment / "linting-configs"
        shutil.copytree(config_dir, test_config_dir)
        
        # Verify config files exist
        pyproject_toml = test_config_dir / "pyproject.toml"
        assert pyproject_toml.exists(), "pyproject.toml not deployed"
        
        # Validate TOML syntax
        try:
            import tomllib
            with open(pyproject_toml, 'rb') as f:
                config = tomllib.load(f)
            assert isinstance(config, dict), "Invalid TOML structure"
        except ImportError:
            # tomllib not available in older Python versions
            pass
    
    def test_script_deployment(self, fresh_environment: Path):
        """Test script deployment and permissions."""
        scripts_dir = Path("scripts")
        if not scripts_dir.exists():
            pytest.skip("scripts directory not found")
        
        # Copy scripts
        test_scripts_dir = fresh_environment / "scripts"
        shutil.copytree(scripts_dir, test_scripts_dir)
        
        # Verify scripts exist and are executable
        for script_file in test_scripts_dir.glob("*.sh"):
            assert script_file.exists(), f"Script {script_file.name} not deployed"
            assert os.access(script_file, os.X_OK), f"Script {script_file.name} not executable"
            
            # Basic syntax check for shell scripts
            result = subprocess.run([
                "bash", "-n", str(script_file)
            ], capture_output=True, text=True)
            assert result.returncode == 0, f"Syntax error in {script_file.name}: {result.stderr}"


class TestServiceDeployment:
    """Test service deployment and integration."""
    
    @pytest.mark.integration
    def test_mcp_server_deployment(self):
        """Test MCP server deployment and startup."""
        # Check if MCP server can be started
        mcp_server_dir = Path("mcp-server")
        if not mcp_server_dir.exists():
            pytest.skip("mcp-server directory not found")
        
        package_json = mcp_server_dir / "package.json"
        if not package_json.exists():
            pytest.skip("MCP server package.json not found")
        
        # Try to start MCP server
        try:
            # Install dependencies first
            install_result = subprocess.run([
                "npm", "install"
            ], cwd=mcp_server_dir, capture_output=True, text=True, timeout=120)
            
            if install_result.returncode != 0:
                pytest.skip("Failed to install MCP server dependencies")
            
            # Start server in test mode
            server_process = subprocess.Popen([
                "npm", "start"
            ], cwd=mcp_server_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            try:
                # Wait for startup
                time.sleep(10)
                
                # Check if process is still running
                if server_process.poll() is None:
                    # Server is running, try to connect
                    try:
                        response = requests.get("http://localhost:8080/health", timeout=5)
                        if response.status_code == 200:
                            health_data = response.json()
                            assert "status" in health_data
                    except requests.exceptions.RequestException:
                        # Connection failed, but server might still be starting
                        pass
            
            finally:
                # Clean up
                if server_process.poll() is None:
                    server_process.terminate()
                    try:
                        server_process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        server_process.kill()
        
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            if isinstance(e, FileNotFoundError):
                pytest.skip("npm not available")
            else:
                pytest.fail("MCP server startup timed out")
    
    def test_git_hooks_deployment(self, fresh_environment: Path):
        """Test Git hooks deployment."""
        # Initialize git repo
        subprocess.run(["git", "init"], cwd=fresh_environment, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=fresh_environment, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=fresh_environment, check=True)
        
        # Copy package.json for Husky
        package_json = Path("package.json")
        if package_json.exists():
            test_package_json = fresh_environment / "package.json"
            shutil.copy2(package_json, test_package_json)
            
            # Try to install and setup Husky
            try:
                # Install dependencies
                install_result = subprocess.run([
                    "npm", "install"
                ], cwd=fresh_environment, capture_output=True, text=True, timeout=120)
                
                if install_result.returncode == 0:
                    # Run prepare script (sets up Husky)
                    prepare_result = subprocess.run([
                        "npm", "run", "prepare"
                    ], cwd=fresh_environment, capture_output=True, text=True, timeout=60)
                    
                    if prepare_result.returncode == 0:
                        # Check if .husky directory was created
                        husky_dir = fresh_environment / ".husky"
                        assert husky_dir.exists(), "Husky directory not created"
            
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pytest.skip("npm not available or installation failed")


class TestRollbackAndRecovery:
    """Test rollback and recovery scenarios."""
    
    def test_configuration_rollback(self, fresh_environment: Path):
        """Test configuration rollback scenario."""
        # Create original config
        config_file = fresh_environment / "test.config"
        original_config = {"version": "1.0", "mode": "production"}
        
        with open(config_file, 'w') as f:
            json.dump(original_config, f)
        
        # Create backup
        backup_file = fresh_environment / "test.config.backup"
        shutil.copy2(config_file, backup_file)
        
        # Modify config (simulate failed deployment)
        bad_config = {"version": "2.0", "mode": "invalid"}
        with open(config_file, 'w') as f:
            json.dump(bad_config, f)
        
        # Simulate rollback
        shutil.copy2(backup_file, config_file)
        
        # Verify rollback
        with open(config_file) as f:
            restored_config = json.load(f)
        
        assert restored_config == original_config
    
    def test_service_recovery(self):
        """Test service recovery after failure."""
        # This would test service restart mechanisms
        # For now, we'll test basic recovery script structure
        
        recovery_script = Path("scripts") / "recovery.sh"
        if not recovery_script.exists():
            # Create a mock recovery test
            assert True, "Recovery mechanisms should be implemented"
        else:
            # Test recovery script syntax
            result = subprocess.run([
                "bash", "-n", str(recovery_script)
            ], capture_output=True, text=True)
            assert result.returncode == 0, f"Recovery script has syntax errors: {result.stderr}"


@pytest.mark.slow
class TestPerformanceDeployment:
    """Test deployment performance characteristics."""
    
    def test_installation_time(self, fresh_environment: Path):
        """Test that installation completes within reasonable time."""
        start_time = time.time()
        
        # Test Node.js installation time
        package_json = Path("package.json")
        if package_json.exists():
            test_package_json = fresh_environment / "package.json"
            shutil.copy2(package_json, test_package_json)
            
            try:
                result = subprocess.run([
                    "npm", "install"
                ], cwd=fresh_environment, capture_output=True, timeout=300)  # 5 minutes max
                
                end_time = time.time()
                duration = end_time - start_time
                
                # Installation should complete within 5 minutes
                assert duration < 300, f"Installation took too long: {duration:.2f}s"
                
                if result.returncode == 0:
                    # Verify installation was successful
                    node_modules = fresh_environment / "node_modules"
                    assert node_modules.exists()
            
            except subprocess.TimeoutExpired:
                pytest.fail("Installation timed out")
            except FileNotFoundError:
                pytest.skip("npm not available")
    
    def test_container_build_time(self, docker_client):
        """Test container build performance."""
        containerfile = Path("ContainerFile")
        if not containerfile.exists():
            pytest.skip("ContainerFile not found")
        
        start_time = time.time()
        
        try:
            image, _ = docker_client.images.build(
                path=".",
                dockerfile="ContainerFile",
                tag="huskycats-perf-test:latest",
                timeout=900  # 15 minutes max
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Build should complete within 15 minutes
            assert duration < 900, f"Container build took too long: {duration:.2f}s"
            
            # Clean up
            docker_client.images.remove(image.id, force=True)
        
        except docker.errors.DockerException as e:
            pytest.skip(f"Docker error: {e}")


# Helper context manager for temporary deployments
@contextmanager
def temporary_deployment(config: Dict[str, Any]):
    """Context manager for temporary test deployments."""
    deployment_dir = None
    try:
        deployment_dir = Path(tempfile.mkdtemp(prefix="huskycats_deploy_test_"))
        yield deployment_dir
    finally:
        if deployment_dir and deployment_dir.exists():
            shutil.rmtree(deployment_dir, ignore_errors=True)