# Claude Code Instructions for HuskyCat Project

## CRITICAL: Git Commit Rules

**NEVER use `--no-verify` flag when committing in this repository!**

HuskyCat IS a verification and validation project. We must use our own
validation tools and git hooks for every commit. This is non-negotiable.

### Always use:

```bash
git commit -m "message"  # Let hooks run
```

### Never use:

```bash
git commit --no-verify -m "message"  # FORBIDDEN in HuskyCat
```

## Build System: npm-mediated Commands

All builds are mediated through npm scripts for lean reproducibility:

```bash
# Development
npm run dev                    # Run HuskyCat CLI
npm run validate              # Validate current directory
npm run validate:ci           # Validate CI configuration
npm run hooks:install         # Install git hooks (calls setup-hooks)
npm run mcp:server           # Start MCP server for Claude Code
npm run clean                # Clean cache and temporary files
npm run status               # Show HuskyCat status

# Building & Testing  
npm run container:build       # Build validation container
npm run container:test        # Test container works
npm run build:binary         # Create PyInstaller binary
npm run build:upx           # Create UPX-compressed binary
npm run build:all           # Build container and UPX binary
npm run test:unit           # Run unit tests only
npm run test:integration    # Run integration tests only
npm run test:e2e            # Run end-to-end tests only
npm run test:all            # Run all tests (may have import errors)

# Documentation
npm run docs:build          # Build MkDocs
npm run docs:serve          # Serve docs locally
npm run pages:deploy        # Deploy to GitHub Pages

# Installation & Dependencies
npm run install:local       # Install locally with uv
npm run install:deps        # Install development dependencies
```

## Project Context

HuskyCat is a comprehensive code validation platform that includes:

- GitLab CI/CD validation
- Git hooks integration
- MCP server for Claude Code
- Container-based validation tools
- Property-based testing with Hypothesis

## Development Workflow

1. **Always validate before committing** - Let the git hooks run
2. **Use HuskyCat's own tools** to validate changes:
   - Run `npm run validate:ci` for GitLab CI validation
   - Use `npm run container:build` for container testing
   - Run individual test suites with `npm run test:unit` (PBT tests have import issues)

3. **Debug validation failures** instead of bypassing them
4. **If hooks fail**, fix the issues rather than skipping verification

## Available CLI Commands

HuskyCat provides these commands (use `npm run dev -- COMMAND --help` for details):

```bash
# Core validation commands
npm run dev -- validate           # Run validation on files
npm run dev -- validate --staged  # Validate only staged git files  
npm run dev -- validate --all     # Validate all files in repository
npm run dev -- ci-validate FILE   # Validate CI configuration files

# Setup and management
npm run dev -- install            # Install HuskyCat and dependencies
npm run dev -- setup-hooks        # Setup git hooks (NOT "install hooks")
npm run dev -- update-schemas     # Update validation schemas
npm run dev -- clean              # Clean cache and temporary files
npm run dev -- status             # Show HuskyCat status and configuration

# Advanced features
npm run dev -- auto-devops        # Validate Auto-DevOps Helm/K8s manifests
npm run dev -- mcp-server         # Start MCP server for AI integration

# Direct UV commands (if needed)
uv run black src/ tests/          # Code formatting
uv run flake8 src/ tests/         # Linting
uv run mypy src/                  # Type checking
uv run ruff check src/ tests/     # Fast linting

# External tools (if available)
glab ci lint .gitlab-ci.yml       # GitLab CI validation (requires glab CLI)
```

## Repository Standards

- Python code uses UV package manager
- All code must pass Black, Flake8, MyPy, and Ruff checks
- GitLab CI must validate with both `npm run validate:ci` and yamllint
- Tests use property-based testing with Hypothesis (currently has import issues)
- Documentation in MkDocs format
- Container builds with Podman/Docker using ContainerFile

## Current Test Status

⚠️ **Note**: The test suite currently has several issues:

**Import/Dependency Issues:**
- Missing dependencies: `websockets`, `playwright` 
- Module import issues: `mcp_server`, `unified_validation`
- Several PBT (Property-Based Testing) files have broken imports

**Container Testing Issues:**
- Container entrypoint conflicts with test expectations (runs HuskyCat CLI instead of arbitrary commands)
- Many container tests fail due to ENTRYPOINT design

**Recommended Testing Approach:**
- Use direct Python execution: `uv run python -m src.huskycat COMMAND` 
- Individual validation: `uv run black src/`, `uv run mypy src/`
- Container build testing: `npm run container:build && npm run container:test`
- Avoid `npm run test:all` until import issues are resolved

## Quick Reference: Working Commands

**✅ Verified working commands:**

```bash
# Basic CLI operations
npm run dev                          # Show HuskyCat help
npm run dev -- --help               # Show detailed help
npm run dev -- setup-hooks --help   # Setup git hooks (corrected command)
npm run validate                     # Validate current directory
npm run validate:ci                  # Validate .gitlab-ci.yml  
npm run clean                        # Clean cache
npm run status                       # Show status

# Container operations
npm run container:build              # Build validation container
npm run container:test               # Test container basic functionality

# Documentation
npm run docs:build                   # Build MkDocs documentation
npm run docs:serve                   # Serve documentation locally

# Direct UV operations (bypass npm)
uv run python -m src.huskycat --help    # Direct CLI access
uv run black src/                        # Format code
uv run mypy src/                         # Type checking
```

**⚠️ Commands with issues:**
- `npm run test:all` - Import errors
- `npm run build:binary` - May need PyInstaller setup
- `npm run build:upx` - Requires UPX installation

## Remember

This project is about code quality and validation. We must demonstrate best
practices by using our own tools consistently. No shortcuts on verification!
