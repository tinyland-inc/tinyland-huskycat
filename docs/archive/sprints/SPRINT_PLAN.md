# HuskyCat Focused Sprint Plan

Based on comprehensive repository audit, this sprint addresses critical issues and establishes clear product modes with distinct architectural requirements.

---

## Product Mode Architecture

### The Core Problem

HuskyCat serves **five distinct product modes** that share validation logic but have fundamentally different:
- Performance requirements
- Output formats
- Interactivity expectations
- Error handling strategies
- Tool availability assumptions
- Environment contexts

This architectural ambiguity has caused design friction. The factory pattern helps with command dispatch but doesn't address **mode-specific behavior differences**.

### The Five Product Modes

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         HUSKYCAT PRODUCT MODES                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐     │
│  │  GIT HOOKS  │   │     CI      │   │     CLI     │   │  PIPELINE   │     │
│  │    MODE     │   │    MODE     │   │    MODE     │   │    MODE     │     │
│  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘   └──────┬──────┘     │
│         │                 │                 │                 │            │
│         v                 v                 v                 v            │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │                    MCP SERVER MODE                              │       │
│  │              (AI assistant integration)                         │       │
│  └─────────────────────────────────────────────────────────────────┘       │
│                                    │                                        │
│                                    v                                        │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │              UNIFIED VALIDATION ENGINE                          │       │
│  │         (shared validation logic, tool execution)               │       │
│  └─────────────────────────────────────────────────────────────────┘       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Mode 1: Git Hooks Mode

**Purpose**: Pre-commit/pre-push validation
**Runtime**: Binary (fast) or container fallback
**Critical Requirements**:
- **Speed**: Must complete in <5s for good DX
- **Staged files only**: `--staged` flag
- **Silent success**: No output on pass
- **Loud failure**: Clear, actionable errors
- **Auto-fix prompts**: Interactive when terminal available
- **Exit codes**: 0=pass, 1=fail (blocks commit)

```python
class GitHooksAdapter:
    output_format = "minimal"      # Errors only
    interactive = "auto"           # Detect TTY
    fail_fast = True               # Stop on first error
    tools = "fast"                 # black, ruff, mypy only
    color = "auto"                 # Detect terminal
```

### Mode 2: CI Validation Mode

**Purpose**: Pipeline integration for MR/PR checks
**Runtime**: Container (guaranteed environment)
**Critical Requirements**:
- **Comprehensive**: Run ALL validators
- **Structured output**: JUnit XML, JSON reports
- **Exit codes**: 0=pass, non-zero=fail
- **Artifacts**: Save reports for pipeline artifacts
- **No interactivity**: Fully automated
- **Badge-ready**: Status for MR badges

```python
class CIAdapter:
    output_format = "structured"   # JUnit XML, JSON
    interactive = False            # Never prompt
    fail_fast = False              # Run all validators
    tools = "all"                  # Complete toolchain
    color = False                  # No ANSI codes
    report_path = "./reports/"     # Artifact directory
```

### Mode 3: Standalone CLI Mode

**Purpose**: Developer running validation manually
**Runtime**: Binary or container
**Critical Requirements**:
- **Interactive feedback**: Progress indicators
- **Colored output**: Rich terminal experience
- **Auto-fix**: `--fix` flag with prompts
- **File selection**: Glob patterns, paths
- **Verbose options**: `-v`, `-vv`, `-vvv`
- **Help text**: Comprehensive `--help`

```python
class CLIAdapter:
    output_format = "human"        # Colored, formatted
    interactive = True             # Prompts enabled
    fail_fast = False              # Show all issues
    tools = "configured"           # Per .huskycat.yaml
    color = True                   # Rich output
    progress = True                # Spinners, bars
```

### Mode 4: Pipeline Tool Mode

**Purpose**: Part of larger build/lint/validate toolchain
**Runtime**: Container only
**Critical Requirements**:
- **Composable**: stdin/stdout friendly
- **Machine-readable**: JSON output
- **Non-interactive**: Never prompt
- **Scriptable**: Predictable behavior
- **Exit codes**: Semantic (0, 1, 2, etc.)
- **No side effects**: Read-only by default

```python
class PipelineAdapter:
    output_format = "json"         # Machine-readable
    interactive = False            # Never prompt
    fail_fast = False              # Complete run
    tools = "all"                  # Complete toolchain
    color = False                  # No ANSI
    stdin_mode = True              # Accept file list from stdin
```

### Mode 5: MCP Server Mode

**Purpose**: AI assistant integration
**Runtime**: Container or local (stdio)
**Critical Requirements**:
- **JSON-RPC protocol**: stdio transport
- **Tool registration**: Expose validators as tools
- **Context-aware**: Understand project structure
- **No terminal output**: Pure protocol
- **Stateless requests**: Each call independent
- **Error responses**: JSON-RPC error format

```python
class MCPAdapter:
    output_format = "jsonrpc"      # JSON-RPC 2.0
    interactive = False            # Never prompt
    fail_fast = True               # Per-request
    tools = "all"                  # All available
    color = False                  # No ANSI
    transport = "stdio"            # stdin/stdout
```

### Mode Detection Strategy

```python
# src/huskycat/core/mode_detector.py

from enum import Enum
import os
import sys

class ProductMode(Enum):
    GIT_HOOKS = "git_hooks"
    CI = "ci"
    CLI = "cli"
    PIPELINE = "pipeline"
    MCP = "mcp"

def detect_mode() -> ProductMode:
    """Auto-detect product mode from environment."""

    # Explicit mode override
    if mode := os.environ.get("HUSKYCAT_MODE"):
        return ProductMode(mode)

    # MCP mode: invoked with mcp-server command
    if "mcp-server" in sys.argv or "mcp" in sys.argv:
        return ProductMode.MCP

    # Git hooks: GIT_* environment variables present
    if os.environ.get("GIT_AUTHOR_NAME") or os.environ.get("GIT_INDEX_FILE"):
        return ProductMode.GIT_HOOKS

    # CI mode: CI environment variables
    ci_vars = ["CI", "GITLAB_CI", "GITHUB_ACTIONS", "JENKINS_URL", "TRAVIS"]
    if any(os.environ.get(v) for v in ci_vars):
        return ProductMode.CI

    # Pipeline mode: no TTY or piped input
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        return ProductMode.PIPELINE

    # Default: CLI mode
    return ProductMode.CLI

def get_adapter(mode: ProductMode) -> "ModeAdapter":
    """Get mode-specific adapter."""
    adapters = {
        ProductMode.GIT_HOOKS: GitHooksAdapter,
        ProductMode.CI: CIAdapter,
        ProductMode.CLI: CLIAdapter,
        ProductMode.PIPELINE: PipelineAdapter,
        ProductMode.MCP: MCPAdapter,
    }
    return adapters[mode]()
```

### Architecture Implementation

```
src/huskycat/
├── core/
│   ├── mode_detector.py      # Mode detection logic
│   ├── adapters/             # Mode-specific adapters
│   │   ├── base.py           # Abstract adapter interface
│   │   ├── git_hooks.py      # Git hooks adapter
│   │   ├── ci.py             # CI adapter
│   │   ├── cli.py            # CLI adapter
│   │   ├── pipeline.py       # Pipeline adapter
│   │   └── mcp.py            # MCP adapter
│   ├── validation_engine.py  # Shared validation logic
│   └── factory.py            # Command factory (unchanged)
├── commands/                 # Command implementations
├── tools/                    # Individual validators
└── __main__.py               # Entry point with mode detection
```

### Key Design Decisions

1. **Mode detection at entry point**: Detect mode once, configure adapter
2. **Adapter pattern**: Mode-specific behavior without conditionals everywhere
3. **Shared validation engine**: All modes use same validation logic
4. **Output formatting at edge**: Adapter handles all output formatting
5. **Tool availability per mode**: Git hooks = fast tools, CI = all tools

### Migration Path

Current codebase has mode logic scattered throughout. Migration:

1. **Sprint 0**: Create mode detector and adapter interfaces
2. **Sprint 1-5**: Existing sprint work (critical fixes, builds, etc.)
3. **Sprint 6**: Refactor commands to use adapters
4. **Sprint 7**: Consolidate all mode-specific logic into adapters

---

## Execution Modes (Runtime)

Orthogonal to product modes, HuskyCat supports two **execution modes**:

### Execution Mode 1: Container
- Complete toolchain guaranteed
- Consistent across environments
- Used by: CI mode, Pipeline mode, MCP mode (default)
- Image: `ghcr.io/huskycats/validator:latest`

### Execution Mode 2: Binary
- Fast startup, minimal dependencies
- Core tools only (black, ruff, mypy, flake8)
- Used by: Git hooks mode, CLI mode
- Binaries: `linux-amd64`, `linux-arm64`, `darwin-arm64`, `darwin-amd64`, `windows-amd64`

```
┌────────────────────────────────────────────────────────────┐
│                    PRODUCT MODE                            │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐ │
│  │Git Hooks │    CI    │   CLI    │ Pipeline │   MCP    │ │
│  └────┬─────┴────┬─────┴────┬─────┴────┬─────┴────┬─────┘ │
│       │          │          │          │          │        │
│       v          v          v          v          v        │
│  ┌─────────────────────────────────────────────────────┐  │
│  │              EXECUTION MODE                         │  │
│  │  ┌─────────────────┐    ┌─────────────────┐        │  │
│  │  │     BINARY      │    │    CONTAINER    │        │  │
│  │  │  (fast, local)  │    │ (complete, CI)  │        │  │
│  │  └─────────────────┘    └─────────────────┘        │  │
│  └─────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

---

## Auto-Fix Architecture

### The Value Proposition

Most linting tools only **complain**. HuskyCat should **fix**. Auto-fix transforms validation from a friction point into a productivity multiplier.

```
Traditional Linting:           HuskyCat Auto-Fix:

  detect → report → manual     detect → fix → report → commit
     ↓                            ↓
  frustration                  productivity
```

### Auto-Fix Categories

| Category | Fixable | Tool | Confidence |
|----------|---------|------|------------|
| **Formatting** | Always | black, prettier, gofmt | 100% |
| **Import sorting** | Always | isort, ruff | 100% |
| **Unused imports** | Usually | autoflake, ruff | 95% |
| **Whitespace** | Always | yamllint, trim | 100% |
| **Simple patterns** | Usually | ruff, eslint | 90% |
| **Security issues** | Sometimes | Manual + suggestion | 50% |
| **Type errors** | Rarely | Manual + suggestion | 10% |

### Auto-Fix Tiers

```python
class FixConfidence(Enum):
    SAFE = "safe"           # 100% safe, always apply (formatting)
    LIKELY = "likely"       # 90%+ safe, apply with --fix
    UNCERTAIN = "uncertain" # Needs review, apply with --fix-unsafe
    MANUAL = "manual"       # Cannot auto-fix, provide suggestion
```

### Mode-Specific Auto-Fix Behavior

| Mode | `--fix` Behavior | Interactive | Report |
|------|------------------|-------------|--------|
| **Git Hooks** | Fix SAFE, prompt for LIKELY | Yes (if TTY) | Changed files |
| **CI** | Report only (no fixes) | No | JSON diff |
| **CLI** | Fix SAFE+LIKELY, prompt for UNCERTAIN | Yes | Detailed |
| **Pipeline** | Fix all (SAFE+LIKELY+UNCERTAIN) | No | JSON |
| **MCP** | Return fix suggestions | No | JSON-RPC |

### AutoFixer Interface

```python
# src/huskycat/core/autofix.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional

class FixConfidence(Enum):
    SAFE = "safe"
    LIKELY = "likely"
    UNCERTAIN = "uncertain"
    MANUAL = "manual"

@dataclass
class FixResult:
    file: Path
    original: str
    fixed: str
    confidence: FixConfidence
    tool: str
    description: str
    line_range: Optional[tuple[int, int]] = None

@dataclass
class FixSuggestion:
    file: Path
    line: int
    message: str
    suggested_fix: Optional[str]
    confidence: FixConfidence

class AutoFixer(ABC):
    """Base class for all auto-fixers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name (e.g., 'black', 'ruff')."""
        pass

    @property
    @abstractmethod
    def confidence(self) -> FixConfidence:
        """Default confidence level for this fixer."""
        pass

    @abstractmethod
    def can_fix(self, file: Path) -> bool:
        """Check if this fixer can handle the file type."""
        pass

    @abstractmethod
    def fix(self, file: Path, dry_run: bool = False) -> List[FixResult]:
        """Apply fixes to the file."""
        pass

    @abstractmethod
    def suggest(self, file: Path, issues: List[dict]) -> List[FixSuggestion]:
        """Generate fix suggestions without applying."""
        pass
```

### Implemented Auto-Fixers

#### Python Auto-Fixers

```python
class BlackFixer(AutoFixer):
    name = "black"
    confidence = FixConfidence.SAFE

    def fix(self, file: Path, dry_run: bool = False) -> List[FixResult]:
        if dry_run:
            result = subprocess.run(
                ["black", "--check", "--diff", str(file)],
                capture_output=True, text=True
            )
            # Parse diff to create FixResult
        else:
            subprocess.run(["black", str(file)])
        # ...

class RuffFixer(AutoFixer):
    name = "ruff"
    confidence = FixConfidence.LIKELY

    def fix(self, file: Path, dry_run: bool = False) -> List[FixResult]:
        cmd = ["ruff", "check", "--fix"]
        if dry_run:
            cmd.append("--diff")
        cmd.append(str(file))
        # ...

class AutoflakeFixer(AutoFixer):
    name = "autoflake"
    confidence = FixConfidence.LIKELY

    def fix(self, file: Path, dry_run: bool = False) -> List[FixResult]:
        cmd = ["autoflake", "--remove-all-unused-imports"]
        if not dry_run:
            cmd.append("--in-place")
        cmd.append(str(file))
        # ...

class IsortFixer(AutoFixer):
    name = "isort"
    confidence = FixConfidence.SAFE

    def fix(self, file: Path, dry_run: bool = False) -> List[FixResult]:
        cmd = ["isort"]
        if dry_run:
            cmd.append("--diff")
        cmd.append(str(file))
        # ...
```

#### JavaScript Auto-Fixers

```python
class ESLintFixer(AutoFixer):
    name = "eslint"
    confidence = FixConfidence.LIKELY

    def fix(self, file: Path, dry_run: bool = False) -> List[FixResult]:
        cmd = ["eslint", "--fix"]
        if dry_run:
            cmd.append("--fix-dry-run")
        cmd.append(str(file))
        # ...

class PrettierFixer(AutoFixer):
    name = "prettier"
    confidence = FixConfidence.SAFE

    def fix(self, file: Path, dry_run: bool = False) -> List[FixResult]:
        if dry_run:
            cmd = ["prettier", "--check", str(file)]
        else:
            cmd = ["prettier", "--write", str(file)]
        # ...
```

#### YAML/Config Auto-Fixers

```python
class YAMLFixer(AutoFixer):
    name = "yamllint"
    confidence = FixConfidence.SAFE

    def fix(self, file: Path, dry_run: bool = False) -> List[FixResult]:
        # Fix trailing whitespace, missing newlines, indentation
        content = file.read_text()
        fixed = self._fix_yaml(content)
        if not dry_run:
            file.write_text(fixed)
        # ...

    def _fix_yaml(self, content: str) -> str:
        lines = content.split('\n')
        # Remove trailing whitespace
        lines = [line.rstrip() for line in lines]
        # Ensure final newline
        result = '\n'.join(lines)
        if not result.endswith('\n'):
            result += '\n'
        return result
```

#### Security Auto-Fixers

```python
class SecurityFixer(AutoFixer):
    name = "security"
    confidence = FixConfidence.UNCERTAIN  # Always needs review

    # Pattern-based replacements for common issues
    SAFE_REPLACEMENTS = {
        # SQL injection
        r'cursor\.execute\(f"': 'cursor.execute(',
        # eval() usage
        r'eval\(': 'ast.literal_eval(',
        # Hardcoded secrets (suggest .env)
        r'password\s*=\s*["\'][^"\']+["\']': 'password = os.environ.get("PASSWORD")',
    }

    def suggest(self, file: Path, issues: List[dict]) -> List[FixSuggestion]:
        suggestions = []
        for issue in issues:
            if fix := self._get_suggestion(issue):
                suggestions.append(FixSuggestion(
                    file=file,
                    line=issue['line'],
                    message=issue['message'],
                    suggested_fix=fix,
                    confidence=FixConfidence.UNCERTAIN
                ))
        return suggestions
```

### Fix Orchestration

```python
# src/huskycat/core/fix_orchestrator.py

class FixOrchestrator:
    """Coordinates auto-fix across multiple tools."""

    def __init__(self, mode: ProductMode):
        self.mode = mode
        self.adapter = get_adapter(mode)
        self.fixers = self._load_fixers()

    def fix_files(
        self,
        files: List[Path],
        dry_run: bool = False,
        confidence_threshold: FixConfidence = FixConfidence.LIKELY
    ) -> FixReport:
        """Apply fixes to files based on mode and confidence."""

        results = []
        suggestions = []

        for file in files:
            for fixer in self._get_fixers_for_file(file):
                if fixer.confidence.value <= confidence_threshold.value:
                    if self.adapter.interactive and fixer.confidence == FixConfidence.UNCERTAIN:
                        # Prompt user in CLI mode
                        if not self._prompt_for_fix(file, fixer):
                            continue

                    result = fixer.fix(file, dry_run=dry_run)
                    results.extend(result)
                else:
                    # Generate suggestions for lower-confidence fixes
                    sugg = fixer.suggest(file, self._get_issues(file, fixer))
                    suggestions.extend(sugg)

        return FixReport(
            fixed=results,
            suggestions=suggestions,
            mode=self.mode
        )
```

### CLI Integration

```bash
# Basic fix
huskycat fix src/

# Fix with preview (dry-run)
huskycat fix --dry-run src/

# Fix only safe changes
huskycat fix --safe-only src/

# Fix everything including uncertain
huskycat fix --unsafe src/

# Fix staged files (git hooks)
huskycat fix --staged

# Interactive mode (prompts for each uncertain fix)
huskycat fix --interactive src/

# JSON output for pipelines
huskycat fix --format=json src/ | jq '.fixed[]'
```

### MCP Tool Exposure

```python
# MCP tools for AI-assisted fixing

@mcp_tool("huskycat_fix")
def fix_files(paths: List[str], dry_run: bool = True) -> dict:
    """Fix code issues in specified files."""
    return orchestrator.fix_files(paths, dry_run=dry_run).to_dict()

@mcp_tool("huskycat_suggest_fixes")
def suggest_fixes(path: str) -> List[dict]:
    """Get fix suggestions without applying."""
    return orchestrator.get_suggestions(path)

@mcp_tool("huskycat_apply_suggestion")
def apply_suggestion(file: str, suggestion_id: str) -> dict:
    """Apply a specific fix suggestion."""
    return orchestrator.apply_suggestion(file, suggestion_id)
```

### Fix Reporting

```json
{
  "summary": {
    "files_scanned": 42,
    "files_fixed": 12,
    "fixes_applied": 28,
    "suggestions_generated": 5
  },
  "fixed": [
    {
      "file": "src/main.py",
      "tool": "black",
      "confidence": "safe",
      "changes": [
        {"line": 15, "type": "formatting", "description": "Reformatted function"}
      ]
    }
  ],
  "suggestions": [
    {
      "file": "src/auth.py",
      "line": 42,
      "tool": "security",
      "confidence": "uncertain",
      "message": "Hardcoded password detected",
      "suggested_fix": "Use environment variable: os.environ.get('DB_PASSWORD')"
    }
  ],
  "unfixable": [
    {
      "file": "src/types.py",
      "line": 88,
      "tool": "mypy",
      "message": "Type error requires manual review",
      "reason": "Complex generic type inference"
    }
  ]
}
```

---

## Sprint 1: Critical Fixes (Blocking Issues)

### 1.1 Fix pyproject.toml Entry Point
**File**: `pyproject.toml:68`
**Issue**: Entry point `huskycat = "huskycat:main"` references non-existent function
**Fix**:
```toml
[project.scripts]
huskycat = "huskycat.__main__:main"
```

### 1.2 Fix GitLab CI Binary Build Path
**File**: `.gitlab-ci.yml:287`
**Issue**: References `src/__main__.py` which doesn't exist
**Fix**:
```yaml
- uv run pyinstaller --onefile --name huskycat-linux-amd64 huskycat_main.py
```

### 1.3 Remove or Create ContainerFile.dev
**File**: `.gitlab-ci.yml:220-221`
**Issue**: References `ContainerFile.dev` that doesn't exist
**Options**:
- Create `ContainerFile.dev` with development tools
- Remove the dev container build job if not needed

### 1.4 Fix Test Imports
**File**: `tests/test_mcp_integration_comprehensive.py`
**Issue**: `MCPServer` type annotation causes NameError
**Fix**: Use `TYPE_CHECKING` pattern:
```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.huskycat.mcp_server import MCPServer
```

---

## Sprint 2: Multiarch CI Builds (Adopt Crush Patterns)

### 2.1 GitLab CI Multiarch Configuration

Add platform-specific runners and build jobs following crush patterns:

```yaml
# .gitlab-ci.yml additions

# macOS runner template
.macos_saas_runners:
  tags:
    - saas-macos-medium-m1
  image: macos-14-xcode-15

# Build matrix
build:linux-amd64:
  stage: build
  image: python:3.11-slim
  script:
    - pip install uv
    - uv pip install --system pyinstaller
    - uv pip install --system -e .
    - pyinstaller --onefile --name huskycat-linux-amd64 huskycat_main.py
  artifacts:
    paths:
      - dist/huskycat-linux-amd64

build:linux-arm64:
  stage: build
  tags:
    - arm64
  image: python:3.11-slim
  script:
    - pip install uv
    - uv pip install --system pyinstaller
    - uv pip install --system -e .
    - pyinstaller --onefile --name huskycat-linux-arm64 huskycat_main.py
  artifacts:
    paths:
      - dist/huskycat-linux-arm64

build:darwin-arm64:
  extends: .macos_saas_runners
  stage: build
  script:
    - pip3 install uv
    - uv pip install --system pyinstaller
    - uv pip install --system -e .
    - pyinstaller --onefile --name huskycat-darwin-arm64 huskycat_main.py
  artifacts:
    paths:
      - dist/huskycat-darwin-arm64
```

### 2.2 Darwin Code Signing

Following crush patterns for Darwin signing:

```yaml
# Required CI/CD Variables:
# APPLE_CERTIFICATE_BASE64 - Base64 encoded .p12 certificate
# APPLE_CERTIFICATE_PASSWORD - Certificate password
# APPLE_DEVELOPER_ID_APPLICATION - "Developer ID Application: Your Name (TEAMID)"
# APPLE_DEVELOPER_ID_INSTALLER - "Developer ID Installer: Your Name (TEAMID)"
# APPLE_ID - Apple ID email
# APPLE_NOTARIZE_PASSWORD - App-specific password
# APPLE_TEAM_ID - Team ID

sign:darwin:
  extends: .macos_saas_runners
  stage: sign
  needs:
    - build:darwin-arm64
  variables:
    KEYCHAIN_NAME: "signing.keychain-db"
    KEYCHAIN_PASSWORD: "ci-keychain-password"
  script:
    # Download Developer ID CA certificates
    - curl -fsSL -o DeveloperIDG2CA.cer "https://www.apple.com/certificateauthority/DeveloperIDG2CA.cer"
    - curl -fsSL -o AppleWWDRCAG2.cer "https://www.apple.com/certificateauthority/AppleWWDRCAG2.cer"

    # Create and configure keychain
    - security create-keychain -p "$KEYCHAIN_PASSWORD" "$KEYCHAIN_NAME"
    - security default-keychain -s "$KEYCHAIN_NAME"
    - security unlock-keychain -p "$KEYCHAIN_PASSWORD" "$KEYCHAIN_NAME"
    - security set-keychain-settings -lut 3600 "$KEYCHAIN_NAME"

    # Import certificates
    - security import DeveloperIDG2CA.cer -k "$KEYCHAIN_NAME" -T /usr/bin/codesign -T /usr/bin/productsign
    - security import AppleWWDRCAG2.cer -k "$KEYCHAIN_NAME" -T /usr/bin/codesign -T /usr/bin/productsign
    - echo "$APPLE_CERTIFICATE_BASE64" | base64 -d > certificate.p12
    - security import certificate.p12 -k "$KEYCHAIN_NAME" -P "$APPLE_CERTIFICATE_PASSWORD" -T /usr/bin/codesign -T /usr/bin/productsign

    # Set partition list (critical for CI)
    - security set-key-partition-list -S apple-tool:,apple:,codesign: -s -k "$KEYCHAIN_PASSWORD" "$KEYCHAIN_NAME"

    # Sign binary
    - |
      codesign --force --options runtime \
        --sign "$APPLE_DEVELOPER_ID_APPLICATION" \
        --timestamp \
        dist/huskycat-darwin-arm64

    # Verify signature
    - codesign --verify --verbose=4 dist/huskycat-darwin-arm64

    # Create ZIP for notarization
    - zip -j huskycat-darwin-arm64.zip dist/huskycat-darwin-arm64

    # Submit for notarization
    - |
      xcrun notarytool submit huskycat-darwin-arm64.zip \
        --apple-id "$APPLE_ID" \
        --password "$APPLE_NOTARIZE_PASSWORD" \
        --team-id "$APPLE_TEAM_ID" \
        --wait

    # Cleanup
    - security delete-keychain "$KEYCHAIN_NAME"
  artifacts:
    paths:
      - dist/huskycat-darwin-arm64
```

---

## Sprint 3: Git Hooks CLI Installer

### 3.1 Clean Hooks Installer Command

Create a streamlined `setup-hooks` command:

```python
# src/huskycat/commands/hooks.py

import os
import stat
from pathlib import Path

HOOK_TEMPLATE = '''#!/usr/bin/env sh
# HuskyCat pre-commit hook
# Installed by: huskycat setup-hooks

# Find huskycat binary (prefer local, then global, then container)
if [ -x "./dist/huskycat" ]; then
    HUSKYCAT="./dist/huskycat"
elif command -v huskycat >/dev/null 2>&1; then
    HUSKYCAT="huskycat"
elif command -v podman >/dev/null 2>&1; then
    HUSKYCAT="podman run --rm -v .:/workspace ghcr.io/huskycats/validator:latest"
elif command -v docker >/dev/null 2>&1; then
    HUSKYCAT="docker run --rm -v .:/workspace ghcr.io/huskycats/validator:latest"
else
    echo "HuskyCat not found. Install from: https://github.com/huskycats/huskycat"
    exit 1
fi

# Run validation on staged files
$HUSKYCAT validate --staged
'''

def setup_hooks(git_dir: Path = None):
    """Install HuskyCat git hooks in repository."""
    if git_dir is None:
        git_dir = Path.cwd()

    hooks_dir = git_dir / ".git" / "hooks"
    if not hooks_dir.exists():
        raise ValueError(f"Not a git repository: {git_dir}")

    # Install pre-commit hook
    pre_commit = hooks_dir / "pre-commit"
    pre_commit.write_text(HOOK_TEMPLATE)
    pre_commit.chmod(pre_commit.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    print(f"Installed pre-commit hook: {pre_commit}")
    return True
```

### 3.2 One-Line Installer Script

Create `scripts/install.sh` for curl-pipe-bash installation:

```bash
#!/usr/bin/env bash
set -euo pipefail

# HuskyCat installer
# Usage: curl -fsSL https://huskycat.io/install | bash

GITHUB_REPO="huskycats/huskycat"
INSTALL_DIR="${HOME}/.local/bin"

# Detect platform
detect_platform() {
    local os arch
    os="$(uname -s | tr '[:upper:]' '[:lower:]')"
    arch="$(uname -m)"

    case "$arch" in
        x86_64) arch="amd64" ;;
        aarch64|arm64) arch="arm64" ;;
        *) echo "Unsupported architecture: $arch"; exit 1 ;;
    esac

    case "$os" in
        linux) echo "linux-${arch}" ;;
        darwin) echo "darwin-${arch}" ;;
        *) echo "Unsupported OS: $os"; exit 1 ;;
    esac
}

# Download and install
install_huskycat() {
    local platform="$1"
    local version="${HUSKYCAT_VERSION:-latest}"
    local url

    if [ "$version" = "latest" ]; then
        url="https://github.com/${GITHUB_REPO}/releases/latest/download/huskycat-${platform}"
    else
        url="https://github.com/${GITHUB_REPO}/releases/download/${version}/huskycat-${platform}"
    fi

    mkdir -p "$INSTALL_DIR"
    echo "Downloading huskycat from $url..."
    curl -fsSL "$url" -o "${INSTALL_DIR}/huskycat"
    chmod +x "${INSTALL_DIR}/huskycat"

    echo "Installed huskycat to ${INSTALL_DIR}/huskycat"

    # Check PATH
    if [[ ":$PATH:" != *":${INSTALL_DIR}:"* ]]; then
        echo ""
        echo "Add to your PATH:"
        echo "  export PATH=\"\$PATH:${INSTALL_DIR}\""
    fi
}

# Optional: setup git hooks
setup_hooks() {
    if [ -d ".git" ]; then
        read -p "Setup git hooks in current repository? [y/N] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            "${INSTALL_DIR}/huskycat" setup-hooks
        fi
    fi
}

main() {
    local platform
    platform="$(detect_platform)"
    echo "Detected platform: $platform"

    install_huskycat "$platform"
    setup_hooks

    echo ""
    echo "Installation complete!"
    echo "Run 'huskycat --help' to get started."
}

main "$@"
```

---

## Sprint 4: CI Templates

### 4.1 GitLab CI Template (Remote Include)

Create `ci-templates/gitlab-ci-huskycat.yml` for remote include:

```yaml
# HuskyCat GitLab CI Template
# Include in your .gitlab-ci.yml:
#   include:
#     - remote: 'https://raw.githubusercontent.com/huskycats/huskycat/main/ci-templates/gitlab-ci-huskycat.yml'

.huskycat:validate:
  image: ghcr.io/huskycats/validator:latest
  script:
    - huskycat validate ${HUSKYCAT_PATHS:-"."}
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH

.huskycat:validate-staged:
  image: ghcr.io/huskycats/validator:latest
  script:
    - git diff --cached --name-only | xargs huskycat validate
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"

# Ready-to-use jobs
huskycat:lint:
  extends: .huskycat:validate
  stage: test
  allow_failure: false

huskycat:security:
  extends: .huskycat:validate
  stage: test
  variables:
    HUSKYCAT_TOOLS: "bandit,gitleaks"
  allow_failure: true
```

### 4.2 GitHub Actions Workflow

Create `.github/workflows/huskycat.yml`:

```yaml
# HuskyCat GitHub Actions Workflow
# Copy to your repository's .github/workflows/ directory

name: HuskyCat Validation

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  validate:
    runs-on: ubuntu-latest
    container:
      image: ghcr.io/huskycats/validator:latest
    steps:
      - uses: actions/checkout@v4
      - name: Run HuskyCat validation
        run: huskycat validate .

  # Optional: Run on specific file types
  validate-python:
    runs-on: ubuntu-latest
    container:
      image: ghcr.io/huskycats/validator:latest
    steps:
      - uses: actions/checkout@v4
      - name: Validate Python files
        run: |
          find . -name "*.py" -not -path "./venv/*" | xargs huskycat validate
```

### 4.3 Reusable GitHub Action

Create `action.yml` in repository root:

```yaml
name: 'HuskyCat Validation'
description: 'Run HuskyCat code validation'
branding:
  icon: 'check-circle'
  color: 'blue'

inputs:
  paths:
    description: 'Paths to validate'
    required: false
    default: '.'
  tools:
    description: 'Comma-separated list of tools to run'
    required: false
    default: 'all'
  fix:
    description: 'Auto-fix issues where possible'
    required: false
    default: 'false'

runs:
  using: 'docker'
  image: 'docker://ghcr.io/huskycats/validator:latest'
  args:
    - validate
    - ${{ inputs.paths }}
    - --tools=${{ inputs.tools }}
    - ${{ inputs.fix == 'true' && '--fix' || '' }}
```

---

## Sprint 5: Documentation Accuracy

### 5.1 Update CLAUDE.md
- Remove "container-only" claims (code has fallback logic)
- Document actual dual-mode execution
- Update command examples to match implementation

### 5.2 Update Architecture Docs
- Remove specific timing claims
- Document actual tool availability per execution mode
- Add architecture decision records (ADRs)

---

## Priority Matrix

| Item | Severity | Effort | Sprint |
|------|----------|--------|--------|
| Mode detector + adapter interfaces | Critical | Medium | 0 |
| pyproject.toml entry point | Critical | Low | 1 |
| GitLab CI binary path | Critical | Low | 1 |
| ContainerFile.dev | High | Medium | 1 |
| Test imports | High | Low | 1 |
| Multiarch builds | High | High | 2 |
| Darwin signing | High | High | 2 |
| Git hooks installer | Medium | Medium | 3 |
| CI templates | Medium | Medium | 4 |
| Documentation + ADRs | Medium | Medium | 5 |
| Adapter implementations | Medium | High | 6 |
| Mode consolidation | Medium | High | 7 |
| Auto-fix framework | High | High | 8 |

### Sprint Dependencies

```
Sprint 0 (Foundation) ─┬─> Sprint 1 (Critical) ─> Sprint 2 (Builds)
                       │
                       └─> Sprint 6 (Adapters) ─> Sprint 7 (Consolidation) ─> Sprint 8 (Auto-Fix)

Sprint 3 (Hooks) ─┬─> Sprint 4 (CI Templates)
                  │
                  └─> Sprint 5 (Docs)
```

**Parallel Work Possible**:
- Sprints 1-2 can proceed independently of Sprint 6-8
- Sprints 3-5 can proceed in parallel with Sprint 2
- Sprint 0 must complete before Sprint 6
- Sprint 7 must complete before Sprint 8 (auto-fix uses adapters)

**Critical Path**: Sprint 0 → Sprint 6 → Sprint 7 → Sprint 8

---

## Required CI/CD Variables (Darwin Signing)

For Darwin code signing, configure these in GitLab CI/CD settings:

| Variable | Description | Protected | Masked |
|----------|-------------|-----------|--------|
| `APPLE_CERTIFICATE_BASE64` | Base64 .p12 certificate | Yes | Yes |
| `APPLE_CERTIFICATE_PASSWORD` | Certificate password | Yes | Yes |
| `APPLE_DEVELOPER_ID_APPLICATION` | Signing identity | Yes | No |
| `APPLE_DEVELOPER_ID_INSTALLER` | Installer identity | Yes | No |
| `APPLE_ID` | Apple ID email | Yes | No |
| `APPLE_NOTARIZE_PASSWORD` | App-specific password | Yes | Yes |
| `APPLE_TEAM_ID` | Team ID | Yes | No |

---

## Implementation Checklist

### Sprint 0 (Architecture Foundation) - COMPLETE
- [x] Create `ProductMode` enum in `src/huskycat/core/mode_detector.py` (line 30-82)
- [x] Implement `detect_mode()` function (mode_detector.py:30-82)
- [x] Create base `ModeAdapter` abstract class (core/adapters/base.py:1-333)
- [x] Create adapter interfaces for all five modes (core/adapters/*.py - 5 files)
- [x] Wire mode detection into `__main__.py` entry point (__main__.py:1-50)
- [x] Add `HUSKYCAT_MODE` environment variable override (mode_detector.py:35-37)
- [x] Add unit tests for mode detection (tests/test_mode_detection.py)

### Sprint 1 (Critical Fixes)
- [ ] Fix pyproject.toml entry point
- [ ] Fix .gitlab-ci.yml binary build path
- [ ] Create ContainerFile.dev or remove job
- [ ] Fix test import issues

### Sprint 2 (Multiarch Builds)
- [ ] Add linux-arm64 build job
- [ ] Add darwin-arm64 build job
- [ ] Add darwin-amd64 build job
- [ ] Implement Darwin signing job
- [ ] Test notarization workflow

### Sprint 3 (Git Hooks)
- [ ] Refactor setup-hooks command
- [ ] Create one-line installer script
- [ ] Test on Linux, macOS, Windows
- [ ] Add uninstall command

### Sprint 4 (CI Templates)
- [ ] Create GitLab CI template
- [ ] Create GitHub Actions workflow
- [ ] Create reusable GitHub Action
- [ ] Test remote includes

### Sprint 5 (Documentation)
- [ ] Update CLAUDE.md accuracy
- [ ] Update architecture docs
- [ ] Add ADR for product mode architecture
- [ ] Document mode detection logic
- [ ] Add usage examples for each mode

### Sprint 6 (Adapter Refactor)
- [ ] Implement `GitHooksAdapter` with minimal output
- [ ] Implement `CIAdapter` with JUnit XML output
- [ ] Implement `CLIAdapter` with rich terminal output
- [ ] Implement `PipelineAdapter` with JSON output
- [ ] Implement `MCPAdapter` with JSON-RPC output
- [ ] Refactor `validate` command to use adapters
- [ ] Add adapter selection tests

### Sprint 7 (Mode Consolidation)
- [ ] Audit codebase for scattered mode-specific logic
- [ ] Consolidate output formatting into adapters
- [ ] Consolidate error handling into adapters
- [ ] Consolidate tool selection into adapters
- [ ] Remove duplicate conditionals
- [ ] Final integration testing across all modes

### Sprint 8 (Auto-Fix Framework) - FUTURE WORK

**Status**: SKELETON IMPLEMENTED - Full implementation pending

**What exists**:
- `FixConfidence` enum in `adapters/base.py`
- `should_auto_fix()` method in adapters
- Basic `--fix` flag support

**What does NOT exist**:
- `BlackFixer`, `RuffFixer`, etc. classes
- Full `AutoFixer` interface
- Fix orchestration
- Interactive fix prompts

**Implementation Checklist** (FUTURE):
- [ ] Create unified `AutoFixer` interface
- [ ] Implement Python auto-fixers (black, ruff, autoflake, isort)
- [ ] Implement JavaScript auto-fixers (eslint --fix, prettier)
- [ ] Implement YAML auto-fixers (yamllint suggestions)
- [ ] Implement Shell auto-fixers (shellcheck directives)
- [ ] Implement security auto-fixers (safe pattern replacements)
- [ ] Add `--fix` flag to all validate commands
- [ ] Add `--fix-dry-run` for preview mode
- [ ] Implement interactive fix prompts (CLI mode)
- [ ] Implement batch fix mode (Pipeline/CI modes)
- [ ] Add fix reporting (what was changed, what couldn't be fixed)
- [ ] Test auto-fix across all product modes

---

## Mode-Specific Test Matrix

### Validation Tests

| Mode | Input | Expected Output | Exit Code |
|------|-------|-----------------|-----------|
| Git Hooks | Staged files with errors | Minimal error text | 1 |
| Git Hooks | Staged files clean | (silent) | 0 |
| CI | Any files with errors | JUnit XML report | 1 |
| CI | Clean files | JUnit XML (pass) | 0 |
| CLI | Files with errors | Colored output + suggestions | 1 |
| CLI | Clean files | Success message | 0 |
| Pipeline | stdin file list | JSON array of results | 0/1 |
| MCP | JSON-RPC request | JSON-RPC response | N/A |

### Auto-Fix Tests

| Mode | Input | `--fix` Behavior | Output |
|------|-------|------------------|--------|
| Git Hooks | Staged + fixable | Fix SAFE only | List of fixed files |
| Git Hooks | Staged + LIKELY fixes | Prompt if TTY | Fixed + prompted files |
| CI | Any files | Report only (no changes) | JSON diff of what would fix |
| CLI | Files + `--fix` | Fix SAFE+LIKELY | Colored report |
| CLI | Files + `--fix --interactive` | Prompt for each UNCERTAIN | Interactive prompts |
| CLI | Files + `--fix --unsafe` | Fix ALL including UNCERTAIN | Full report |
| CLI | Files + `--fix --dry-run` | Preview changes | Diff output |
| Pipeline | stdin + `--fix` | Fix all | JSON report |
| MCP | `huskycat_fix` tool | Return suggestions | JSON-RPC with fixes |
| MCP | `huskycat_apply_suggestion` | Apply single fix | JSON-RPC confirmation |
