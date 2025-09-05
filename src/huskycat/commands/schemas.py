"""
Schema update command for fetching latest validation schemas.
"""

import json
import requests
from datetime import datetime, timedelta
from pathlib import Path

from ..core.base import BaseCommand, CommandResult, CommandStatus


class UpdateSchemasCommand(BaseCommand):
    """Command to update validation schemas from official sources."""

    SCHEMAS = {
        "gitlab-ci": {
            "url": "https://gitlab.com/gitlab-org/gitlab/-/raw/master/app/assets/javascripts/editor/schema/ci.json",
            "fallback": "https://json.schemastore.org/gitlab-ci",
            "cache_file": "gitlab-ci-schema.json",
        },
        "github-actions": {
            "url": "https://json.schemastore.org/github-workflow",
            "fallback": None,
            "cache_file": "github-actions-schema.json",
        },
        "package-json": {
            "url": "https://json.schemastore.org/package",
            "fallback": None,
            "cache_file": "package-schema.json",
        },
    }

    @property
    def name(self) -> str:
        return "update-schemas"

    @property
    def description(self) -> str:
        return "Update validation schemas from official sources"

    def execute(self, force: bool = False, helm: bool = False) -> CommandResult:
        """
        Update all schemas.

        Args:
            force: Force update even if cache is fresh
            helm: Also update Helm chart schemas from Auto-DevOps

        Returns:
            CommandResult with update status
        """
        cache_dir = Path.home() / ".cache" / "huskycats"
        cache_dir.mkdir(parents=True, exist_ok=True)

        updated = []
        failed = []
        skipped = []

        for schema_name, schema_info in self.SCHEMAS.items():
            cache_file = cache_dir / schema_info["cache_file"]

            # Check if update is needed
            if not force and cache_file.exists():
                # Check age of cache
                cache_age = datetime.now() - datetime.fromtimestamp(
                    cache_file.stat().st_mtime
                )
                if cache_age < timedelta(days=7):
                    self.log(f"Schema {schema_name} is up to date")
                    skipped.append(schema_name)
                    continue

            # Try to fetch schema
            self.log(f"Updating {schema_name} schema...")
            success = False

            for url in [schema_info["url"], schema_info.get("fallback")]:
                if not url:
                    continue

                try:
                    response = requests.get(url, timeout=30)
                    response.raise_for_status()

                    # Validate it's valid JSON
                    schema_data = response.json()

                    # Save to cache
                    cache_file.write_text(json.dumps(schema_data, indent=2))
                    updated.append(schema_name)
                    success = True
                    self.log(f"Successfully updated {schema_name}")
                    break

                except Exception as e:
                    self.log(f"Failed to fetch from {url}: {e}", level="WARNING")

            if not success:
                failed.append(schema_name)
                self.log(f"Failed to update {schema_name}", level="ERROR")

        # Update Helm chart schemas if requested
        if helm:
            try:
                helm_success = self._update_helm_schemas(cache_dir, force)
                if helm_success:
                    updated.append("Helm chart schemas")
                else:
                    failed.append("Helm chart schemas")
            except Exception as e:
                failed.append("Helm chart schemas")
                self.log(f"Failed to update Helm schemas: {e}", level="ERROR")

        # Determine status
        if failed and not updated:
            status = CommandStatus.FAILED
            message = f"Failed to update schemas: {', '.join(failed)}"
        elif failed:
            status = CommandStatus.WARNING
            message = f"Updated {len(updated)} schemas, {len(failed)} failed"
        else:
            status = CommandStatus.SUCCESS
            message = (
                f"Updated {len(updated)} schemas, {len(skipped)} already up to date"
            )

        return CommandResult(
            status=status,
            message=message,
            data={
                "updated": updated,
                "failed": failed,
                "skipped": skipped,
                "cache_dir": str(cache_dir),
            },
        )

    def _update_helm_schemas(self, cache_dir: Path, force: bool = False) -> bool:
        """Update Helm chart schemas from GitLab Auto-DevOps repository."""
        import yaml

        helm_dir = cache_dir / "schemas" / "helm"
        helm_dir.mkdir(parents=True, exist_ok=True)

        # Check if update is needed
        if not force:
            rules_file = helm_dir / "validation-rules.json"
            if rules_file.exists():
                cache_age = datetime.now() - datetime.fromtimestamp(
                    rules_file.stat().st_mtime
                )
                if cache_age < timedelta(days=7):
                    self.log("Helm schemas are up to date")
                    return True

        try:
            # GitLab Auto-DevOps Helm chart sources
            helm_chart_urls = [
                "https://gitlab.com/gitlab-org/cluster-integration/auto-devops-deploy/-/raw/master/Chart.yaml",
                "https://gitlab.com/gitlab-org/cluster-integration/auto-devops-deploy/-/raw/master/values.yaml",
                "https://gitlab.com/gitlab-org/cluster-integration/auto-devops-deploy/-/raw/master/values-production.yaml",
            ]

            common_chart_urls = [
                "https://raw.githubusercontent.com/helm/helm/main/pkg/chart/schema.json",
            ]

            # Fetch Auto-DevOps Helm charts
            for url in helm_chart_urls:
                try:
                    response = requests.get(url, timeout=30)
                    response.raise_for_status()

                    filename = url.split("/")[-1]
                    target_file = helm_dir / f"autodevops-{filename}"

                    # Parse and validate YAML
                    if filename.endswith((".yaml", ".yml")):
                        data = yaml.safe_load(response.text)
                        with open(target_file, "w") as f:
                            yaml.dump(data, f, indent=2, default_flow_style=False)
                    else:
                        with open(target_file, "w") as f:
                            f.write(response.text)

                    self.log(f"Updated: {target_file}")
                except Exception as e:
                    self.log(f"Failed to fetch {url}: {e}", level="WARNING")

            # Fetch common Helm schemas
            for url in common_chart_urls:
                try:
                    response = requests.get(url, timeout=30)
                    response.raise_for_status()

                    filename = url.split("/")[-1]
                    target_file = helm_dir / f"common-{filename}"

                    if filename.endswith(".json"):
                        data = response.json()
                        with open(target_file, "w") as f:
                            import json

                            json.dump(data, f, indent=2)
                    else:
                        with open(target_file, "w") as f:
                            f.write(response.text)

                    self.log(f"Updated: {target_file}")
                except Exception as e:
                    self.log(f"Failed to fetch {url}: {e}", level="WARNING")

            # Generate validation rules from schemas
            validation_rules = {
                "autodevops_validation": {
                    "required_fields": ["name", "version", "appVersion"],
                    "values_schema": {},
                    "common_patterns": {},
                }
            }

            # Extract patterns from Auto-DevOps charts
            for chart_file in helm_dir.glob("autodevops-*.yaml"):
                try:
                    with open(chart_file) as f:
                        data = yaml.safe_load(f)

                    if chart_file.name == "autodevops-Chart.yaml":
                        validation_rules["autodevops_validation"]["chart_metadata"] = {
                            "name": data.get("name"),
                            "version_pattern": r"^[0-9]+\.[0-9]+\.[0-9]+",
                            "required_fields": list(data.keys()) if data else [],
                        }
                    elif "values" in chart_file.name:
                        # Extract common value patterns
                        if data:
                            validation_rules["autodevops_validation"][
                                "values_schema"
                            ].update(data)

                except Exception as e:
                    self.log(f"Error processing {chart_file}: {e}", level="WARNING")

            # Save validation rules
            rules_file = helm_dir / "validation-rules.json"
            import json

            with open(rules_file, "w") as f:
                json.dump(validation_rules, f, indent=2)

            self.log(f"Generated validation rules: {rules_file}")
            return True

        except Exception as e:
            self.log(f"Failed to update Helm schemas: {e}", level="ERROR")
            return False
