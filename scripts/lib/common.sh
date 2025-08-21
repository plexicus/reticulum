#!/bin/bash

# Common functions for Reticulum scripts
# Shared utilities to eliminate code duplication

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
        "BUMP")
            echo -e "${PURPLE}📈 BUMP${NC}: $message"
            ;;
    esac
}

# Check if we're in the right directory
check_project_root() {
    if [ ! -f "pyproject.toml" ]; then
        print_status "FAIL" "Not in reticulum project root directory"
        exit 1
    fi
}

# Check if Poetry is available
check_poetry() {
    if ! command -v poetry >/dev/null 2>&1; then
        print_status "FAIL" "Poetry is not installed or not in PATH"
        exit 1
    fi
}

# Check if git working directory is clean
is_git_clean() {
    [ -z "$(git status --porcelain)" ]
}

# Check if we're on main branch
check_main_branch() {
    local current_branch=$(git branch --show-current)
    if [ "$current_branch" != "main" ]; then
        print_status "FAIL" "You're not on main branch (currently on: $current_branch)"
        print_status "FAIL" "Releases should only be made from main branch"
        exit 1
    fi
}

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

get_latest_tag() {
    git describe --tags --abbrev=0 2>/dev/null || echo "none"
}

# Functions to update version files
update_init_version() {
    local new_version=$1
    print_status "AUTO" "Updating __init__.py to version $new_version"
    sed -i.bak "s/^__version__ = \".*\"/__version__ = \"$new_version\"/" src/reticulum/__init__.py
    rm -f src/reticulum/__init__.py.bak
}

update_cli_version() {
    local new_version=$1
    print_status "AUTO" "Updating CLI version to $new_version"
    sed -i.bak "s/version=\"%(prog)s [^\"]*\"/version=\"%(prog)s $new_version\"/" src/reticulum/cli.py
    rm -f src/reticulum/cli.py.bak
}

update_readme_version() {
    local new_version=$1
    print_status "AUTO" "Updating README.md to version $new_version"
    sed -i.bak "s/🚀 \*\*Latest Release: v[0-9.][0-9.]*[0-9]/🚀 **Latest Release: v$new_version/" README.md
    sed -i.bak "s/### ✅ \*\*What's New in v[0-9.][0-9.]*[0-9]/### ✅ **What's New in v$new_version/" README.md
    rm -f README.md.bak
}

update_pyproject_version() {
    local new_version=$1
    print_status "AUTO" "Updating pyproject.toml to version $new_version"
    sed -i.bak "s/^version = \".*\"/version = \"$new_version\"/" pyproject.toml
    rm -f pyproject.toml.bak
}

# Sync all version files to match pyproject.toml
sync_all_versions() {
    local source_version=$(get_pyproject_version)
    local files_updated=""
    
    print_status "SYNC" "Synchronizing all version files to $source_version..."
    
    # Get current versions
    local init_version=$(get_init_version)
    local cli_version=$(get_cli_version)
    local readme_version=$(get_readme_version)
    
    # Update files if needed
    if [ "$init_version" != "$source_version" ]; then
        update_init_version "$source_version"
        files_updated="$files_updated src/reticulum/__init__.py"
    fi
    
    if [ "$cli_version" != "$source_version" ]; then
        update_cli_version "$source_version"
        files_updated="$files_updated src/reticulum/cli.py"
    fi
    
    if [ "$readme_version" != "$source_version" ] && [ "$readme_version" != "none" ]; then
        update_readme_version "$source_version"
        files_updated="$files_updated README.md"
    fi
    
    # Return files updated (trimmed)
    echo "$files_updated" | sed 's/^ *//'
}

# Validate all versions are synchronized
validate_versions() {
    local pyproject_version=$(get_pyproject_version)
    local init_version=$(get_init_version)
    local cli_version=$(get_cli_version)
    local readme_version=$(get_readme_version)
    
    local mismatches=0
    
    if [ "$pyproject_version" != "$init_version" ]; then
        print_status "WARN" "Version mismatch: pyproject.toml ($pyproject_version) != __init__.py ($init_version)"
        mismatches=$((mismatches + 1))
    fi
    
    if [ "$pyproject_version" != "$cli_version" ]; then
        print_status "WARN" "Version mismatch: pyproject.toml ($pyproject_version) != cli.py ($cli_version)"
        mismatches=$((mismatches + 1))
    fi
    
    if [ "$pyproject_version" != "$readme_version" ] && [ "$readme_version" != "none" ]; then
        print_status "WARN" "Version mismatch: pyproject.toml ($pyproject_version) != README.md ($readme_version)"
        mismatches=$((mismatches + 1))
    fi
    
    return $mismatches
}

# Run quality checks (linting + formatting + tests)
run_quality_checks() {
    local auto_fix=${1:-false}
    
    print_status "INFO" "Installing dependencies..."
    poetry install --no-interaction
    
    # Linting
    print_status "INFO" "Running linting..."
    if [ "$auto_fix" = true ]; then
        poetry run ruff check src/ --fix
    else
        poetry run ruff check src/
    fi
    
    if [ $? -ne 0 ]; then
        print_status "FAIL" "Linting failed"
        return 1
    fi
    
    # Formatting
    print_status "INFO" "Checking code formatting..."
    if poetry run black --check src/; then
        print_status "PASS" "Code formatting is correct"
    else
        if [ "$auto_fix" = true ]; then
            print_status "AUTO" "Auto-formatting code..."
            poetry run black src/
        else
            print_status "FAIL" "Code formatting check failed (use --fix to auto-format)"
            return 1
        fi
    fi
    
    # Tests
    print_status "INFO" "Running tests..."
    if poetry run pytest -v; then
        print_status "PASS" "All tests passed"
    else
        print_status "FAIL" "Tests failed"
        return 1
    fi
    
    return 0
}

# Calculate next version based on bump type
calculate_next_version() {
    local current_version=$1
    local bump_type=$2
    
    IFS='.' read -r -a version_parts <<< "$current_version"
    local major=${version_parts[0]}
    local minor=${version_parts[1]}
    local patch=${version_parts[2]}
    
    case $bump_type in
        patch)
            echo "$major.$minor.$((patch + 1))"
            ;;
        minor)
            echo "$major.$((minor + 1)).0"
            ;;
        major)
            echo "$((major + 1)).0.0"
            ;;
        *)
            echo "Invalid bump type: $bump_type" >&2
            return 1
            ;;
    esac
}
