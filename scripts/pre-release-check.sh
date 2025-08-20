#!/bin/bash

# Pre-release check script for Reticulum
# This script verifies all quality checks before allowing a tag to be created

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
    esac
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
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
    print_status "WARN" "You have uncommitted changes. Consider committing them first."
    git status --short
    echo
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "INFO" "Pre-release check cancelled"
        exit 0
    fi
else
    print_status "PASS" "Working directory is clean"
fi

# Check if we're on main branch
current_branch=$(git branch --show-current)
if [ "$current_branch" != "main" ]; then
    print_status "WARN" "You're not on main branch (currently on: $current_branch)"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "INFO" "Pre-release check cancelled"
        exit 0
    fi
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

# 3. Check if ruff made any changes
if [ -n "$(git status --porcelain)" ]; then
    print_status "WARN" "Ruff made changes to fix linting issues"
    git status --short
    echo
    read -p "Commit these fixes? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git add .
        git commit -m "style: auto-fix linting issues with ruff"
        print_status "INFO" "Linting fixes committed"
    else
        print_status "WARN" "Linting fixes not committed - you should review them"
    fi
fi

# 4. Run black formatting check
print_status "INFO" "Running black formatting check..."
if poetry run black --check src/; then
    print_status "PASS" "Black formatting check passed"
else
    print_status "WARN" "Black formatting check failed - formatting code..."
    poetry run black src/
    print_status "INFO" "Code formatted with black"
    
    # Check if formatting made changes
    if [ -n "$(git status --porcelain)" ]; then
        print_status "WARN" "Black made formatting changes"
        git status --short
        echo
        read -p "Commit formatting changes? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            git add .
            git commit -m "style: auto-format code with black"
            print_status "INFO" "Formatting changes committed"
        fi
    fi
fi

# 5. Run tests
print_status "INFO" "Running tests..."
if poetry run pytest -v; then
    print_status "PASS" "All tests passed"
else
    print_status "FAIL" "Tests failed"
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
    read -p "Continue despite TODO/FIXME comments? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "INFO" "Pre-release check cancelled due to TODO/FIXME comments"
        exit 0
    fi
else
    print_status "PASS" "No TODO/FIXME comments found"
fi

# 8. Check for any remaining linting issues
print_status "INFO" "Final linting check..."
if poetry run ruff check src/; then
    print_status "PASS" "Final linting check passed"
else
    print_status "FAIL" "Final linting check failed - please fix remaining issues"
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
    read -p "Pull latest changes? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git pull origin main
        print_status "INFO" "Pulled latest changes"
    else
        print_status "WARN" "Not pulling latest changes - you may be behind"
    fi
else
    print_status "PASS" "Local is up to date with remote main"
fi

echo
echo "🎉 Pre-release check completed successfully!"
echo "=========================================="
print_status "PASS" "All quality checks passed"
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
