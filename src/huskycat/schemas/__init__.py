"""
JSON schemas for HuskyCat configuration files.

This package contains JSON Schema files for IDE autocompletion
and validation of HuskyCat configuration files.
"""

import json
from pathlib import Path
from typing import Any, Dict

_SCHEMA_DIR = Path(__file__).parent


def get_config_schema() -> Dict[str, Any]:
    """
    Get the HuskyCat configuration JSON Schema.

    Returns:
        Dict containing the JSON Schema for .huskycat.yaml
    """
    schema_path = _SCHEMA_DIR / "huskycat-config.schema.json"
    return json.loads(schema_path.read_text())


def get_schema_path() -> Path:
    """
    Get the path to the config schema file.

    Returns:
        Path to huskycat-config.schema.json
    """
    return _SCHEMA_DIR / "huskycat-config.schema.json"


__all__ = ["get_config_schema", "get_schema_path"]
