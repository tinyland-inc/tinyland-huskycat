"""
Clean command for removing cache and temporary files.
"""

import shutil
from pathlib import Path

from ..core.base import BaseCommand, CommandResult, CommandStatus


class CleanCommand(BaseCommand):
    """Command to clean cache and temporary files."""
    
    @property
    def name(self) -> str:
        return "clean"
    
    @property
    def description(self) -> str:
        return "Clean cache and temporary files"
    
    def execute(self, all_files: bool = False) -> CommandResult:
        """
        Clean cache and temporary files.
        
        Args:
            all_files: Remove all cache including schemas
            
        Returns:
            CommandResult with cleanup status
        """
        removed_items = []
        
        # Clean cache directory
        cache_dir = Path.home() / ".cache" / "huskycats"
        if cache_dir.exists():
            if all_files:
                # Remove entire cache directory
                shutil.rmtree(cache_dir)
                removed_items.append(str(cache_dir))
                self.log(f"Removed cache directory: {cache_dir}")
            else:
                # Remove only temporary files, keep schemas
                for temp_file in cache_dir.glob("*.tmp"):
                    temp_file.unlink()
                    removed_items.append(str(temp_file))
                for log_file in cache_dir.glob("*.log"):
                    log_file.unlink()
                    removed_items.append(str(log_file))
                self.log(f"Cleaned temporary files from {cache_dir}")
        
        # Clean Python cache
        for cache_pattern in ["__pycache__", "*.pyc", ".pytest_cache", ".mypy_cache"]:
            for cache_item in Path(".").rglob(cache_pattern):
                if cache_item.is_dir():
                    shutil.rmtree(cache_item)
                else:
                    cache_item.unlink()
                removed_items.append(str(cache_item))
        
        # Clean build artifacts
        for build_dir in ["build", "dist", "*.egg-info"]:
            for build_item in Path(".").glob(build_dir):
                if build_item.is_dir():
                    shutil.rmtree(build_item)
                else:
                    build_item.unlink()
                removed_items.append(str(build_item))
        
        if removed_items:
            return CommandResult(
                status=CommandStatus.SUCCESS,
                message=f"Cleaned {len(removed_items)} items",
                data={"removed": removed_items}
            )
        else:
            return CommandResult(
                status=CommandStatus.SUCCESS,
                message="Nothing to clean"
            )