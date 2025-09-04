"""
Auto-DevOps validation command for Helm charts and Kubernetes manifests.
"""

import os
import json
import subprocess
import tempfile
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any

from ..core.base import BaseCommand, CommandResult, CommandStatus


class AutoDevOpsCommand(BaseCommand):
    """Command to validate Auto-DevOps Helm charts and Kubernetes manifests."""

    REQUIRED_STAGES = ["build", "test", "security", "deploy"]

    # Schema cache directory for Auto-DevOps validation
    SCHEMAS_DIR = Path.home() / ".cache" / "huskycats" / "schemas" / "helm"
    SECURITY_TEMPLATES = [
        "Security/SAST.gitlab-ci.yml",
        "Security/Secret-Detection.gitlab-ci.yml",
        "Security/Dependency-Scanning.gitlab-ci.yml",
        "Security/Container-Scanning.gitlab-ci.yml",
    ]

    @property
    def name(self) -> str:
        return "auto-devops"

    @property
    def description(self) -> str:
        return "Validate Auto-DevOps Helm charts and Kubernetes manifests"

    def execute(
        self,
        project_path: str = ".",
        validate_helm: bool = True,
        validate_k8s: bool = True,
        simulate_deployment: bool = False,
        strict_mode: bool = False,
    ) -> CommandResult:
        """
        Execute Auto-DevOps validation.

        Args:
            project_path: Path to project directory
            validate_helm: Validate Helm charts and values
            validate_k8s: Validate Kubernetes manifests
            simulate_deployment: Simulate Helm deployment
            strict_mode: Enable strict validation mode

        Returns:
            CommandResult with validation status
        """
        project_path_obj = Path(project_path).resolve()

        if not project_path_obj.exists():
            return CommandResult(
                status=CommandStatus.FAILED,
                message=f"Project path does not exist: {project_path_obj}",
                errors=[f"Invalid project path: {project_path_obj}"],
            )

        results = {
            "project_analysis": self._analyze_project_structure(project_path_obj),
            "gitlab_ci_validation": None,
            "helm_validation": None,
            "k8s_validation": None,
            "deployment_simulation": None,
        }

        all_errors = []
        all_warnings = []

        # Validate GitLab CI configuration
        gitlab_ci_path = project_path_obj / ".gitlab-ci.yml"
        if gitlab_ci_path.exists():
            ci_result = self._validate_gitlab_ci_autodevops(gitlab_ci_path, strict_mode)
            results["gitlab_ci_validation"] = ci_result
            if not ci_result["valid"]:
                all_errors.extend(ci_result["errors"])
            all_warnings.extend(ci_result["warnings"])

        # Validate Helm charts
        if validate_helm:
            helm_result = self._validate_helm_charts(project_path_obj)
            results["helm_validation"] = helm_result
            if not helm_result["valid"]:
                all_errors.extend(helm_result["errors"])
            all_warnings.extend(helm_result["warnings"])

        # Validate Kubernetes manifests
        if validate_k8s:
            k8s_result = self._validate_k8s_manifests(project_path_obj)
            results["k8s_validation"] = k8s_result
            if not k8s_result["valid"]:
                all_errors.extend(k8s_result["errors"])
            all_warnings.extend(k8s_result["warnings"])

        # Simulate Auto-DevOps deployment
        if simulate_deployment:
            deployment_result = self._simulate_auto_devops_deployment(project_path_obj)
            results["deployment_simulation"] = deployment_result
            if not deployment_result["valid"]:
                all_errors.extend(deployment_result["errors"])
            all_warnings.extend(deployment_result["warnings"])

        # Determine overall status
        if all_errors:
            status = CommandStatus.FAILED
            message = f"Auto-DevOps validation failed: {len(all_errors)} error(s)"
        elif all_warnings:
            status = CommandStatus.WARNING
            message = (
                f"Auto-DevOps validation passed with {len(all_warnings)} warning(s)"
            )
        else:
            status = CommandStatus.SUCCESS
            message = "Auto-DevOps validation passed successfully"

        return CommandResult(
            status=status,
            message=message,
            errors=all_errors,
            warnings=all_warnings,
            data=results,
        )

    def _analyze_project_structure(self, project_path_obj: Path) -> Dict:
        """Analyze project structure for Auto-DevOps compatibility."""
        analysis = {
            "project_type": "unknown",
            "has_dockerfile": False,
            "has_gitlab_ci": False,
            "has_helm_charts": False,
            "has_k8s_manifests": False,
            "auto_devops_ready": False,
        }

        # Detect project type
        if (project_path_obj / "package.json").exists():
            analysis["project_type"] = "node"
        elif (project_path_obj / "pyproject.toml").exists() or (
            project_path_obj / "requirements.txt"
        ).exists():
            analysis["project_type"] = "python"
        elif (project_path_obj / "go.mod").exists():
            analysis["project_type"] = "go"
        elif (project_path_obj / "pom.xml").exists():
            analysis["project_type"] = "java"

        # Check for Docker
        analysis["has_dockerfile"] = (project_path_obj / "Dockerfile").exists() or (
            project_path_obj / "ContainerFile"
        ).exists()

        # Check for GitLab CI
        analysis["has_gitlab_ci"] = (project_path_obj / ".gitlab-ci.yml").exists()

        # Check for Helm charts
        helm_dirs = ["chart", "charts", ".helm", "helm"]
        analysis["has_helm_charts"] = any(
            (project_path_obj / d).exists() for d in helm_dirs
        )

        # Check for Kubernetes manifests
        k8s_dirs = ["k8s", "kubernetes", "manifests", "deploy"]
        analysis["has_k8s_manifests"] = any(
            (project_path_obj / d).exists() for d in k8s_dirs
        )

        # Check for Helm values files
        values_files = [
            "values.yaml",
            "values.yml",
            "values-production.yaml",
            "values-staging.yaml",
        ]
        analysis["has_helm_values"] = any(
            (project_path_obj / f).exists() for f in values_files
        )

        # Determine Auto-DevOps readiness
        analysis["auto_devops_ready"] = (
            analysis["has_dockerfile"]
            and analysis["has_gitlab_ci"]
            and (
                analysis["has_helm_charts"]
                or analysis["has_helm_values"]
                or analysis["has_k8s_manifests"]
            )
        )

        return analysis

    def _load_helm_validation_rules(self) -> Dict[str, Any]:
        """Load cached Helm validation rules from scheduled updates."""
        rules_file = self.SCHEMAS_DIR / "validation-rules.json"

        if not rules_file.exists():
            self.log(f"Helm validation rules not found at {rules_file}")
            self.log("Consider running: huskycat update-schemas --helm")
            return {}

        try:
            with open(rules_file) as f:
                rules = json.load(f)
            self.log(f"Loaded Helm validation rules from {rules_file}")
            return rules
        except Exception as e:
            self.log(f"Failed to load Helm validation rules: {e}")
            return {}

    def _validate_with_cached_helm_schemas(
        self, chart_path: Path, chart_name: str
    ) -> Dict[str, Any]:
        """Validate Helm chart using cached Auto-DevOps schemas."""
        result = {"valid": True, "errors": [], "warnings": []}

        # Load validation rules
        rules = self._load_helm_validation_rules()
        if not rules:
            result["warnings"].append(
                "No cached Helm schemas available - using basic validation"
            )
            return result

        autodevops_rules = rules.get("autodevops_validation", {})

        try:
            # Validate Chart.yaml
            chart_yaml = chart_path / "Chart.yaml"
            if chart_yaml.exists():
                with open(chart_yaml) as f:
                    chart_data = yaml.safe_load(f)

                # Check required fields
                required_fields = autodevops_rules.get("required_fields", [])
                for field in required_fields:
                    if field not in chart_data:
                        result["errors"].append(
                            f"Missing required field '{field}' in Chart.yaml"
                        )
                        result["valid"] = False

                # Validate version pattern
                chart_metadata = autodevops_rules.get("chart_metadata", {})
                version_pattern = chart_metadata.get("version_pattern")
                if version_pattern and "version" in chart_data:
                    import re

                    if not re.match(version_pattern, str(chart_data["version"])):
                        result["warnings"].append(
                            f"Chart version '{chart_data['version']}' "
                            f"doesn't match recommended pattern {version_pattern}"
                        )

            # Validate values.yaml against cached schema
            values_yaml = chart_path / "values.yaml"
            if values_yaml.exists():
                with open(values_yaml) as f:
                    values_data = yaml.safe_load(f)

                values_schema = autodevops_rules.get("values_schema", {})
                if values_schema:
                    # Simple schema validation - check for common Auto-DevOps patterns
                    self._validate_values_against_schema(
                        values_data, values_schema, result
                    )

        except Exception as e:
            result["errors"].append(f"Schema validation failed: {e}")
            result["valid"] = False

        return result

    def _validate_values_against_schema(
        self,
        values_data: Dict[str, Any],
        schema: Dict[str, Any],
        result: Dict[str, Any],
    ) -> None:
        """Validate values.yaml against Auto-DevOps schema patterns."""
        # Check for Auto-DevOps specific configurations
        autodevops_keys = [
            "replicaCount",
            "image",
            "service",
            "ingress",
            "resources",
            "nodeSelector",
            "tolerations",
            "affinity",
        ]

        for key in autodevops_keys:
            if key in schema and key not in values_data:
                result["warnings"].append(
                    f"Consider adding '{key}' configuration for Auto-DevOps compatibility"
                )

        # Validate image configuration
        if "image" in values_data and "image" in schema:
            image_config = values_data["image"]
            schema_image = schema["image"]

            if isinstance(image_config, dict) and isinstance(schema_image, dict):
                for required_key in ["repository", "tag"]:
                    if required_key not in image_config:
                        result["errors"].append(
                            f"Missing required image.{required_key} in values.yaml"
                        )
                        result["valid"] = False

    def _validate_gitlab_ci_autodevops(
        self, gitlab_ci_path: Path, strict_mode: bool
    ) -> Dict:
        """Validate GitLab CI for Auto-DevOps compliance."""
        result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "stages": {"defined": [], "missing": [], "compliance": False},
            "security": {"templates": [], "missing_templates": [], "compliant": False},
        }

        try:
            with open(gitlab_ci_path, "r") as f:
                ci_config: Optional[Dict[str, Any]] = yaml.safe_load(f)

            if not ci_config:
                result["valid"] = False
                result["errors"].append("Empty or invalid GitLab CI configuration")
                return result

            # Check stages
            defined_stages = ci_config.get("stages", [])
            result["stages"]["defined"] = defined_stages

            for required_stage in self.REQUIRED_STAGES:
                if required_stage not in defined_stages:
                    result["stages"]["missing"].append(required_stage)
                    error_msg = f"Missing required Auto-DevOps stage: {required_stage}"
                    if strict_mode:
                        result["errors"].append(error_msg)
                        result["valid"] = False
                    else:
                        result["warnings"].append(error_msg)

            result["stages"]["compliance"] = len(result["stages"]["missing"]) == 0

            # Check security templates
            includes = ci_config.get("include", [])
            if not isinstance(includes, list):
                includes = [includes] if includes else []

            template_includes = [
                inc for inc in includes if isinstance(inc, dict) and "template" in inc
            ]
            included_templates = [inc["template"] for inc in template_includes]

            result["security"]["templates"] = included_templates

            for template in self.SECURITY_TEMPLATES:
                if template not in included_templates:
                    result["security"]["missing_templates"].append(template)
                    warning_msg = f"Missing security template: {template}"
                    if strict_mode:
                        result["errors"].append(warning_msg)
                        result["valid"] = False
                    else:
                        result["warnings"].append(warning_msg)

            result["security"]["compliant"] = (
                len(result["security"]["missing_templates"]) == 0
            )

        except Exception as e:
            result["valid"] = False
            result["errors"].append(f"Failed to validate GitLab CI: {str(e)}")

        return result

    def _validate_helm_charts(self, project_path_obj: Path) -> Dict:
        """Validate Helm charts and values files."""
        result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "charts_found": [],
            "values_files": [],
        }

        # Find Helm charts
        chart_dirs = ["chart", "charts", ".helm"]
        for chart_dir in chart_dirs:
            chart_path = project_path_obj / chart_dir
            if chart_path.exists():
                result["charts_found"].append(str(chart_path))

        # Find values files
        values_patterns = ["values*.yaml", "values*.yml"]
        for pattern in values_patterns:
            for values_file in project_path_obj.glob(pattern):
                result["values_files"].append(str(values_file))

        # Validate each chart using cached schemas
        for chart_dir in result["charts_found"]:
            chart_path = Path(chart_dir)
            chart_name = chart_path.name

            # Use cached Auto-DevOps schemas for enhanced validation
            schema_result = self._validate_with_cached_helm_schemas(
                chart_path, chart_name
            )

            if not schema_result["valid"]:
                result["valid"] = False
                result["errors"].extend(schema_result["errors"])
            result["warnings"].extend(schema_result["warnings"])

        # Validate each values file
        for values_file in result["values_files"]:
            try:
                with open(values_file, "r") as f:
                    yaml.safe_load(f)
                self.log(f"Valid YAML in {values_file}")
            except yaml.YAMLError as e:
                result["valid"] = False
                result["errors"].append(f"Invalid YAML in {values_file}: {str(e)}")

        # Try helm template if helm is available and charts found
        if result["charts_found"] and self._is_helm_available():
            template_result = self._validate_with_helm_template(
                project_path_obj, result["charts_found"][0]
            )
            if not template_result["valid"]:
                result["valid"] = False
                result["errors"].extend(template_result["errors"])
            result["warnings"].extend(template_result["warnings"])

        return result

    def _validate_k8s_manifests(self, project_path_obj: Path) -> Dict:
        """Validate Kubernetes manifests."""
        result = {"valid": True, "errors": [], "warnings": [], "manifests": []}

        # Find Kubernetes manifest directories
        k8s_dirs = ["k8s", "kubernetes", "manifests", "deploy"]
        manifest_files = []

        for k8s_dir in k8s_dirs:
            k8s_path = project_path_obj / k8s_dir
            if k8s_path.exists():
                for manifest in k8s_path.rglob("*.yaml"):
                    manifest_files.append(manifest)
                for manifest in k8s_path.rglob("*.yml"):
                    manifest_files.append(manifest)

        # Also check root level manifests
        for manifest in project_path_obj.glob("*.k8s.yaml"):
            manifest_files.append(manifest)

        result["manifests"] = [str(m) for m in manifest_files]

        # Validate each manifest
        for manifest_file in manifest_files:
            try:
                with open(manifest_file, "r") as f:
                    docs = list(yaml.safe_load_all(f))
                    for doc in docs:
                        if doc and isinstance(doc, dict):
                            if "apiVersion" not in doc or "kind" not in doc:
                                result["warnings"].append(
                                    f"Manifest {manifest_file} missing required fields (apiVersion, kind)"
                                )
                self.log(f"Valid Kubernetes manifest: {manifest_file}")
            except yaml.YAMLError as e:
                result["valid"] = False
                result["errors"].append(f"Invalid YAML in {manifest_file}: {str(e)}")

        # Try kubectl validation if available
        if manifest_files and self._is_kubectl_available():
            kubectl_result = self._validate_with_kubectl(manifest_files)
            if not kubectl_result["valid"]:
                result["warnings"].extend(
                    kubectl_result["warnings"]
                )  # kubectl issues are warnings, not errors

        return result

    def _simulate_auto_devops_deployment(self, project_path_obj: Path) -> Dict:
        """Simulate Auto-DevOps deployment with Helm."""
        result = {"valid": True, "errors": [], "warnings": [], "simulation_output": ""}

        if not self._is_helm_available():
            result["warnings"].append(
                "Helm not available - skipping deployment simulation"
            )
            return result

        # Download Auto-DevOps chart if needed
        auto_deploy_chart = self._ensure_auto_deploy_chart()
        if not auto_deploy_chart:
            result["errors"].append("Failed to download Auto-DevOps chart")
            result["valid"] = False
            return result

        # Prepare values
        values_args = []
        for values_file in project_path_obj.glob("values*.yaml"):
            values_args.extend(["-f", str(values_file)])

        # Add default Auto-DevOps values
        default_values = {
            "application": {
                "repository": "registry.example.com/project",
                "tag": "latest",
            },
            "service": {"enabled": True, "type": "ClusterIP", "port": 80},
            "ingress": {"enabled": False},
        }

        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".yaml", delete=False
            ) as f:
                yaml.dump(default_values, f)
                values_args.extend(["-f", f.name])

            # Run helm template
            cmd = [
                "helm",
                "template",
                "test-release",
                auto_deploy_chart,
                "--dry-run",
            ] + values_args

            process = subprocess.run(
                cmd, capture_output=True, text=True, cwd=project_path_obj
            )

            if process.returncode != 0:
                result["valid"] = False
                result["errors"].append(f"Helm template failed: {process.stderr}")
            else:
                result["simulation_output"] = process.stdout
                self.log("Auto-DevOps deployment simulation successful")

        except Exception as e:
            result["valid"] = False
            result["errors"].append(f"Deployment simulation failed: {str(e)}")
        finally:
            # Cleanup temp file
            try:
                os.unlink(f.name)
            except Exception:
                pass

        return result

    def _is_helm_available(self) -> bool:
        """Check if Helm is available."""
        try:
            subprocess.run(["helm", "version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _is_kubectl_available(self) -> bool:
        """Check if kubectl is available."""
        try:
            subprocess.run(
                ["kubectl", "version", "--client"], capture_output=True, check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _validate_with_helm_template(
        self, project_path_obj: Path, chart_path: str
    ) -> Dict:
        """Validate using helm template."""
        result = {"valid": True, "errors": [], "warnings": []}

        try:
            cmd = ["helm", "template", chart_path, "--dry-run"]
            process = subprocess.run(
                cmd, capture_output=True, text=True, cwd=project_path_obj
            )

            if process.returncode != 0:
                result["valid"] = False
                result["errors"].append(
                    f"Helm template validation failed: {process.stderr}"
                )
            else:
                self.log("Helm template validation passed")

        except Exception as e:
            result["warnings"].append(f"Helm template validation error: {str(e)}")

        return result

    def _validate_with_kubectl(self, manifest_files: List[Path]) -> Dict:
        """Validate using kubectl dry-run."""
        result = {"valid": True, "warnings": []}

        for manifest_file in manifest_files:
            try:
                cmd = ["kubectl", "apply", "--dry-run=client", "-f", str(manifest_file)]
                process = subprocess.run(cmd, capture_output=True, text=True)

                if process.returncode != 0:
                    result["warnings"].append(
                        f"kubectl validation warning for {manifest_file}: {process.stderr}"
                    )

            except Exception as e:
                result["warnings"].append(
                    f"kubectl validation error for {manifest_file}: {str(e)}"
                )

        return result

    def _ensure_auto_deploy_chart(self) -> Optional[str]:
        """Ensure Auto-Deploy chart is available."""
        cache_dir = Path.home() / ".cache" / "huskycats"
        chart_dir = cache_dir / "auto-deploy-app"

        if chart_dir.exists():
            return str(chart_dir)

        # Download Auto-Deploy chart
        try:
            cache_dir.mkdir(parents=True, exist_ok=True)

            # Clone the auto-deploy-image repository
            cmd = [
                "git",
                "clone",
                "--depth",
                "1",
                "https://gitlab.com/gitlab-org/cluster-integration/auto-deploy-image.git",
                str(cache_dir / "auto-deploy-image"),
            ]

            process = subprocess.run(cmd, capture_output=True, text=True)

            if process.returncode == 0:
                chart_path = (
                    cache_dir / "auto-deploy-image" / "assets" / "auto-deploy-app"
                )
                if chart_path.exists():
                    return str(chart_path)

        except Exception as e:
            self.log(f"Failed to download Auto-Deploy chart: {e}", level="ERROR")

        return None
