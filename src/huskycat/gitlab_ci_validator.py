#!/usr/bin/env python3
"""
GitLab CI Schema Validator with Dynamic Schema Fetching and Caching
Validates GitLab CI YAML files against the official GitLab CI JSON Schema
"""

import json
import yaml
import requests
import logging
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import jsonschema
from jsonschema import Draft7Validator, FormatChecker

logger = logging.getLogger(__name__)


class GitLabCISchemaValidator:
    """
    Validates GitLab CI configuration files against the official schema.
    Features:
    - Dynamic schema fetching from GitLab
    - Local caching with configurable refresh interval
    - JSON Schema Draft-07 validation
    - Detailed error reporting
    """
    
    # Official GitLab CI Schema URL
    SCHEMA_URL = "https://gitlab.com/gitlab-org/gitlab/-/raw/master/app/assets/javascripts/editor/schema/ci.json"
    
    # Alternative schema URLs for fallback
    FALLBACK_URLS = [
        "https://json.schemastore.org/gitlab-ci",
        "https://raw.githubusercontent.com/SchemaStore/schemastore/master/src/schemas/json/gitlab-ci.json"
    ]
    
    # Cache configuration
    CACHE_DIR = Path.home() / ".cache" / "huskycats"
    SCHEMA_CACHE_FILE = CACHE_DIR / "gitlab-ci-schema.json"
    CACHE_META_FILE = CACHE_DIR / "gitlab-ci-schema.meta.json"
    CACHE_REFRESH_DAYS = 7
    
    def __init__(self, force_refresh: bool = False):
        """Initialize the validator with optional forced schema refresh."""
        self.schema = None
        self.validator = None
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
            with open(self.CACHE_META_FILE, 'r') as f:
                meta = json.load(f)
                cached_date = datetime.fromisoformat(meta.get('cached_at', ''))
                if datetime.now() - cached_date > timedelta(days=self.CACHE_REFRESH_DAYS):
                    logger.info(f"Cache older than {self.CACHE_REFRESH_DAYS} days")
                    return True
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning(f"Error reading cache metadata: {e}")
            return True
        
        return False
    
    def _fetch_schema(self) -> Optional[Dict]:
        """Fetch the GitLab CI schema from the official source."""
        urls_to_try = [self.SCHEMA_URL] + self.FALLBACK_URLS
        
        for url in urls_to_try:
            try:
                logger.info(f"Fetching GitLab CI schema from: {url}")
                response = requests.get(url, timeout=30, headers={
                    'User-Agent': 'HuskyCat-Validator/2.0'
                })
                response.raise_for_status()
                
                schema = response.json()
                logger.info(f"Successfully fetched schema from {url}")
                
                # Validate it's a proper JSON Schema
                if '$schema' in schema or 'properties' in schema:
                    return schema
                else:
                    logger.warning(f"Invalid schema format from {url}")
                    
            except requests.RequestException as e:
                logger.warning(f"Failed to fetch from {url}: {e}")
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON from {url}: {e}")
        
        return None
    
    def _save_schema_to_cache(self, schema: Dict) -> None:
        """Save the schema to local cache with metadata."""
        try:
            # Save schema
            with open(self.SCHEMA_CACHE_FILE, 'w') as f:
                json.dump(schema, f, indent=2)
            
            # Save metadata
            meta = {
                'cached_at': datetime.now().isoformat(),
                'source_url': self.SCHEMA_URL,
                'schema_hash': hashlib.sha256(
                    json.dumps(schema, sort_keys=True).encode()
                ).hexdigest(),
                'cache_refresh_days': self.CACHE_REFRESH_DAYS
            }
            with open(self.CACHE_META_FILE, 'w') as f:
                json.dump(meta, f, indent=2)
            
            logger.info(f"Schema cached at {self.SCHEMA_CACHE_FILE}")
            
        except IOError as e:
            logger.error(f"Failed to save schema to cache: {e}")
    
    def _load_schema_from_cache(self) -> Optional[Dict]:
        """Load the schema from local cache."""
        try:
            with open(self.SCHEMA_CACHE_FILE, 'r') as f:
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
        self.validator = Draft7Validator(
            schema,
            format_checker=FormatChecker()
        )
    
    def _get_minimal_schema(self) -> Dict:
        """Return a minimal GitLab CI schema for fallback."""
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "stages": {"type": "array", "items": {"type": "string"}},
                "variables": {"type": "object"},
                "image": {"type": ["string", "object"]},
                "services": {"type": "array"},
                "before_script": {"type": ["array", "string"]},
                "after_script": {"type": ["array", "string"]},
                "cache": {"type": "object"},
                "artifacts": {"type": "object"}
            },
            "additionalProperties": {
                "type": "object",
                "properties": {
                    "script": {
                        "oneOf": [
                            {"type": "string"},
                            {"type": "array", "items": {"type": "string"}}
                        ]
                    },
                    "image": {"type": ["string", "object"]},
                    "stage": {"type": "string"},
                    "when": {"type": "string"},
                    "only": {"type": ["object", "array"]},
                    "except": {"type": ["object", "array"]},
                    "rules": {"type": "array"},
                    "needs": {"type": "array"},
                    "dependencies": {"type": "array"},
                    "artifacts": {"type": "object"},
                    "cache": {"type": "object"},
                    "retry": {"type": ["integer", "object"]},
                    "timeout": {"type": "string"},
                    "parallel": {"type": ["integer", "object"]},
                    "trigger": {"type": ["string", "object"]},
                    "extends": {"type": ["string", "array"]},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "allow_failure": {"type": ["boolean", "object"]},
                    "coverage": {"type": "string"},
                    "environment": {"type": ["string", "object"]},
                    "release": {"type": "object"},
                    "pages": {"type": "object"}
                }
            }
        }
    
    def validate_file(self, file_path: str) -> Tuple[bool, List[str], List[str]]:
        """
        Validate a GitLab CI YAML file against the schema.
        
        Args:
            file_path: Path to the .gitlab-ci.yml file
            
        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        errors = []
        warnings = []
        
        try:
            # Load YAML file
            with open(file_path, 'r') as f:
                ci_config = yaml.safe_load(f)
            
            if not ci_config:
                errors.append("Empty or invalid YAML file")
                return False, errors, warnings
            
            # Validate against schema
            validation_errors = list(self.validator.iter_errors(ci_config))
            
            for error in validation_errors:
                # Format error message with path
                path = " -> ".join(str(p) for p in error.path) if error.path else "root"
                errors.append(f"{path}: {error.message}")
            
            # Additional semantic validations
            warnings.extend(self._semantic_validation(ci_config))
            
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
    
    def _semantic_validation(self, config: Dict) -> List[str]:
        """Perform additional semantic validation beyond schema."""
        warnings = []
        
        # Check for unused stages
        if 'stages' in config:
            defined_stages = set(config['stages'])
            used_stages = set()
            
            for job_name, job_config in config.items():
                if isinstance(job_config, dict) and 'stage' in job_config:
                    used_stages.add(job_config['stage'])
            
            unused = defined_stages - used_stages
            for stage in unused:
                warnings.append(f"Defined stage never used: '{stage}'")
        
        # Check for deprecated keywords
        deprecated = {
            'types': 'Use "stages" instead of "types"',
            'type': 'Use "stage" instead of "type" in jobs'
        }
        
        for key, message in deprecated.items():
            if key in config:
                warnings.append(message)
        
        # Check for jobs without scripts or triggers
        for job_name, job_config in config.items():
            if job_name.startswith('.') or job_name in ['stages', 'variables', 'include']:
                continue
            if isinstance(job_config, dict):
                if 'script' not in job_config and 'trigger' not in job_config and 'extends' not in job_config:
                    warnings.append(f"Job '{job_name}' has no script, trigger, or extends")
        
        return warnings
    
    def validate_content(self, content: str) -> Tuple[bool, List[str], List[str]]:
        """
        Validate GitLab CI YAML content directly.
        
        Args:
            content: YAML content as string
            
        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        errors = []
        warnings = []
        
        try:
            ci_config = yaml.safe_load(content)
            
            if not ci_config:
                errors.append("Empty or invalid YAML content")
                return False, errors, warnings
            
            # Validate against schema
            validation_errors = list(self.validator.iter_errors(ci_config))
            
            for error in validation_errors:
                path = " -> ".join(str(p) for p in error.path) if error.path else "root"
                errors.append(f"{path}: {error.message}")
            
            # Additional semantic validations
            warnings.extend(self._semantic_validation(ci_config))
            
            return len(errors) == 0, errors, warnings
            
        except yaml.YAMLError as e:
            errors.append(f"YAML parsing error: {e}")
            return False, errors, warnings
        except Exception as e:
            errors.append(f"Validation error: {e}")
            return False, errors, warnings
    
    def get_schema_info(self) -> Dict[str, Any]:
        """Get information about the loaded schema."""
        info = {
            'schema_loaded': self.schema is not None,
            'cache_location': str(self.SCHEMA_CACHE_FILE),
            'cache_exists': self.SCHEMA_CACHE_FILE.exists()
        }
        
        if self.CACHE_META_FILE.exists():
            try:
                with open(self.CACHE_META_FILE, 'r') as f:
                    meta = json.load(f)
                    info.update({
                        'cached_at': meta.get('cached_at'),
                        'source_url': meta.get('source_url'),
                        'schema_hash': meta.get('schema_hash')
                    })
            except (IOError, json.JSONDecodeError):
                pass
        
        return info


def main():
    """CLI interface for GitLab CI validation."""
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(
        description='Validate GitLab CI YAML files against official schema'
    )
    parser.add_argument('file', help='Path to .gitlab-ci.yml file')
    parser.add_argument('--refresh', action='store_true', 
                       help='Force refresh of cached schema')
    parser.add_argument('--info', action='store_true',
                       help='Show schema information')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format='%(levelname)s: %(message)s'
    )
    
    # Create validator
    validator = GitLabCISchemaValidator(force_refresh=args.refresh)
    
    if args.info:
        info = validator.get_schema_info()
        print("GitLab CI Schema Information:")
        for key, value in info.items():
            print(f"  {key}: {value}")
        return
    
    # Validate file
    is_valid, errors, warnings = validator.validate_file(args.file)
    
    # Output results
    if errors:
        print("\n❌ VALIDATION FAILED")
        print("Errors found:")
        for i, error in enumerate(errors, 1):
            print(f"  {i}. {error}")
    
    if warnings:
        print("\n⚠️  WARNINGS")
        for i, warning in enumerate(warnings, 1):
            print(f"  {i}. {warning}")
    
    if is_valid:
        print("\n✅ VALIDATION PASSED" + (" (with warnings)" if warnings else ""))
    
    print(f"\nSummary: {len(errors)} errors, {len(warnings)} warnings")
    
    # Exit code
    sys.exit(0 if is_valid else 1)


if __name__ == "__main__":
    main()