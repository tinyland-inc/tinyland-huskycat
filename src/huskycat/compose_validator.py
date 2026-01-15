#!/usr/bin/env python3
"""
Docker Compose Schema Validator with Dynamic Schema Fetching and Caching.

Validates Docker Compose and Podman Compose YAML files against the official JSON Schema.
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


class ComposeSchemaValidator:
    """
    Validates Docker/Podman Compose files against the official schema.

    Features:
    - Dynamic schema fetching from SchemaStore
    - Local caching with configurable refresh interval
    - JSON Schema Draft-07 validation
    - Detailed error reporting
    - Semantic validation for common issues
    """

    # Official Docker Compose Schema URL (SchemaStore is canonical)
    SCHEMA_URL = "https://json.schemastore.org/compose-spec.json"

    # Alternative schema URLs for fallback
    FALLBACK_URLS = [
        "https://raw.githubusercontent.com/compose-spec/compose-spec/master/schema/compose-spec.json",
        "https://raw.githubusercontent.com/SchemaStore/schemastore/master/src/schemas/json/compose-spec.json",
    ]

    # Cache configuration
    CACHE_DIR = Path.home() / ".cache" / "huskycats"
    SCHEMA_CACHE_FILE = CACHE_DIR / "compose-schema.json"
    CACHE_META_FILE = CACHE_DIR / "compose-schema.meta.json"
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
        """Fetch the Compose schema from the official source."""
        urls_to_try = [self.SCHEMA_URL] + self.FALLBACK_URLS

        for url in urls_to_try:
            try:
                logger.info(f"Fetching Compose schema from: {url}")
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
        """Return a minimal Compose schema for fallback."""
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "version": {"type": "string"},
                "name": {"type": "string"},
                "services": {
                    "type": "object",
                    "additionalProperties": {
                        "type": "object",
                        "properties": {
                            "image": {"type": "string"},
                            "build": {
                                "oneOf": [{"type": "string"}, {"type": "object"}]
                            },
                            "container_name": {"type": "string"},
                            "command": {
                                "oneOf": [
                                    {"type": "string"},
                                    {"type": "array", "items": {"type": "string"}},
                                ]
                            },
                            "entrypoint": {
                                "oneOf": [
                                    {"type": "string"},
                                    {"type": "array", "items": {"type": "string"}},
                                ]
                            },
                            "environment": {
                                "oneOf": [
                                    {"type": "object"},
                                    {"type": "array", "items": {"type": "string"}},
                                ]
                            },
                            "env_file": {
                                "oneOf": [
                                    {"type": "string"},
                                    {"type": "array", "items": {"type": "string"}},
                                ]
                            },
                            "ports": {"type": "array"},
                            "volumes": {"type": "array"},
                            "networks": {
                                "oneOf": [
                                    {"type": "array", "items": {"type": "string"}},
                                    {"type": "object"},
                                ]
                            },
                            "depends_on": {
                                "oneOf": [
                                    {"type": "array", "items": {"type": "string"}},
                                    {"type": "object"},
                                ]
                            },
                            "restart": {"type": "string"},
                            "healthcheck": {"type": "object"},
                            "labels": {
                                "oneOf": [
                                    {"type": "object"},
                                    {"type": "array", "items": {"type": "string"}},
                                ]
                            },
                            "deploy": {"type": "object"},
                            "logging": {"type": "object"},
                            "secrets": {"type": "array"},
                            "configs": {"type": "array"},
                            "expose": {"type": "array"},
                            "extra_hosts": {"type": "array"},
                            "working_dir": {"type": "string"},
                            "user": {"type": "string"},
                            "privileged": {"type": "boolean"},
                            "tty": {"type": "boolean"},
                            "stdin_open": {"type": "boolean"},
                        },
                    },
                },
                "networks": {"type": "object"},
                "volumes": {"type": "object"},
                "secrets": {"type": "object"},
                "configs": {"type": "object"},
            },
        }

    def validate_file(self, file_path: str) -> Tuple[bool, List[str], List[str]]:
        """
        Validate a Compose YAML file against the schema.

        Args:
            file_path: Path to the compose .yml file

        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        errors: List[str] = []
        warnings: List[str] = []

        try:
            # Load YAML file
            with open(file_path, "r") as f:
                compose_config = yaml.safe_load(f)

            if not compose_config:
                errors.append("Empty or invalid YAML file")
                return False, errors, warnings

            # Validate against schema
            if self.validator:
                validation_errors = list(self.validator.iter_errors(compose_config))

                for error in validation_errors:
                    # Format error message with path
                    path = (
                        " -> ".join(str(p) for p in error.path)
                        if error.path
                        else "root"
                    )
                    errors.append(f"{path}: {error.message}")

            # Additional semantic validations
            warnings.extend(self._semantic_validation(compose_config))

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

    def _semantic_validation(self, config: Dict[str, Any]) -> List[str]:
        """Perform additional semantic validation beyond schema."""
        warnings: List[str] = []

        # Check for deprecated version field
        if "version" in config:
            version = config.get("version", "")
            if version:
                warnings.append(
                    f"'version' field ('{version}') is obsolete in Compose Specification - "
                    "consider removing it"
                )

        # Check for services
        services = config.get("services", {})
        if not services:
            warnings.append("No services defined in compose file")
            return warnings

        if not isinstance(services, dict):
            warnings.append("'services' should be an object/dictionary")
            return warnings

        # Check each service
        defined_networks = set(config.get("networks", {}).keys())
        defined_volumes = set(config.get("volumes", {}).keys())
        defined_secrets = set(config.get("secrets", {}).keys())
        defined_configs = set(config.get("configs", {}).keys())
        service_names = set(services.keys())

        for service_name, service_config in services.items():
            if not isinstance(service_config, dict):
                warnings.append(f"Service '{service_name}' has invalid configuration")
                continue

            # Check that service has either image or build
            if "image" not in service_config and "build" not in service_config:
                warnings.append(
                    f"Service '{service_name}' missing 'image' or 'build' - "
                    "one is required"
                )

            # Check depends_on references
            depends_on = service_config.get("depends_on", [])
            if isinstance(depends_on, list):
                for dep in depends_on:
                    if dep not in service_names:
                        warnings.append(
                            f"Service '{service_name}' depends on non-existent "
                            f"service '{dep}'"
                        )
            elif isinstance(depends_on, dict):
                for dep in depends_on.keys():
                    if dep not in service_names:
                        warnings.append(
                            f"Service '{service_name}' depends on non-existent "
                            f"service '{dep}'"
                        )

            # Check network references
            networks = service_config.get("networks", [])
            network_names = []
            if isinstance(networks, list):
                network_names = networks
            elif isinstance(networks, dict):
                network_names = list(networks.keys())

            for net in network_names:
                if net != "default" and defined_networks and net not in defined_networks:
                    warnings.append(
                        f"Service '{service_name}' uses undefined network '{net}'"
                    )

            # Check volume references (for named volumes)
            volumes = service_config.get("volumes", [])
            if isinstance(volumes, list):
                for vol in volumes:
                    if isinstance(vol, str):
                        # Parse volume string: source:target[:options]
                        parts = vol.split(":")
                        if len(parts) >= 2:
                            source = parts[0]
                            # If source doesn't start with . or / it's a named volume
                            if (
                                not source.startswith(".")
                                and not source.startswith("/")
                                and source not in defined_volumes
                                and defined_volumes
                            ):
                                warnings.append(
                                    f"Service '{service_name}' uses undefined "
                                    f"volume '{source}'"
                                )
                    elif isinstance(vol, dict):
                        source = vol.get("source", "")
                        vol_type = vol.get("type", "volume")
                        if (
                            vol_type == "volume"
                            and source
                            and source not in defined_volumes
                            and defined_volumes
                        ):
                            warnings.append(
                                f"Service '{service_name}' uses undefined "
                                f"volume '{source}'"
                            )

            # Check secret references
            secrets = service_config.get("secrets", [])
            if isinstance(secrets, list):
                for secret in secrets:
                    secret_name = (
                        secret if isinstance(secret, str) else secret.get("source", "")
                    )
                    if secret_name and defined_secrets and secret_name not in defined_secrets:
                        warnings.append(
                            f"Service '{service_name}' uses undefined "
                            f"secret '{secret_name}'"
                        )

            # Check config references
            configs = service_config.get("configs", [])
            if isinstance(configs, list):
                for cfg in configs:
                    config_name = (
                        cfg if isinstance(cfg, str) else cfg.get("source", "")
                    )
                    if config_name and defined_configs and config_name not in defined_configs:
                        warnings.append(
                            f"Service '{service_name}' uses undefined "
                            f"config '{config_name}'"
                        )

            # Check for common security issues
            if service_config.get("privileged", False):
                warnings.append(
                    f"Service '{service_name}' runs in privileged mode - "
                    "ensure this is necessary"
                )

            # Check for latest tag
            image = service_config.get("image", "")
            if isinstance(image, str) and (
                image.endswith(":latest") or ":" not in image
            ):
                warnings.append(
                    f"Service '{service_name}' uses image without specific tag - "
                    "consider pinning to a specific version"
                )

        return warnings

    def validate_content(self, content: str) -> Tuple[bool, List[str], List[str]]:
        """
        Validate Compose YAML content directly.

        Args:
            content: YAML content as string

        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        errors: List[str] = []
        warnings: List[str] = []

        try:
            compose_config = yaml.safe_load(content)

            if not compose_config:
                errors.append("Empty or invalid YAML content")
                return False, errors, warnings

            # Validate against schema
            if self.validator:
                validation_errors = list(self.validator.iter_errors(compose_config))

                for error in validation_errors:
                    path = (
                        " -> ".join(str(p) for p in error.path)
                        if error.path
                        else "root"
                    )
                    errors.append(f"{path}: {error.message}")

            # Additional semantic validations
            warnings.extend(self._semantic_validation(compose_config))

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
    """CLI interface for Compose validation."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Validate Docker/Podman Compose files against official schema"
    )
    parser.add_argument("file", help="Path to compose .yml file")
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
    validator = ComposeSchemaValidator(force_refresh=args.refresh)

    if args.info:
        info = validator.get_schema_info()
        print("Compose Schema Information:")
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
