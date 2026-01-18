# SPDX-License-Identifier: Apache-2.0
"""
HuskyCat integrations module.

Provides integration points with external tools and services:
- RemoteJuggler: Git identity management and profile switching
"""

from .remote_juggler import RemoteJugglerIntegration, is_remote_juggler_available

__all__ = [
    "RemoteJugglerIntegration",
    "is_remote_juggler_available",
]
