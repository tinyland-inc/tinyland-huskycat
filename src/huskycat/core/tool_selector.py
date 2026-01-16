# SPDX-License-Identifier: Apache-2.0
"""
Tool selector for license-compliant linting.

This module provides tool selection logic based on:
- License compliance (Apache-2.0 vs GPL tools)
- Linting mode (FAST binary-only vs COMPREHENSIVE with containers)
- File types being validated
- Execution context (bundled binary, local tools, container)
"""

import os
from enum import Enum
from pathlib import Path
from typing import Dict, List, Set

from dataclasses import dataclass


class LintingMode(Enum):
    """Linting mode determines tool selection and execution strategy."""

    FAST = "fast"  # Binary-only, Apache-2.0/MIT tools (git hooks, CLI quick checks)
    COMPREHENSIVE = "comprehensive"  # All tools including GPL (CI, full validation)


class ToolLicense(Enum):
    """License types for validation tools."""

    MIT = "mit"
    APACHE = "apache"
    GPL = "gpl"  # GPL-3.0 or similar copyleft licenses


@dataclass
class ToolInfo:
    """Metadata about a validation tool."""

    name: str
    license: ToolLicense
    description: str
    file_types: Set[str]  # File types this tool handles (python, shell, yaml, etc.)
    bundled: bool = True  # Available in fat binary
    validator_class: str = ""  # Class name in unified_validation.py

    def __post_init__(self):
        """Auto-generate validator class name if not provided."""
        if not self.validator_class:
            # Convert tool name to validator class name
            # e.g., "python-black" -> "BlackValidator"
            parts = self.name.split("-")
            self.validator_class = "".join(p.capitalize() for p in parts) + "Validator"


# Registry of all tools with license and capability metadata
TOOL_REGISTRY: Dict[str, ToolInfo] = {
    # Python tools - MIT/Apache
    "ruff": ToolInfo(
        "ruff",
        ToolLicense.MIT,
        "Fast Python linting and formatting",
        {"python"},
        bundled=True,
        validator_class="RuffValidator",
    ),
    "python-black": ToolInfo(
        "python-black",
        ToolLicense.MIT,
        "Python code formatter",
        {"python"},
        bundled=True,
        validator_class="BlackValidator",
    ),
    "mypy": ToolInfo(
        "mypy",
        ToolLicense.MIT,
        "Python static type checker",
        {"python"},
        bundled=True,
        validator_class="MypyValidator",
    ),
    "flake8": ToolInfo(
        "flake8",
        ToolLicense.MIT,
        "Python style guide enforcer",
        {"python"},
        bundled=True,
        validator_class="Flake8Validator",
    ),
    "isort": ToolInfo(
        "isort",
        ToolLicense.MIT,
        "Python import sorter",
        {"python"},
        bundled=True,
        validator_class="IsortValidator",
    ),
    "autoflake": ToolInfo(
        "autoflake",
        ToolLicense.MIT,
        "Remove unused imports/variables",
        {"python"},
        bundled=True,
        validator_class="AutoflakeValidator",
    ),
    "bandit": ToolInfo(
        "bandit",
        ToolLicense.APACHE,
        "Python security vulnerability scanner",
        {"python"},
        bundled=True,
        validator_class="BanditValidator",
    ),
    # TOML tools - MIT
    "taplo": ToolInfo(
        "taplo",
        ToolLicense.MIT,
        "TOML formatter and linter",
        {"toml"},
        bundled=True,
        validator_class="TaploValidator",
    ),
    # JavaScript/TypeScript tools - MIT
    "js-eslint": ToolInfo(
        "js-eslint",
        ToolLicense.MIT,
        "JavaScript/TypeScript linter",
        {"javascript", "typescript"},
        bundled=True,
        validator_class="ESLintValidator",
    ),
    "js-prettier": ToolInfo(
        "js-prettier",
        ToolLicense.MIT,
        "JavaScript/TypeScript/JSON formatter",
        {"javascript", "typescript", "json"},
        bundled=True,
        validator_class="PrettierValidator",
    ),
    # Infrastructure as Code - Apache
    "terraform": ToolInfo(
        "terraform",
        ToolLicense.APACHE,
        "Terraform plan validator",
        {"terraform"},
        bundled=True,
        validator_class="TerraformValidator",
    ),
    "ansible-lint": ToolInfo(
        "ansible-lint",
        ToolLicense.APACHE,
        "Ansible playbook linter",
        {"ansible"},
        bundled=True,
        validator_class="AnsibleLintValidator",
    ),
    # Chapel language - Apache
    "chapel": ToolInfo(
        "chapel",
        ToolLicense.APACHE,
        "Chapel language formatter",
        {"chapel"},
        bundled=True,
        validator_class="ChapelValidator",
    ),
    # CI/CD validators - Project-specific (Apache)
    "gitlab-ci": ToolInfo(
        "gitlab-ci",
        ToolLicense.APACHE,
        "GitLab CI configuration validator",
        {"yaml"},
        bundled=True,
        validator_class="GitLabCIValidator",
    ),
    # GPL tools - container only
    "shellcheck": ToolInfo(
        "shellcheck",
        ToolLicense.GPL,
        "Shell script static analysis",
        {"shell", "bash"},
        bundled=False,
        validator_class="ShellcheckValidator",
    ),
    "hadolint": ToolInfo(
        "hadolint",
        ToolLicense.GPL,
        "Comprehensive Dockerfile linting",
        {"dockerfile"},
        bundled=False,
        validator_class="HadolintValidator",
    ),
    "yamllint": ToolInfo(
        "yamllint",
        ToolLicense.GPL,
        "Comprehensive YAML linting",
        {"yaml"},
        bundled=False,
        validator_class="YamlLintValidator",
    ),
}


def get_tools_for_mode(
    mode: LintingMode, file_types: Set[str], include_ci: bool = False
) -> Set[str]:
    """
    Select tools based on linting mode and file types.

    Args:
        mode: Linting mode (FAST or COMPREHENSIVE)
        file_types: Set of file types to validate (e.g., {"python", "yaml"})
        include_ci: Include CI-specific validators (GitLab CI, etc.)

    Returns:
        Set of tool names to run

    Example:
        >>> get_tools_for_mode(LintingMode.FAST, {"python"})
        {'ruff', 'mypy', 'python-black', 'flake8'}
    """
    tools = set()

    for tool_name, tool_info in TOOL_REGISTRY.items():
        # Skip CI validators unless explicitly requested
        if tool_name == "gitlab-ci" and not include_ci:
            continue

        # In FAST mode, skip GPL tools
        if mode == LintingMode.FAST and tool_info.license == ToolLicense.GPL:
            continue

        # Check if tool handles any of the requested file types
        if file_types & tool_info.file_types:
            tools.add(tool_name)

    return tools


def get_bundled_tools() -> Set[str]:
    """
    Get tools available in fat binary (non-GPL).

    Returns:
        Set of bundled tool names (Apache-2.0 and MIT only)

    Example:
        >>> tools = get_bundled_tools()
        >>> "ruff" in tools
        True
        >>> "shellcheck" in tools
        False
    """
    return {
        name for name, info in TOOL_REGISTRY.items() if info.bundled and info.license != ToolLicense.GPL
    }


def get_gpl_tools() -> Set[str]:
    """
    Get GPL tools requiring container/sidecar execution.

    Returns:
        Set of GPL tool names

    Example:
        >>> tools = get_gpl_tools()
        >>> "shellcheck" in tools
        True
        >>> "ruff" in tools
        False
    """
    return {name for name, info in TOOL_REGISTRY.items() if info.license == ToolLicense.GPL}


def detect_file_types(paths: List[Path]) -> Set[str]:
    """
    Detect file types from file paths.

    This maps file extensions and filenames to logical file types that
    tools understand.

    Args:
        paths: List of file paths to analyze

    Returns:
        Set of detected file types (e.g., {"python", "yaml", "shell"})

    Example:
        >>> paths = [Path("test.py"), Path(".gitlab-ci.yml"), Path("script.sh")]
        >>> detect_file_types(paths)
        {'python', 'yaml', 'shell'}
    """
    file_types = set()

    # Extension to file type mapping
    EXTENSION_MAP = {
        ".py": "python",
        ".pyi": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".sh": "shell",
        ".bash": "bash",
        ".yml": "yaml",
        ".yaml": "yaml",
        ".toml": "toml",
        ".json": "json",
        ".tf": "terraform",
        ".hcl": "terraform",
        ".chpl": "chapel",
        "Dockerfile": "dockerfile",
        "Containerfile": "dockerfile",
    }

    # Filename pattern matching (for files without extensions)
    FILENAME_PATTERNS = {
        "Dockerfile": "dockerfile",
        "Containerfile": "dockerfile",
        ".gitlab-ci.yml": "yaml",
        "gitlab-ci.yml": "yaml",
        ".github": "yaml",  # GitHub Actions
    }

    for path in paths:
        path_obj = Path(path) if not isinstance(path, Path) else path

        # Check extension
        ext = path_obj.suffix.lower()
        if ext in EXTENSION_MAP:
            file_types.add(EXTENSION_MAP[ext])

        # Check filename patterns
        filename = path_obj.name
        if filename in FILENAME_PATTERNS:
            file_types.add(FILENAME_PATTERNS[filename])

        # Check for Ansible files (special detection)
        if filename.endswith(".yml") or filename.endswith(".yaml"):
            # Heuristic: if in playbooks/ or roles/ directory, likely Ansible
            parts = path_obj.parts
            if any(p in {"playbooks", "roles", "tasks", "handlers"} for p in parts):
                file_types.add("ansible")

        # Shebang detection for shell scripts (if file exists)
        if path_obj.exists() and path_obj.is_file() and ext == "":
            try:
                with open(path_obj, "r", encoding="utf-8", errors="ignore") as f:
                    first_line = f.readline()
                    if first_line.startswith("#!"):
                        if "bash" in first_line or "sh" in first_line:
                            file_types.add("shell")
                        elif "python" in first_line:
                            file_types.add("python")
            except (IOError, PermissionError):
                pass

    return file_types


def get_mode_from_env() -> LintingMode:
    """
    Detect linting mode from environment variables.

    Checks:
    - HUSKYCAT_LINTING_MODE: Explicit mode setting
    - HUSKYCAT_MODE: Product mode (git_hooks -> FAST, ci -> COMPREHENSIVE)
    - Container detection: In container -> COMPREHENSIVE

    Returns:
        LintingMode enum value

    Example:
        >>> os.environ["HUSKYCAT_LINTING_MODE"] = "fast"
        >>> get_mode_from_env()
        <LintingMode.FAST: 'fast'>
    """
    # Explicit linting mode
    mode_str = os.getenv("HUSKYCAT_LINTING_MODE", "").lower()
    if mode_str == "fast":
        return LintingMode.FAST
    elif mode_str == "comprehensive":
        return LintingMode.COMPREHENSIVE

    # Infer from product mode
    product_mode = os.getenv("HUSKYCAT_MODE", "").lower()
    if product_mode in ("git_hooks", "cli"):
        return LintingMode.FAST
    elif product_mode in ("ci", "pipeline"):
        return LintingMode.COMPREHENSIVE

    # Container detection
    if os.path.exists("/.dockerenv") or os.path.exists("/run/.containerenv"):
        return LintingMode.COMPREHENSIVE

    # Default to FAST for better UX
    return LintingMode.FAST


def get_tool_info(tool_name: str) -> ToolInfo:
    """
    Get metadata for a specific tool.

    Args:
        tool_name: Name of the tool

    Returns:
        ToolInfo object

    Raises:
        KeyError: If tool not found in registry

    Example:
        >>> info = get_tool_info("ruff")
        >>> info.license
        <ToolLicense.MIT: 'mit'>
    """
    if tool_name not in TOOL_REGISTRY:
        raise KeyError(f"Tool '{tool_name}' not found in registry")
    return TOOL_REGISTRY[tool_name]


def is_tool_bundled(tool_name: str) -> bool:
    """
    Check if a tool is bundled in the fat binary.

    Args:
        tool_name: Name of the tool

    Returns:
        True if tool is bundled, False otherwise

    Example:
        >>> is_tool_bundled("ruff")
        True
        >>> is_tool_bundled("shellcheck")
        False
    """
    try:
        info = get_tool_info(tool_name)
        return info.bundled
    except KeyError:
        return False


def get_tools_for_file_type(file_type: str, mode: LintingMode = LintingMode.FAST) -> List[str]:
    """
    Get all tools that can validate a specific file type.

    Args:
        file_type: File type (e.g., "python", "yaml")
        mode: Linting mode (affects GPL tool inclusion)

    Returns:
        List of tool names sorted by priority

    Example:
        >>> get_tools_for_file_type("python", LintingMode.FAST)
        ['ruff', 'mypy', 'python-black', 'flake8', 'isort', 'autoflake', 'bandit']
    """
    tools = []

    for tool_name, tool_info in TOOL_REGISTRY.items():
        # Skip GPL tools in FAST mode
        if mode == LintingMode.FAST and tool_info.license == ToolLicense.GPL:
            continue

        if file_type in tool_info.file_types:
            tools.append(tool_name)

    # Sort by priority: formatters first, then linters, then type checkers
    priority_order = {
        "python-black": 0,
        "js-prettier": 0,
        "taplo": 0,
        "isort": 1,
        "ruff": 2,
        "flake8": 3,
        "mypy": 4,
    }

    tools.sort(key=lambda t: priority_order.get(t, 10))
    return tools


# Convenience sets for common tool groupings
FAST_PYTHON_TOOLS = {"ruff", "mypy", "python-black", "flake8"}
COMPREHENSIVE_PYTHON_TOOLS = FAST_PYTHON_TOOLS | {"isort", "autoflake", "bandit"}

FAST_YAML_TOOLS = set()  # No bundled YAML linters (basic rules only)
COMPREHENSIVE_YAML_TOOLS = {"yamllint"}  # GPL tool

FAST_SHELL_TOOLS = set()  # No Apache/MIT shell linters available
COMPREHENSIVE_SHELL_TOOLS = {"shellcheck"}  # GPL tool

FAST_DOCKERFILE_TOOLS = set()  # Basic checks in validator
COMPREHENSIVE_DOCKERFILE_TOOLS = {"hadolint"}  # GPL tool
