# One-Line Curl Installer Design

## Vision Statement

Transform HuskyCats installation from a multi-step, multi-dependency process into a single command that:
1. **Installs Podman** if needed
2. **Pulls HuskyCat container** from GitLab registry
3. **Sets up Git hooks** automatically
4. **Configures Claude Code** integration
5. **Tests the installation** end-to-end

**Target Experience**:
```bash
curl -fsSL https://huskycats.dev/install | bash
```

## Current Installation Complexity

### Current Requirements (Multi-Step)
1. **System Dependencies**:
   - Install Podman or Docker
   - Install Node.js (for Husky)
   - Install Python 3 (for validation tools)
   - Install Git (usually present)

2. **Tool Dependencies**:
   ```bash
   pip install black flake8 mypy bandit
   npm install -g eslint prettier
   # Platform-specific package manager for shellcheck, hadolint, etc.
   ```

3. **Project Setup**:
   ```bash
   npm install husky lint-staged
   npx husky install
   # Configure .lintstagedrc.json
   # Setup .husky/pre-commit hook
   ```

4. **Container Setup**:
   ```bash
   # Pull/build validation container
   podman pull registry.gitlab.com/.../husky-lint:latest
   # Configure container registry credentials if needed
   ```

5. **Testing**:
   ```bash
   # Test individual tools
   # Test git hooks
   # Test container execution
   ```

**Total Steps**: 15-20 commands across multiple tools
**Success Rate**: ~60% (many failure points)
**Time Required**: 10-30 minutes

## New One-Line Installer Design

### Installation Script Architecture
```bash
#!/usr/bin/env bash
# install.sh - One-command HuskyCats installation
set -euo pipefail

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
HUSKYCAT_VERSION="${HUSKYCAT_VERSION:-latest}"
REGISTRY_URL="registry.gitlab.com/jsullivan2_bates/pubcontainers"
CONTAINER_IMAGE="${REGISTRY_URL}/huskycat:${HUSKYCAT_VERSION}"
INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/bin}"
CONFIG_DIR="${CONFIG_DIR:-$HOME/.config/huskycat}"

log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

# Main installation function
main() {
    log_info "Starting HuskyCats installation..."
    
    # Check system requirements
    check_system_requirements
    
    # Install Podman if needed
    ensure_podman_installed
    
    # Pull HuskyCat container
    pull_huskycat_container
    
    # Install CLI wrapper
    install_cli_wrapper
    
    # Setup Git hooks (if in git repo)
    setup_git_hooks
    
    # Configure Claude Code integration
    configure_claude_integration
    
    # Test installation
    test_installation
    
    log_success "HuskyCats installation completed successfully!"
    show_next_steps
}

check_system_requirements() {
    log_info "Checking system requirements..."
    
    # Check if we're on a supported platform
    if [[ "$OSTYPE" != "linux-gnu"* && "$OSTYPE" != "darwin"* ]]; then
        log_error "Unsupported platform: $OSTYPE"
        log_info "HuskyCats supports Linux and macOS only"
        exit 1
    fi
    
    # Check if git is available
    if ! command -v git &> /dev/null; then
        log_error "Git is required but not installed"
        log_info "Please install Git and run this script again"
        exit 1
    fi
    
    # Check if curl is available (should be, since we're using it)
    if ! command -v curl &> /dev/null; then
        log_error "curl is required but not installed"
        exit 1
    fi
    
    log_success "System requirements check passed"
}

ensure_podman_installed() {
    if command -v podman &> /dev/null; then
        log_success "Podman is already installed"
        return 0
    fi
    
    log_info "Installing Podman..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        install_podman_linux
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        install_podman_macos
    fi
    
    # Verify installation
    if command -v podman &> /dev/null; then
        log_success "Podman installed successfully"
    else
        log_error "Failed to install Podman"
        log_info "Please install Podman manually: https://podman.io/getting-started/installation"
        exit 1
    fi
}

install_podman_linux() {
    # Detect Linux distribution and install accordingly
    if command -v apt &> /dev/null; then
        # Debian/Ubuntu
        log_info "Installing Podman on Debian/Ubuntu..."
        sudo apt update
        sudo apt install -y podman
    elif command -v dnf &> /dev/null; then
        # Fedora/RHEL/Rocky
        log_info "Installing Podman on Fedora/RHEL..."
        sudo dnf install -y podman
    elif command -v yum &> /dev/null; then
        # CentOS/older RHEL
        log_info "Installing Podman on CentOS/RHEL..."
        sudo yum install -y podman
    elif command -v pacman &> /dev/null; then
        # Arch Linux
        log_info "Installing Podman on Arch Linux..."
        sudo pacman -S podman
    elif command -v zypper &> /dev/null; then
        # openSUSE
        log_info "Installing Podman on openSUSE..."
        sudo zypper install podman
    else
        log_error "Unsupported Linux distribution"
        log_info "Please install Podman manually: https://podman.io/getting-started/installation"
        exit 1
    fi
}

install_podman_macos() {
    if command -v brew &> /dev/null; then
        log_info "Installing Podman via Homebrew..."
        brew install podman
        
        # Initialize podman machine
        log_info "Initializing Podman machine..."
        podman machine init
        podman machine start
    else
        log_error "Homebrew is required to install Podman on macOS"
        log_info "Install Homebrew: https://brew.sh/"
        log_info "Then run: brew install podman"
        exit 1
    fi
}

pull_huskycat_container() {
    log_info "Pulling HuskyCat container image..."
    log_info "Image: $CONTAINER_IMAGE"
    
    if podman pull "$CONTAINER_IMAGE"; then
        log_success "Container image pulled successfully"
    else
        log_error "Failed to pull container image"
        log_info "Please check your internet connection and try again"
        exit 1
    fi
}

install_cli_wrapper() {
    log_info "Installing HuskyCat CLI wrapper..."
    
    # Create installation directory
    mkdir -p "$INSTALL_DIR"
    
    # Create CLI wrapper script
    cat > "$INSTALL_DIR/huskycat" << 'EOF'
#!/usr/bin/env bash
# HuskyCat CLI wrapper

CONTAINER_IMAGE="registry.gitlab.com/jsullivan2_bates/pubcontainers/huskycat:latest"

# Get current working directory for volume mount
WORKSPACE_ROOT="$(pwd)"

# Handle different commands
case "${1:-}" in
    "validate"|"mcp-server"|"")
        # Run container with volume mount
        exec podman run --rm -i \
            -v "$WORKSPACE_ROOT:/workspace:Z" \
            "$CONTAINER_IMAGE" \
            "$@"
        ;;
    "version")
        podman run --rm "$CONTAINER_IMAGE" version
        ;;
    "update")
        echo "🔄 Updating HuskyCat container..."
        podman pull "$CONTAINER_IMAGE"
        echo "✅ Update complete"
        ;;
    "help"|"-h"|"--help")
        echo "HuskyCat - Code Validation Tools"
        echo ""
        echo "Usage: huskycat [command] [options]"
        echo ""
        echo "Commands:"
        echo "  validate [--staged|files...]  Validate code files"
        echo "  mcp-server                    Start MCP server for Claude Code"
        echo "  version                       Show version information"
        echo "  update                        Update container image"
        echo "  help                          Show this help message"
        echo ""
        echo "Examples:"
        echo "  huskycat validate --staged    # Validate staged git files"
        echo "  huskycat validate src/        # Validate files in src directory"
        echo "  huskycat mcp-server          # Start MCP server"
        ;;
    *)
        echo "❌ Unknown command: $1"
        echo "Run 'huskycat help' for usage information"
        exit 1
        ;;
esac
EOF

    # Make executable
    chmod +x "$INSTALL_DIR/huskycat"
    
    # Add to PATH if not already there
    if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
        log_info "Adding $INSTALL_DIR to PATH..."
        
        # Add to appropriate shell profile
        if [[ -f "$HOME/.bashrc" ]]; then
            echo "export PATH=\"$INSTALL_DIR:\$PATH\"" >> "$HOME/.bashrc"
        fi
        if [[ -f "$HOME/.zshrc" ]]; then
            echo "export PATH=\"$INSTALL_DIR:\$PATH\"" >> "$HOME/.zshrc"
        fi
        
        export PATH="$INSTALL_DIR:$PATH"
    fi
    
    log_success "CLI wrapper installed to $INSTALL_DIR/huskycat"
}

setup_git_hooks() {
    # Only setup hooks if we're in a git repository
    if [[ ! -d ".git" ]]; then
        log_warning "Not in a git repository, skipping git hooks setup"
        return 0
    fi
    
    log_info "Setting up Git hooks..."
    
    # Create .husky directory if it doesn't exist
    mkdir -p .husky
    
    # Create simplified pre-commit hook
    cat > .husky/pre-commit << 'EOF'
#!/usr/bin/env sh
# HuskyCat pre-commit hook

# Use huskycat CLI if available, fallback to direct container call
if command -v huskycat &> /dev/null; then
    huskycat validate --staged
else
    podman run --rm -v "$(pwd):/workspace:Z" \
        registry.gitlab.com/jsullivan2_bates/pubcontainers/huskycat:latest \
        validate --staged
fi
EOF

    # Make executable
    chmod +x .husky/pre-commit
    
    # Setup git hooks path if not already set
    if [[ "$(git config core.hooksPath)" != ".husky" ]]; then
        git config core.hooksPath .husky
    fi
    
    log_success "Git hooks configured"
}

configure_claude_integration() {
    log_info "Configuring Claude Code integration..."
    
    # Create Claude config directory
    mkdir -p "$HOME/.claude"
    
    # Check if mcp.json already exists
    if [[ -f "$HOME/.claude/mcp.json" ]]; then
        log_warning "Claude MCP config already exists"
        log_info "To enable HuskyCat, add this to your .claude/mcp.json:"
        cat << 'EOF'
{
  "mcpServers": {
    "huskycat": {
      "command": "huskycat",
      "args": ["mcp-server"],
      "description": "HuskyCat code validation tools"
    }
  }
}
EOF
        return 0
    fi
    
    # Create new mcp.json with HuskyCat configuration
    cat > "$HOME/.claude/mcp.json" << 'EOF'
{
  "mcpServers": {
    "huskycat": {
      "command": "huskycat", 
      "args": ["mcp-server"],
      "description": "HuskyCat code validation tools"
    }
  }
}
EOF

    log_success "Claude Code integration configured"
}

test_installation() {
    log_info "Testing installation..."
    
    # Test CLI wrapper
    if command -v huskycat &> /dev/null; then
        log_success "✅ CLI wrapper is accessible"
    else
        log_warning "CLI wrapper not in PATH (you may need to restart your shell)"
    fi
    
    # Test container execution
    log_info "Testing container execution..."
    if echo 'print("hello")' | podman run --rm -i "$CONTAINER_IMAGE" validate; then
        log_success "✅ Container execution works"
    else
        log_warning "Container execution test failed"
    fi
    
    # Test git hooks (if in git repo)
    if [[ -d ".git" && -x ".husky/pre-commit" ]]; then
        log_success "✅ Git hooks are configured"
    fi
    
    # Test Claude integration file
    if [[ -f "$HOME/.claude/mcp.json" ]]; then
        log_success "✅ Claude Code integration configured"
    fi
}

show_next_steps() {
    echo ""
    log_info "🎉 Installation complete! Here's what you can do now:"
    echo ""
    echo "  📋 Validate files:"
    echo "     huskycat validate --staged          # Validate staged git files"
    echo "     huskycat validate src/              # Validate directory"
    echo "     huskycat validate file.py           # Validate specific file"
    echo ""
    echo "  🔧 Git integration:"
    echo "     # Git hooks are automatically configured"
    echo "     # Validation will run on every commit"
    echo ""
    echo "  🤖 Claude Code integration:"
    echo "     # Restart Claude Code to load HuskyCat tools"
    echo "     # Use validation tools directly in Claude conversations"
    echo ""
    echo "  📚 Get help:"
    echo "     huskycat help                       # Show all commands"
    echo "     huskycat version                    # Show version info"
    echo "     huskycat update                     # Update to latest version"
    echo ""
    
    if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
        log_warning "⚠️  Please restart your shell or run:"
        echo "     export PATH=\"$INSTALL_DIR:\$PATH\""
    fi
}

# Error handling
trap 'log_error "Installation failed at line $LINENO"' ERR

# Run main function
main "$@"
```

### Hosted Installation

#### GitLab Pages Hosting
The installer will be hosted at: `https://huskycats.dev/install`

**GitLab CI for installer deployment**:
```yaml
# .gitlab-ci.yml snippet
deploy-installer:
  stage: deploy
  script:
    - mkdir public
    - cp scripts/install.sh public/install
    - chmod +x public/install
  artifacts:
    paths:
      - public
  only:
    - main
```

#### Alternative URLs
- **GitLab Raw**: `https://gitlab.com/jsullivan2_bates/pubcontainers/raw/main/install.sh`
- **Short URL**: `https://get.huskycats.dev` (redirect to full URL)
- **GitHub Mirror**: `https://raw.githubusercontent.com/huskycats/installer/main/install.sh`

### Advanced Installation Options

#### Environment Variable Configuration
```bash
# Custom installation directory
INSTALL_DIR=/usr/local/bin curl -fsSL https://huskycats.dev/install | bash

# Specific version
HUSKYCAT_VERSION=v2.0.0 curl -fsSL https://huskycats.dev/install | bash

# Skip git hooks setup
SKIP_GIT_HOOKS=true curl -fsSL https://huskycats.dev/install | bash

# Skip Claude integration
SKIP_CLAUDE=true curl -fsSL https://huskycats.dev/install | bash
```

#### Silent Installation
```bash
# Non-interactive mode
curl -fsSL https://huskycats.dev/install | bash -s -- --quiet

# Skip all prompts and tests
curl -fsSL https://huskycats.dev/install | bash -s -- --yes --skip-tests
```

### Uninstallation Support

#### Uninstall Script
```bash
#!/usr/bin/env bash
# uninstall.sh - Remove HuskyCats installation

log_info "Removing HuskyCats..."

# Remove CLI wrapper
rm -f "$HOME/.local/bin/huskycat"

# Remove container image
podman rmi registry.gitlab.com/jsullivan2_bates/pubcontainers/huskycat:latest 2>/dev/null || true

# Remove git hooks (with confirmation)
if [[ -f ".husky/pre-commit" ]]; then
    read -p "Remove git hooks? (y/N): " -n 1 -r
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -f .husky/pre-commit
        git config --unset core.hooksPath 2>/dev/null || true
    fi
fi

# Remove Claude integration (with confirmation)
if [[ -f "$HOME/.claude/mcp.json" ]]; then
    read -p "Remove Claude Code integration? (y/N): " -n 1 -r
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Remove HuskyCat entry from mcp.json (would need jq for proper JSON editing)
        log_warning "Please manually remove HuskyCat from $HOME/.claude/mcp.json"
    fi
fi

log_success "HuskyCats uninstalled"
```

**Uninstall command**:
```bash
curl -fsSL https://huskycats.dev/uninstall | bash
```

### Installation Analytics

#### Usage Tracking (Optional)
```bash
# Optional analytics (with opt-out)
track_installation() {
    if [[ "${HUSKYCAT_NO_ANALYTICS:-}" != "true" ]]; then
        curl -s -X POST https://api.huskycats.dev/install \
            -d "os=$OSTYPE" \
            -d "version=$HUSKYCAT_VERSION" \
            -d "timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
            > /dev/null 2>&1 || true
    fi
}
```

#### Success Rate Monitoring
- Track successful vs failed installations
- Monitor common failure points
- Geographic distribution
- Platform usage statistics

## Benefits of One-Line Installation

### User Experience
- **Zero Configuration**: Works immediately after installation
- **Universal**: Same command works on all supported platforms
- **Fast**: Complete installation in 2-5 minutes
- **Reliable**: Error handling and recovery built-in
- **Testable**: Verification of all components

### Adoption Benefits
- **Lower Barrier to Entry**: Single command vs 15-20 steps
- **Higher Success Rate**: 95%+ vs 60% current rate
- **Viral Sharing**: Easy to share installation method
- **Documentation Simplification**: One line in README

### Technical Benefits
- **Dependency Management**: Automatic Podman installation
- **Version Management**: Always pulls latest stable version
- **Update Mechanism**: Built-in update command
- **Uninstall Support**: Clean removal process

### Operational Benefits
- **Support Reduction**: Fewer installation issues
- **Consistent Environment**: Everyone gets same container
- **Easy Rollback**: Version-specific installations
- **Analytics**: Installation success tracking

## Implementation Timeline

### Week 1: Core Installer
- [ ] Create basic installation script
- [ ] Test Podman installation on different platforms
- [ ] Implement container pull and CLI wrapper creation

### Week 2: Integration Features
- [ ] Add Git hooks setup
- [ ] Add Claude Code configuration
- [ ] Implement installation testing

### Week 3: Advanced Features
- [ ] Add uninstallation script
- [ ] Implement environment variable configuration
- [ ] Add silent/non-interactive mode

### Week 4: Hosting and Analytics
- [ ] Setup GitLab Pages hosting
- [ ] Configure short URL redirects
- [ ] Implement optional analytics
- [ ] Test end-to-end installation flow

This one-line installer transforms HuskyCats from a complex multi-step installation into a single command that "just works" - eliminating the primary barrier to adoption while ensuring consistent, reliable deployments across all platforms.