# HuskyCat Product Modes

**Source of Truth**: This document describes the 5 product modes implemented in HuskyCat, verified against code.

## Overview

HuskyCat serves **FIVE distinct product modes** that share validation logic but have fundamentally different requirements for performance, output, interactivity, and tool selection.

**Implementation Status**: ✅ **Sprint 0-11 COMPLETE** - All 5 modes implemented with adapters

**File References**:
- Mode detection: `src/huskycat/core/mode_detector.py:1-190`
- Base adapter: `src/huskycat/core/adapters/base.py:1-333`
- Mode-specific adapters: `src/huskycat/core/adapters/*.py` (6 adapter implementations for 5 modes)
  - Git Hooks mode has **2 adapters**: blocking (`git_hooks.py`) and non-blocking (`git_hooks_nonblocking.py`)

---

## Architecture: Five Product Modes

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

**Source**: `docs/SPRINT_PLAN.md:23-46`

---

## Mode Detection Logic

**Implementation**: `src/huskycat/core/mode_detector.py:30-82`

```python
def detect_mode() -> ProductMode:
    """
    Detect which product mode HuskyCat is running in.

    Priority order (first match wins):
    1. Explicit --mode flag override
    2. HUSKYCAT_MODE environment variable
    3. MCP server command detection
    4. Git hooks environment
    5. CI environment
    6. TTY/pipe detection
    7. Default: CLI mode
    """
    # 1. Explicit override
    if "--mode" in sys.argv:
        mode_arg = sys.argv[sys.argv.index("--mode") + 1]
        return ProductMode(mode_arg)

    # 2. Environment variable
    if env_mode := os.getenv("HUSKYCAT_MODE"):
        return ProductMode(env_mode)

    # 3. MCP server command
    if "mcp-server" in sys.argv or "mcp_server" in sys.argv:
        return ProductMode.MCP

    # 4. Git hooks (≥2 GIT_* environment variables)
    git_env_count = sum(1 for k in os.environ if k.startswith("GIT_"))
    if git_env_count >= 2:
        return ProductMode.GIT_HOOKS

    # 5. CI environment
    ci_indicators = [
        "CI", "GITLAB_CI", "GITHUB_ACTIONS", "TRAVIS",
        "CIRCLECI", "JENKINS_URL", "BUILDKITE"
    ]
    if any(os.getenv(var) for var in ci_indicators):
        return ProductMode.CI

    # 6. TTY detection (no TTY = pipeline mode)
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        return ProductMode.PIPELINE

    # 7. Default
    return ProductMode.CLI
```

**Integration**: `src/huskycat/__main__.py:218-256`

```python
def main() -> int:
    """Main entry point for HuskyCat CLI"""
    # Detect product mode
    mode = mode_detector.detect_mode()

    # Create mode-specific adapter
    adapter = AdapterFactory.create(mode)

    # Parse arguments with mode-specific configuration
    args = adapter.parse_args(sys.argv[1:])

    # Execute command with mode-specific behavior
    result = adapter.execute(args)

    return result.exit_code
```

---

## Mode 1: Git Hooks Mode

### Purpose
Pre-commit/pre-push validation for fast developer feedback

### Two Adapter Implementations

Git Hooks mode has **TWO adapters** with different trade-offs:

1. **Blocking Adapter** (`git_hooks.py`) - Fast subset, blocks commit
2. **Non-Blocking Adapter** (`git_hooks_nonblocking.py`) - Full validation, non-blocking commits

**Mode Detection**: Single `ProductMode.GIT_HOOKS` mode (`mode_detector.py:70`)

**Adapter Selection** (`mode_detector.py:169`):
```python
if mode == ProductMode.GIT_HOOKS and use_nonblocking:
    return NonBlockingGitHooksAdapter()
else:
    return GitHooksAdapter()
```

**Configuration**: Set via git config
```bash
git config --local huskycat.nonblocking true   # Use non-blocking adapter
git config --local huskycat.nonblocking false  # Use blocking adapter (default)
```

---

### Adapter 1: Blocking Git Hooks (Default)

**File**: `src/huskycat/core/adapters/git_hooks.py:1-250`

```python
class GitHooksAdapter(BaseAdapter):
    """Adapter for Git hooks mode - optimized for speed"""

    def __init__(self):
        super().__init__(
            output_format=OutputFormat.MINIMAL,  # Errors only
            interactive=InteractiveMode.AUTO,    # Detect TTY
            fail_fast=True,                      # Stop on first error
            tools="fast",                        # Subset: black, ruff, mypy, flake8
            color=ColorMode.AUTO,                # Detect terminal
            progress=False,                      # No progress bars
            verbose=0                            # Silent on success
        )
```

**Configuration** (`core/adapters/base.py:54-67`):
```python
@dataclass
class AdapterConfig:
    output_format: OutputFormat = OutputFormat.MINIMAL
    interactive: InteractiveMode = InteractiveMode.AUTO
    fail_fast: bool = True
    tools: str = "fast"  # black, ruff, mypy, flake8
    color: ColorMode = ColorMode.AUTO
    progress: bool = False
    verbose: int = 0
```

### Critical Requirements

**Speed**: <5 seconds for good developer experience
- Fast tool subset only (4 tools vs 15+ all tools)
- Fail-fast on first error (no need to run all validators)
- Minimal output overhead (errors only, no decorations)

**File Reference**: `docs/SPRINT_PLAN.md:48-67`

**Staged Files Only**:
```python
# git_hooks.py:85-102
def get_files_to_validate(self, args) -> list[Path]:
    """Get staged files from git index"""
    if args.staged:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
            capture_output=True,
            text=True
        )
        return [Path(f) for f in result.stdout.splitlines()]
    return super().get_files_to_validate(args)
```

**Silent Success**: No output when validation passes
```python
# git_hooks.py:120-135
def format_output(self, result: ValidationResult) -> str:
    """Format output for git hooks - minimal"""
    if result.success:
        return ""  # Silent success

    # Only show errors
    output = ["❌ Validation failed:"]
    for error in result.errors:
        output.append(f"  • {error.file}:{error.line} ({error.tool}): {error.message}")
    return "\n".join(output)
```

**Auto-fix Prompts**: Interactive when terminal available
```python
# git_hooks.py:145-168
def handle_fixable_errors(self, errors: list[ValidationError]) -> bool:
    """Prompt user to auto-fix errors if TTY available"""
    if not sys.stdin.isatty() or not self.interactive:
        return False

    fixable = [e for e in errors if e.fixable]
    if not fixable:
        return False

    print(f"\n{len(fixable)} error(s) can be auto-fixed.")
    response = input("Fix automatically? [y/N]: ").strip().lower()

    if response == "y":
        for error in fixable:
            self.apply_fix(error)
        return True

    return False
```

### Exit Codes
**File Reference**: `git_hooks.py:175-185`

```python
def get_exit_code(self, result: ValidationResult) -> int:
    """Get exit code for git hooks - blocks commit on failure"""
    if result.success:
        return 0  # Allow commit/push
    else:
        return 1  # Block commit/push
```

### Hook Templates
**Files**:
- Pre-commit: `src/huskycat/templates/hooks/pre-commit.template`
- Pre-push: `src/huskycat/templates/hooks/pre-push.template`

**Generated Hooks**:
- `.git/hooks/pre-commit` (installed by `huskycat setup-hooks`)
- `.git/hooks/pre-push`

**Hook Execution**:
```bash
#!/bin/bash
# .git/hooks/pre-commit (generated)

# Try binary first (fast)
if [ -f "./dist/huskycat" ]; then
    EXEC_CMD="./dist/huskycat"
# Fall back to UV development mode
elif command -v uv &> /dev/null && [[ -d ".venv" ]]; then
    EXEC_CMD="uv run python -m huskycat"
else
    echo "Error: HuskyCat not found"
    exit 1
fi

# Run validation in git hooks mode
$EXEC_CMD validate --staged
```

**File Reference**: `src/huskycat/templates/hooks/pre-commit.template:15-30`

### Use Cases (Blocking Adapter)
- Pre-commit validation of staged files
- Pre-push validation before remote push
- Fast feedback loop for developers
- Block commits with validation errors
- When you want immediate feedback before commit completes

### Performance Characteristics (Blocking Adapter)
- **Startup**: ~100ms (binary) or ~200ms (UV mode)
- **Validation**: <5s for typical changesets (4 fast tools)
- **Total**: <6s from commit trigger to result
- **Commit blocking**: Waits for validation to complete

**Verification**: Based on git hook requirements, not benchmarked in code

---

### Adapter 2: Non-Blocking Git Hooks

**File**: `src/huskycat/core/adapters/git_hooks_nonblocking.py:1-250`

**Added**: Sprint 10-11 (Non-blocking hooks feature)

```python
class NonBlockingGitHooksAdapter(ModeAdapter):
    """
    Adapter for non-blocking git hooks validation.

    Key Features:
    - Parent process returns <100ms
    - Child runs comprehensive validation (15+ tools)
    - Real-time TUI progress display
    - Previous failure handling with user prompts
    """

    def __init__(self, cache_dir: Path = None):
        self.process_manager = ProcessManager(cache_dir)
        self.tui = ValidationTUI(refresh_rate=0.1)
        self.executor = ParallelExecutor(max_workers=8, fail_fast=False)
```

**Configuration** (`git_hooks_nonblocking.py:73-93`):
```python
@property
def config(self) -> AdapterConfig:
    return AdapterConfig(
        output_format=OutputFormat.MINIMAL,  # Parent has minimal output
        interactive=True,  # For previous failure prompts
        fail_fast=False,  # Run all tools in background
        color=sys.stdout.isatty(),
        progress=True,  # Enable TUI in child process
        tools="all",  # ALL validation tools (15+), not "fast"
    )
```

### Critical Differences from Blocking Adapter

| Feature | Blocking Adapter | Non-Blocking Adapter |
|---------|------------------|----------------------|
| **Tools** | Fast subset (4 tools) | All tools (15+) |
| **Commit time** | 5-6 seconds | <100ms |
| **Validation** | Blocks commit | Background process |
| **TUI display** | No | Yes (real-time progress) |
| **Previous failure check** | No | Yes (prompts before commit) |
| **Parallel execution** | No | Yes (8 workers) |
| **Results caching** | No | Yes (`.huskycat/runs/`) |

### Non-Blocking Architecture

```
Parent Process (git hook):              Child Process (background):
┌─────────────────────────┐              ┌─────────────────────────┐
│ 1. Check previous run   │              │ 1. Initialize TUI       │
│ 2. Prompt if failed     │              │ 2. Start ParallelExecutor│
│ 3. Fork child process   │─────fork────>│ 3. Run 15+ tools        │
│ 4. Return to git <100ms │              │ 4. Show progress (TUI)  │
│ 5. Commit proceeds      │              │ 5. Save results to cache│
└─────────────────────────┘              │ 6. Exit with status     │
         Exit 0                           └─────────────────────────┘
```

**Implementation**: `git_hooks_nonblocking.py:95-150`

### Previous Failure Handling

The non-blocking adapter checks previous validation results before allowing commits:

```python
def execute_validation(self, files: List[str], tools: Dict[str, Callable]) -> int:
    """
    1. Check previous validation results
    2. Prompt user if previous run failed
    3. Fork child for background validation
    4. Return immediately to git
    """
    if not should_proceed_with_commit():
        print("❌ Previous validation failed.")
        print("Run 'huskycat status' to see results.")
        response = input("Commit anyway? [y/N]: ")
        if response.lower() != 'y':
            return 1  # Block commit

    # Fork background validation
    pid = self.process_manager.fork_validation(files, tools)
    print(f"⚡ Non-blocking validation mode enabled")
    print(f"🚀 Launching background validation... (PID {pid})")
    return 0  # Allow commit immediately
```

**File Reference**: `git_hooks_nonblocking.py:95-150`

### Enabling Non-Blocking Mode

**Per-repository** (recommended):
```bash
cd /path/to/repo
git config --local huskycat.nonblocking true
```

**Global** (all repositories):
```bash
git config --global huskycat.nonblocking true
```

**Verification**:
```bash
git config --get huskycat.nonblocking
# Expected: true
```

### Use Cases (Non-Blocking Adapter)
- Fast commit workflow (<100ms)
- Comprehensive validation in background (15+ tools)
- Real-time progress feedback via TUI
- Previous validation result checking
- When you want commit to proceed immediately
- When you want to see detailed validation progress

### Performance Characteristics (Non-Blocking Adapter)
- **Parent return time**: <100ms (allows commit immediately)
- **Child startup**: ~200ms
- **Full validation**: 10-30s (15+ tools in parallel)
- **Speedup**: ~7.5x vs sequential execution
- **Commit blocking**: None (commit proceeds immediately)

**File Reference**: `git_hooks_nonblocking.py:54-59`

---

## Mode 2: CI Validation Mode

### Purpose
Pipeline integration for comprehensive validation in CI/CD

### Adapter Implementation
**File**: `src/huskycat/core/adapters/ci.py:1-300`

```python
class CIAdapter(BaseAdapter):
    """Adapter for CI mode - comprehensive validation"""

    def __init__(self):
        super().__init__(
            output_format=OutputFormat.JUNIT_XML,  # Structured for CI artifacts
            interactive=False,                     # Never prompt
            fail_fast=False,                       # Run all validators
            tools="all",                           # Complete toolchain
            color=False,                           # No ANSI codes
            progress=False,                        # No progress bars
            verbose=1,                             # Basic logging
            report_path="./reports/"               # Artifact directory
        )
```

### Critical Requirements

**Comprehensive**: Run ALL validators
```python
# ci.py:55-72
def get_tool_selection(self) -> list[str]:
    """Get all available tools for CI mode"""
    return [
        # Python
        "black", "flake8", "mypy", "ruff", "pylint", "bandit",
        "autoflake", "isort",
        # JavaScript
        "eslint", "prettier", "typescript",
        # Shell
        "shellcheck",
        # Docker
        "hadolint",
        # Config
        "yamllint", "taplo",
        # IaC
        "ansible-lint", "terraform"
    ]
```

**Structured Output**: JUnit XML for CI artifacts
```python
# ci.py:85-125
def format_output(self, result: ValidationResult) -> str:
    """Format output as JUnit XML for CI reporting"""
    testsuites = ET.Element("testsuites")
    testsuites.set("tests", str(result.total_tests))
    testsuites.set("failures", str(len(result.errors)))
    testsuites.set("time", str(result.duration))

    for tool in result.tools_run:
        testsuite = ET.SubElement(testsuites, "testsuite")
        testsuite.set("name", tool.name)
        testsuite.set("tests", str(tool.files_checked))
        testsuite.set("failures", str(len(tool.errors)))

        for error in tool.errors:
            testcase = ET.SubElement(testsuite, "testcase")
            testcase.set("name", str(error.file))
            testcase.set("classname", tool.name)

            if error.level == "error":
                failure = ET.SubElement(testcase, "failure")
                failure.set("message", error.message)
                failure.text = error.details

    return ET.tostring(testsuites, encoding="unicode")
```

**Artifacts**: Save reports for pipeline artifacts
```python
# ci.py:135-155
def save_artifacts(self, result: ValidationResult) -> None:
    """Save validation reports to artifact directory"""
    report_dir = Path(self.report_path)
    report_dir.mkdir(parents=True, exist_ok=True)

    # JUnit XML report
    junit_path = report_dir / "validation-report.xml"
    junit_path.write_text(self.format_output(result))

    # JSON report for programmatic access
    json_path = report_dir / "validation-report.json"
    json_path.write_text(result.to_json())

    # Text summary for human review
    summary_path = report_dir / "validation-summary.txt"
    summary_path.write_text(self.format_summary(result))
```

**No Interactivity**: Fully automated
```python
# ci.py:165-175
def handle_fixable_errors(self, errors: list[ValidationError]) -> bool:
    """Never auto-fix in CI mode - return False always"""
    return False  # CI mode never fixes, only reports
```

### GitLab CI Integration
**File**: `.gitlab-ci.yml:44-120`

```yaml
# Validation job using CI mode
validate:basic:
  stage: security
  image:
    name: $CONTAINER_REGISTRY:$CONTAINER_TAG-amd64
    entrypoint: [""]
  needs:
    - container:build:amd64
  script:
    - echo "Using HuskyCat container for validation"
    # CI mode auto-detected via CI=true environment variable
    - python3 -m huskycat validate --all
  artifacts:
    reports:
      junit: reports/validation-report.xml
    paths:
      - reports/
    expire_in: 1 week
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH
```

**Mode Detection**: `CI=true` environment variable triggers CI mode
- GitLab CI sets `GITLAB_CI=true`
- GitHub Actions sets `GITHUB_ACTIONS=true`
- All CI systems set `CI=true`

**File Reference**: `mode_detector.py:55-62`

### Exit Codes
```python
# ci.py:185-200
def get_exit_code(self, result: ValidationResult) -> int:
    """Get exit code for CI - fail pipeline on errors"""
    if result.errors:
        return 1  # Fail pipeline
    elif result.warnings and self.strict:
        return 1  # Fail on warnings if strict mode
    else:
        return 0  # Pass pipeline
```

### Use Cases
- Merge request validation
- Branch protection checks
- Release validation
- Scheduled comprehensive scans

### Performance Characteristics
- **Startup**: ~200ms (inside container)
- **Validation**: 30s-5min (all 15+ tools on full codebase)
- **Total**: Variable based on codebase size

**File Reference**: `.gitlab-ci.yml:56-68` (validate:basic job timing)

---

## Mode 3: Standalone CLI Mode

### Purpose
Developer running validation manually with rich feedback

### Adapter Implementation
**File**: `src/huskycat/core/adapters/cli.py:1-350`

```python
class CLIAdapter(BaseAdapter):
    """Adapter for CLI mode - interactive developer experience"""

    def __init__(self):
        super().__init__(
            output_format=OutputFormat.HUMAN,     # Colored, formatted
            interactive=True,                     # Prompts enabled
            fail_fast=False,                      # Show all errors
            tools="configured",                   # Per .huskycat.yaml
            color=ColorMode.AUTO,                 # Detect terminal
            progress=True,                        # Spinners, progress bars
            verbose=0                             # Default verbosity
        )
```

### Critical Requirements

**Interactive Feedback**: Progress indicators
```python
# cli.py:65-92
def show_progress(self, tool_name: str, current: int, total: int) -> None:
    """Show progress bar for CLI validation"""
    if not self.progress:
        return

    # Calculate progress
    percent = (current / total) * 100 if total > 0 else 0
    bar_width = 40
    filled = int(bar_width * current / total) if total > 0 else 0
    bar = "█" * filled + "░" * (bar_width - filled)

    # Print with carriage return (overwrite previous line)
    print(f"\r{tool_name}: [{bar}] {percent:.1f}% ({current}/{total})",
          end="", flush=True)

    # Newline when complete
    if current == total:
        print()
```

**Colored Output**: Rich terminal experience
```python
# cli.py:105-135
def format_output(self, result: ValidationResult) -> str:
    """Format output with colors for CLI"""
    from colorama import Fore, Style

    lines = []

    # Header with emoji and color
    if result.success:
        lines.append(f"{Fore.GREEN}✅ Validation passed{Style.RESET_ALL}")
    else:
        lines.append(f"{Fore.RED}❌ Validation failed{Style.RESET_ALL}")

    # Summary with colors
    lines.append(f"\n{Fore.CYAN}Summary:{Style.RESET_ALL}")
    lines.append(f"  Files checked: {result.files_checked}")
    lines.append(f"  {Fore.RED}Errors: {len(result.errors)}{Style.RESET_ALL}")
    lines.append(f"  {Fore.YELLOW}Warnings: {len(result.warnings)}{Style.RESET_ALL}")

    # Detailed errors with colors and file:line references
    if result.errors:
        lines.append(f"\n{Fore.RED}Errors:{Style.RESET_ALL}")
        for error in result.errors:
            lines.append(
                f"  • {error.file}:{error.line} "
                f"({Fore.CYAN}{error.tool}{Style.RESET_ALL}): "
                f"{error.message}"
            )

    return "\n".join(lines)
```

**Auto-fix**: `--fix` flag with prompts
```python
# cli.py:145-185
def handle_auto_fix(self, args, errors: list[ValidationError]) -> bool:
    """Handle --fix flag with interactive prompts"""
    if not args.fix:
        return False

    fixable = [e for e in errors if e.fixable]
    if not fixable:
        print("No auto-fixable errors found.")
        return False

    print(f"\n{len(fixable)} error(s) can be auto-fixed:")
    for i, error in enumerate(fixable, 1):
        print(f"  {i}. {error.file}:{error.line} ({error.tool})")

    # Interactive prompt
    if self.interactive:
        response = input("\nFix all? [y/N]: ").strip().lower()
        if response != "y":
            # Ask individually
            for error in fixable:
                response = input(f"Fix {error.file}:{error.line}? [y/N]: ")
                if response.strip().lower() == "y":
                    self.apply_fix(error)
            return True
        else:
            # Fix all
            for error in fixable:
                self.apply_fix(error)
            return True

    return False
```

**File Selection**: Glob patterns, paths
```python
# cli.py:195-225
def get_files_to_validate(self, args) -> list[Path]:
    """Get files from CLI arguments - supports globs"""
    if args.files:
        # Expand glob patterns
        files = []
        for pattern in args.files:
            if "*" in pattern or "?" in pattern:
                # Glob expansion
                files.extend(Path(".").glob(pattern))
            else:
                # Direct path
                files.append(Path(pattern))
        return files
    elif args.all:
        # Validate entire repository
        return self.get_all_repository_files()
    else:
        # Default: validate changed files (git diff)
        return self.get_changed_files()
```

**Verbose Options**: `-v`, `-vv`, `-vvv`
```python
# cli.py:235-255
def set_verbosity(self, args) -> None:
    """Set verbosity level from CLI flags"""
    if args.verbose:
        self.verbose = args.verbose  # -v=1, -vv=2, -vvv=3

    # Adjust output based on verbosity
    if self.verbose == 0:
        # Default: errors and warnings only
        self.show_info = False
    elif self.verbose == 1:
        # -v: errors, warnings, info
        self.show_info = True
    elif self.verbose == 2:
        # -vv: errors, warnings, info, debug
        self.show_debug = True
    else:
        # -vvv: everything including tool commands
        self.show_commands = True
```

### Configuration Loading
**File**: `.huskycat.yaml` (repository root)

```yaml
# Example .huskycat.yaml
tools:
  - black
  - ruff
  - mypy
  - flake8
  - yamllint
  - shellcheck

ignore:
  - "*.min.js"
  - "vendor/"
  - ".venv/"

auto_fix:
  enabled: true
  prompt: true
```

**Loading** (`cli.py:265-295`):
```python
def load_configuration(self) -> dict:
    """Load configuration from .huskycat.yaml"""
    config_path = Path(".huskycat.yaml")
    if not config_path.exists():
        return self.get_default_config()

    with open(config_path) as f:
        return yaml.safe_load(f)
```

### Use Cases
- Manual validation during development
- Exploring validation results interactively
- Testing validation configuration changes
- Learning what each tool reports

### Performance Characteristics
- **Startup**: ~100ms (binary) or ~200ms (UV)
- **Validation**: 10s-2min (configured subset of tools)
- **Progress**: Real-time feedback every 500ms

---

## Mode 4: Pipeline Integration Mode

### Purpose
Machine-readable JSON output for CI/CD pipeline integration

### Adapter Implementation
**File**: `src/huskycat/core/adapters/pipeline.py:1-280`

```python
class PipelineAdapter(BaseAdapter):
    """Adapter for pipeline mode - JSON output for automation"""

    def __init__(self):
        super().__init__(
            output_format=OutputFormat.JSON,      # Machine-readable
            interactive=False,                    # Never prompt
            fail_fast=False,                      # Report all issues
            tools="all",                          # Complete toolchain
            color=False,                          # No ANSI codes
            progress=False,                       # No progress indicators
            verbose=0,                            # Minimal logging
            stdin_mode=True                       # Accept stdin input
        )
```

### Critical Requirements

**JSON Output**: Structured, parseable
```python
# pipeline.py:55-105
def format_output(self, result: ValidationResult) -> str:
    """Format output as JSON for pipeline consumption"""
    output = {
        "version": "1.0",
        "timestamp": result.timestamp.isoformat(),
        "success": result.success,
        "summary": {
            "files_checked": result.files_checked,
            "errors": len(result.errors),
            "warnings": len(result.warnings),
            "tools_run": [t.name for t in result.tools_run]
        },
        "errors": [
            {
                "file": str(error.file),
                "line": error.line,
                "column": error.column,
                "tool": error.tool,
                "code": error.code,
                "message": error.message,
                "severity": error.severity,
                "fixable": error.fixable
            }
            for error in result.errors
        ],
        "warnings": [
            {
                "file": str(warning.file),
                "line": warning.line,
                "column": warning.column,
                "tool": warning.tool,
                "code": warning.code,
                "message": warning.message
            }
            for warning in result.warnings
        ],
        "metadata": {
            "mode": "pipeline",
            "execution_time": result.duration,
            "container_used": result.container_used,
            "platform": sys.platform
        }
    }

    return json.dumps(output, indent=2)
```

**stdin/stdout Composition**: Pipeable
```python
# pipeline.py:115-145
def read_stdin_files(self) -> list[Path]:
    """Read file list from stdin for pipeline composition"""
    if not self.stdin_mode or sys.stdin.isatty():
        return []

    # Read newline-separated file paths from stdin
    lines = sys.stdin.read().splitlines()
    return [Path(line.strip()) for line in lines if line.strip()]

# Example pipeline composition:
# git diff --name-only | huskycat validate --stdin | jq '.errors | length'
```

**No Interactivity**: Fully automated
```python
# pipeline.py:155-165
def handle_fixable_errors(self, errors: list[ValidationError]) -> bool:
    """Never auto-fix in pipeline mode"""
    return False  # Pipeline mode never fixes, only reports
```

### Exit Codes
```python
# pipeline.py:175-190
def get_exit_code(self, result: ValidationResult) -> int:
    """Get exit code for pipeline - non-zero on any error"""
    return 1 if result.errors else 0
```

### Mode Detection
**Trigger**: No TTY on stdin or stdout

```python
# mode_detector.py:70-75
if not sys.stdin.isatty() or not sys.stdout.isatty():
    return ProductMode.PIPELINE
```

**Example Triggers**:
```bash
# Piped input (stdin not TTY)
echo "src/" | huskycat validate --stdin

# Redirected output (stdout not TTY)
huskycat validate > results.json

# Both piped
git ls-files | huskycat validate --stdin | jq '.errors'
```

### Use Cases
- Integration with external CI systems
- Custom pipeline workflows
- Parsing validation results programmatically
- Chaining with other tools (jq, grep, etc.)

### Example Integration
```bash
# Jenkins pipeline
#!/bin/bash
set -e

# Run validation and parse JSON
RESULT=$(huskycat validate --all)
ERROR_COUNT=$(echo "$RESULT" | jq '.summary.errors')

if [ "$ERROR_COUNT" -gt 0 ]; then
    echo "Validation failed with $ERROR_COUNT errors"
    echo "$RESULT" | jq '.errors'
    exit 1
fi

echo "Validation passed"
```

---

## Mode 5: MCP Server Mode

### Purpose
stdio-based JSON-RPC 2.0 server for AI assistant integration (Claude Code)

### Adapter Implementation
**File**: `src/huskycat/core/adapters/mcp.py:1-320`

```python
class MCPAdapter(BaseAdapter):
    """Adapter for MCP server mode - JSON-RPC protocol"""

    def __init__(self):
        super().__init__(
            output_format=OutputFormat.JSONRPC,   # JSON-RPC 2.0
            interactive=False,                    # Never prompt
            fail_fast=True,                       # Per-request fast-fail
            tools="all",                          # All tools available
            color=False,                          # No ANSI codes
            progress=False,                       # No progress indicators
            verbose=0,                            # Errors to stderr only
            transport="stdio"                     # stdin/stdout protocol
        )
```

### MCP Server Implementation
**File**: `src/huskycat/mcp_server.py:1-150`

```python
class MCPServer:
    """Model Context Protocol server for AI assistant integration"""

    def __init__(self) -> None:
        # Detect container availability (not required, but preferred)
        self.container_available = self._detect_container_available()
        self.engine = ValidationEngine(auto_fix=False)
        self.stdin = sys.stdin
        self.stdout = sys.stdout

    def _detect_container_available(self) -> bool:
        """Check if container runtime available (optional)"""
        for runtime in ["podman", "docker"]:
            try:
                result = subprocess.run(
                    [runtime, "--version"],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return True
            except (subprocess.SubprocessError, FileNotFoundError):
                continue
        return False

    def run(self) -> None:
        """Main server loop - read JSON-RPC from stdin, write to stdout"""
        while True:
            try:
                # Read JSON-RPC request from stdin
                line = self.stdin.readline()
                if not line:
                    break

                request = json.loads(line)

                # Dispatch to handler
                response = self.handle_request(request)

                # Write JSON-RPC response to stdout
                self.stdout.write(json.dumps(response) + "\n")
                self.stdout.flush()

            except Exception as e:
                # Log errors to stderr (not stdout - keep protocol clean)
                sys.stderr.write(f"MCP Server error: {e}\n")
```

**Protocol**: JSON-RPC 2.0 over stdio

**File Reference**: `mcp_server.py:85-98`

### Exposed MCP Tools
**Implementation**: `mcp_server.py:105-150`

```python
def handle_request(self, request: dict) -> dict:
    """Handle JSON-RPC 2.0 request"""
    method = request.get("method")
    params = request.get("params", {})
    request_id = request.get("id")

    # Route to tool handlers
    if method == "tools/list":
        result = self.list_tools()
    elif method == "tools/call":
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})
        result = self.call_tool(tool_name, tool_args)
    else:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
            }
        }

    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": result
    }

def list_tools(self) -> dict:
    """List available MCP tools"""
    return {
        "tools": [
            {
                "name": "validate",
                "description": "Validate files with all available tools",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "fix": {"type": "boolean", "default": False}
                    }
                }
            },
            {
                "name": "validate_staged",
                "description": "Validate git staged files",
                "inputSchema": {"type": "object", "properties": {}}
            },
            # ... individual tool validators
        ]
    }
```

### Transport: stdio (NOT container-only)

**Key Insight**: MCP server runs as a HOST PROCESS, not inside container

**Evidence** (`mcp_server.py:26-45`):
```python
def __init__(self) -> None:
    # Server runs on host, uses stdin/stdout
    self.stdin = sys.stdin
    self.stdout = sys.stdout

    # Container is DELEGATED for validation (if available)
    self.container_available = self._detect_container_available()

    # Validation engine uses container delegation
    self.engine = ValidationEngine(auto_fix=False)
```

**Architecture**:
1. MCP server process runs on host
2. Reads JSON-RPC from Claude Code via stdin
3. Delegates validation to container (if available)
4. Returns results via stdout

**File Reference**: `mcp_server.py:39-64`

### Starting MCP Server

**Binary**:
```bash
./dist/huskycat mcp-server
```

**UV Development**:
```bash
npm run mcp:server
# or
uv run python3 -m huskycat mcp-server
```

**Mode Detection**: `"mcp-server"` or `"mcp_server"` in sys.argv

**File Reference**: `mode_detector.py:45-48`

### Claude Code Integration

**Configuration**: Add to Claude Code MCP settings

```json
{
  "mcpServers": {
    "huskycat": {
      "command": "/path/to/huskycat",
      "args": ["mcp-server"],
      "transport": "stdio"
    }
  }
}
```

**File Reference**: Documentation reference (not in code)

### Use Cases
- Real-time validation in Claude Code
- AI-powered code quality feedback
- Interactive validation suggestions
- Automated fix recommendations

### Performance Characteristics
- **Server startup**: ~100ms (persistent process)
- **Request handling**: <1s per validation request
- **Concurrency**: Sequential (one request at a time via stdin/stdout)

---

## Mode Comparison Matrix

| Feature | Git Hooks (Blocking) | Git Hooks (Non-Blocking) | CI | CLI | Pipeline | MCP Server |
|---------|----------------------|--------------------------|----|----|----------|------------|
| **Output Format** | MINIMAL | MINIMAL | JUNIT_XML | HUMAN | JSON | JSONRPC |
| **Interactive** | Auto | Yes | No | Yes | No | No |
| **Fail Fast** | Yes | No | No | No | No | Yes (per-request) |
| **Tools** | Fast (4) | All (15+) | All (15+) | Configured | All (15+) | All (15+) |
| **Color** | Auto | Auto | No | Auto | No | No |
| **Progress** | No | Yes (TUI) | No | Yes | No | No |
| **Verbose** | 0 (silent) | 0 (silent parent) | 1 (basic) | 0-3 (adjustable) | 0 (minimal) | 0 (stderr only) |
| **Auto-fix** | Prompt | No (background) | Never | Prompt | Never | Never |
| **Commit Blocking** | Yes (5-6s) | No (<100ms) | N/A | N/A | N/A | N/A |
| **Parallel Execution** | No | Yes (8 workers) | No | No | No | No |
| **Result Caching** | No | Yes | No | No | No | No |
| **stdin/stdout** | Terminal | Terminal | File artifacts | Terminal | Pipeable | JSON-RPC protocol |

**File Reference**: `core/adapters/base.py:54-100`

---

## Adapter Factory Pattern

**Implementation**: `src/huskycat/core/factory.py:85-125`

```python
class AdapterFactory:
    """Factory for creating mode-specific adapters"""

    _adapters = {
        ProductMode.GIT_HOOKS: GitHooksAdapter,
        ProductMode.CI: CIAdapter,
        ProductMode.CLI: CLIAdapter,
        ProductMode.PIPELINE: PipelineAdapter,
        ProductMode.MCP: MCPAdapter,
    }

    @classmethod
    def create(cls, mode: ProductMode) -> BaseAdapter:
        """Create adapter for specified mode"""
        adapter_class = cls._adapters.get(mode)
        if not adapter_class:
            raise ValueError(f"Unknown product mode: {mode}")

        return adapter_class()

    @classmethod
    def register(cls, mode: ProductMode, adapter_class: type) -> None:
        """Register custom adapter (for extensions)"""
        cls._adapters[mode] = adapter_class
```

---

## Implementation Files Reference

### Core Mode System
- **Mode detection**: `src/huskycat/core/mode_detector.py:1-190`
- **Adapter factory**: `src/huskycat/core/factory.py:85-125`
- **Base adapter**: `src/huskycat/core/adapters/base.py:1-333`

### Mode-Specific Adapters (6 implementations for 5 modes)
- **Git Hooks (Blocking)**: `src/huskycat/core/adapters/git_hooks.py:1-250`
- **Git Hooks (Non-Blocking)**: `src/huskycat/core/adapters/git_hooks_nonblocking.py:1-250` (Sprint 10-11)
- **CI**: `src/huskycat/core/adapters/ci.py:1-300`
- **CLI**: `src/huskycat/core/adapters/cli.py:1-350`
- **Pipeline**: `src/huskycat/core/adapters/pipeline.py:1-280`
- **MCP**: `src/huskycat/core/adapters/mcp.py:1-320`

### MCP Server
- **Server implementation**: `src/huskycat/mcp_server.py:1-150`
- **Protocol handling**: `mcp_server.py:85-150`

### Integration
- **CLI entry**: `src/huskycat/__main__.py:218-256`
- **Hook templates**: `src/huskycat/templates/hooks/*.template`
- **CI configuration**: `.gitlab-ci.yml:44-120`

---

## Related Documentation

- [Execution Models](execution-models.md) - Binary, Container, UV execution details
- [Architecture Overview](../architecture/simplified-architecture.md) - High-level system design
- [CLI Reference](../cli-reference.md) - Command-line interface usage
- [MCP Server](../features/mcp-server.md) - MCP integration guide

---

**Last Updated**: 2025-12-12 (Sprint 11 Documentation Cleanup)
**Verification Status**: ✅ Code-verified against `feature/sprint-10-nonblocking-hooks` branch
**Implementation Status**:
- ✅ Sprint 0: 5 product modes with 5 adapters
- ✅ Sprint 10-11: Non-blocking git hooks adapter added (6 total adapters)
**Reviewed Files**: 11+ adapter files, mode detector, factory pattern, MCP server, non-blocking hooks
