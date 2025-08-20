#!/bin/bash

# Version synchronization script for Reticulum
# This script helps ensure version consistency across all files
# Now fully unattended and intelligent - no user prompts needed

set -e  # Exit on any error

echo "🔄 Version synchronization check for Reticulum..."
echo "================================================"

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

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    print_status "FAIL" "Not in reticulum project root directory"
    exit 1
fi

# Function to extract version from pyproject.toml
get_pyproject_version() {
    grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/'
}

# Function to extract version from __init__.py
get_init_version() {
    grep '^__version__ = ' src/reticulum/__init__.py | sed 's/__version__ = "\(.*\)"/\1/'
}

# Function to get latest git tag
get_latest_tag() {
    git describe --tags --abbrev=0 2>/dev/null || echo "none"
}

# Function to get current commit hash
get_current_commit() {
    git rev-parse --short HEAD
}

# Function to check if working directory is clean
is_working_directory_clean() {
    [ -z "$(git status --porcelain)" ]
}

# Function to auto-fix version mismatches
auto_fix_version_mismatch() {
    local pyproject_version=$1
    local init_version=$2
    
    print_status "AUTO" "Auto-fixing version mismatch..."
    
    # Update __init__.py to match pyproject.toml (source of truth)
    sed -i.bak "s/^__version__ = \".*\"/__version__ = \"$pyproject_version\"/" src/reticulum/__init__.py
    rm -f src/reticulum/__init__.py.bak
    
    print_status "INFO" "Updated __init__.py to version $pyproject_version"
    
    # Commit the fix
    if git add src/reticulum/__init__.py && git commit -m "fix: sync __init__.py version with pyproject.toml"; then
        print_status "INFO" "Version fix committed"
        return 0
    else
        print_status "FAIL" "Failed to commit version fix"
        return 1
    fi
}

echo "📋 Checking version consistency..."
echo "================================"

# Get versions from different sources
pyproject_version=$(get_pyproject_version)
init_version=$(get_init_version)
latest_tag=$(get_latest_tag)
current_commit=$(get_current_commit)

print_status "INFO" "pyproject.toml version: $pyproject_version"
print_status "INFO" "__init__.py version: $init_version"
print_status "INFO" "Latest git tag: $latest_tag"
print_status "INFO" "Current commit: $current_commit"

# Check if versions match
if [ "$pyproject_version" = "$init_version" ]; then
    print_status "PASS" "pyproject.toml and __init__.py versions match"
else
    print_status "FAIL" "Version mismatch: pyproject.toml ($pyproject_version) != __init__.py ($init_version)"
    
    # Auto-fix the mismatch
    if auto_fix_version_mismatch "$pyproject_version" "$init_version"; then
        # Re-check after fix
        init_version=$(get_init_version)
        if [ "$pyproject_version" = "$init_version" ]; then
            print_status "PASS" "Version mismatch auto-fixed"
        else
            print_status "FAIL" "Version mismatch persists after auto-fix"
            exit 1
        fi
    else
        exit 1
    fi
fi

# Check if latest tag matches current version
if [ "$latest_tag" = "v$pyproject_version" ]; then
    print_status "PASS" "Git tag matches current version"
else
    print_status "WARN" "Git tag ($latest_tag) doesn't match current version ($pyproject_version)"
    
    # Check if we need to create a new tag
    if [ "$latest_tag" != "none" ]; then
        echo
        echo "🔍 Analyzing tag situation..."
        print_status "INFO" "Latest tag ($latest_tag) points to commit $(git rev-parse --short $latest_tag)"
        print_status "INFO" "Current commit is $current_commit"
        
        # Check if current commit is ahead of latest tag
        if git merge-base --is-ancestor $latest_tag HEAD 2>/dev/null; then
            print_status "INFO" "Current commit is ahead of latest tag - this is expected for new releases"
        else
            print_status "WARN" "Current commit is not a descendant of latest tag - unusual situation"
        fi
    else
        print_status "INFO" "No tags found - this appears to be the first release"
    fi
fi

# Check if working directory is clean
if is_working_directory_clean; then
    print_status "PASS" "Working directory is clean"
else
    print_status "WARN" "Working directory has uncommitted changes"
    git status --short
    
    # Auto-analyze if changes are safe to commit
    unstaged_files=$(git diff --name-only 2>/dev/null | wc -l | tr -d ' ')
    staged_files=$(git diff --cached --name-only 2>/dev/null | wc -l | tr -d ' ')
    
    if [ "$unstaged_files" -gt 0 ] || [ "$staged_files" -gt 0 ]; then
        print_status "WARN" "Found $unstaged_files unstaged and $staged_files staged files"
        
        # Check if changes are only in source files (likely safe)
        source_changes=$(git diff --name-only 2>/dev/null | grep -E '^src/|^tests/' | wc -l | tr -d ' ')
        if [ "$source_changes" -gt 0 ]; then
            print_status "INFO" "Changes include $source_changes source/test files - these should be committed before release"
        fi
    fi
fi

# Check if tests pass
print_status "INFO" "Running tests to ensure code quality..."
if poetry run pytest --quiet; then
    print_status "PASS" "All tests passed"
else
    print_status "FAIL" "Tests failed - CANNOT PROCEED WITH RELEASE"
    print_status "FAIL" "Fix all test failures before creating tags"
    exit 1
fi

echo
echo "📊 Version Status Summary:"
echo "=========================="

# Final version check
pyproject_version=$(get_pyproject_version)
init_version=$(get_init_version)
latest_tag=$(get_latest_tag)

if [ "$pyproject_version" = "$init_version" ] && [ "$latest_tag" = "v$pyproject_version" ] && is_working_directory_clean; then
    print_status "PASS" "All versions are synchronized and ready for release!"
    print_status "PASS" "✅ READY FOR RELEASE - All tests passed, all versions synced"
    echo
    echo "🚀 You can safely create a new tag:"
    echo "   git tag v$pyproject_version"
    echo "   git push origin v$pyproject_version"
else
    print_status "WARN" "Version synchronization issues detected"
    echo
    echo "🔧 Recommended actions:"
    
    if [ "$pyproject_version" != "$init_version" ]; then
        echo "   1. Fix version mismatch between pyproject.toml and __init__.py"
    fi
    
    if [ "$latest_tag" != "v$pyproject_version" ]; then
        echo "   2. Create new tag: git tag v$pyproject_version"
    fi
    
    if ! is_working_directory_clean; then
        echo "   3. Commit or stash uncommitted changes"
    fi
    
    echo "   4. Push tag: git push origin v$pyproject_version"
fi

echo
echo "💡 Pro tip: Run this script before creating tags to ensure consistency!"
