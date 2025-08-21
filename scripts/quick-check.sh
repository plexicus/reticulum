#!/bin/bash

# Quick check script for Reticulum development
# This script runs essential quality checks without interactive prompts

set -e  # Exit on any error

echo "🔍 Quick quality check for Reticulum..."
echo "======================================"

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

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    print_status "FAIL" "Not in reticulum project root directory"
    exit 1
fi

# Check if Poetry is available
if ! command -v poetry >/dev/null 2>&1; then
    print_status "FAIL" "Poetry is not installed or not in PATH"
    exit 1
fi

print_status "INFO" "Starting quick quality checks..."

# 1. Install dependencies
print_status "INFO" "Installing dependencies..."
poetry install --no-interaction

# 2. Run linting with ruff (auto-fix)
print_status "INFO" "Running ruff linting with auto-fix..."
if poetry run ruff check src/ --fix; then
    print_status "PASS" "Ruff linting passed"
else
    print_status "FAIL" "Ruff linting failed"
    exit 1
fi

# 3. Run black formatting check
print_status "INFO" "Running black formatting check..."
if poetry run black --check src/; then
    print_status "PASS" "Black formatting check passed"
else
    print_status "WARN" "Black formatting check failed - formatting code..."
    poetry run black src/
    print_status "INFO" "Code formatted with black"
fi

# 4. Run tests
print_status "INFO" "Running tests..."
if poetry run pytest -v; then
    print_status "PASS" "All tests passed"
else
    print_status "FAIL" "Tests failed"
    exit 1
fi

# 5. Final linting check
print_status "INFO" "Final linting check..."
if poetry run ruff check src/; then
    print_status "PASS" "Final linting check passed"
else
    print_status "FAIL" "Final linting check failed - please fix remaining issues"
    exit 1
fi

echo
echo "🎉 Quick check completed successfully!"
echo "====================================="
print_status "PASS" "All quality checks passed"

# Show current status
echo
echo "📊 Current status:"
echo "=================="
echo "Branch: $(git branch --show-current)"
echo "Commit: $(git rev-parse --short HEAD)"
echo "Modified files: $(git status --porcelain | wc -l | tr -d ' ')"

# Check if there are uncommitted changes
if [ -n "$(git status --porcelain)" ]; then
    print_status "WARN" "You have uncommitted changes:"
    git status --short
    echo
    print_status "INFO" "Consider running: git add . && git commit -m 'style: auto-fix quality issues'"
fi

# Quick version sync check
echo
print_status "INFO" "Quick version synchronization check..."
if scripts/version-sync.sh >/dev/null 2>&1; then
    print_status "PASS" "All versions are synchronized ✅"
else
    print_status "WARN" "Version files may need synchronization - run: make version-sync"
fi

exit 0
