#!/bin/bash

# Unified Release Script for Reticulum
# Provides complete release workflow with version management
# Usage: ./release.sh [patch|minor|major|sync]

set -e

# Source common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"

# Function to display usage
show_usage() {
    echo "Unified Release Script for Reticulum"
    echo "==================================="
    echo ""
    echo "Usage: $0 [patch|minor|major|sync]"
    echo ""
    echo "Commands:"
    echo "  patch  - Bump patch version (x.y.Z) - bug fixes"
    echo "  minor  - Bump minor version (x.Y.z) - new features"
    echo "  major  - Bump major version (X.y.z) - breaking changes"
    echo "  sync   - Synchronize version files only (no version bump)"
    echo ""
    echo "Examples:"
    echo "  $0 patch   # 0.4.3 → 0.4.4"
    echo "  $0 minor   # 0.4.3 → 0.5.0"
    echo "  $0 major   # 0.4.3 → 1.0.0"
    echo "  $0 sync    # Fix version mismatches"
    echo ""
    echo "Full Release Process:"
    echo "  • Environment validation"
    echo "  • Quality checks (linting, formatting, tests)"
    echo "  • Version management"
    echo "  • Git tagging"
    echo "  • Push instructions"
}

# Check arguments
if [ $# -ne 1 ]; then
    show_usage
    exit 1
fi

COMMAND=$1

# Validate command
case $COMMAND in
    patch|minor|major|sync)
        ;;
    *)
        echo "❌ Invalid command: $COMMAND"
        echo ""
        show_usage
        exit 1
        ;;
esac

echo "🚀 Reticulum Release Manager"
echo "==========================="
echo ""

# Environment validation
print_status "INFO" "Validating environment..."
check_project_root
check_python_env_available
check_main_branch

# Check git working directory
if ! is_git_clean; then
    print_status "FAIL" "Working directory is not clean. Please commit or stash changes first."
    git status --short
    exit 1
fi
print_status "PASS" "Working directory is clean"

# Get current version
current_version=$(get_pyproject_version)
print_status "INFO" "Current version: $current_version"

# Handle sync command
if [ "$COMMAND" = "sync" ]; then
    print_status "SYNC" "Synchronizing version files..."
    
    if validate_versions; then
        print_status "PASS" "All versions are already synchronized"
        exit 0
    fi
    
    files_updated_str=$(sync_all_versions)
    files_updated=($files_updated_str)
    
    if [ ${#files_updated[@]} -gt 0 ]; then
        print_status "AUTO" "Updated files: ${files_updated[*]}"
        
        # Commit changes
        git add ${files_updated[@]}
        git commit -m "fix: sync all version files to v$current_version"
        print_status "PASS" "Version synchronization completed and committed"
    else
        print_status "PASS" "No files needed updating"
    fi
    
    exit 0
fi

# For version bumps, run quality checks first
echo ""
print_status "INFO" "Running quality checks..."
if ! run_quality_checks false; then
    print_status "FAIL" "Quality checks failed - cannot proceed with release"
    exit 1
fi
print_status "PASS" "All quality checks passed"

# Use Commitizen for version bump
print_status "BUMP" "Using Commitizen for $COMMAND version bump"
if commitizen_bump_version "$COMMAND"; then
    # Get the new version from pyproject.toml
    new_version=$(get_pyproject_version)
    print_status "PASS" "Commitizen version bump: $current_version → $new_version"
else
    print_status "FAIL" "Commitizen version bump failed"
    exit 1
fi

# Verify version sync
print_status "SYNC" "Verifying version synchronization..."
if validate_versions >/dev/null 2>&1; then
    print_status "PASS" "All version files synchronized"
else
    print_status "WARN" "Version files out of sync - attempting to fix..."
    files_updated_str=$(sync_all_versions)
    files_updated=($files_updated_str)
    if [ ${#files_updated[@]} -gt 0 ]; then
        print_status "PASS" "Fixed synchronization for ${#files_updated[@]} files"
    else
        print_status "PASS" "Version files already synchronized"
    fi
fi

# Check for TODO/FIXME comments
print_status "INFO" "Checking for critical TODO/FIXME comments..."
critical_todos=$(grep -r "TODO\|FIXME" src/ --exclude-dir=__pycache__ 2>/dev/null | grep -i "critical\|urgent\|blocking" | wc -l || echo "0")

if [ "$critical_todos" -gt 0 ]; then
    print_status "FAIL" "Found $critical_todos critical TODO/FIXME comments - cannot proceed with release"
    grep -r "TODO\|FIXME" src/ --exclude-dir=__pycache__ 2>/dev/null | grep -i "critical\|urgent\|blocking" || true
    exit 1
else
    print_status "PASS" "No critical TODO/FIXME comments found"
fi

# Check if Commitizen already committed the changes
print_status "INFO" "Checking if changes are already committed..."
if is_git_clean; then
    print_status "PASS" "Changes already committed by Commitizen"
else
    # Commit any remaining changes
    print_status "INFO" "Committing version bump..."
    if [ ${#files_updated[@]} -gt 0 ]; then
        git add pyproject.toml CHANGELOG.md ${files_updated[@]}
    else
        git add pyproject.toml CHANGELOG.md
    fi

    # Create intelligent commit message
    commit_msg="chore: bump version to v$new_version ($COMMAND release)"
    if git commit -m "$commit_msg"; then
        print_status "PASS" "Version bump committed"
    else
        print_status "FAIL" "Failed to commit version bump"
        exit 1
    fi
fi

# Create git tag
print_status "INFO" "Creating git tag v$new_version..."
if git tag "v$new_version"; then
    print_status "PASS" "Git tag v$new_version created"
else
    print_status "FAIL" "Failed to create git tag"
    exit 1
fi

# Final validation
echo ""
print_status "INFO" "Final release validation..."

# Check version sync
if validate_versions >/dev/null 2>&1; then
    print_status "PASS" "✅ All version files synchronized"
else
    print_status "FAIL" "❌ Version files not synchronized"
    exit 1
fi

# Check tag
latest_tag=$(get_latest_tag)
if [ "$latest_tag" = "v$new_version" ]; then
    print_status "PASS" "✅ Git tag matches new version"
else
    print_status "FAIL" "❌ Git tag mismatch"
    exit 1
fi

# Check working directory
if is_git_clean; then
    print_status "PASS" "✅ Working directory is clean"
else
    print_status "FAIL" "❌ Working directory has uncommitted changes"
    exit 1
fi

# Success summary
echo ""
echo "🎉 Release v$new_version Ready!"
echo "==============================="
print_status "PASS" "Version bumped: $current_version → $new_version"
print_status "PASS" "All files synchronized"
print_status "PASS" "Changes committed"
print_status "PASS" "Git tag v$new_version created"

echo ""
echo "🚀 Next Steps:"
echo "=============="
echo "1. Push the changes and tag:"
echo "   git push origin main v$new_version"
echo ""
echo "2. GitHub Actions will automatically:"
echo "   • Run comprehensive tests"
echo "   • Build the package"
echo "   • Publish to PyPI"
echo "   • Create GitHub release"
echo ""
echo "3. Monitor the deployment:"
echo "   • GitHub: https://github.com/plexicus/reticulum/actions"
echo "   • PyPI: https://pypi.org/project/reticulum/"

exit 0
