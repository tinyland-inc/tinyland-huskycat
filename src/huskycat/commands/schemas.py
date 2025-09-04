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
            "cache_file": "gitlab-ci-schema.json"
        },
        "github-actions": {
            "url": "https://json.schemastore.org/github-workflow",
            "fallback": None,
            "cache_file": "github-actions-schema.json"
        },
        "docker-compose": {
            "url": "https://json.schemastore.org/docker-compose",
            "fallback": None,
            "cache_file": "docker-compose-schema.json"
        },
        "package-json": {
            "url": "https://json.schemastore.org/package",
            "fallback": None,
            "cache_file": "package-schema.json"
        }
    }
    
    @property
    def name(self) -> str:
        return "update-schemas"
    
    @property
    def description(self) -> str:
        return "Update validation schemas from official sources"
    
    def execute(self, force: bool = False) -> CommandResult:
        """
        Update all schemas.
        
        Args:
            force: Force update even if cache is fresh
            
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
                cache_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
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
        
        # Determine status
        if failed and not updated:
            status = CommandStatus.FAILED
            message = f"Failed to update schemas: {', '.join(failed)}"
        elif failed:
            status = CommandStatus.WARNING
            message = f"Updated {len(updated)} schemas, {len(failed)} failed"
        else:
            status = CommandStatus.SUCCESS
            message = f"Updated {len(updated)} schemas, {len(skipped)} already up to date"
        
        return CommandResult(
            status=status,
            message=message,
            data={
                "updated": updated,
                "failed": failed,
                "skipped": skipped,
                "cache_dir": str(cache_dir)
            }
        )