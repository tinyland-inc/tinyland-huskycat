#!/bin/bash
# HuskyCat Clean-Slate Script
# Completely removes all HuskyCat files and configurations

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Log functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Confirmation prompt
confirm_removal() {
    echo -e "${YELLOW}⚠️  WARNING: This will remove ALL HuskyCat files and configurations${NC}"
    echo "The following will be removed:"
    echo "  • ~/.huskycat (configuration directory)"
    echo "  • ~/.local/bin/huskycat (binary)"
    echo "  • /usr/local/bin/huskycat (system binary)"
    echo "  • ~/.config/huskycat.yaml (config file)"
    echo "  • .git/hooks (git hooks in current repo)"
    echo "  • ~/.claude/mcp-servers/huskycat.json (MCP config)"
    echo "  • All HuskyCat containers and images"
    echo ""
    read -p "Are you sure you want to continue? (yes/no): " -r
    echo
    if [[ ! $REPLY == "yes" ]]; then
        log_info "Aborted"
        exit 0
    fi
}

# Remove user files
remove_user_files() {
    log_info "Removing user files..."
    
    # Configuration directory
    if [ -d "$HOME/.huskycat" ]; then
        rm -rf "$HOME/.huskycat"
        log_success "Removed ~/.huskycat"
    fi
    
    # User binary
    if [ -f "$HOME/.local/bin/huskycat" ]; then
        rm -f "$HOME/.local/bin/huskycat"
        log_success "Removed ~/.local/bin/huskycat"
    fi
    
    # Config file
    if [ -f "$HOME/.config/huskycat.yaml" ]; then
        rm -f "$HOME/.config/huskycat.yaml"
        log_success "Removed ~/.config/huskycat.yaml"
    fi
    
    # MCP configuration
    if [ -f "$HOME/.claude/mcp-servers/huskycat.json" ]; then
        rm -f "$HOME/.claude/mcp-servers/huskycat.json"
        log_success "Removed Claude MCP configuration"
    fi
}

# Remove system files
remove_system_files() {
    log_info "Removing system files..."
    
    # System binary
    if [ -f "/usr/local/bin/huskycat" ]; then
        if [ -w "/usr/local/bin" ]; then
            rm -f "/usr/local/bin/huskycat"
            log_success "Removed /usr/local/bin/huskycat"
        else
            log_warn "Need sudo to remove /usr/local/bin/huskycat"
            sudo rm -f "/usr/local/bin/huskycat"
            log_success "Removed /usr/local/bin/huskycat (with sudo)"
        fi
    fi
    
    # System config
    if [ -f "/etc/huskycat/config.yaml" ]; then
        if [ -w "/etc/huskycat" ]; then
            rm -rf "/etc/huskycat"
            log_success "Removed /etc/huskycat"
        else
            log_warn "Need sudo to remove /etc/huskycat"
            sudo rm -rf "/etc/huskycat"
            log_success "Removed /etc/huskycat (with sudo)"
        fi
    fi
}

# Remove git hooks from current repository
remove_git_hooks() {
    if [ -d ".git" ]; then
        log_info "Removing git hooks from current repository..."
        
        # Remove HuskyCat hooks
        for hook in pre-commit commit-msg pre-push post-merge; do
            if [ -f ".git/hooks/$hook" ]; then
                if grep -q "huskycat" ".git/hooks/$hook" 2>/dev/null; then
                    rm -f ".git/hooks/$hook"
                    log_success "Removed .git/hooks/$hook"
                fi
            fi
        done
        
        # Remove Husky hooks that use HuskyCat
        if [ -d ".husky" ]; then
            for hook in .husky/*; do
                if [ -f "$hook" ] && grep -q "huskycat" "$hook" 2>/dev/null; then
                    log_warn "Found HuskyCat reference in $hook"
                fi
            done
        fi
    fi
}

# Remove containers and images
remove_containers() {
    log_info "Removing HuskyCat containers and images..."
    
    # Detect container runtime
    if command -v podman &> /dev/null; then
        RUNTIME="podman"
    elif command -v docker &> /dev/null; then
        RUNTIME="docker"
    else
        log_info "No container runtime found"
        return
    fi
    
    # Stop and remove containers
    CONTAINERS=$($RUNTIME ps -a --filter "ancestor=huskycat" --format "{{.ID}}" 2>/dev/null || true)
    if [ -n "$CONTAINERS" ]; then
        echo "$CONTAINERS" | xargs $RUNTIME stop 2>/dev/null || true
        echo "$CONTAINERS" | xargs $RUNTIME rm 2>/dev/null || true
        log_success "Removed HuskyCat containers"
    fi
    
    # Remove images
    IMAGES=$($RUNTIME images --filter "reference=huskycat*" --format "{{.ID}}" 2>/dev/null || true)
    if [ -n "$IMAGES" ]; then
        echo "$IMAGES" | xargs $RUNTIME rmi -f 2>/dev/null || true
        log_success "Removed HuskyCat images"
    fi
    
    # Also check for registry images
    REGISTRY_IMAGES=$($RUNTIME images --filter "reference=*huskycat*" --format "{{.Repository}}:{{.Tag}}" 2>/dev/null || true)
    if [ -n "$REGISTRY_IMAGES" ]; then
        echo "$REGISTRY_IMAGES" | xargs $RUNTIME rmi -f 2>/dev/null || true
        log_success "Removed registry HuskyCat images"
    fi
}

# Remove build artifacts
remove_build_artifacts() {
    log_info "Removing build artifacts..."
    
    # Python artifacts
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
    
    # Build directories
    rm -rf build/ dist/ 2>/dev/null || true
    rm -rf .pytest_cache/ .mypy_cache/ .ruff_cache/ 2>/dev/null || true
    rm -f *.spec 2>/dev/null || true
    
    log_success "Removed build artifacts"
}

# Remove package manager installations
remove_package_installations() {
    log_info "Checking for package manager installations..."
    
    # Homebrew (macOS)
    if command -v brew &> /dev/null; then
        if brew list huskycat &> /dev/null; then
            log_info "Removing Homebrew installation..."
            brew uninstall huskycat
            log_success "Removed Homebrew package"
        fi
    fi
    
    # APT (Debian/Ubuntu)
    if command -v apt &> /dev/null; then
        if dpkg -l | grep -q huskycat; then
            log_info "Removing APT package..."
            sudo apt remove -y huskycat
            log_success "Removed APT package"
        fi
    fi
    
    # YUM/DNF (RHEL/Fedora/Rocky)
    if command -v dnf &> /dev/null; then
        if dnf list installed huskycat &> /dev/null; then
            log_info "Removing DNF package..."
            sudo dnf remove -y huskycat
            log_success "Removed DNF package"
        fi
    elif command -v yum &> /dev/null; then
        if yum list installed huskycat &> /dev/null; then
            log_info "Removing YUM package..."
            sudo yum remove -y huskycat
            log_success "Removed YUM package"
        fi
    fi
}

# Main cleanup function
main() {
    echo "======================================"
    echo "     HuskyCat Clean-Slate Removal"
    echo "======================================"
    echo
    
    # Get confirmation
    confirm_removal
    
    # Start removal process
    log_info "Starting complete removal..."
    
    # Remove all components
    remove_user_files
    remove_system_files
    remove_git_hooks
    remove_containers
    remove_build_artifacts
    remove_package_installations
    
    echo
    echo "======================================"
    log_success "HuskyCat completely removed!"
    echo "======================================"
    echo
    echo "You can now perform a fresh installation with:"
    echo "  make install-local    # For local installation"
    echo "  curl -fsSL https://huskycat.io/install | bash    # For online installation"
}

# Run main function
main "$@"