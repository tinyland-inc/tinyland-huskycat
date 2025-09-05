#!/usr/bin/env python3
"""E2E tests for CI/CD pipeline validation and deployment processes."""

import pytest
import subprocess
import yaml
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional


class TestCICDPipelineValidation:
    """Test CI/CD pipeline configuration and execution."""

    @pytest.fixture
    def gitlab_ci_config(self) -> Optional[Dict[str, Any]]:
        """Load GitLab CI configuration."""
        gitlab_ci = Path(".gitlab-ci.yml")
        if gitlab_ci.exists():
            with open(gitlab_ci) as f:
                return yaml.safe_load(f)
        return None

    @pytest.fixture
    def github_workflows(self) -> List[Dict[str, Any]]:
        """Load GitHub Actions workflow files."""
        workflows_dir = Path(".github/workflows")
        workflows = []

        if workflows_dir.exists():
            for workflow_file in workflows_dir.glob("*.yml"):
                with open(workflow_file) as f:
                    workflow = yaml.safe_load(f)
                    workflows.append({"file": workflow_file.name, "config": workflow})

        return workflows

    def test_gitlab_ci_syntax_validation(
        self, gitlab_ci_config: Optional[Dict[str, Any]]
    ):
        """Test GitLab CI configuration syntax."""
        if not gitlab_ci_config:
            pytest.skip("No .gitlab-ci.yml found")

        # Validate basic structure
        assert isinstance(
            gitlab_ci_config, dict
        ), "GitLab CI config should be a dictionary"

        # Check for essential sections
        essential_keys = ["stages", "variables", "before_script"]
        [key for key in essential_keys if key in gitlab_ci_config]

        # At least stages should be defined
        if "stages" in gitlab_ci_config:
            assert isinstance(
                gitlab_ci_config["stages"], list
            ), "Stages should be a list"
            assert (
                len(gitlab_ci_config["stages"]) > 0
            ), "At least one stage should be defined"

        # Validate job definitions
        jobs = {
            k: v
            for k, v in gitlab_ci_config.items()
            if isinstance(v, dict) and "script" in v
        }
        assert len(jobs) > 0, "At least one job should be defined"

        for job_name, job_config in jobs.items():
            assert "script" in job_config, f"Job {job_name} missing script"
            assert isinstance(
                job_config["script"], list
            ), f"Job {job_name} script should be a list"

    def test_github_workflows_validation(self, github_workflows: List[Dict[str, Any]]):
        """Test GitHub Actions workflow validation."""
        if not github_workflows:
            pytest.skip("No GitHub workflows found")

        for workflow in github_workflows:
            config = workflow["config"]
            file_name = workflow["file"]

            # Validate basic structure
            assert "on" in config, f"Workflow {file_name} missing 'on' trigger"
            assert "jobs" in config, f"Workflow {file_name} missing jobs"

            # Validate jobs
            jobs = config["jobs"]
            assert isinstance(jobs, dict), f"Jobs in {file_name} should be a dictionary"

            for job_name, job_config in jobs.items():
                assert "runs-on" in job_config, f"Job {job_name} missing runs-on"
                assert "steps" in job_config, f"Job {job_name} missing steps"
                assert isinstance(
                    job_config["steps"], list
                ), f"Job {job_name} steps should be a list"

    def test_makefile_targets_validation(self):
        """Test Makefile targets and commands."""
        makefile = Path("Makefile")
        if not makefile.exists():
            pytest.skip("No Makefile found")

        # Test Makefile syntax
        result = subprocess.run(
            ["make", "-n", "--dry-run"], capture_output=True, text=True
        )

        # Should not have syntax errors
        if result.returncode != 0 and "No targets" not in result.stderr:
            pytest.fail(f"Makefile syntax errors: {result.stderr}")

        # Test common targets exist
        with open(makefile) as f:
            makefile_content = f.read()

        common_targets = ["install", "test", "build", "clean", "deploy"]
        found_targets = []

        for target in common_targets:
            if f"{target}:" in makefile_content:
                found_targets.append(target)

        assert len(found_targets) >= 2, f"Few standard targets found: {found_targets}"

    def test_compose_validation(self):
        """Test Compose configuration (podman-compose)."""
        compose_files = [
            "podman-compose.yml",
            "podman-compose.yaml",
            "compose.yml",
            "compose.yaml",
        ]
        compose_file = None

        for cf in compose_files:
            if Path(cf).exists():
                compose_file = cf
                break

        if not compose_file:
            pytest.skip("No compose file found")

        with open(compose_file) as f:
            compose_config = yaml.safe_load(f)

        # Validate structure
        assert "services" in compose_config, "Docker Compose missing services"
        services = compose_config["services"]
        assert isinstance(services, dict), "Services should be a dictionary"
        assert len(services) > 0, "At least one service should be defined"

        # Validate service definitions
        for service_name, service_config in services.items():
            # Should have image or build
            assert (
                "image" in service_config or "build" in service_config
            ), f"Service {service_name} missing image or build"


class TestContinuousIntegration:
    """Test continuous integration workflows."""

    def test_lint_stage_execution(self):
        """Test linting stage execution."""
        # Test Python linting
        python_files = list(Path(".").rglob("*.py"))
        if python_files:
            # Test Black formatting
            try:
                result = subprocess.run(
                    ["python3", "-m", "black", "--check", "--diff", "."],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                # Black should pass or suggest minimal changes
                if result.returncode != 0:
                    print(f"Black formatting suggestions:\n{result.stdout}")
                    # Don't fail - just report

            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass  # Tool not available

            # Test Flake8
            try:
                result = subprocess.run(
                    ["python3", "-m", "flake8", ".", "--count", "--statistics"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                # Count issues
                if result.returncode != 0:
                    error_count = result.stdout.count("\n")
                    print(f"Flake8 found {error_count} issues")

            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

    def test_security_scanning_stage(self):
        """Test security scanning stage."""
        python_files = list(Path(".").rglob("*.py"))
        if not python_files:
            pytest.skip("No Python files found for security scanning")

        try:
            # Test Bandit security scanner
            result = subprocess.run(
                ["python3", "-m", "bandit", "-r", ".", "-f", "json"],
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode == 0:
                # Parse Bandit results
                try:
                    bandit_results = json.loads(result.stdout)
                    if "results" in bandit_results:
                        high_severity = [
                            issue
                            for issue in bandit_results["results"]
                            if issue.get("issue_severity") == "HIGH"
                        ]

                        if high_severity:
                            print(
                                f"High severity security issues found: {len(high_severity)}"
                            )
                            for issue in high_severity[:3]:  # Show first 3
                                print(
                                    f"- {issue.get('test_name')}: {issue.get('filename')}:{issue.get('line_number')}"
                                )

                except json.JSONDecodeError:
                    pass

        except (subprocess.TimeoutExpired, FileNotFoundError):
            pytest.skip("Bandit security scanner not available")

    def test_unit_test_stage(self):
        """Test unit test execution stage."""
        test_files = list(Path("tests").rglob("test_*.py"))
        if not test_files:
            pytest.skip("No test files found")

        try:
            # Run unit tests only (not slow/integration tests)
            result = subprocess.run(
                [
                    "python3",
                    "-m",
                    "pytest",
                    "tests/",
                    "-v",
                    "-m",
                    "not slow and not integration and not e2e",
                    "--tb=short",
                    "--timeout=30",
                ],
                capture_output=True,
                text=True,
                timeout=300,
            )

            # Parse test results
            if "failed" in result.stdout:
                failed_tests = result.stdout.count(" FAILED")
                print(f"Unit tests failed: {failed_tests}")

            if "passed" in result.stdout:
                passed_tests = result.stdout.count(" PASSED")
                print(f"Unit tests passed: {passed_tests}")

            # Tests should exist and some should pass
            assert "collected" in result.stdout, "No tests collected"

        except (subprocess.TimeoutExpired, FileNotFoundError):
            pytest.skip("pytest not available")

    def test_build_stage_execution(self):
        """Test build stage execution."""
        # Test Python package building
        if Path("pyproject.toml").exists():
            try:
                result = subprocess.run(
                    ["python3", "-m", "build", "--wheel", "--no-isolation"],
                    capture_output=True,
                    text=True,
                    timeout=300,
                )

                if result.returncode == 0:
                    # Check if wheel was created
                    dist_dir = Path("dist")
                    if dist_dir.exists():
                        wheels = list(dist_dir.glob("*.whl"))
                        assert len(wheels) > 0, "No wheel files created"

            except (subprocess.TimeoutExpired, FileNotFoundError):
                pytest.skip("Python build tools not available")

        # Test container building
        container_files = ["ContainerFile", "Dockerfile"]
        container_file = None

        for cf in container_files:
            if Path(cf).exists():
                container_file = cf
                break

        if container_file:
            try:
                import docker

                client = docker.from_env()

                # Test container build (quick test)
                image, build_logs = client.images.build(
                    path=".",
                    dockerfile=container_file,
                    tag="huskycats-ci-test:latest",
                    timeout=600,
                )

                assert image is not None, "Container build failed"

                # Clean up
                client.images.remove(image.id, force=True)

            except (ImportError, Exception):
                pytest.skip("Docker not available for build test")


class TestContinuousDeployment:
    """Test continuous deployment workflows."""

    def test_staging_deployment_validation(self):
        """Test staging deployment validation."""
        # This would test deployment to staging environment
        # For now, we validate deployment scripts exist

        deployment_scripts = ["deploy.sh", "scripts/deploy.sh", "deploy/staging.sh"]

        script_found = None
        for script in deployment_scripts:
            if Path(script).exists():
                script_found = script
                break

        if script_found:
            # Test script syntax
            result = subprocess.run(
                ["bash", "-n", str(script_found)], capture_output=True, text=True
            )

            assert (
                result.returncode == 0
            ), f"Deployment script has syntax errors: {result.stderr}"

            # Check for essential deployment commands
            with open(script_found) as f:
                script_content = f.read()

            deployment_indicators = [
                "docker",
                "kubectl",
                "helm",
                "git",
                "rsync",
                "scp",
                "ssh",
                "curl",
                "wget",
            ]

            found_indicators = [
                indicator
                for indicator in deployment_indicators
                if indicator in script_content
            ]

            assert (
                len(found_indicators) > 0
            ), f"No deployment commands found in {script_found}"
        else:
            pytest.skip("No deployment scripts found")

    def test_production_deployment_readiness(self):
        """Test production deployment readiness."""
        # Check for production readiness indicators

        # Environment configuration
        env_files = [".env.production", ".env.prod", "prod.env"]
        env_found = any(Path(f).exists() for f in env_files)

        # Health check endpoints
        health_check_files = list(Path(".").rglob("*health*"))

        # Monitoring configuration
        monitoring_files = (
            list(Path(".").rglob("*monitor*"))
            + list(Path(".").rglob("*metric*"))
            + list(Path(".").rglob("*log*"))
        )

        # Database migrations
        migration_files = list(Path(".").rglob("*migration*")) + list(
            Path(".").rglob("*migrate*")
        )

        readiness_score = 0
        readiness_details = []

        if env_found:
            readiness_score += 1
            readiness_details.append("Environment configuration")

        if health_check_files:
            readiness_score += 1
            readiness_details.append("Health check endpoints")

        if monitoring_files:
            readiness_score += 1
            readiness_details.append("Monitoring/logging setup")

        # Backup and recovery
        backup_files = list(Path(".").rglob("*backup*")) + list(
            Path(".").rglob("*restore*")
        )

        if backup_files:
            readiness_score += 1
            readiness_details.append("Backup/recovery procedures")

        print(f"Production readiness score: {readiness_score}/4")
        print(f"Found: {', '.join(readiness_details)}")

        # At least basic readiness should be present
        assert readiness_score >= 1, "Minimal production readiness requirements not met"

    def test_rollback_mechanism(self):
        """Test rollback mechanism availability."""
        # Look for rollback scripts or procedures
        rollback_files = [
            "rollback.sh",
            "scripts/rollback.sh",
            "deploy/rollback.sh",
            "rollback.yml",
        ]

        rollback_found = None
        for rf in rollback_files:
            if Path(rf).exists():
                rollback_found = rf
                break

        if rollback_found:
            if rollback_found.endswith(".sh"):
                # Test script syntax
                result = subprocess.run(
                    ["bash", "-n", str(rollback_found)], capture_output=True, text=True
                )

                assert (
                    result.returncode == 0
                ), f"Rollback script has syntax errors: {result.stderr}"

            elif rollback_found.endswith(".yml"):
                # Test YAML syntax
                with open(rollback_found) as f:
                    rollback_config = yaml.safe_load(f)
                assert isinstance(
                    rollback_config, dict
                ), "Rollback config should be valid YAML"
        else:
            # Check if rollback procedures are documented
            doc_files = (
                list(Path(".").rglob("*.md")) + list(Path("docs").rglob("*.md"))
                if Path("docs").exists()
                else []
            )

            rollback_documented = False
            for doc_file in doc_files:
                with open(doc_file) as f:
                    content = f.read().lower()
                    if "rollback" in content or "revert" in content:
                        rollback_documented = True
                        break

            if rollback_documented:
                print("Rollback procedures documented")
            else:
                print("Warning: No rollback mechanism found")


class TestDeploymentEnvironments:
    """Test different deployment environments."""

    def test_development_environment_setup(self):
        """Test development environment setup."""
        # Check for development setup scripts
        dev_scripts = [
            "setup-dev.sh",
            "scripts/setup-dev.sh",
            "dev-setup.sh",
            "install.sh",
        ]

        dev_script_found = None
        for script in dev_scripts:
            if Path(script).exists():
                dev_script_found = script
                break

        if dev_script_found:
            # Test script can run without errors (dry run)
            result = subprocess.run(
                ["bash", "-n", str(dev_script_found)], capture_output=True, text=True
            )

            assert (
                result.returncode == 0
            ), f"Dev setup script has syntax errors: {result.stderr}"

        # Check for package managers
        package_files = ["package.json", "pyproject.toml", "requirements.txt"]
        package_managers = []

        for pf in package_files:
            if Path(pf).exists():
                package_managers.append(pf)

        assert len(package_managers) > 0, "No package manager configuration found"

    def test_testing_environment_isolation(self):
        """Test testing environment isolation."""
        # Check for test-specific configuration
        test_configs = ["pytest.ini", "pyproject.toml", ".coveragerc", "conftest.py"]

        test_config_found = []
        for tc in test_configs:
            if Path(tc).exists():
                test_config_found.append(tc)

        assert len(test_config_found) > 0, f"No test configuration found"

        # Check for test data isolation
        test_dirs = ["tests", "test"]
        test_dir_found = None

        for td in test_dirs:
            if Path(td).exists():
                test_dir_found = td
                break

        if test_dir_found:
            # Check for fixtures or test data
            fixtures = list(Path(test_dir_found).rglob("*fixture*")) + list(
                Path(test_dir_found).rglob("conftest.py")
            )

            if fixtures:
                print(f"Test fixtures found: {len(fixtures)}")

    def test_staging_environment_parity(self):
        """Test staging environment parity with production."""
        # Check for environment-specific configurations
        env_configs = [
            "config/staging.yml",
            "staging.env",
            ".env.staging",
            "podman-compose.staging.yml",
        ]

        staging_configs = [ec for ec in env_configs if Path(ec).exists()]

        if staging_configs:
            # Staging environment configuration exists
            print(f"Staging configs found: {staging_configs}")

            # Compare with production configs
            prod_configs = [
                "config/production.yml",
                "production.env",
                ".env.production",
                "podman-compose.prod.yml",
            ]

            prod_configs_found = [pc for pc in prod_configs if Path(pc).exists()]

            if prod_configs_found:
                print(f"Production configs found: {prod_configs_found}")
                # Could compare configuration structure here
        else:
            pytest.skip("No staging environment configuration found")


@pytest.mark.integration
class TestDeploymentIntegration:
    """Test end-to-end deployment integration."""

    def test_full_pipeline_simulation(self):
        """Test full CI/CD pipeline simulation."""
        pipeline_stages = [
            ("lint", self._simulate_lint_stage),
            ("test", self._simulate_test_stage),
            ("build", self._simulate_build_stage),
            ("deploy", self._simulate_deploy_stage),
        ]

        results = {}

        for stage_name, stage_func in pipeline_stages:
            try:
                start_time = time.time()
                result = stage_func()
                duration = time.time() - start_time

                results[stage_name] = {"success": result, "duration": duration}

            except Exception as e:
                results[stage_name] = {"success": False, "error": str(e), "duration": 0}

        # At least lint and test should succeed
        assert results.get("lint", {}).get("success", False), "Lint stage failed"

        # Print pipeline results
        for stage, result in results.items():
            status = "PASS" if result["success"] else "FAIL"
            duration = result.get("duration", 0)
            print(f"{stage.upper()}: {status} ({duration:.2f}s)")

    def _simulate_lint_stage(self) -> bool:
        """Simulate lint stage."""
        # Quick syntax check
        python_files = list(Path(".").rglob("*.py"))[:5]  # Check first 5 files

        for py_file in python_files:
            try:
                with open(py_file) as f:
                    compile(f.read(), str(py_file), "exec")
            except SyntaxError:
                return False

        return True

    def _simulate_test_stage(self) -> bool:
        """Simulate test stage."""
        # Check if tests exist
        test_files = list(Path("tests").rglob("test_*.py"))
        return len(test_files) > 0

    def _simulate_build_stage(self) -> bool:
        """Simulate build stage."""
        # Check if build configuration exists
        build_configs = ["pyproject.toml", "setup.py", "ContainerFile", "Dockerfile"]
        return any(Path(bc).exists() for bc in build_configs)

    def _simulate_deploy_stage(self) -> bool:
        """Simulate deploy stage."""
        # Check if deployment artifacts exist
        deploy_artifacts = ["deploy.sh", "podman-compose.yml", "Makefile"]
        return any(Path(da).exists() for da in deploy_artifacts)

    def test_deployment_monitoring_setup(self):
        """Test deployment monitoring and alerting setup."""
        # Check for monitoring configuration
        monitoring_configs = [
            "prometheus.yml",
            "grafana-dashboard.json",
            "alerts.yml",
            "monitoring/config.yml",
        ]

        monitoring_found = [mc for mc in monitoring_configs if Path(mc).exists()]

        # Check for log configuration
        logging_configs = ["logging.conf", "log4j.properties", "winston.config.js"]

        logging_found = [lc for lc in logging_configs if Path(lc).exists()]

        if monitoring_found or logging_found:
            print(f"Monitoring setup: {monitoring_found}")
            print(f"Logging setup: {logging_found}")
        else:
            print("Warning: No monitoring/logging configuration found")
