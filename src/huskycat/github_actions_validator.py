#!/usr/bin/env python3
"""
GitHub Actions Schema Validator with Dynamic Schema Fetching and Caching.

Validates GitHub Actions workflow YAML files against the official JSON Schema.
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
import yaml
from jsonschema import Draft7Validator, FormatChecker

logger = logging.getLogger(__name__)


def _fix_yaml_boolean_keys(data: Any) -> Any:
    """
    Fix YAML boolean key issues.

    YAML 1.1 treats 'on', 'off', 'yes', 'no' as boolean values.
    GitHub Actions uses 'on' as a key, which gets converted to True.
    This function converts the boolean True key back to 'on' string.
    """
    if isinstance(data, dict):
        fixed = {}
        for key, value in data.items():
            # Convert True key (from 'on') back to 'on' string
            if key is True:
                fixed["on"] = _fix_yaml_boolean_keys(value)
            # Convert False key (from 'off') back to 'off' string
            elif key is False:
                fixed["off"] = _fix_yaml_boolean_keys(value)
            else:
                fixed[key] = _fix_yaml_boolean_keys(value)
        return fixed
    elif isinstance(data, list):
        return [_fix_yaml_boolean_keys(item) for item in data]
    return data


class GitHubActionsSchemaValidator:
    """
    Validates GitHub Actions workflow files against the official schema.

    Features:
    - Dynamic schema fetching from SchemaStore
    - Local caching with configurable refresh interval
    - JSON Schema Draft-07 validation
    - Detailed error reporting
    - Semantic validation for common issues
    """

    # Official GitHub Actions Schema URL (SchemaStore is canonical)
    SCHEMA_URL = "https://json.schemastore.org/github-workflow.json"

    # Alternative schema URLs for fallback
    FALLBACK_URLS = [
        "https://raw.githubusercontent.com/SchemaStore/schemastore/master/src/schemas/json/github-workflow.json",
    ]

    # Cache configuration
    CACHE_DIR = Path.home() / ".cache" / "huskycats"
    SCHEMA_CACHE_FILE = CACHE_DIR / "github-actions-schema.json"
    CACHE_META_FILE = CACHE_DIR / "github-actions-schema.meta.json"
    CACHE_REFRESH_DAYS = 7

    def __init__(self, force_refresh: bool = False):
        """Initialize the validator with optional forced schema refresh."""
        self.schema: Optional[Dict[str, Any]] = None
        self.validator: Optional[Draft7Validator] = None
        self.force_refresh = force_refresh
        self._ensure_cache_dir()
        self._load_schema()

    def _ensure_cache_dir(self) -> None:
        """Ensure the cache directory exists."""
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def _should_refresh_cache(self) -> bool:
        """Check if the cached schema should be refreshed."""
        if self.force_refresh:
            logger.info("Forced refresh requested")
            return True

        if not self.SCHEMA_CACHE_FILE.exists() or not self.CACHE_META_FILE.exists():
            logger.info("Cache files not found")
            return True

        try:
            with open(self.CACHE_META_FILE, "r") as f:
                meta = json.load(f)
                cached_date = datetime.fromisoformat(meta.get("cached_at", ""))
                if datetime.now() - cached_date > timedelta(
                    days=self.CACHE_REFRESH_DAYS
                ):
                    logger.info(f"Cache older than {self.CACHE_REFRESH_DAYS} days")
                    return True
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning(f"Error reading cache metadata: {e}")
            return True

        return False

    def _fetch_schema(self) -> Optional[Dict[str, Any]]:
        """Fetch the GitHub Actions schema from the official source."""
        urls_to_try = [self.SCHEMA_URL] + self.FALLBACK_URLS

        for url in urls_to_try:
            try:
                logger.info(f"Fetching GitHub Actions schema from: {url}")
                response = requests.get(
                    url, timeout=30, headers={"User-Agent": "HuskyCat-Validator/2.0"}
                )
                response.raise_for_status()

                schema = response.json()
                logger.info(f"Successfully fetched schema from {url}")

                # Validate it's a proper JSON Schema
                if "$schema" in schema or "properties" in schema:
                    return schema
                else:
                    logger.warning(f"Invalid schema format from {url}")

            except requests.RequestException as e:
                logger.warning(f"Failed to fetch from {url}: {e}")
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON from {url}: {e}")

        return None

    def _save_schema_to_cache(self, schema: Dict[str, Any]) -> None:
        """Save the schema to local cache with metadata."""
        try:
            # Save schema
            with open(self.SCHEMA_CACHE_FILE, "w") as f:
                json.dump(schema, f, indent=2)

            # Save metadata
            meta = {
                "cached_at": datetime.now().isoformat(),
                "source_url": self.SCHEMA_URL,
                "schema_hash": hashlib.sha256(
                    json.dumps(schema, sort_keys=True).encode()
                ).hexdigest(),
                "cache_refresh_days": self.CACHE_REFRESH_DAYS,
            }
            with open(self.CACHE_META_FILE, "w") as f:
                json.dump(meta, f, indent=2)

            logger.info(f"Schema cached at {self.SCHEMA_CACHE_FILE}")

        except IOError as e:
            logger.error(f"Failed to save schema to cache: {e}")

    def _load_schema_from_cache(self) -> Optional[Dict[str, Any]]:
        """Load the schema from local cache."""
        try:
            with open(self.SCHEMA_CACHE_FILE, "r") as f:
                schema = json.load(f)
            logger.info(f"Loaded schema from cache: {self.SCHEMA_CACHE_FILE}")
            return schema
        except (IOError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to load schema from cache: {e}")
            return None

    def _load_schema(self) -> None:
        """Load the schema, either from cache or by fetching it."""
        schema = None

        if self._should_refresh_cache():
            # Try to fetch fresh schema
            schema = self._fetch_schema()
            if schema:
                self._save_schema_to_cache(schema)
        else:
            # Load from cache
            schema = self._load_schema_from_cache()
            if not schema:
                # Cache load failed, fetch fresh
                schema = self._fetch_schema()
                if schema:
                    self._save_schema_to_cache(schema)

        if not schema:
            # Fall back to embedded minimal schema
            logger.warning("Using fallback minimal schema")
            schema = self._get_minimal_schema()

        self.schema = schema
        self.validator = Draft7Validator(schema, format_checker=FormatChecker())

    def _get_minimal_schema(self) -> Dict[str, Any]:
        """Return a minimal GitHub Actions schema for fallback."""
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "required": ["on", "jobs"],
            "properties": {
                "name": {"type": "string"},
                "on": {
                    "oneOf": [
                        {"type": "string"},
                        {"type": "array", "items": {"type": "string"}},
                        {
                            "type": "object",
                            "properties": {
                                "push": {"type": ["object", "null"]},
                                "pull_request": {"type": ["object", "null"]},
                                "workflow_dispatch": {"type": ["object", "null"]},
                                "schedule": {"type": "array"},
                                "release": {"type": "object"},
                            },
                            "additionalProperties": True,
                        },
                    ]
                },
                "env": {"type": "object"},
                "defaults": {"type": "object"},
                "concurrency": {
                    "oneOf": [{"type": "string"}, {"type": "object"}]
                },
                "jobs": {
                    "type": "object",
                    "additionalProperties": {
                        "type": "object",
                        "required": ["runs-on", "steps"],
                        "properties": {
                            "name": {"type": "string"},
                            "runs-on": {
                                "oneOf": [
                                    {"type": "string"},
                                    {"type": "array", "items": {"type": "string"}},
                                ]
                            },
                            "needs": {
                                "oneOf": [
                                    {"type": "string"},
                                    {"type": "array", "items": {"type": "string"}},
                                ]
                            },
                            "if": {"type": "string"},
                            "env": {"type": "object"},
                            "environment": {
                                "oneOf": [{"type": "string"}, {"type": "object"}]
                            },
                            "outputs": {"type": "object"},
                            "strategy": {"type": "object"},
                            "container": {
                                "oneOf": [{"type": "string"}, {"type": "object"}]
                            },
                            "services": {"type": "object"},
                            "steps": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "id": {"type": "string"},
                                        "if": {"type": "string"},
                                        "uses": {"type": "string"},
                                        "run": {"type": "string"},
                                        "with": {"type": "object"},
                                        "env": {"type": "object"},
                                        "continue-on-error": {"type": "boolean"},
                                        "timeout-minutes": {"type": "number"},
                                        "shell": {"type": "string"},
                                        "working-directory": {"type": "string"},
                                    },
                                },
                            },
                            "timeout-minutes": {"type": "number"},
                            "continue-on-error": {"type": "boolean"},
                            "permissions": {
                                "oneOf": [{"type": "string"}, {"type": "object"}]
                            },
                        },
                    },
                },
                "permissions": {
                    "oneOf": [{"type": "string"}, {"type": "object"}]
                },
            },
        }

    def validate_file(self, file_path: str) -> Tuple[bool, List[str], List[str]]:
        """
        Validate a GitHub Actions workflow YAML file against the schema.

        Args:
            file_path: Path to the workflow .yml file

        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        errors: List[str] = []
        warnings: List[str] = []

        try:
            # Load YAML file
            with open(file_path, "r") as f:
                workflow = yaml.safe_load(f)

            # Fix YAML boolean key issues (on -> True in YAML 1.1)
            workflow = _fix_yaml_boolean_keys(workflow)

            if not workflow:
                errors.append("Empty or invalid YAML file")
                return False, errors, warnings

            # Validate against schema
            if self.validator:
                validation_errors = list(self.validator.iter_errors(workflow))

                for error in validation_errors:
                    # Format error message with path
                    path = (
                        " -> ".join(str(p) for p in error.path)
                        if error.path
                        else "root"
                    )
                    errors.append(f"{path}: {error.message}")

            # Additional semantic validations
            warnings.extend(self._semantic_validation(workflow))

            return len(errors) == 0, errors, warnings

        except yaml.YAMLError as e:
            errors.append(f"YAML parsing error: {e}")
            return False, errors, warnings
        except IOError as e:
            errors.append(f"File reading error: {e}")
            return False, errors, warnings
        except Exception as e:
            errors.append(f"Validation error: {e}")
            return False, errors, warnings

    def _semantic_validation(self, workflow: Dict[str, Any]) -> List[str]:
        """Perform additional semantic validation beyond schema."""
        warnings: List[str] = []

        # Check for missing 'on' trigger
        if "on" not in workflow:
            warnings.append("Workflow has no 'on' trigger defined")

        # Check for missing 'jobs'
        if "jobs" not in workflow:
            warnings.append("Workflow has no 'jobs' defined")
            return warnings

        jobs = workflow.get("jobs", {})
        if not isinstance(jobs, dict):
            warnings.append("'jobs' should be an object/dictionary")
            return warnings

        # Check each job
        for job_name, job_config in jobs.items():
            if not isinstance(job_config, dict):
                warnings.append(f"Job '{job_name}' has invalid configuration")
                continue

            # Check for runs-on
            if "runs-on" not in job_config:
                warnings.append(f"Job '{job_name}' missing 'runs-on' runner")

            # Check for steps
            if "steps" not in job_config:
                warnings.append(f"Job '{job_name}' missing 'steps'")
                continue

            steps = job_config.get("steps", [])
            if not isinstance(steps, list):
                warnings.append(f"Job '{job_name}' steps should be a list")
                continue

            # Check each step
            for idx, step in enumerate(steps):
                if not isinstance(step, dict):
                    warnings.append(
                        f"Job '{job_name}' step {idx + 1} has invalid format"
                    )
                    continue

                # Step must have either 'uses' or 'run'
                if "uses" not in step and "run" not in step:
                    step_name = step.get("name", f"step {idx + 1}")
                    warnings.append(
                        f"Job '{job_name}' {step_name} missing 'uses' or 'run'"
                    )

        # Check for deprecated patterns
        if "on" in workflow:
            on_config = workflow["on"]
            if isinstance(on_config, dict):
                # Check for deprecated branch patterns
                for event in ["push", "pull_request"]:
                    if event in on_config and isinstance(on_config[event], dict):
                        event_config = on_config[event]
                        if "branches-ignore" in event_config and "branches" in event_config:
                            warnings.append(
                                f"'{event}' has both 'branches' and 'branches-ignore' - "
                                "only one should be used"
                            )

        # Check for 'needs' referencing non-existent jobs
        job_names = set(jobs.keys())
        for job_name, job_config in jobs.items():
            if not isinstance(job_config, dict):
                continue
            needs = job_config.get("needs", [])
            if isinstance(needs, str):
                needs = [needs]
            if isinstance(needs, list):
                for needed_job in needs:
                    if needed_job not in job_names:
                        warnings.append(
                            f"Job '{job_name}' needs non-existent job '{needed_job}'"
                        )

        # Check for common security issues
        for job_name, job_config in jobs.items():
            if not isinstance(job_config, dict):
                continue
            steps = job_config.get("steps", [])
            if not isinstance(steps, list):
                continue

            for idx, step in enumerate(steps):
                if not isinstance(step, dict):
                    continue

                # Check for actions using @master or @main (should pin version)
                uses = step.get("uses", "")
                if isinstance(uses, str):
                    if uses.endswith("@master") or uses.endswith("@main"):
                        step_name = step.get("name", f"step {idx + 1}")
                        warnings.append(
                            f"Job '{job_name}' {step_name}: Action '{uses}' "
                            "uses unpinned branch - consider pinning to a specific version"
                        )

        return warnings

    def validate_content(self, content: str) -> Tuple[bool, List[str], List[str]]:
        """
        Validate GitHub Actions YAML content directly.

        Args:
            content: YAML content as string

        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        errors: List[str] = []
        warnings: List[str] = []

        try:
            workflow = yaml.safe_load(content)

            # Fix YAML boolean key issues (on -> True in YAML 1.1)
            workflow = _fix_yaml_boolean_keys(workflow)

            if not workflow:
                errors.append("Empty or invalid YAML content")
                return False, errors, warnings

            # Validate against schema
            if self.validator:
                validation_errors = list(self.validator.iter_errors(workflow))

                for error in validation_errors:
                    path = (
                        " -> ".join(str(p) for p in error.path)
                        if error.path
                        else "root"
                    )
                    errors.append(f"{path}: {error.message}")

            # Additional semantic validations
            warnings.extend(self._semantic_validation(workflow))

            return len(errors) == 0, errors, warnings

        except yaml.YAMLError as e:
            errors.append(f"YAML parsing error: {e}")
            return False, errors, warnings
        except Exception as e:
            errors.append(f"Validation error: {e}")
            return False, errors, warnings

    def get_schema_info(self) -> Dict[str, Any]:
        """Get information about the loaded schema."""
        info: Dict[str, Any] = {
            "schema_loaded": self.schema is not None,
            "cache_location": str(self.SCHEMA_CACHE_FILE),
            "cache_exists": self.SCHEMA_CACHE_FILE.exists(),
        }

        if self.CACHE_META_FILE.exists():
            try:
                with open(self.CACHE_META_FILE, "r") as f:
                    meta = json.load(f)
                    info.update(
                        {
                            "cached_at": meta.get("cached_at"),
                            "source_url": meta.get("source_url"),
                            "schema_hash": meta.get("schema_hash"),
                        }
                    )
            except (IOError, json.JSONDecodeError):
                pass

        return info


def main() -> None:
    """CLI interface for GitHub Actions validation."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Validate GitHub Actions workflow files against official schema"
    )
    parser.add_argument("file", help="Path to workflow .yml file")
    parser.add_argument(
        "--refresh", action="store_true", help="Force refresh of cached schema"
    )
    parser.add_argument("--info", action="store_true", help="Show schema information")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s: %(message)s",
    )

    # Create validator
    validator = GitHubActionsSchemaValidator(force_refresh=args.refresh)

    if args.info:
        info = validator.get_schema_info()
        print("GitHub Actions Schema Information:")
        for key, value in info.items():
            print(f"  {key}: {value}")
        return

    # Validate file
    is_valid, errors, warnings = validator.validate_file(args.file)

    # Output results
    if errors:
        print("\nVALIDATION FAILED")
        print("Errors found:")
        for i, error in enumerate(errors, 1):
            print(f"  {i}. {error}")

    if warnings:
        print("\nWARNINGS")
        for i, warning in enumerate(warnings, 1):
            print(f"  {i}. {warning}")

    if is_valid:
        print("\nVALIDATION PASSED" + (" (with warnings)" if warnings else ""))

    print(f"\nSummary: {len(errors)} errors, {len(warnings)} warnings")

    # Exit code
    sys.exit(0 if is_valid else 1)


if __name__ == "__main__":
    main()
