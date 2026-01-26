#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
HuskyCat Validators Utilities

Internal utilities for validators package including GPL sidecar management.
"""

import logging
from typing import Optional

from huskycat.core.tool_selector import get_gpl_tools
from huskycat.core.gpl_client import GPLSidecarClient

logger = logging.getLogger(__name__)

# GPL Sidecar client (lazy initialized)
_gpl_sidecar_client: Optional[GPLSidecarClient] = None
_gpl_sidecar_checked: bool = False


def get_gpl_sidecar() -> Optional[GPLSidecarClient]:
    """Get GPL sidecar client if available.

    Returns lazily-initialized client if sidecar is running, None otherwise.
    Caches the result to avoid repeated socket connection attempts.
    """
    global _gpl_sidecar_client, _gpl_sidecar_checked

    if _gpl_sidecar_checked:
        return _gpl_sidecar_client

    _gpl_sidecar_checked = True
    client = GPLSidecarClient()

    if client.is_available():
        logger.info("GPL sidecar is available - using IPC for GPL tools")
        _gpl_sidecar_client = client
        return client
    else:
        logger.debug("GPL sidecar not available - GPL tools will use local/container execution")
        return None


def is_gpl_tool(tool_name: str) -> bool:
    """Check if a tool is a GPL-licensed tool requiring sidecar execution."""
    gpl_tools = get_gpl_tools()
    return tool_name in gpl_tools


def is_running_in_container() -> bool:
    """Detect if we're running inside a container.

    This is a standalone utility function that can be used without
    instantiating a Validator class.

    Returns:
        True if running inside Docker, Podman, or other container runtime.
    """
    import os

    return (
        os.path.exists("/.dockerenv")  # Docker
        or bool(os.environ.get("container"))  # Podman
        or os.path.exists("/run/.containerenv")  # Podman
    )
