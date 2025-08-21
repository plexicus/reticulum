#!/bin/bash

# Version Synchronization Script for Reticulum
# Ensures version consistency across all project files

set -e  # Exit on any error

echo "🔄 Version Synchronization for Reticulum..."
echo "==========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
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
            echo -e "${CYAN}🤖 AUTO${NC}: $message"
            ;;
        "SYNC")
            echo -e "${PURPLE}🔄 SYNC${NC}: $message"
            ;;
        "UPDATE")
            echo -e "${CYAN}📝 UPDATE${NC}: $message"
            ;;
    esac
}

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    print_status "FAIL" "Not in reticulum project root directory"
    exit 1
fi

# Version extraction functions
get_pyproject_version() {
    grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/'
}

get_init_version() {
    grep '^__version__ = ' src/reticulum/__init__.py | sed 's/__version__ = "\(.*\)"/\1/'
}

get_cli_version() {
    grep 'version="%(prog)s' src/reticulum/cli.py | sed 's/.*version="%(prog)s \([^"]*\)".*/\1/'
}

get_readme_version() {
    grep '🚀 \*\*Latest Release:' README.md | sed 's/.*v\([0-9.][0-9.]*[0-9]\).*/\1/' || echo "none"
}

# Functions to update versions in all files
update_init_version() {
    local new_version=$1
    print_status "UPDATE" "Updating __init__.py to version $new_version"
    sed -i.bak "s/^__version__ = \".*\"/__version__ = \"$new_version\"/" src/reticulum/__init__.py
    rm -f src/reticulum/__init__.py.bak
}

update_cli_version() {
    local new_version=$1
    print_status "UPDATE" "Updating CLI version to $new_version"
    sed -i.bak "s/version=\"%(prog)s [^\"]*\"/version=\"%(prog)s $new_version\"/" src/reticulum/cli.py
    rm -f src/reticulum/cli.py.bak
}

update_readme_version() {
    local new_version=$1
    print_status "UPDATE" "Updating README.md to version $new_version"
    # Update the main version announcement
    sed -i.bak "s/🚀 \*\*Latest Release: v[0-9.][0-9.]*[0-9]/🚀 **Latest Release: v$new_version/" README.md
    # Update the version section header
    sed -i.bak "s/### ✅ \*\*What's New in v[0-9.][0-9.]*[0-9]/### ✅ **What's New in v$new_version/" README.md
    rm -f README.md.bak
}

update_pyproject_version() {
    local new_version=$1
    print_status "UPDATE" "Updating pyproject.toml to version $new_version"
    sed -i.bak "s/^version = \".*\"/version = \"$new_version\"/" pyproject.toml
    rm -f pyproject.toml.bak
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

# Auto-sync function for version files
auto_sync_all_versions() {
    local source_version=$1  # pyproject.toml is the source of truth
    local files_updated=()
    
    print_status "SYNC" "Synchronizing version files to $source_version..."
    
    # Get current versions
    local init_version=$(get_init_version)
    local cli_version=$(get_cli_version)
    local readme_version=$(get_readme_version)
    
    # Update __init__.py if needed
    if [ "$init_version" != "$source_version" ]; then
        update_init_version "$source_version"
        files_updated+=("src/reticulum/__init__.py")
    fi
    
    # Update CLI version if needed
    if [ "$cli_version" != "$source_version" ]; then
        update_cli_version "$source_version"
        files_updated+=("src/reticulum/cli.py")
    fi
    
    # Update README version if needed
    if [ "$readme_version" != "$source_version" ]; then
        update_readme_version "$source_version"
        files_updated+=("README.md")
    fi
    
    # Commit all changes if any were made
    if [ ${#files_updated[@]} -gt 0 ]; then
        print_status "AUTO" "Files updated: ${files_updated[*]}"
        
        # Add all updated files
        for file in "${files_updated[@]}"; do
            git add "$file"
        done
        
        # Create intelligent commit message
        local commit_msg="fix: sync all version files to v$source_version"
        if git commit -m "$commit_msg"; then
            print_status "INFO" "All version files synchronized and committed"
            return 0
        else
            print_status "FAIL" "Failed to commit version synchronization"
            return 1
        fi
    else
        print_status "PASS" "All version files already synchronized"
        return 0
    fi
}

# Function to validate and compare all versions
validate_all_versions() {
    local pyproject_version=$(get_pyproject_version)
    local init_version=$(get_init_version)
    local cli_version=$(get_cli_version)
    local readme_version=$(get_readme_version)
    
    print_status "INFO" "Version comparison across all files:"
    print_status "INFO" "  pyproject.toml: $pyproject_version"
    print_status "INFO" "  __init__.py:    $init_version"
    print_status "INFO" "  cli.py:         $cli_version"
    print_status "INFO" "  README.md:      $readme_version"
    
    # Check for mismatches
    local mismatches=0
    
    if [ "$pyproject_version" != "$init_version" ]; then
        print_status "WARN" "Mismatch: pyproject.toml ($pyproject_version) != __init__.py ($init_version)"
        mismatches=$((mismatches + 1))
    fi
    
    if [ "$pyproject_version" != "$cli_version" ]; then
        print_status "WARN" "Mismatch: pyproject.toml ($pyproject_version) != cli.py ($cli_version)"
        mismatches=$((mismatches + 1))
    fi
    
    if [ "$pyproject_version" != "$readme_version" ] && [ "$readme_version" != "none" ]; then
        print_status "WARN" "Mismatch: pyproject.toml ($pyproject_version) != README.md ($readme_version)"
        mismatches=$((mismatches + 1))
    fi
    
    return $mismatches
}

echo "📋 Version Consistency Check..."
echo "=============================="

# Get the source of truth version
pyproject_version=$(get_pyproject_version)
latest_tag=$(get_latest_tag)
current_commit=$(get_current_commit)

print_status "INFO" "Source of truth (pyproject.toml): $pyproject_version"
print_status "INFO" "Latest git tag: $latest_tag"
print_status "INFO" "Current commit: $current_commit"

echo
print_status "INFO" "Validating all version files..."

# Validate all versions and check for mismatches
if validate_all_versions; then
    print_status "PASS" "All version files are synchronized ✨"
else
    mismatches=$?
    print_status "WARN" "Found $mismatches version mismatch(es) - auto-synchronizing..."
    
    # Auto-sync all versions to match pyproject.toml
    if auto_sync_all_versions "$pyproject_version"; then
        echo
        print_status "SYNC" "Re-validating after synchronization..."
        
        # Re-validate after sync
        if validate_all_versions; then
            print_status "PASS" "All version files now synchronized! 🎉"
        else
            print_status "FAIL" "Version synchronization failed - manual intervention required"
            exit 1
        fi
    else
        print_status "FAIL" "Auto-synchronization failed"
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
echo "📊 Release Status..."
echo "=================="

# Re-check all versions after potential sync
pyproject_version=$(get_pyproject_version)
latest_tag=$(get_latest_tag)
all_versions_synced=true

# Validate that all version files are now in sync
if ! validate_all_versions >/dev/null 2>&1; then
    all_versions_synced=false
fi

# Comprehensive release readiness check
echo
print_status "INFO" "Release readiness checklist:"

# Check 1: All versions synchronized
if [ "$all_versions_synced" = true ]; then
    print_status "PASS" "✅ All version files synchronized"
else
    print_status "FAIL" "❌ Version files not synchronized"
fi

# Check 2: Git tag status
if [ "$latest_tag" = "v$pyproject_version" ]; then
    print_status "PASS" "✅ Git tag matches current version"
else
    print_status "WARN" "⚠️  Git tag needs updating (latest: $latest_tag, current: v$pyproject_version)"
fi

# Check 3: Working directory status
if is_working_directory_clean; then
    print_status "PASS" "✅ Working directory is clean"
else
    print_status "WARN" "⚠️  Working directory has uncommitted changes"
fi

# Final assessment
if [ "$all_versions_synced" = true ] && [ "$latest_tag" = "v$pyproject_version" ] && is_working_directory_clean; then
    echo
    print_status "PASS" "🎉 RELEASE READY!"
    echo
    echo "🚀 Next steps for release:"
    echo "   1. All version files are already synchronized ✅"
    echo "   2. Tag already exists: $latest_tag ✅"
    echo "   3. Ready to push: git push origin $latest_tag"
    echo "   4. GitHub Actions will handle the rest automatically 🤖"
elif [ "$all_versions_synced" = true ] && is_working_directory_clean; then
    echo
    print_status "PASS" "🚀 READY FOR NEW RELEASE!"
    echo
    echo "🏷️  Create new release tag:"
    echo "   git tag v$pyproject_version"
    echo "   git push origin v$pyproject_version"
    echo
    echo "🤖 GitHub Actions will then:"
    echo "   • Run comprehensive tests"
    echo "   • Build the package"
    echo "   • Publish to PyPI"
    echo "   • Create GitHub release with changelog"
else
    echo
    print_status "WARN" "🔧 Action items for release readiness:"
    
    if [ "$all_versions_synced" != true ]; then
        echo "   ❌ Fix remaining version synchronization issues"
    fi
    
    if [ "$latest_tag" != "v$pyproject_version" ]; then
        echo "   🏷️  Create new tag: git tag v$pyproject_version"
    fi
    
    if ! is_working_directory_clean; then
        echo "   📝 Commit or stash uncommitted changes"
    fi
    
    echo "   🚀 Then push tag: git push origin v$pyproject_version"
fi


