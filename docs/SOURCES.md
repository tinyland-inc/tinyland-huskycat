# Documentation Sources of Truth

**Last Updated**: 2026-01-18
**Purpose**: Prevent documentation drift by identifying authoritative sources

---

## Core Architecture

| Topic | Authoritative Source | Update Protocol |
|-------|---------------------|-----------------|
| **Mode Detection** | `src/huskycat/core/mode_detector.py` | Update docstring first, then docs |
| **Product Modes** | `docs/architecture/product-modes.md` | Single source of truth |
| **Execution Models** | `docs/architecture/execution-models.md` | Single source of truth |
| **Adapter Config** | `src/huskycat/core/adapters/base.py` | AdapterConfig dataclass is truth |
| **Fix Confidence** | `src/huskycat/core/adapters/base.py` | FixConfidence enum is truth |

## MCP Server

| Topic | Authoritative Source | Notes |
|-------|---------------------|-------|
| **Tool List** | `src/huskycat/mcp_server.py` | Tools registered in `__init__` |
| **Protocol** | `src/huskycat/mcp_server.py` | JSON-RPC 2.0 implementation |
| **Tool Count** | **28+ tools** (context-dependent) | Varies by available integrations |

### MCP Tool Breakdown

- **14 core tools**: validate, validate_staged, status, async operations, history
- **8-17 validator tools**: Varies by linting mode (FAST vs COMPREHENSIVE)
- **6 RemoteJuggler tools**: When integration enabled (`juggler_*` prefix)

## Integrations

| Integration | Authoritative Source | Config Location |
|-------------|---------------------|-----------------|
| **RemoteJuggler** | `src/huskycat/integrations/remote_juggler.py` | `~/.huskycat/integrations/remote-juggler.yaml` |

## Configuration

| Config Type | Authoritative Source | Notes |
|-------------|---------------------|-------|
| **AdapterConfig** | `src/huskycat/core/adapters/base.py:AdapterConfig` | Dataclass definition |
| **OutputFormat** | `src/huskycat/core/adapters/base.py:OutputFormat` | Enum definition |
| **ProductMode** | `src/huskycat/core/mode_detector.py:ProductMode` | Enum definition |
| **FixConfidence** | `src/huskycat/core/adapters/base.py:FixConfidence` | Enum definition |

## Environment Variables

| Variable | Purpose | Reference |
|----------|---------|-----------|
| `HUSKYCAT_MODE` | Force product mode | `mode_detector.py` |
| `HUSKYCAT_FIX` | Auto-fix threshold | `adapters/base.py` |
| `HUSKYCAT_NONBLOCKING` | Enable async hooks | `adapters/git_hooks_nonblocking.py` |
| `HUSKYCAT_LINTING_MODE` | Tool selection (fast/comprehensive) | `unified_validation.py` |

## Output Formats by Mode

| Mode | Format | Exit Codes | Auto-fix | Interactive |
|------|--------|------------|----------|-------------|
| `GIT_HOOKS` | MINIMAL | 0/1 | SAFE only | TTY-detect |
| `CI` | JUNIT_XML | 0/1 | Never | Never |
| `CLI` | HUMAN | 0/1 | --fix flag | Yes |
| `PIPELINE` | JSON | 0-4 | Never | Never |
| `MCP` | JSONRPC | N/A | Never | Never |

## Execution Models

| Model | Entry Point | When Used |
|-------|-------------|-----------|
| **Binary (bundled)** | `huskycat_main.py` | PyInstaller binary with embedded tools |
| **Binary (delegated)** | `huskycat_main.py` | Binary delegates to container |
| **Container** | `ContainerFile` | CI/CD, explicit container execution |
| **UV Development** | `package.json` scripts | Development and testing |

## Adapter Files

| Mode | Adapter File | Key Characteristics |
|------|-------------|---------------------|
| Git Hooks (blocking) | `core/adapters/git_hooks.py` | Fast subset, fail-fast, minimal output |
| Git Hooks (nonblocking) | `core/adapters/git_hooks_nonblocking.py` | Background execution, TUI, all tools |
| CI | `core/adapters/ci.py` | JUnit XML, comprehensive, never interactive |
| CLI | `core/adapters/cli.py` | Rich output, interactive, progress bars |
| Pipeline | `core/adapters/pipeline.py` | JSON output, stdin mode, scriptable |
| MCP | `core/adapters/mcp.py` | JSON-RPC 2.0, stdio transport |

---

## Documentation Update Workflow

1. **Code changes**: Update code first, including docstrings
2. **Architecture docs**: Update `docs/architecture/` if behavior changes
3. **Feature docs**: Update `docs/features/` for user-facing changes
4. **Reference this file**: Verify you're updating the authoritative source

## What NOT to Duplicate

The following information should be referenced, not copied:

- **Execution models**: Link to `docs/architecture/execution-models.md`
- **Product modes**: Link to `docs/architecture/product-modes.md`
- **MCP tools list**: Reference "28+ tools (context-dependent)"
- **Config schema**: Reference dataclass source files

## Verification Commands

```bash
# Verify mode detection
uv run python -c "from src.huskycat.core.mode_detector import ProductMode; print([m.value for m in ProductMode])"

# Count MCP tools (approximate)
grep -c "@mcp_tool\|register_tool" src/huskycat/mcp_server.py

# List adapters
ls -la src/huskycat/core/adapters/
```

---

## Known Documentation Issues (Resolved)

| Issue | Resolution |
|-------|------------|
| License contradiction (MIT vs Apache-2.0) | Fixed: Apache-2.0 in all docs |
| "Container-only" claims | Fixed: Updated to "multi-modal execution" |
| MCP tools count inconsistent | Fixed: "28+ (context-dependent)" |
| GPL sidecar IPC claims | Fixed: Tool filtering, not IPC |

## Future Documentation Work

| Item | Status |
|------|--------|
| Auto-fix framework | FUTURE (skeleton exists, full impl pending) |
| GPL sidecar IPC | NOT PLANNED (tool filtering is sufficient) |
