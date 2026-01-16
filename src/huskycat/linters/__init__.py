# SPDX-License-Identifier: Apache-2.0
"""
HuskyCat Linters Module
Clean-room implementations of code quality linters
"""

__all__ = ["yaml_lint", "yaml_lint_validator", "DockerLintValidator"]

try:
    from huskycat.linters.dockerlint_validator import DockerLintValidator
except ImportError:
    # dockerfile library not installed, validator won't be available
    pass
