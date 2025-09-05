"""
Git hooks setup command.
"""

import subprocess
from pathlib import Path

from ..core.base import BaseCommand, CommandResult, CommandStatus


class SetupHooksCommand(BaseCommand):
    """Command to setup git hooks for automatic validation."""

    @property
    def name(self) -> str:
        return "setup-hooks"

    @property
    def description(self) -> str:
        return "Setup git hooks for automatic validation"

    def execute(self, force: bool = False) -> CommandResult:
        """
        Setup git hooks.

        Args:
            force: Force overwrite existing hooks

        Returns:
            CommandResult with setup status
        """
        # Find git directory
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                capture_output=True,
                text=True,
                check=True,
            )
            git_dir = Path(result.stdout.strip())
        except subprocess.CalledProcessError:
            return CommandResult(
                status=CommandStatus.FAILED,
                message="Not in a git repository",
                errors=["Current directory is not a git repository"],
            )

        hooks_dir = git_dir / "hooks"
        hooks_dir.mkdir(exist_ok=True)

        # Get absolute path to main module
        Path(__file__).parent.parent / "__main__.py"

        # Create pre-commit hook with interactive auto-fix support
        pre_commit = hooks_dir / "pre-commit"
        pre_commit_content = """#!/bin/bash
# HuskyCat pre-commit hook - Binary first, container fallback with auto-fix support

# Function to run validation with binary-first approach
run_validation() {
    local args="$1"
    
    if [ -f "./dist/huskycat" ]; then
        ./dist/huskycat validate --staged $args
    elif command -v huskycat >/dev/null 2>&1; then
        huskycat validate --staged $args
    elif command -v uv >/dev/null 2>&1 && [ -f "pyproject.toml" ]; then
        uv run python3 -m src.huskycat validate --staged $args
    elif command -v podman >/dev/null 2>&1; then
        podman run --rm -v "$(pwd)":/workspace -it huskycat:local validate --staged $args
    else
        echo "❌ HuskyCat not found. Install: curl -sSL https://huskycat.pages.io/install.sh | bash"
        exit 1
    fi
}

# Run validation with interactive auto-fix
run_validation "--interactive"
exit_code=$?

# If validation failed and user wants auto-fix, re-stage the files
if [ $exit_code -ne 0 ]; then
    echo ""
    echo "💡 Note: Fixed files need to be re-staged before committing."
    echo "   Run: git add <fixed-files> && git commit"
fi

exit $exit_code
"""

        if pre_commit.exists() and not force:
            return CommandResult(
                status=CommandStatus.WARNING,
                message="Pre-commit hook already exists",
                warnings=["Use --force to overwrite existing hooks"],
            )

        pre_commit.write_text(pre_commit_content)
        pre_commit.chmod(0o755)

        # Create pre-push hook
        pre_push = hooks_dir / "pre-push"
        pre_push_content = """#!/bin/bash
# HuskyCat pre-push hook - Binary first, uv fallback, container last

if [ -f "./dist/huskycat" ]; then
    ./dist/huskycat validate --all && glab ci lint .gitlab-ci.yml
elif command -v huskycat >/dev/null 2>&1; then
    huskycat validate --all && glab ci lint .gitlab-ci.yml
elif command -v uv >/dev/null 2>&1 && [ -f "pyproject.toml" ]; then
    uv run python3 -m src.huskycat validate --all && glab ci lint .gitlab-ci.yml
elif command -v podman >/dev/null 2>&1; then
    podman run --rm -v "$(pwd)":/workspace huskycat:local validate --all && glab ci lint .gitlab-ci.yml
else
    echo "❌ HuskyCat not found. Install: curl -sSL https://huskycat.pages.io/install.sh | bash"
    exit 1
fi
"""

        pre_push.write_text(pre_push_content)
        pre_push.chmod(0o755)

        # Create pre-index hook for auto-fix on git add
        pre_index = hooks_dir / "pre-index"
        pre_index_content = """#!/bin/bash
# HuskyCat pre-index hook - Auto-fix validation on git add
# This hook runs when files are added to the index (git add)

# Get the files being added to the index (both new and modified)
files_to_add=$(git diff --cached --name-only)

if [ -z "$files_to_add" ]; then
    exit 0
fi

echo "🔍 HuskyCat: Validating files being added to index..."

# Function to run validation with binary-first approach
run_validation() {
    local files="$1"
    local args="$2"
    
    if [ -f "./dist/huskycat" ]; then
        ./dist/huskycat validate $files $args
    elif command -v huskycat >/dev/null 2>&1; then
        huskycat validate $files $args
    elif command -v uv >/dev/null 2>&1 && [ -f "pyproject.toml" ]; then
        uv run python3 -m src.huskycat validate $files $args
    elif command -v podman >/dev/null 2>&1; then
        podman run --rm -v "$(pwd)":/workspace -it huskycat:local validate $files $args
    else
        echo "❌ HuskyCat not found. Install: curl -sSL https://huskycat.pages.io/install.sh | bash"
        exit 1
    fi
}

# Validate each file and prompt for auto-fix if needed
validation_failed=false

for file in $files_to_add; do
    if [ -f "$file" ]; then
        echo "🔍 Validating $file..."
        run_validation "$file" ""
        exit_code=$?
        
        if [ $exit_code -ne 0 ]; then
            echo ""
            echo "💡 Auto-fix available for $file"
            echo -n "🤖 Apply auto-fix? [y/N]: "
            read -r response
            
            if [[ "$response" =~ ^[Yy]$ ]]; then
                echo "🔧 Applying auto-fix to $file..."
                run_validation "$file" "--fix"
                
                if [ $? -eq 0 ]; then
                    echo "✅ Auto-fix applied to $file"
                    echo "📝 Re-staging $file with fixes..."
                    git add "$file"
                else
                    echo "❌ Auto-fix failed for $file"
                    validation_failed=true
                fi
            else
                echo "❌ Validation failed for $file - fix manually or use auto-fix"
                validation_failed=true
            fi
        fi
    fi
done

if [ "$validation_failed" = true ]; then
    exit 1
fi

echo "✅ All files validated successfully"
exit 0
"""

        pre_index.write_text(pre_index_content)
        pre_index.chmod(0o755)

        # Create commit-msg hook for conventional commits
        commit_msg = hooks_dir / "commit-msg"
        commit_msg_content = """#!/bin/bash
# HuskyCat commit-msg hook
# Validates commit message format (conventional commits)

commit_regex='^(feat|fix|docs|style|refactor|test|chore|perf|ci|build|revert)(\\(.+\\))?!?: .+'

# Read the commit message
commit_message=$(cat "$1")

# Skip validation for merge commits and revert commits
if [[ "$commit_message" =~ ^Merge.* ]] || [[ "$commit_message" =~ ^Revert.* ]]; then
    exit 0
fi

# Get just the first line for validation (conventional commits validate the first line)
first_line=$(echo "$commit_message" | head -n1)

# Check if first line follows conventional commit format
if [[ ! "$first_line" =~ $commit_regex ]]; then
    echo "❌ Commit message does not follow conventional commit format!"
    echo ""
    echo "Format: <type>[optional scope]: <description>"
    echo ""
    echo "Types: feat, fix, docs, style, refactor, test, chore, perf, ci, build, revert"
    echo ""
    echo "Examples:"
    echo "  feat: add new user authentication"
    echo "  fix(api): resolve login endpoint error"
    echo "  docs: update installation guide"
    echo ""
    echo "Your first line: $first_line"
    exit 1
fi

exit 0
"""

        commit_msg.write_text(commit_msg_content)
        commit_msg.chmod(0o755)

        # Create git wrapper script for enhanced git add with validation
        git_wrapper_dir = Path.home() / ".huskycat" / "bin"
        git_wrapper_dir.mkdir(parents=True, exist_ok=True)

        git_add_wrapper = git_wrapper_dir / "git-add-with-validation"
        git_add_wrapper_content = """#!/bin/bash
# HuskyCat git add wrapper with auto-fix validation
# Usage: git-add-with-validation [files...]

# Function to run validation with binary-first approach
run_validation() {
    local files="$1"
    local args="$2"
    
    if [ -f "./dist/huskycat" ]; then
        ./dist/huskycat validate $files $args
    elif command -v huskycat >/dev/null 2>&1; then
        huskycat validate $files $args
    elif command -v uv >/dev/null 2>&1 && [ -f "pyproject.toml" ]; then
        uv run python3 -m src.huskycat validate $files $args
    elif command -v podman >/dev/null 2>&1; then
        podman run --rm -v "$(pwd)":/workspace -it huskycat:local validate $files $args
    else
        echo "❌ HuskyCat not found. Install: curl -sSL https://huskycat.pages.io/install.sh | bash"
        exit 1
    fi
}

# Process each file before adding
for file in "$@"; do
    if [ -f "$file" ]; then
        echo "🔍 Validating $file before adding to index..."
        run_validation "$file" ""
        exit_code=$?
        
        if [ $exit_code -ne 0 ]; then
            echo ""
            echo "💡 Auto-fix available for $file"
            echo -n "🤖 Apply auto-fix before adding? [y/N]: "
            read -r response
            
            if [[ "$response" =~ ^[Yy]$ ]]; then
                echo "🔧 Applying auto-fix to $file..."
                run_validation "$file" "--fix"
                
                if [ $? -eq 0 ]; then
                    echo "✅ Auto-fix applied to $file"
                else
                    echo "❌ Auto-fix failed for $file"
                    exit 1
                fi
            else
                echo "❌ Validation failed for $file - fix manually or use auto-fix"
                exit 1
            fi
        fi
    fi
done

# Now add the files normally
exec git add "$@"
"""

        git_add_wrapper.write_text(git_add_wrapper_content)
        git_add_wrapper.chmod(0o755)

        # Create git alias setup script
        alias_setup_script = git_wrapper_dir / "setup-git-aliases.sh"
        alias_setup_content = f"""#!/bin/bash
# HuskyCat git aliases setup script
# Run this script to setup git aliases for auto-fix validation

echo "Setting up git aliases for HuskyCat auto-fix validation..."

# Create git alias for enhanced git add
git config --global alias.add-fix '!{git_add_wrapper} "$@" && git add "$@"'

# Alternative: create a function-based alias that works better
git config --global alias.addf '!f() {{ 
    for file in "$@"; do
        if [ -f "$file" ]; then
            echo "🔍 Validating $file before adding...";
            if [ -f "./dist/huskycat" ]; then
                ./dist/huskycat validate "$file" || {{
                    echo "💡 Auto-fix available for $file";
                    echo -n "🤖 Apply auto-fix? [y/N]: ";
                    read -r response;
                    if [[ "$response" =~ ^[Yy]$ ]]; then
                        ./dist/huskycat validate "$file" --fix && echo "✅ Fixed $file";
                    else
                        echo "❌ Skipping $file - fix manually"; exit 1;
                    fi;
                }};
            elif command -v huskycat >/dev/null 2>&1; then
                huskycat validate "$file" || {{
                    echo "💡 Auto-fix available for $file";
                    echo -n "🤖 Apply auto-fix? [y/N]: ";
                    read -r response;
                    if [[ "$response" =~ ^[Yy]$ ]]; then
                        huskycat validate "$file" --fix && echo "✅ Fixed $file";
                    else
                        echo "❌ Skipping $file - fix manually"; exit 1;
                    fi;
                }};
            elif command -v uv >/dev/null 2>&1 && [ -f "pyproject.toml" ]; then
                uv run python3 -m src.huskycat validate "$file" || {{
                    echo "💡 Auto-fix available for $file";
                    echo -n "🤖 Apply auto-fix? [y/N]: ";
                    read -r response;
                    if [[ "$response" =~ ^[Yy]$ ]]; then
                        uv run python3 -m src.huskycat validate "$file" --fix && echo "✅ Fixed $file";
                    else
                        echo "❌ Skipping $file - fix manually"; exit 1;
                    fi;
                }};
            fi;
        fi;
    done;
    git add "$@";
}}; f'

echo "✅ Git aliases configured successfully!"
echo ""
echo "Usage:"
echo "  git addf <files>  # Add files with auto-fix validation"
echo ""
echo "Example:"
echo "  git addf src/file1.py src/file2.py"
echo "  git addf ."
echo ""
echo "To remove these aliases later:"
echo "  git config --global --unset alias.add-fix"
echo "  git config --global --unset alias.addf"
"""

        alias_setup_script.write_text(alias_setup_content)
        alias_setup_script.chmod(0o755)

        # Run the alias setup script automatically
        try:
            subprocess.run([str(alias_setup_script)], check=True, capture_output=True)
            alias_setup_success = True
            alias_message = "Git aliases configured automatically"
        except subprocess.CalledProcessError:
            alias_setup_success = False
            alias_message = f"Run {alias_setup_script} manually to setup git aliases"

        return CommandResult(
            status=CommandStatus.SUCCESS,
            message="Git hooks installed successfully",
            data={
                "hooks_dir": str(hooks_dir),
                "hooks_installed": [
                    "pre-commit",
                    "pre-push",
                    "pre-index",
                    "commit-msg",
                ],
                "git_wrapper": str(git_add_wrapper),
                "alias_setup_script": str(alias_setup_script),
                "aliases_configured": alias_setup_success,
                "usage_note": alias_message,
                "instructions": [
                    "Use 'git addf <files>' for auto-fix validation before adding",
                    "Use 'git addf .' to validate and add all files with auto-fix prompts",
                    f"Manual setup: {alias_setup_script}",
                ],
            },
        )
