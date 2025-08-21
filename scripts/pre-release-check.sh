#!/bin/bash

# Pre-release check script for Reticulum
# This script verifies all quality checks before allowing a tag to be created
# Now fully unattended and intelligent - no user prompts needed
# 
# EXECUTION PHASES (strict order to prevent race conditions):
# 1. PREPARATION: Check environment, branch, working directory
# 2. CODE QUALITY: Lint, format, and fix code (NO COMMITS YET)
# 3. VALIDATION: Run tests and final checks
# 4. SYNCHRONIZATION: Sync with remote if needed
# 5. FINALIZATION: Commit all changes at once, final validation

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
        "PHASE")
            echo -e "${BLUE}🚀 PHASE${NC}: $message"
            ;;
    esac
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if there are any changes to commit
has_changes_to_commit() {
    [ -n "$(git status --porcelain)" ]
}

# Function to get change summary
get_change_summary() {
    local staged_files=$(git diff --cached --name-only 2>/dev/null | wc -l | tr -d ' ')
    local unstaged_files=$(git diff --name-only 2>/dev/null | wc -l | tr -d ' ')
    echo "staged:$staged_files,unstaged:$unstaged_files"
}

# Function to commit all accumulated changes at once
commit_all_changes() {
    local phase=$1
    
    if has_changes_to_commit; then
        local change_summary=$(get_change_summary)
        print_status "AUTO" "Committing all accumulated changes from $phase phase ($change_summary)"
        
        # Add all changes before committing
        git add .
        
        # Generate intelligent commit message based on phase
        case $phase in
            "quality")
                git commit -m "style: auto-fix code quality issues (linting + formatting)"
                ;;
            "sync")
                git commit -m "chore: sync with remote changes"
                ;;
            *)
                git commit -m "chore: auto-fix issues from $phase phase"
                ;;
        esac
        
        print_status "INFO" "All changes committed successfully"
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

# ============================================================================
# PHASE 1: PREPARATION - Check environment and working directory
# ============================================================================
print_status "PHASE" "1. PREPARATION - Checking environment and working directory"
echo "=================================================================="

# Check if we're on main branch
current_branch=$(git branch --show-current)
if [ "$current_branch" != "main" ]; then
    print_status "FAIL" "You're not on main branch (currently on: $current_branch)"
    print_status "FAIL" "Releases should only be made from main branch"
    exit 1
else
    print_status "PASS" "On main branch"
fi

# Check initial working directory state
if has_changes_to_commit; then
    print_status "WARN" "Initial working directory has uncommitted changes"
    git status --short
    
    change_summary=$(get_change_summary)
    print_status "INFO" "Change summary: $change_summary"
    
    # Don't commit yet - we'll handle all changes at the end
    print_status "INFO" "Changes will be committed after all quality checks pass"
else
    print_status "PASS" "Working directory is clean"
fi

# ============================================================================
# PHASE 2: CODE QUALITY - Lint, format, and fix code (NO COMMITS YET)
# ============================================================================
print_status "PHASE" "2. CODE QUALITY - Linting, formatting, and fixing code"
echo "=================================================================="

# Install dependencies
print_status "INFO" "Installing dependencies..."
poetry install --no-interaction

# Run linting with ruff (with auto-fix)
print_status "INFO" "Running ruff linting with auto-fix..."
if poetry run ruff check src/ --fix; then
    print_status "PASS" "Ruff linting passed"
else
    print_status "FAIL" "Ruff linting failed"
    exit 1
fi

# Run black formatting check (with auto-fix if needed)
print_status "INFO" "Running black formatting check..."
if poetry run black --check src/; then
    print_status "PASS" "Black formatting check passed"
else
    print_status "WARN" "Black formatting check failed - auto-formatting code..."
    poetry run black src/
    print_status "INFO" "Code formatted with black"
fi

# Check if any quality fixes were made
if has_changes_to_commit; then
    change_summary=$(get_change_summary)
    print_status "INFO" "Quality fixes made ($change_summary) - will commit after validation"
else
    print_status "PASS" "No quality fixes needed"
fi

# ============================================================================
# PHASE 3: VALIDATION - Run tests and final checks
# ============================================================================
print_status "PHASE" "3. VALIDATION - Running tests and final checks"
echo "=================================================================="

# Run tests
print_status "INFO" "Running tests..."
if poetry run pytest -v; then
    print_status "PASS" "All tests passed"
else
    print_status "FAIL" "Tests failed - CANNOT PROCEED WITH RELEASE"
    print_status "FAIL" "Fix all test failures before creating tags"
    exit 1
fi

# Check test coverage (if available)
if command_exists coverage; then
    print_status "INFO" "Checking test coverage..."
    poetry run coverage run -m pytest
    poetry run coverage report --show-missing
else
    print_status "INFO" "Coverage not available, skipping coverage check"
fi

# Check for TODO/FIXME comments
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

# Final linting check
print_status "INFO" "Final linting check..."
if poetry run ruff check src/; then
    print_status "PASS" "Final linting check passed"
else
    print_status "FAIL" "Final linting check failed - CANNOT PROCEED WITH RELEASE"
    print_status "FAIL" "Fix all linting issues before creating tags"
    exit 1
fi

# ============================================================================
# PHASE 4: SYNCHRONIZATION - Sync with remote if needed
# ============================================================================
print_status "PHASE" "4. SYNCHRONIZATION - Checking remote sync status"
echo "=================================================================="

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

# ============================================================================
# PHASE 5: FINALIZATION - Commit all changes and final validation
# ============================================================================
print_status "PHASE" "5. FINALIZATION - Committing changes and final validation"
echo "=================================================================="

# Commit all accumulated changes from quality fixes
if has_changes_to_commit; then
    commit_all_changes "quality"
else
    print_status "PASS" "No changes to commit"
fi

# Final working directory check
if has_changes_to_commit; then
    print_status "FAIL" "Working directory still has uncommitted changes after finalization"
    git status --short
    exit 1
else
    print_status "PASS" "Working directory is clean"
fi

# ============================================================================
# SUCCESS - All checks passed
# ============================================================================
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
# Run version synchronization
echo "🔄 Running version synchronization..."
bash scripts/version-sync.sh

echo
echo "🚀 Next steps:"
echo "=============="
echo "1. Versions synchronized ✅"
echo "2. Create tag: git tag v$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')"
echo "3. Push tag: git push origin v$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')"
echo "4. GitHub Actions will automatically build and publish 🤖"

exit 0
