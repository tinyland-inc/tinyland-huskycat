#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
HuskyCat Validators Package

This package contains all validator implementations for HuskyCat.
Each validator is a separate module for maintainability and testability.

Usage:
    from huskycat.validators import (
        ValidationResult,
        Validator,
        BlackValidator,
        RuffValidator,
        # ... etc
    )

Or import specific validators:
    from huskycat.validators.black import BlackValidator
    from huskycat.validators.ruff import RuffValidator
"""

# Base classes
from huskycat.validators.base import ValidationResult, Validator

# Utility functions
from huskycat.validators._utils import (
    get_gpl_sidecar,
    is_gpl_tool,
    is_running_in_container,
)

# Python validators
from huskycat.validators.black import BlackValidator
from huskycat.validators.autoflake import AutoflakeValidator
from huskycat.validators.flake8 import Flake8Validator
from huskycat.validators.mypy import MypyValidator
from huskycat.validators.ruff import RuffValidator
from huskycat.validators.isort import IsortValidator
from huskycat.validators.bandit import BanditValidator

# TOML validator
from huskycat.validators.taplo import TaploValidator

# Terraform validator
from huskycat.validators.terraform import TerraformValidator

# JavaScript/TypeScript validators
from huskycat.validators.eslint import ESLintValidator
from huskycat.validators.prettier import PrettierValidator

# Chapel validator
from huskycat.validators.chapel import ChapelValidator

# Ansible validator
from huskycat.validators.ansible_lint import AnsibleLintValidator

# YAML validator (GPL)
from huskycat.validators.yamllint import YamlLintValidator

# Container validators (GPL)
from huskycat.validators.hadolint import HadolintValidator

# Shell validator (GPL)
from huskycat.validators.shellcheck import ShellcheckValidator

# GitLab CI validator
from huskycat.validators.gitlab_ci import GitLabCIValidator

__all__ = [
    # Base classes
    "ValidationResult",
    "Validator",
    # Utility functions
    "get_gpl_sidecar",
    "is_gpl_tool",
    "is_running_in_container",
    # Python validators
    "BlackValidator",
    "AutoflakeValidator",
    "Flake8Validator",
    "MypyValidator",
    "RuffValidator",
    "IsortValidator",
    "BanditValidator",
    # TOML validator
    "TaploValidator",
    # Terraform validator
    "TerraformValidator",
    # JavaScript/TypeScript validators
    "ESLintValidator",
    "PrettierValidator",
    # Chapel validator
    "ChapelValidator",
    # Ansible validator
    "AnsibleLintValidator",
    # YAML validator
    "YamlLintValidator",
    # Container validators
    "HadolintValidator",
    # Shell validator
    "ShellcheckValidator",
    # GitLab CI validator
    "GitLabCIValidator",
]
