"""
Auto-DevOps validation command for Helm charts and Kubernetes manifests.
"""

import os
import json
import subprocess
import tempfile
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..core.base import BaseCommand, CommandResult, CommandStatus


class AutoDevOpsCommand(BaseCommand):
    """Command to validate Auto-DevOps Helm charts and Kubernetes manifests."""
    
    REQUIRED_STAGES = ['build', 'test', 'security', 'deploy']
    SECURITY_TEMPLATES = [
        'Security/SAST.gitlab-ci.yml',
        'Security/Secret-Detection.gitlab-ci.yml', 
        'Security/Dependency-Scanning.gitlab-ci.yml',
        'Security/Container-Scanning.gitlab-ci.yml'
    ]
    
    @property
    def name(self) -> str:
        return "auto-devops"
    
    @property
    def description(self) -> str:
        return "Validate Auto-DevOps Helm charts and Kubernetes manifests"
    
    def execute(self, 
                project_path: str = ".",
                validate_helm: bool = True,
                validate_k8s: bool = True,
                simulate_deployment: bool = False,
                strict_mode: bool = False) -> CommandResult:
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
        project_path = Path(project_path).resolve()
        
        if not project_path.exists():
            return CommandResult(
                status=CommandStatus.FAILED,
                message=f"Project path does not exist: {project_path}",
                errors=[f"Invalid project path: {project_path}"]
            )
        
        results = {
            'project_analysis': self._analyze_project_structure(project_path),
            'gitlab_ci_validation': None,
            'helm_validation': None,
            'k8s_validation': None,
            'deployment_simulation': None
        }
        
        all_errors = []
        all_warnings = []
        
        # Validate GitLab CI configuration
        gitlab_ci_path = project_path / '.gitlab-ci.yml'
        if gitlab_ci_path.exists():
            ci_result = self._validate_gitlab_ci_autodevops(gitlab_ci_path, strict_mode)
            results['gitlab_ci_validation'] = ci_result
            if not ci_result['valid']:
                all_errors.extend(ci_result['errors'])
            all_warnings.extend(ci_result['warnings'])
        
        # Validate Helm charts
        if validate_helm:
            helm_result = self._validate_helm_charts(project_path)
            results['helm_validation'] = helm_result
            if not helm_result['valid']:
                all_errors.extend(helm_result['errors'])
            all_warnings.extend(helm_result['warnings'])
        
        # Validate Kubernetes manifests
        if validate_k8s:
            k8s_result = self._validate_k8s_manifests(project_path)
            results['k8s_validation'] = k8s_result
            if not k8s_result['valid']:
                all_errors.extend(k8s_result['errors'])
            all_warnings.extend(k8s_result['warnings'])
        
        # Simulate Auto-DevOps deployment
        if simulate_deployment:
            deployment_result = self._simulate_auto_devops_deployment(project_path)
            results['deployment_simulation'] = deployment_result
            if not deployment_result['valid']:
                all_errors.extend(deployment_result['errors'])
            all_warnings.extend(deployment_result['warnings'])
        
        # Determine overall status
        if all_errors:
            status = CommandStatus.FAILED
            message = f"Auto-DevOps validation failed: {len(all_errors)} error(s)"
        elif all_warnings:
            status = CommandStatus.WARNING
            message = f"Auto-DevOps validation passed with {len(all_warnings)} warning(s)"
        else:
            status = CommandStatus.SUCCESS
            message = "Auto-DevOps validation passed successfully"
        
        return CommandResult(
            status=status,
            message=message,
            errors=all_errors,
            warnings=all_warnings,
            data=results
        )
    
    def _analyze_project_structure(self, project_path: Path) -> Dict:
        """Analyze project structure for Auto-DevOps compatibility."""
        analysis = {
            'project_type': 'unknown',
            'has_dockerfile': False,
            'has_gitlab_ci': False,
            'has_helm_charts': False,
            'has_k8s_manifests': False,
            'auto_devops_ready': False
        }
        
        # Detect project type
        if (project_path / 'package.json').exists():
            analysis['project_type'] = 'node'
        elif (project_path / 'pyproject.toml').exists() or (project_path / 'requirements.txt').exists():
            analysis['project_type'] = 'python'
        elif (project_path / 'go.mod').exists():
            analysis['project_type'] = 'go'
        elif (project_path / 'pom.xml').exists():
            analysis['project_type'] = 'java'
        
        # Check for Docker
        analysis['has_dockerfile'] = (project_path / 'Dockerfile').exists() or (project_path / 'ContainerFile').exists()
        
        # Check for GitLab CI
        analysis['has_gitlab_ci'] = (project_path / '.gitlab-ci.yml').exists()
        
        # Check for Helm charts
        helm_dirs = ['chart', 'charts', '.helm', 'helm']
        analysis['has_helm_charts'] = any((project_path / d).exists() for d in helm_dirs)
        
        # Check for Kubernetes manifests
        k8s_dirs = ['k8s', 'kubernetes', 'manifests', 'deploy']
        analysis['has_k8s_manifests'] = any((project_path / d).exists() for d in k8s_dirs)
        
        # Check for Helm values files
        values_files = ['values.yaml', 'values.yml', 'values-production.yaml', 'values-staging.yaml']
        analysis['has_helm_values'] = any((project_path / f).exists() for f in values_files)
        
        # Determine Auto-DevOps readiness
        analysis['auto_devops_ready'] = (
            analysis['has_dockerfile'] and
            analysis['has_gitlab_ci'] and
            (analysis['has_helm_charts'] or analysis['has_helm_values'] or analysis['has_k8s_manifests'])
        )
        
        return analysis
    
    def _validate_gitlab_ci_autodevops(self, gitlab_ci_path: Path, strict_mode: bool) -> Dict:
        """Validate GitLab CI for Auto-DevOps compliance."""
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'stages': {
                'defined': [],
                'missing': [],
                'compliance': False
            },
            'security': {
                'templates': [],
                'missing_templates': [],
                'compliant': False
            }
        }
        
        try:
            with open(gitlab_ci_path, 'r') as f:
                ci_config = yaml.safe_load(f)
            
            if not ci_config:
                result['valid'] = False
                result['errors'].append("Empty or invalid GitLab CI configuration")
                return result
            
            # Check stages
            defined_stages = ci_config.get('stages', [])
            result['stages']['defined'] = defined_stages
            
            for required_stage in self.REQUIRED_STAGES:
                if required_stage not in defined_stages:
                    result['stages']['missing'].append(required_stage)
                    error_msg = f"Missing required Auto-DevOps stage: {required_stage}"
                    if strict_mode:
                        result['errors'].append(error_msg)
                        result['valid'] = False
                    else:
                        result['warnings'].append(error_msg)
            
            result['stages']['compliance'] = len(result['stages']['missing']) == 0
            
            # Check security templates
            includes = ci_config.get('include', [])
            if not isinstance(includes, list):
                includes = [includes] if includes else []
            
            template_includes = [inc for inc in includes if isinstance(inc, dict) and 'template' in inc]
            included_templates = [inc['template'] for inc in template_includes]
            
            result['security']['templates'] = included_templates
            
            for template in self.SECURITY_TEMPLATES:
                if template not in included_templates:
                    result['security']['missing_templates'].append(template)
                    warning_msg = f"Missing security template: {template}"
                    if strict_mode:
                        result['errors'].append(warning_msg)
                        result['valid'] = False
                    else:
                        result['warnings'].append(warning_msg)
            
            result['security']['compliant'] = len(result['security']['missing_templates']) == 0
            
        except Exception as e:
            result['valid'] = False
            result['errors'].append(f"Failed to validate GitLab CI: {str(e)}")
        
        return result
    
    def _validate_helm_charts(self, project_path: Path) -> Dict:
        """Validate Helm charts and values files."""
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'charts_found': [],
            'values_files': []
        }
        
        # Find Helm charts
        chart_dirs = ['chart', 'charts', '.helm']
        for chart_dir in chart_dirs:
            chart_path = project_path / chart_dir
            if chart_path.exists():
                result['charts_found'].append(str(chart_path))
        
        # Find values files
        values_patterns = ['values*.yaml', 'values*.yml']
        for pattern in values_patterns:
            for values_file in project_path.glob(pattern):
                result['values_files'].append(str(values_file))
        
        # Validate each values file
        for values_file in result['values_files']:
            try:
                with open(values_file, 'r') as f:
                    yaml.safe_load(f)
                self.log(f"Valid YAML in {values_file}")
            except yaml.YAMLError as e:
                result['valid'] = False
                result['errors'].append(f"Invalid YAML in {values_file}: {str(e)}")
        
        # Try helm template if helm is available and charts found
        if result['charts_found'] and self._is_helm_available():
            template_result = self._validate_with_helm_template(project_path, result['charts_found'][0])
            if not template_result['valid']:
                result['valid'] = False
                result['errors'].extend(template_result['errors'])
            result['warnings'].extend(template_result['warnings'])
        
        return result
    
    def _validate_k8s_manifests(self, project_path: Path) -> Dict:
        """Validate Kubernetes manifests."""
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'manifests': []
        }
        
        # Find Kubernetes manifest directories
        k8s_dirs = ['k8s', 'kubernetes', 'manifests', 'deploy']
        manifest_files = []
        
        for k8s_dir in k8s_dirs:
            k8s_path = project_path / k8s_dir
            if k8s_path.exists():
                for manifest in k8s_path.rglob('*.yaml'):
                    manifest_files.append(manifest)
                for manifest in k8s_path.rglob('*.yml'):
                    manifest_files.append(manifest)
        
        # Also check root level manifests
        for manifest in project_path.glob('*.k8s.yaml'):
            manifest_files.append(manifest)
        
        result['manifests'] = [str(m) for m in manifest_files]
        
        # Validate each manifest
        for manifest_file in manifest_files:
            try:
                with open(manifest_file, 'r') as f:
                    docs = list(yaml.safe_load_all(f))
                    for doc in docs:
                        if doc and isinstance(doc, dict):
                            if 'apiVersion' not in doc or 'kind' not in doc:
                                result['warnings'].append(
                                    f"Manifest {manifest_file} missing required fields (apiVersion, kind)"
                                )
                self.log(f"Valid Kubernetes manifest: {manifest_file}")
            except yaml.YAMLError as e:
                result['valid'] = False
                result['errors'].append(f"Invalid YAML in {manifest_file}: {str(e)}")
        
        # Try kubectl validation if available
        if manifest_files and self._is_kubectl_available():
            kubectl_result = self._validate_with_kubectl(manifest_files)
            if not kubectl_result['valid']:
                result['warnings'].extend(kubectl_result['warnings'])  # kubectl issues are warnings, not errors
        
        return result
    
    def _simulate_auto_devops_deployment(self, project_path: Path) -> Dict:
        """Simulate Auto-DevOps deployment with Helm."""
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'simulation_output': ''
        }
        
        if not self._is_helm_available():
            result['warnings'].append("Helm not available - skipping deployment simulation")
            return result
        
        # Download Auto-DevOps chart if needed
        auto_deploy_chart = self._ensure_auto_deploy_chart()
        if not auto_deploy_chart:
            result['errors'].append("Failed to download Auto-DevOps chart")
            result['valid'] = False
            return result
        
        # Prepare values
        values_args = []
        for values_file in project_path.glob('values*.yaml'):
            values_args.extend(['-f', str(values_file)])
        
        # Add default Auto-DevOps values
        default_values = {
            'application': {
                'repository': 'registry.example.com/project',
                'tag': 'latest'
            },
            'service': {
                'enabled': True,
                'type': 'ClusterIP',
                'port': 80
            },
            'ingress': {
                'enabled': False
            }
        }
        
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                yaml.dump(default_values, f)
                values_args.extend(['-f', f.name])
        
            # Run helm template
            cmd = [
                'helm', 'template', 'test-release', auto_deploy_chart,
                '--dry-run'
            ] + values_args
            
            process = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True,
                cwd=project_path
            )
            
            if process.returncode != 0:
                result['valid'] = False
                result['errors'].append(f"Helm template failed: {process.stderr}")
            else:
                result['simulation_output'] = process.stdout
                self.log("Auto-DevOps deployment simulation successful")
                
        except Exception as e:
            result['valid'] = False
            result['errors'].append(f"Deployment simulation failed: {str(e)}")
        finally:
            # Cleanup temp file
            try:
                os.unlink(f.name)
            except:
                pass
        
        return result
    
    def _is_helm_available(self) -> bool:
        """Check if Helm is available."""
        try:
            subprocess.run(['helm', 'version'], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def _is_kubectl_available(self) -> bool:
        """Check if kubectl is available."""
        try:
            subprocess.run(['kubectl', 'version', '--client'], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def _validate_with_helm_template(self, project_path: Path, chart_path: str) -> Dict:
        """Validate using helm template."""
        result = {'valid': True, 'errors': [], 'warnings': []}
        
        try:
            cmd = ['helm', 'template', chart_path, '--dry-run']
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=project_path
            )
            
            if process.returncode != 0:
                result['valid'] = False
                result['errors'].append(f"Helm template validation failed: {process.stderr}")
            else:
                self.log("Helm template validation passed")
                
        except Exception as e:
            result['warnings'].append(f"Helm template validation error: {str(e)}")
            
        return result
    
    def _validate_with_kubectl(self, manifest_files: List[Path]) -> Dict:
        """Validate using kubectl dry-run."""
        result = {'valid': True, 'warnings': []}
        
        for manifest_file in manifest_files:
            try:
                cmd = ['kubectl', 'apply', '--dry-run=client', '-f', str(manifest_file)]
                process = subprocess.run(cmd, capture_output=True, text=True)
                
                if process.returncode != 0:
                    result['warnings'].append(f"kubectl validation warning for {manifest_file}: {process.stderr}")
                    
            except Exception as e:
                result['warnings'].append(f"kubectl validation error for {manifest_file}: {str(e)}")
        
        return result
    
    def _ensure_auto_deploy_chart(self) -> Optional[str]:
        """Ensure Auto-Deploy chart is available."""
        cache_dir = Path.home() / '.cache' / 'huskycats'
        chart_dir = cache_dir / 'auto-deploy-app'
        
        if chart_dir.exists():
            return str(chart_dir)
        
        # Download Auto-Deploy chart
        try:
            cache_dir.mkdir(parents=True, exist_ok=True)
            
            # Clone the auto-deploy-image repository
            cmd = [
                'git', 'clone', '--depth', '1',
                'https://gitlab.com/gitlab-org/cluster-integration/auto-deploy-image.git',
                str(cache_dir / 'auto-deploy-image')
            ]
            
            process = subprocess.run(cmd, capture_output=True, text=True)
            
            if process.returncode == 0:
                chart_path = cache_dir / 'auto-deploy-image' / 'assets' / 'auto-deploy-app'
                if chart_path.exists():
                    return str(chart_path)
                    
        except Exception as e:
            self.log(f"Failed to download Auto-Deploy chart: {e}", level="ERROR")
        
        return None