"""
CLI interface for HuskyCat using factory pattern.
"""

import sys
import argparse
from pathlib import Path

from .core.factory import HuskyCatFactory
from .core.base import CommandStatus


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for HuskyCat CLI."""
    parser = argparse.ArgumentParser(
        prog="huskycat",
        description="Universal Code Validation Platform with MCP Server Integration",
    )
    parser.add_argument("--version", action="version", version="%(prog)s 2.0.0")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )
    parser.add_argument(
        "--config-dir", type=Path, help="Configuration directory (default: ~/.huskycat)"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Run validation on files")
    validate_parser.add_argument(
        "files", nargs="*", help="Files to validate (default: staged files)"
    )
    validate_parser.add_argument(
        "--staged", action="store_true", help="Validate only staged git files"
    )
    validate_parser.add_argument(
        "--all",
        action="store_true",
        dest="all_files",
        help="Validate all files in repository",
    )
    validate_parser.add_argument(
        "--fix", action="store_true", help="Auto-fix issues where possible"
    )
    validate_parser.add_argument(
        "--interactive",
        action="store_true",
        help="Prompt for auto-fix decisions (default for git hooks)",
    )

    # Auto-fix command
    autofix_parser = subparsers.add_parser(
        "auto-fix", help="Auto-fix issues using all available validators"
    )
    autofix_parser.add_argument(
        "files", nargs="*", help="Files to fix (default: current directory)"
    )
    autofix_parser.add_argument(
        "--staged", action="store_true", help="Fix only staged git files"
    )
    autofix_parser.add_argument(
        "--all",
        action="store_true",
        dest="all_files",
        help="Fix all files in repository",
    )
    autofix_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be fixed without making changes",
    )

    # Install command
    install_parser = subparsers.add_parser(
        "install", help="Install HuskyCat and dependencies"
    )
    install_parser.add_argument(
        "--dev", action="store_true", help="Install development dependencies"
    )
    install_parser.add_argument(
        "--global",
        action="store_true",
        dest="global_install",
        help="Install globally (not recommended)",
    )

    # Setup hooks command
    hooks_parser = subparsers.add_parser(
        "setup-hooks", help="Setup git hooks for automatic validation"
    )
    hooks_parser.add_argument(
        "--force", action="store_true", help="Force overwrite existing hooks"
    )

    # Update schemas command
    schemas_parser = subparsers.add_parser(
        "update-schemas", help="Update validation schemas from official sources"
    )
    schemas_parser.add_argument(
        "--force", action="store_true", help="Force update even if cache is fresh"
    )
    schemas_parser.add_argument(
        "--helm",
        action="store_true",
        help="Also update Helm chart schemas from Auto-DevOps",
    )

    # CI validate command
    ci_parser = subparsers.add_parser(
        "ci-validate", help="Validate CI configuration files"
    )
    ci_parser.add_argument("files", nargs="*", help="CI files to validate")

    # Auto-DevOps command
    autodevops_parser = subparsers.add_parser(
        "auto-devops", help="Validate Auto-DevOps Helm charts and Kubernetes manifests"
    )
    autodevops_parser.add_argument(
        "project_path", nargs="?", default=".", help="Path to project directory"
    )
    autodevops_parser.add_argument(
        "--no-helm",
        action="store_false",
        dest="validate_helm",
        help="Skip Helm validation",
    )
    autodevops_parser.add_argument(
        "--no-k8s",
        action="store_false",
        dest="validate_k8s",
        help="Skip Kubernetes manifest validation",
    )
    autodevops_parser.add_argument(
        "--simulate",
        action="store_true",
        dest="simulate_deployment",
        help="Simulate Auto-DevOps deployment",
    )
    autodevops_parser.add_argument(
        "--strict",
        action="store_true",
        dest="strict_mode",
        help="Enable strict validation mode",
    )

    # MCP server command (stdio mode only)
    mcp_parser = subparsers.add_parser(
        "mcp-server", help="Start MCP server for Claude Code integration (stdio mode)"
    )

    # Clean command
    clean_parser = subparsers.add_parser(
        "clean", help="Clean cache and temporary files"
    )
    clean_parser.add_argument(
        "--all",
        action="store_true",
        dest="all_files",
        help="Remove all cache including schemas",
    )

    # Status command
    subparsers.add_parser("status", help="Show HuskyCat status and configuration")

    # Bootstrap command for Claude Code integration
    bootstrap_parser = subparsers.add_parser(
        "bootstrap", help="Bootstrap Claude Code MCP integration"
    )
    bootstrap_parser.add_argument(
        "--force", action="store_true", help="Overwrite existing configuration files"
    )

    return parser


def main() -> int:
    """Main entry point for HuskyCat CLI."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    # Create factory
    factory = HuskyCatFactory(
        config_dir=args.config_dir if hasattr(args, "config_dir") else None,
        verbose=args.verbose if hasattr(args, "verbose") else False,
    )

    # Build kwargs from args
    kwargs = vars(args)
    command_name = kwargs.pop("command")
    kwargs.pop("verbose", None)
    kwargs.pop("config_dir", None)

    # Execute command
    result = factory.execute_command(command_name, **kwargs)

    # Print results
    if result.status == CommandStatus.SUCCESS:
        print(f"✅ {result.message}")
    elif result.status == CommandStatus.WARNING:
        print(f"⚠️  {result.message}")
    else:
        print(f"❌ {result.message}")

    if result.errors:
        print("\nErrors:")
        for error in result.errors:
            print(f"  • {error}")

    if result.warnings:
        print("\nWarnings:")
        for warning in result.warnings:
            print(f"  • {warning}")

    # Return appropriate exit code
    if result.status == CommandStatus.FAILED:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
