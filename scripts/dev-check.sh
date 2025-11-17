#!/bin/bash

# Development Quality Check Script for Reticulum
# Provides comprehensive development quality checks with auto-fix capability
# Usage: ./dev-check.sh [--fix]

set -e

# Source common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"

# Parse arguments
AUTO_FIX=false
if [ "$1" = "--fix" ]; then
    AUTO_FIX=true
fi

echo "🔍 Development Quality Check for Reticulum..."
echo "============================================"
echo ""

# Basic environment checks
check_project_root
check_poetry

print_status "INFO" "Starting development quality checks..."
if [ "$AUTO_FIX" = true ]; then
    print_status "INFO" "Auto-fix mode enabled"
fi

# Run quality checks
if run_quality_checks $AUTO_FIX; then
    print_status "PASS" "All quality checks passed"
else
    print_status "FAIL" "Quality checks failed"
    exit 1
fi

# Quick version sync check (non-intrusive)
echo ""
print_status "INFO" "Checking version synchronization..."
if validate_versions >/dev/null 2>&1; then
    print_status "PASS" "All versions are synchronized"
else
    print_status "WARN" "Version files may need synchronization"
    print_status "INFO" "Run: make release sync (to fix version sync)"
fi

# Show current git status
echo ""
echo "📊 Current Status:"
echo "=================="
echo "Branch: $(git branch --show-current)"
echo "Commit: $(git rev-parse --short HEAD)"
echo "Modified files: $(git status --porcelain | wc -l | tr -d ' ')"

# Check for uncommitted changes
if ! is_git_clean; then
    print_status "WARN" "You have uncommitted changes:"
    git status --short
    echo ""
    print_status "INFO" "Consider committing your changes:"
    echo "   git add . && git commit -m 'your message'"
fi

echo ""
echo "🎉 Development check completed!"
echo "==============================="

if [ "$AUTO_FIX" = true ]; then
    print_status "PASS" "Auto-fixes applied where possible"
fi

print_status "PASS" "Code is ready for development/commit"

exit 0
