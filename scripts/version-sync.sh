#!/bin/bash

# Version synchronization script for Reticulum
# This script helps ensure version consistency across all files

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
    exit 1
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
        
        # Check if the latest tag points to the current commit
        tag_commit=$(git rev-parse --short "$latest_tag" 2>/dev/null || echo "none")
        if [ "$tag_commit" = "$current_commit" ]; then
            print_status "INFO" "Latest tag ($latest_tag) points to current commit ($current_commit)"
            print_status "WARN" "But version doesn't match - you may need to update version files"
        else
            print_status "INFO" "Latest tag ($latest_tag) points to commit $tag_commit"
            print_status "INFO" "Current commit is $current_commit"
            print_status "WARN" "You may need to create a new tag for version $pyproject_version"
        fi
    else
        print_status "INFO" "No git tags found - you may want to create v$pyproject_version"
    fi
fi

# Check if working directory is clean
if is_working_directory_clean; then
    print_status "PASS" "Working directory is clean"
else
    print_status "WARN" "Working directory has uncommitted changes"
    git status --short
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
        echo "   3. Push tag: git push origin v$pyproject_version"
    fi
    
    if ! is_working_directory_clean; then
        echo "   4. Commit or stash uncommitted changes"
    fi
fi

echo
echo "💡 Pro tip: Run this script before creating tags to ensure consistency!"

exit 0
