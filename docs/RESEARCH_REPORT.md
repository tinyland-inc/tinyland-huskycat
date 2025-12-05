# HuskyCat Documentation & CLI Research Report

**Date**: December 4, 2025
**Version**: 2.0.0
**Researcher**: Claude Code Analysis Agent

---

## Executive Summary

This report documents findings from a comprehensive review of HuskyCat's MkDocs documentation, CLI interface, and test coverage. Key findings include significant documentation-to-implementation gaps, missing CLI feature documentation, and limited unit test coverage for CLI commands.

---

## 1. Documentation Accuracy Issues

### 1.1 CRITICAL: MCP Server Port Flag (Does Not Exist)

**Location**: `docs/installation.md:90-95`

**Documentation Claims**:
```bash
./path/to/huskycat mcp-server --port 8080
# Configure in Claude Code MCP settings:
# Args: ["mcp-server", "--port=0"]
```

**Actual Implementation** (`src/huskycat/__main__.py:175-177`):
```python
subparsers.add_parser(
    "mcp-server", help="Start MCP server for Claude Code integration (stdio mode)"
)
```

**Reality**: The `--port` flag does not exist. MCP server is stdio-only.

**CLI Help Output**:
```
usage: huskycat mcp-server [-h]
options:
  -h, --help  show this help message and exit
```

**Recommendation**: Remove all `--port` references from documentation.

---

### 1.2 CRITICAL: MCP Architecture Document Mismatch

**Location**: `docs/mcp-architecture.md:1-100`

**Documentation Claims**:
- HTTP Server with Kubernetes pods
- TypeScript execution with tsx
- Rocky Linux base with fail2ban, firewalld
- Syncthing network for repository sync
- Service mesh and load balancer
- Grafana/Prometheus monitoring

**Actual Implementation** (`src/huskycat/mcp_server.py`):
- Simple stdio-based Python server (lines 442-474)
- JSON-RPC 2.0 over stdin/stdout
- No HTTP server, no Kubernetes, no TypeScript
- Single-process execution

**Recommendation**: Either remove `mcp-architecture.md` or rewrite it to document the actual stdio implementation.

---

### 1.3 Container-Only Claims vs Fallback Behavior

**Location**: Multiple docs claim "container-only" execution

**Documentation** (`docs/index.md:6-7`):
> "HuskyCat is a **container-only** validation platform..."

**Actual Implementation** (`src/huskycat/mcp_server.py:319-340`):
```python
# Fallback to local engine execution
# Update engine settings
self.engine.auto_fix = fix
path = Path(path_str)
if path.is_file():
    results = self.engine.validate_file(path)
```

**Reality**: The MCP server falls back to local execution when containers are unavailable. This is not documented.

**Recommendation**: Update documentation to clarify fallback behavior.

---

### 1.4 MCP Tool Names Mismatch

**Location**: `docs/features/mcp-server.md:47-48`

**Documentation Claims** individual tools are:
- `validate_black`
- `validate_flake8`

**Actual Implementation** (`src/huskycat/unified_validation.py:188-189`):
```python
@property
def name(self) -> str:
    return "python-black"  # Not "black"
```

**Actual MCP Tool Names** (from ValidationEngine):
- `validate_python-black` (not `validate_black`)
- `validate_autoflake`
- `validate_flake8`
- `validate_mypy`
- `validate_ruff`
- `validate_bandit`
- `validate_js-eslint`
- `validate_js-prettier`
- `validate_yamllint`
- `validate_docker-hadolint`
- `validate_shellcheck`
- `validate_gitlab-ci`

**Recommendation**: Update documentation with correct tool names.

---

### 1.5 Missing Documentation for New Features

#### 1.5.1 Product Mode System (Not Documented)

**Implementation Location**: `src/huskycat/core/mode_detector.py`, `src/huskycat/core/adapters/`

The 5 product modes are implemented but not documented in user-facing docs:
- `git_hooks` - Pre-commit/pre-push validation
- `ci` - Pipeline integration with JUnit XML
- `cli` - Interactive terminal with colors
- `pipeline` - Machine-readable JSON
- `mcp` - AI assistant integration via JSON-RPC

**CLI Flag**: `--mode {git_hooks,ci,cli,pipeline,mcp}`

**Recommendation**: Add dedicated documentation page for product modes.

#### 1.5.2 `--json` Flag (Not Documented)

**Implementation** (`src/huskycat/__main__.py:45-46`):
```python
parser.add_argument(
    "--json", action="store_true", help="Force JSON output (sets pipeline mode)"
)
```

**Recommendation**: Document in installation.md and configuration.md.

#### 1.5.3 `bootstrap` Command (Not Documented)

**CLI Help**:
```
bootstrap  Bootstrap Claude Code MCP integration
  --force  Overwrite existing configuration files
```

**Recommendation**: Add to installation.md as part of MCP setup.

#### 1.5.4 FixConfidence Tiers (Not Documented)

**Implementation** (`src/huskycat/core/adapters/base.py:27-51`):
```python
class FixConfidence(Enum):
    SAFE = "safe"      # Formatting (black, prettier)
    LIKELY = "likely"  # Style fixes (autoflake, ruff)
    UNCERTAIN = "uncertain"  # Needs human review

TOOL_FIX_CONFIDENCE = {
    "python-black": FixConfidence.SAFE,
    "js-prettier": FixConfidence.SAFE,
    "autoflake": FixConfidence.LIKELY,
    "ruff": FixConfidence.LIKELY,
    "yamllint": FixConfidence.SAFE,
    "js-eslint": FixConfidence.LIKELY,
}
```

**Recommendation**: Document in configuration.md under auto-fix behavior.

---

## 2. CLI Help, Args, Flow & Completeness Review

### 2.1 CLI Command Inventory

| Command | Documented | Help Accurate | Args Complete |
|---------|------------|---------------|---------------|
| `validate` | Yes | Yes | Yes |
| `auto-fix` | Partial | Yes | Yes |
| `install` | Yes | Yes | Missing `--bin-dir` |
| `setup-hooks` | Yes | Yes | Yes |
| `update-schemas` | Yes | Yes | Yes |
| `ci-validate` | Yes | Yes | Yes |
| `auto-devops` | Yes | Yes | Yes |
| `mcp-server` | Yes | **No** (port flag) | **No** |
| `clean` | Yes | Yes | Yes |
| `status` | Yes | Yes | Yes |
| `bootstrap` | **No** | Yes | Yes |

### 2.2 Global Options

| Option | Documented | Works |
|--------|------------|-------|
| `--version` | Yes | Yes |
| `--verbose, -v` | Yes | Yes |
| `--config-dir` | Partial | Yes |
| `--mode` | **No** | Yes |
| `--json` | **No** | Yes |

### 2.3 Missing CLI Features

1. **No `--help` for individual validators** - Can't see what a specific validator does
2. **No `--list-validators` command** - Users can't discover available validators
3. **No `--dry-run` for validate** - Only exists for auto-fix

### 2.4 CLI Flow Analysis

**Entry Point Flow** (`src/huskycat/__main__.py:204-250`):
```
main() -> create_parser() -> parse_args()
       -> detect_mode() -> get_adapter(mode)
       -> HuskyCatFactory(adapter=adapter)
       -> execute_command() -> _print_result()
```

**Issues Identified**:
1. Mode detection happens after parsing but adapter could inform parser behavior
2. No progress indicator for long-running validations
3. Error messages don't include file:line references

---

## 3. CLI Test Coverage Assessment

### 3.1 Test File Inventory

| Test File | Test Count | Focus Area |
|-----------|-----------|------------|
| `test_mode_detection.py` | 34 | Mode detection, adapters, FixConfidence |
| `test_unified_validation_pbt.py` | 9 | Property-based validation |
| `test_git_hooks.py` | 14 | Git hooks integration |
| `test_validation_pbt.py` | 11 | Property-based validation |
| `test_container_comprehensive.py` | 18 | Container execution |
| `test_property_based.py` | 22 | General PBT |
| `test_mcp_server_pbt.py` | 8 | MCP server PBT |
| `test_real_validation_e2e.py` | 15 | E2E validation |
| `test_mcp_integration_comprehensive.py` | 20 | MCP integration |
| `test_testing_infrastructure.py` | 19 | Test infrastructure |
| `test_sample.py` | - | Sample tests |

**Total**: ~166 test functions

### 3.2 CLI Command Test Coverage

| Command | Unit Tests | Integration Tests | E2E Tests |
|---------|-----------|-------------------|-----------|
| `validate` | **2** (adapter only) | Yes | Yes |
| `auto-fix` | **0** | No | No |
| `install` | **0** | No | No |
| `setup-hooks` | **0** | Partial | No |
| `update-schemas` | **0** | No | No |
| `ci-validate` | **0** | No | No |
| `auto-devops` | **0** | No | No |
| `mcp-server` | **0** | Yes (PBT) | No |
| `clean` | **0** | No | No |
| `status` | **0** | No | No |
| `bootstrap` | **0** | No | No |

### 3.3 Critical Test Gaps

1. **No unit tests for command execution logic**
   - `InstallCommand.execute()` - untested
   - `CleanCommand.execute()` - untested
   - `StatusCommand.execute()` - untested
   - `AutoDevOpsCommand.execute()` - untested
   - `BootstrapCommand.execute()` - untested

2. **No error path testing**
   - What happens when validators fail?
   - What happens with invalid file paths?
   - What happens with permission errors?

3. **No CLI argument parsing tests**
   - Are conflicting arguments handled?
   - Are default values correct?

### 3.4 Recommended Test Additions

```
tests/
  test_cli_commands/
    test_validate_command.py      # ValidateCommand unit tests
    test_install_command.py       # InstallCommand unit tests
    test_clean_command.py         # CleanCommand unit tests
    test_status_command.py        # StatusCommand unit tests
    test_autofix_command.py       # AutoFixCommand unit tests
    test_bootstrap_command.py     # BootstrapCommand unit tests
    test_ci_validate_command.py   # CIValidateCommand unit tests
    test_mcp_command.py           # MCPServerCommand unit tests
    test_autodevops_command.py    # AutoDevOpsCommand unit tests
    test_schemas_command.py       # UpdateSchemasCommand unit tests
  test_cli_parsing.py             # Argument parsing tests
  test_cli_error_handling.py      # Error path tests
```

---

## 4. File Reference Index

### Core Files

| File | Purpose | Lines |
|------|---------|-------|
| `src/huskycat/__main__.py` | CLI entry point | 343 |
| `src/huskycat/core/factory.py` | Command factory | 147 |
| `src/huskycat/core/base.py` | Base command class | ~100 |
| `src/huskycat/core/mode_detector.py` | Mode detection | ~150 |
| `src/huskycat/mcp_server.py` | MCP stdio server | 485 |
| `src/huskycat/unified_validation.py` | Validation engine | ~1000 |

### Command Implementations

| File | Command | Lines |
|------|---------|-------|
| `src/huskycat/commands/validate.py` | validate | ~150 |
| `src/huskycat/commands/autofix.py` | auto-fix | ~100 |
| `src/huskycat/commands/install.py` | install | 274 |
| `src/huskycat/commands/hooks.py` | setup-hooks | ~300 |
| `src/huskycat/commands/schemas.py` | update-schemas | ~100 |
| `src/huskycat/commands/ci.py` | ci-validate | ~100 |
| `src/huskycat/commands/autodevops.py` | auto-devops | ~150 |
| `src/huskycat/commands/mcp.py` | mcp-server | ~50 |
| `src/huskycat/commands/clean.py` | clean | ~80 |
| `src/huskycat/commands/status.py` | status | ~100 |
| `src/huskycat/commands/bootstrap.py` | bootstrap | ~100 |

### Adapter Files

| File | Purpose |
|------|---------|
| `src/huskycat/core/adapters/base.py` | Base adapter + FixConfidence |
| `src/huskycat/core/adapters/git_hooks.py` | Git hooks adapter |
| `src/huskycat/core/adapters/ci.py` | CI adapter |
| `src/huskycat/core/adapters/cli.py` | CLI adapter |
| `src/huskycat/core/adapters/pipeline.py` | Pipeline adapter |
| `src/huskycat/core/adapters/mcp.py` | MCP adapter |

### Documentation Files

| File | Issues |
|------|--------|
| `docs/index.md` | Container-only claim needs clarification |
| `docs/installation.md` | MCP --port flag references (invalid) |
| `docs/configuration.md` | Missing mode, json flags |
| `docs/features/mcp-server.md` | Wrong tool names |
| `docs/api/mcp-tools.md` | Wrong tool names |
| `docs/mcp-architecture.md` | **COMPLETELY WRONG** - describes non-existent HTTP architecture |

---

## 5. Recommendations Summary

### Immediate (High Priority)

1. **Remove/rewrite `docs/mcp-architecture.md`** - Describes non-existent architecture
2. **Remove `--port` references** from `docs/installation.md` and `docs/features/mcp-server.md`
3. **Fix MCP tool names** in `docs/api/mcp-tools.md`

### Short-term (Medium Priority)

4. **Document product modes** - New page or section in configuration.md
5. **Document `--mode` and `--json` flags** - Add to CLI reference
6. **Document `bootstrap` command** - Add to installation.md
7. **Document FixConfidence** - Add to configuration.md

### Long-term (Test Coverage)

8. **Add unit tests for all commands** - Create test_cli_commands/ directory
9. **Add CLI parsing tests** - Test argument handling
10. **Add error path tests** - Test failure scenarios

---

## 6. Appendix: Actual Validator Names

From `src/huskycat/unified_validation.py`:

| Class | `.name` Property | Command |
|-------|-----------------|---------|
| `BlackValidator` | `python-black` | `black` |
| `AutoflakeValidator` | `autoflake` | `autoflake` |
| `Flake8Validator` | `flake8` | `flake8` |
| `MypyValidator` | `mypy` | `mypy` |
| `RuffValidator` | `ruff` | `ruff` |
| `BanditValidator` | `bandit` | `bandit` |
| `ESLintValidator` | `js-eslint` | `eslint` |
| `PrettierValidator` | `js-prettier` | `prettier` |
| `YamlLintValidator` | `yamllint` | `yamllint` |
| `HadolintValidator` | `docker-hadolint` | `hadolint` |
| `ShellcheckValidator` | `shellcheck` | `shellcheck` |
| `GitLabCIValidator` | `gitlab-ci` | `glab` |

---

*Report generated by Claude Code Analysis Agent*
