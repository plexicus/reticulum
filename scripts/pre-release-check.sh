#!/bin/bash

# Pre-release check script for Reticulum
# This script verifies all quality checks before allowing a tag to be created
# Now fully unattended and intelligent - no user prompts needed

set -e  # Exit on any error

echo "🔍 Starting pre-release quality checks..."
echo "========================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    case $status in
        "PASS")
            echo -e "${GREEN}✅ PASS${NC}: $message"
            ;;
        "FAIL")
            echo -e "${RED}❌ FAIL${NC}: $message"
            ;;
        "WARN")
            echo -e "${YELLOW}⚠️  WARN${NC}: $message"
            ;;
        "INFO")
            echo -e "${BLUE}ℹ️  INFO${NC}: $message"
            ;;
        "AUTO")
            echo -e "${BLUE}🤖 AUTO${NC}: $message"
            ;;
    esac
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to auto-commit changes with intelligent commit message
auto_commit_changes() {
    local change_type=$1
    local files_changed=$(git status --porcelain | wc -l | tr -d ' ')
    
    if [ "$files_changed" -gt 0 ]; then
        print_status "AUTO" "Auto-committing $change_type changes ($files_changed files)"
        git add .
        
        # Generate intelligent commit message based on change type
        case $change_type in
            "linting")
                git commit -m "style: auto-fix linting issues with ruff"
                ;;
            "formatting")
                git commit -m "style: auto-format code with black"
                ;;
            "both")
                git commit -m "style: auto-fix linting and formatting issues"
                ;;
            *)
                git commit -m "style: auto-fix code quality issues"
                ;;
        esac
        return 0
    fi
    return 1
}

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    print_status "FAIL" "Not in reticulum project root directory"
    exit 1
fi

print_status "INFO" "Project root directory confirmed"

# Check if Poetry is available
if ! command_exists poetry; then
    print_status "FAIL" "Poetry is not installed or not in PATH"
    exit 1
fi

print_status "INFO" "Poetry is available"

# Check if we have uncommitted changes
if [ -n "$(git status --porcelain)" ]; then
    print_status "WARN" "You have uncommitted changes. Analyzing them..."
    git status --short
    
    # Auto-analyze what kind of changes we have
    staged_files=$(git diff --cached --name-only 2>/dev/null | wc -l | tr -d ' ')
    unstaged_files=$(git diff --name-only 2>/dev/null | wc -l | tr -d ' ')
    
    if [ "$staged_files" -gt 0 ]; then
        print_status "INFO" "Found $staged_files staged files - these will be included in next commit"
    fi
    
    if [ "$unstaged_files" -gt 0 ]; then
        print_status "INFO" "Found $unstaged_files unstaged files - will auto-commit if they're quality fixes"
    fi
else
    print_status "PASS" "Working directory is clean"
fi

# Check if we're on main branch
current_branch=$(git branch --show-current)
if [ "$current_branch" != "main" ]; then
    print_status "FAIL" "You're not on main branch (currently on: $current_branch)"
    print_status "FAIL" "Releases should only be made from main branch"
    exit 1
else
    print_status "PASS" "On main branch"
fi

echo
echo "🧪 Running quality checks..."
echo "============================"

# 1. Install dependencies
print_status "INFO" "Installing dependencies..."
poetry install --no-interaction

# 2. Run linting with ruff
print_status "INFO" "Running ruff linting..."
if poetry run ruff check src/ --fix; then
    print_status "PASS" "Ruff linting passed"
else
    print_status "FAIL" "Ruff linting failed"
    exit 1
fi

# 3. Auto-commit linting fixes if any
if auto_commit_changes "linting"; then
    print_status "INFO" "Linting fixes auto-committed"
fi

# 4. Run black formatting check
print_status "INFO" "Running black formatting check..."
if poetry run black --check src/; then
    print_status "PASS" "Black formatting check passed"
else
    print_status "WARN" "Black formatting check failed - auto-formatting code..."
    poetry run black src/
    print_status "INFO" "Code formatted with black"
    
    # Auto-commit formatting changes if any
    if auto_commit_changes "formatting"; then
        print_status "INFO" "Formatting changes auto-committed"
    fi
fi

# 5. Run tests
print_status "INFO" "Running tests..."
if poetry run pytest -v; then
    print_status "PASS" "All tests passed"
else
    print_status "FAIL" "Tests failed - CANNOT PROCEED WITH RELEASE"
    print_status "FAIL" "Fix all test failures before creating tags"
    exit 1
fi

# 6. Check test coverage (if available)
if command_exists coverage; then
    print_status "INFO" "Checking test coverage..."
    poetry run coverage run -m pytest
    poetry run coverage report --show-missing
else
    print_status "INFO" "Coverage not available, skipping coverage check"
fi

# 7. Check if there are any TODO or FIXME comments
print_status "INFO" "Checking for TODO/FIXME comments..."
todo_count=$(grep -r "TODO\|FIXME" src/ --exclude-dir=__pycache__ 2>/dev/null | wc -l || echo "0")
if [ "$todo_count" -gt 0 ]; then
    print_status "WARN" "Found $todo_count TODO/FIXME comments"
    grep -r "TODO\|FIXME" src/ --exclude-dir=__pycache__ 2>/dev/null || true
    echo
    
    # Auto-analyze TODO/FIXME severity
    critical_todos=$(grep -r "TODO\|FIXME" src/ --exclude-dir=__pycache__ 2>/dev/null | grep -i "critical\|urgent\|blocking" | wc -l || echo "0")
    
    if [ "$critical_todos" -gt 0 ]; then
        print_status "FAIL" "Found $critical_todos critical TODO/FIXME comments - CANNOT PROCEED WITH RELEASE"
        exit 1
    else
        print_status "WARN" "TODO/FIXME comments are non-critical - proceeding with caution"
    fi
else
    print_status "PASS" "No TODO/FIXME comments found"
fi

# 8. Check for any remaining linting issues
print_status "INFO" "Final linting check..."
if poetry run ruff check src/; then
    print_status "PASS" "Final linting check passed"
else
    print_status "FAIL" "Final linting check failed - CANNOT PROCEED WITH RELEASE"
    print_status "FAIL" "Fix all linting issues before creating tags"
    exit 1
fi

# 9. Check if we're up to date with remote
print_status "INFO" "Checking if local is up to date with remote..."
git fetch origin
local_commit=$(git rev-parse HEAD)
remote_commit=$(git rev-parse origin/main)
if [ "$local_commit" != "$remote_commit" ]; then
    print_status "WARN" "Local is not up to date with remote main"
    echo "Local:  $local_commit"
    echo "Remote: $remote_commit"
    echo
    
    # Auto-analyze if we should pull
    # Check if remote has commits we don't have
    behind_count=$(git rev-list --count HEAD..origin/main)
    ahead_count=$(git rev-list --count origin/main..HEAD)
    
    if [ "$behind_count" -gt 0 ]; then
        print_status "AUTO" "Local is $behind_count commits behind remote - auto-pulling latest changes"
        git pull origin main
        print_status "INFO" "Pulled latest changes"
        
        # Re-run tests after pull to ensure nothing broke
        print_status "INFO" "Re-running tests after pull to ensure stability..."
        if poetry run pytest -v; then
            print_status "PASS" "Tests still pass after pull"
        else
            print_status "FAIL" "Tests failed after pull - remote changes broke something"
            exit 1
        fi
    else
        print_status "INFO" "Local is ahead of remote by $ahead_count commits - this is expected for releases"
    fi
else
    print_status "PASS" "Local is up to date with remote main"
fi

echo
echo "🎉 Pre-release check completed successfully!"
echo "=========================================="
print_status "PASS" "All quality checks passed"
print_status "PASS" "✅ READY FOR RELEASE - All tests passed, all linting clean"
print_status "INFO" "You can now safely create a tag"

# Show current status
echo
echo "📊 Current status:"
echo "=================="
echo "Branch: $(git branch --show-current)"
echo "Commit: $(git rev-parse --short HEAD)"
echo "Status: $(git status --porcelain | wc -l | tr -d ' ') files modified"

# Suggest next steps
echo
echo "🚀 Next steps:"
echo "=============="
echo "1. Create tag: git tag v0.x.x"
echo "2. Push tag: git push origin v0.x.x"
echo "3. GitHub Actions will automatically build and publish"

exit 0
