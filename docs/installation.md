# Installation Guide

## One-Line Installer (Recommended)

The easiest way to install HuskyCat is with the automated installer:

```bash
curl -fsSL https://tinyland.gitlab.io/ai/huskycat/install.sh | bash
```

This downloads the correct binary for your platform, verifies checksums, and installs to `~/.local/bin`.

### With Claude Code Integration

To automatically register HuskyCat as an MCP server with Claude Code:

```bash
HUSKYCAT_WITH_CLAUDE=1 curl -fsSL https://tinyland.gitlab.io/ai/huskycat/install.sh | bash
```

**Options:**
- `HUSKYCAT_WITH_CLAUDE=1` - Register MCP server with Claude Code
- `HUSKYCAT_SCOPE=user|project|local` - MCP registration scope (default: user)
- `HUSKYCAT_VERSION=2.0.0` - Install specific version (default: latest)

## Manual Binary Download

If you prefer to download manually:

### Linux (amd64)

```bash
curl -L 'https://gitlab.com/tinyland/ai/huskycat/-/jobs/artifacts/main/raw/dist/bin/huskycat-linux-amd64?job=build:binary:linux-amd64' -o huskycat
chmod +x huskycat
./huskycat install
```

### Linux (ARM64)

```bash
curl -L 'https://gitlab.com/tinyland/ai/huskycat/-/jobs/artifacts/main/raw/dist/bin/huskycat-linux-arm64?job=build:binary:linux-arm64' -o huskycat
chmod +x huskycat
./huskycat install
```

### macOS (ARM64 - M1/M2/M3/M4)

```bash
curl -L 'https://gitlab.com/tinyland/ai/huskycat/-/jobs/artifacts/main/raw/dist/bin/huskycat-darwin-arm64?job=build:binary:darwin-arm64' -o huskycat
chmod +x huskycat
./huskycat install
```

> **Note for Intel Mac users**: The Intel (x86_64) binary is not currently built due to GitLab SaaS runner limitations. Intel Mac users can:
> - Use Rosetta 2 to run the ARM64 binary: `arch -x86_64 ./huskycat install`
> - Use container execution: `podman run -v $(pwd):/workspace tinyland/huskycat validate`

## Verify Installation

After installation, verify HuskyCat is working:

```bash
huskycat --version
huskycat --help
huskycat status
```

Expected output:
```
$ huskycat --version
huskycat 2.0.0

$ huskycat status
HuskyCat Status
===============
Installation:  ~/.local/bin/huskycat
Tools:         ~/.huskycat/tools/ (3 tools)
Configuration: .huskycat.yaml
Mode:          CLI
```

## What Happens During Installation

The `huskycat install` command performs these steps:

### 1. Binary Installation
- Copies binary to `~/.local/bin/huskycat`
- Sets executable permissions (755)
- Creates directory if it doesn't exist

### 2. Tool Extraction
Tools are extracted to `~/.huskycat/tools/` on first use:

- **shellcheck** v0.10.0 (~3.4 MB) - Shell script linter
- **hadolint** v2.12.0 (~12 MB) - Dockerfile linter
- **taplo** v0.9.3 (~18 MB) - TOML formatter

Extraction happens automatically the first time you run validation:
```
$ huskycat validate test.sh
Extracting 3 validation tools to ~/.huskycat/tools/...
  • shellcheck (3.4 MB)
  • hadolint (12.0 MB)
  • taplo (18.3 MB)
✓ Tools extracted successfully
```

### 3. Shell Completions
Completions are created in `~/.huskycat/completions/`:

- **Bash**: `huskycat.bash`
- **Zsh**: `_huskycat`
- **Fish**: `huskycat.fish`

To enable completions, add to your shell profile:

**Bash** (`~/.bashrc`):
```bash
source ~/.huskycat/completions/huskycat.bash
```

**Zsh** (`~/.zshrc`):
```bash
fpath=(~/.huskycat/completions $fpath)
autoload -Uz compinit && compinit
```

**Fish** (`~/.config/fish/config.fish`):
```bash
source ~/.huskycat/completions/huskycat.fish
```

### 4. PATH Configuration
If `~/.local/bin` is not in your PATH, add it:

**Bash/Zsh** (`~/.bashrc` or `~/.zshrc`):
```bash
export PATH="$HOME/.local/bin:$PATH"
```

**Fish** (`~/.config/fish/config.fish`):
```bash
set -gx PATH $HOME/.local/bin $PATH
```

Then reload your shell:
```bash
source ~/.bashrc  # or ~/.zshrc, or restart terminal
```

## Git Hooks Setup

After installation, enable git hooks for your repository:

```bash
cd your-repo
huskycat setup-hooks
```

This installs hooks to `.git/hooks/`:
- `pre-commit` - Validates staged files
- `pre-push` - Validates CI configuration
- `commit-msg` - Validates commit message format

### Enable Non-Blocking Mode (Optional)

For faster commits that don't block on validation:

```bash
git config --local huskycat.nonblocking true
```

With non-blocking mode:
```
$ git commit -m "feat: add feature"
⚡ Non-blocking validation mode enabled
🚀 Launching background validation...
   Validation running in background (PID 12345)
[main abc1234] feat: add feature
 1 file changed, 10 insertions(+)
```

Without non-blocking mode (default):
```
$ git commit -m "feat: add feature"
🚀 Running HuskyCat validation...
✓ black: 5 files passed
✓ mypy: 5 files passed
✓ flake8: 5 files passed
[main abc1234] feat: add feature
 1 file changed, 10 insertions(+)
```

## Troubleshooting

### Tools Not Found

**Symptom**: `shellcheck: command not found`

**Solution**:
```bash
# Check if tools are extracted
ls -la ~/.huskycat/tools/

# Force re-extraction
rm -rf ~/.huskycat/tools
huskycat validate --help  # Triggers extraction
```

### Binary Not in PATH

**Symptom**: `huskycat: command not found`

**Solution**:
```bash
# Check if binary exists
ls -l ~/.local/bin/huskycat

# Verify PATH includes ~/.local/bin
echo $PATH | grep .local/bin

# Add to PATH if missing
export PATH="$HOME/.local/bin:$PATH"

# Make permanent by adding to ~/.bashrc or ~/.zshrc
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Permission Denied

**Symptom**: `Permission denied: ./huskycat`

**Solution**:
```bash
# Make binary executable
chmod +x huskycat

# After installation
chmod +x ~/.local/bin/huskycat
```

### macOS: "Cannot be opened because the developer cannot be verified"

**Solution**:
```bash
# Remove quarantine attribute
xattr -d com.apple.quarantine huskycat

# Or allow in System Preferences
# System Preferences → Security & Privacy → Allow anyway
```

### Hooks Not Running

**Symptom**: Commits succeed without validation

**Solution**:
```bash
# Check if hooks are installed
ls -la .git/hooks/pre-commit

# Verify hook is executable
chmod +x .git/hooks/pre-commit

# Check hook content
head -20 .git/hooks/pre-commit

# Reinstall hooks
huskycat setup-hooks --force
```

### Tool Extraction Fails

**Symptom**: `Failed to extract tools: Permission denied`

**Solution**:
```bash
# Check directory permissions
ls -ld ~/.huskycat/

# Create directory with correct permissions
mkdir -p ~/.huskycat/tools
chmod 755 ~/.huskycat ~/.huskycat/tools

# Try extraction again
huskycat validate --help
```

### Version Mismatch Warning

**Symptom**: `Hook version mismatch detected`

**Solution**:
```bash
# Update hooks to match binary version
huskycat setup-hooks --force

# Or disable version check
export HUSKYCAT_CHECK_VERSION=0
```

## Uninstallation

To remove HuskyCat:

```bash
# Remove binary
rm ~/.local/bin/huskycat

# Remove tools and cache
rm -rf ~/.huskycat/

# Remove git hooks (per repository)
cd your-repo
rm .git/hooks/pre-commit
rm .git/hooks/pre-push
rm .git/hooks/commit-msg

# Or restore original hooks
git config --unset core.hooksPath
```

## Upgrading

To upgrade to a newer version:

```bash
# Download new binary
curl -L <new-binary-url> -o huskycat
chmod +x huskycat

# Install (overwrites old version)
./huskycat install

# Update hooks in repositories
cd your-repo
huskycat setup-hooks --force
```

## Alternative Installation Methods

### From Source (Development)

```bash
# Clone repository
git clone https://gitlab.com/tinyland/ai/huskycat.git
cd huskycat

# Install dependencies
uv sync --dev

# Build binary
npm run build:binary

# Install (with optional Claude Code integration)
./dist/huskycat install --with-claude --scope user
```

**Install Command Options:**
- `--with-claude` - Register MCP server with Claude Code
- `--scope user|project|local` - MCP registration scope
- `--verify` - Verify MCP connection after registration
- `--bin-dir /path` - Custom installation directory
- `--no-hooks` - Skip git hooks setup

### Container-Based (No Installation)

```bash
# Build container
podman build -f ContainerFile -t huskycat:local .

# Run validation
podman run --rm -v "$(pwd)":/workspace huskycat:local validate --all

# Run as MCP server
podman run --rm -i huskycat:local mcp-server
```

### UV Development Mode

For HuskyCat development:

```bash
# Clone repository
git clone https://gitlab.com/jsullivan2/huskycats-bates.git
cd huskycats-bates

# Install with UV
uv sync --dev

# Run directly
uv run python -m huskycat validate --all

# Use tracked git hooks
git config --local core.hooksPath .githooks
```

## Platform-Specific Notes

### Linux

- Binary size: ~150-200 MB (with embedded tools)
- Requires: glibc 2.17+ (most distributions)
- Runs on: x86_64 (amd64) and ARM64 architectures

### macOS

- Binary size: ~21 MB (tools extracted separately)
- Requires: macOS 10.13+ (High Sierra)
- Architectures: Intel (x86_64) and Apple Silicon (ARM64)
- May require: Xcode Command Line Tools for some operations

### Windows

**Note**: Windows support is planned but not yet implemented. Current workarounds:

- Use WSL2 with Linux binary
- Use Docker Desktop with container image
- Use Git Bash with Linux compatibility layer

## Next Steps

After installation:

1. **Configure** - Create `.huskycat.yaml` in your repository
2. **Validate** - Run `huskycat validate --all` to test
3. **Setup Hooks** - Enable git hooks with `huskycat setup-hooks`
4. **Customize** - Configure tools, rules, and behavior

See:
- [Configuration Guide](configuration.md)
- [Git Hooks Guide](dogfooding.md)
- [Binary Downloads](binary-downloads.md)
- [Troubleshooting](troubleshooting.md)
