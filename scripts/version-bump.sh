#!/bin/bash

# Enhanced Version Bump Script for Reticulum
# Automatically increments version numbers and synchronizes across all files
# Supports semantic versioning: major.minor.patch

set -e  # Exit on any error

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
        "BUMP")
            echo -e "${PURPLE}📈 BUMP${NC}: $message"
            ;;
        "SYNC")
            echo -e "${CYAN}🔄 SYNC${NC}: $message"
            ;;
    esac
}

# Function to display usage
show_usage() {
    echo "Enhanced Version Bump Script for Reticulum"
    echo "=========================================="
    echo ""
    echo "Usage: $0 [patch|minor|major]"
    echo ""
    echo "Version Types:"
    echo "  patch  - Bump patch version (x.y.Z) - bug fixes"
    echo "  minor  - Bump minor version (x.Y.z) - new features"
    echo "  major  - Bump major version (X.y.z) - breaking changes"
    echo ""
    echo "Examples:"
    echo "  $0 patch   # 4.1.2 → 4.1.3"
    echo "  $0 minor   # 4.1.2 → 4.2.0"
    echo "  $0 major   # 4.1.2 → 5.0.0"
    echo ""
    echo "This script will:"
    echo "  • Increment the version in pyproject.toml"
    echo "  • Sync all version files automatically"
    echo "  • Commit the changes"
    echo "  • Create a git tag"
    echo "  • Provide push instructions"
}

# Check arguments
if [ $# -ne 1 ]; then
    show_usage
    exit 1
fi

VERSION_TYPE=$1

# Validate version type
case $VERSION_TYPE in
    patch|minor|major)
        ;;
    *)
        echo "❌ Invalid version type: $VERSION_TYPE"
        show_usage
        exit 1
        ;;
esac

echo "🚀 Enhanced Version Bump Script"
echo "==============================="
echo ""

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    print_status "FAIL" "Not in reticulum project root directory"
    exit 1
fi

# Check if git working directory is clean
if [ -n "$(git status --porcelain)" ]; then
    print_status "FAIL" "Working directory is not clean. Please commit or stash changes first."
    git status --short
    exit 1
fi

# Get current version
current_version=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
print_status "INFO" "Current version: $current_version"

# Parse version components
IFS='.' read -r -a version_parts <<< "$current_version"
major=${version_parts[0]}
minor=${version_parts[1]}
patch=${version_parts[2]}

# Calculate new version
case $VERSION_TYPE in
    patch)
        new_patch=$((patch + 1))
        new_version="$major.$minor.$new_patch"
        ;;
    minor)
        new_minor=$((minor + 1))
        new_version="$major.$new_minor.0"
        ;;
    major)
        new_major=$((major + 1))
        new_version="$new_major.0.0"
        ;;
esac

print_status "BUMP" "$VERSION_TYPE version: $current_version → $new_version"

# Update pyproject.toml
print_status "INFO" "Updating pyproject.toml..."
sed -i.bak "s/^version = \".*\"/version = \"$new_version\"/" pyproject.toml
rm -f pyproject.toml.bak

# Verify the update
updated_version=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
if [ "$updated_version" != "$new_version" ]; then
    print_status "FAIL" "Failed to update pyproject.toml"
    exit 1
fi

print_status "PASS" "pyproject.toml updated successfully"

# Run enhanced version synchronization
print_status "SYNC" "Synchronizing all version files..."
if bash scripts/version-sync.sh; then
    print_status "PASS" "All version files synchronized"
else
    print_status "FAIL" "Version synchronization failed"
    exit 1
fi

# Commit the changes
print_status "INFO" "Committing version bump..."
git add pyproject.toml src/reticulum/__init__.py src/reticulum/cli.py README.md

# Create intelligent commit message
case $VERSION_TYPE in
    patch)
        commit_msg="chore: bump version to v$new_version (patch release)"
        ;;
    minor)
        commit_msg="chore: bump version to v$new_version (minor release)"
        ;;
    major)
        commit_msg="chore: bump version to v$new_version (major release)"
        ;;
esac

if git commit -m "$commit_msg"; then
    print_status "PASS" "Version bump committed"
else
    print_status "FAIL" "Failed to commit version bump"
    exit 1
fi

# Create git tag
print_status "INFO" "Creating git tag v$new_version..."
if git tag "v$new_version"; then
    print_status "PASS" "Git tag v$new_version created"
else
    print_status "FAIL" "Failed to create git tag"
    exit 1
fi

# Success summary
echo ""
echo "🎉 Version Bump Completed Successfully!"
echo "======================================"
print_status "PASS" "Version bumped: $current_version → $new_version"
print_status "PASS" "All files synchronized"
print_status "PASS" "Changes committed"
print_status "PASS" "Git tag v$new_version created"

echo ""
echo "🚀 Next Steps:"
echo "============="
echo "1. Push the changes:"
echo "   git push origin main"
echo ""
echo "2. Push the tag:"
echo "   git push origin v$new_version"
echo ""
echo "3. GitHub Actions will automatically:"
echo "   • Run all tests"
echo "   • Build the package"
echo "   • Publish to PyPI"
echo "   • Create GitHub release"
echo ""
echo "💡 Or push both at once:"
echo "   git push origin main v$new_version"

exit 0
