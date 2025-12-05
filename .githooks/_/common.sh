#!/usr/bin/env bash
# .githooks/_/common.sh - Shared hook utilities for HuskyCat
#
# PARADIGM: Eat your own dogfood - hooks use HuskyCat's validation engine
#
# REQUIREMENT: UV venv must be active for development in this repository.
# Run: uv sync --dev
#
# This file provides shared utilities for all git hooks.
# Source it at the top of each hook script.

set -euo pipefail

# ============================================================================
# COLORS AND OUTPUT
# ============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

log_info()    { echo -e "${GREEN}[OK]${NC} $*"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $*"; }
log_step()    { echo -e "${CYAN}[STEP]${NC} $*"; }
log_header()  { echo -e "\n${BOLD}${BLUE}=== $* ===${NC}"; }

# ============================================================================
# ENVIRONMENT DETECTION
# ============================================================================

# Check if running in CI environment
is_ci() {
    [[ -n "${CI:-}" ]] || \
    [[ -n "${GITLAB_CI:-}" ]] || \
    [[ -n "${GITHUB_ACTIONS:-}" ]] || \
    [[ -n "${JENKINS_URL:-}" ]] || \
    [[ -n "${TRAVIS:-}" ]]
}

# Check if running interactively (TTY available)
is_interactive() {
    [[ -t 0 ]] && [[ -t 1 ]] && ! is_ci
}

# Check if hooks should be skipped entirely
should_skip_hooks() {
    [[ "${SKIP_HOOKS:-0}" == "1" ]] || \
    [[ "${HUSKYCAT_SKIP_HOOKS:-0}" == "1" ]]
}

# Check if auto-approve mode is enabled (non-interactive auto-fix)
is_auto_approve() {
    [[ "${HUSKYCAT_AUTO_APPROVE:-0}" == "1" ]] || \
    [[ "${AUTO_FIX:-0}" == "1" ]]
}

# ============================================================================
# UV VENV VERIFICATION
# ============================================================================

# Verify UV is available and venv is set up
verify_uv_environment() {
    # Check for uv command
    if ! command -v uv &> /dev/null; then
        log_error "UV package manager not found!"
        echo ""
        echo "  UV is required for development in this repository."
        echo "  Install: curl -LsSf https://astral.sh/uv/install.sh | sh"
        echo ""
        return 1
    fi

    # Check for pyproject.toml (indicates we're in the right directory)
    if [[ ! -f "pyproject.toml" ]]; then
        log_error "pyproject.toml not found!"
        echo ""
        echo "  Are you in the repository root?"
        echo ""
        return 1
    fi

    # Check if venv exists (uv creates .venv by default)
    if [[ ! -d ".venv" ]]; then
        log_warn "Virtual environment not found. Creating..."
        uv sync --dev || {
            log_error "Failed to create virtual environment"
            echo ""
            echo "  Run manually: uv sync --dev"
            echo ""
            return 1
        }
        log_info "Virtual environment created successfully"
    fi

    return 0
}

# ============================================================================
# GIT UTILITIES
# ============================================================================

# Get list of staged files, optionally filtered by extension
# Usage: staged_files [extension]
# Example: staged_files py
staged_files() {
    local extension="${1:-}"
    if [[ -n "$extension" ]]; then
        git diff --cached --name-only --diff-filter=ACMR | grep -E "\.${extension}$" || true
    else
        git diff --cached --name-only --diff-filter=ACMR
    fi
}

# Get list of all tracked files by extension
# Usage: tracked_files [extension]
tracked_files() {
    local extension="${1:-}"
    if [[ -n "$extension" ]]; then
        git ls-files | grep -E "\.${extension}$" || true
    else
        git ls-files
    fi
}

# Check if any staged files match a pattern
has_staged_files() {
    local pattern="${1:-}"
    if [[ -n "$pattern" ]]; then
        git diff --cached --name-only --diff-filter=ACMR | grep -qE "$pattern"
    else
        [[ -n "$(git diff --cached --name-only --diff-filter=ACMR)" ]]
    fi
}

# ============================================================================
# INTERACTIVE PROMPTS
# ============================================================================

# Ask user yes/no question with default
# Usage: ask_yes_no "Apply auto-fix?" [default: n]
# Returns: 0 for yes, 1 for no
ask_yes_no() {
    local prompt="$1"
    local default="${2:-n}"

    # In CI or non-interactive, use default or auto-approve
    if ! is_interactive; then
        if is_auto_approve; then
            return 0  # Auto-approve means yes
        fi
        [[ "$default" == "y" ]] && return 0 || return 1
    fi

    local yn_hint
    if [[ "$default" == "y" ]]; then
        yn_hint="[Y/n]"
    else
        yn_hint="[y/N]"
    fi

    echo -ne "${CYAN}$prompt${NC} $yn_hint: "
    read -r response

    case "${response,,}" in
        y|yes) return 0 ;;
        n|no)  return 1 ;;
        "")
            [[ "$default" == "y" ]] && return 0 || return 1
            ;;
        *)
            return 1
            ;;
    esac
}
