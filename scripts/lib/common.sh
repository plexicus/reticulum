#!/bin/bash

# Common functions for Reticulum scripts
# Shared utilities to eliminate code duplication

# Status output (no colors)

# Function to print status output
print_status() {
    local status=$1
    local message=$2
    case $status in
        "PASS")
            echo "✅ PASS: $message"
            ;;
        "FAIL")
            echo "❌ FAIL: $message"
            ;;
        "WARN")
            echo "⚠️  WARN: $message"
            ;;
        "INFO")
            echo "ℹ️  INFO: $message"
            ;;
        "AUTO")
            echo "🤖 AUTO: $message"
            ;;
        "SYNC")
            echo "🔄 SYNC: $message"
            ;;
        "BUMP")
            echo "📈 BUMP: $message"
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

# Check if any Python environment is available
check_python_env_available() {
    local env=$(detect_python_env)
    case $env in
        "venv")
            print_status "INFO" "Using virtual environment (.venv)"
            ;;
        "uv")
            print_status "INFO" "Using uv environment"
            ;;
        "system")
            print_status "WARN" "Using system Python (no environment detected)"
            print_status "INFO" "Consider setting up a Python environment for better dependency management:"
            print_status "INFO" "  - uv (recommended): curl -LsSf https://astral.sh/uv/install.sh | sh"
            print_status "INFO" "  - Virtual environment: python -m venv .venv && source .venv/bin/activate"
            ;;
    esac
}

# Detect available Python environment manager
detect_python_env() {
    if command -v uv >/dev/null 2>&1; then
        echo "uv"
    elif [ -d ".venv" ]; then
        echo "venv"
    else
        echo "system"
    fi
}

# Get Python command prefix based on detected environment
get_python_cmd() {
    local env=$(detect_python_env)
    case $env in
        "venv")
            echo ".venv/bin/python -m"
            ;;
        "uv")
            echo "uv run"
            ;;
        "system")
            echo "python -m"
            ;;
    esac
}

# Get Python executable based on detected environment
get_python_exec() {
    local env=$(detect_python_env)
    case $env in
        "venv")
            echo ".venv/bin/python"
            ;;
        "uv")
            echo "uv run python"
            ;;
        "system")
            echo "python"
            ;;
    esac
}

# Check if any Python environment is available
check_python_env() {
    local env=$(detect_python_env)
    case $env in
        "venv")
            print_status "INFO" "Using virtual environment (.venv)"
            ;;
        "uv")
            print_status "INFO" "Using uv environment"
            ;;
        "system")
            print_status "WARN" "Using system Python (no environment detected)"
            print_status "INFO" "Consider setting up a Python environment:"
            print_status "INFO" "  - uv (recommended): curl -LsSf https://astral.sh/uv/install.sh | sh"
            print_status "INFO" "  - Virtual environment: python -m venv .venv && source .venv/bin/activate"
            ;;
    esac
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
    grep 'version="%(prog)s' src/reticulum/cli.py | awk -F'"' '{print $(NF-1)}' | awk '{print $NF}'
}

get_readme_version() {
    grep '\*\*Latest Release:' README.md | sed 's/.*v\([0-9.][0-9.]*[0-9]\).*/\1/' 2>/dev/null || echo "none"
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
    sed -i.bak "s/version=\"%(prog)s [0-9.]*\"/version=\"%(prog)s $new_version\"/" src/reticulum/cli.py
    rm -f src/reticulum/cli.py.bak
}

update_readme_version() {
    local new_version=$1
    print_status "AUTO" "Updating README.md to version $new_version"
    sed -i.bak "s/\*\*Latest Release: v[0-9.][0-9.]*[0-9]/**Latest Release: v$new_version/" README.md
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

    print_status "SYNC" "Synchronizing all version files to $source_version"

    # Get current versions
    local init_version=$(get_init_version)
    local cli_version=$(get_cli_version)
    local readme_version=$(get_readme_version)
    
    # Update files if needed (redirect messages to stderr)
    if [ "$init_version" != "$source_version" ]; then
        print_status "AUTO" "Updating __init__.py to version $source_version" >&2
        sed -i.bak "s/^__version__ = \".*\"/__version__ = \"$source_version\"/" src/reticulum/__init__.py
        rm -f src/reticulum/__init__.py.bak
        files_updated="$files_updated src/reticulum/__init__.py"
    else
        print_status "PASS" "__init__.py already synchronized: $init_version"
    fi
    
    if [ "$cli_version" != "$source_version" ]; then
        print_status "AUTO" "Updating CLI version to $source_version" >&2
        sed -i.bak "s/version=\"%(prog)s [^\"]*\"/version=\"%(prog)s $source_version\"/" src/reticulum/cli.py
        rm -f src/reticulum/cli.py.bak
        files_updated="$files_updated src/reticulum/cli.py"
    else
        print_status "PASS" "CLI already synchronized: $cli_version"
    fi
    
    if [ "$readme_version" = "none" ]; then
        print_status "WARN" "README.md version not found - regex pattern may need adjustment"
    elif [ "$readme_version" != "$source_version" ]; then
        print_status "AUTO" "Updating README.md to version $source_version" >&2
        sed -i.bak "s/\*\*Latest Release: v[0-9.][0-9.]*[0-9]/**Latest Release: v$source_version/" README.md
        sed -i.bak "s/### ✅ \*\*What's New in v[0-9.][0-9.]*[0-9]/### ✅ **What's New in v$source_version/" README.md
        rm -f README.md.bak
        files_updated="$files_updated README.md"
    else
        print_status "PASS" "README.md already synchronized: $readme_version"
    fi
    
    if [ -n "$files_updated" ]; then
        print_status "SYNC" "Updated files: $files_updated"
    else
        print_status "PASS" "All version files are already synchronized"
    fi

    # Return files updated (trimmed and without color codes)
    echo "$files_updated" | sed 's/^ *//'
}

# Validate all versions are synchronized
validate_versions() {
    local pyproject_version=$(get_pyproject_version)
    local init_version=$(get_init_version)
    local cli_version=$(get_cli_version)
    local readme_version=$(get_readme_version)

    local mismatches=0

    print_status "INFO" "Validating version synchronization..."
    print_status "INFO" "Source version (pyproject.toml): $pyproject_version"

    if [ "$pyproject_version" != "$init_version" ]; then
        print_status "WARN" "Version mismatch: pyproject.toml ($pyproject_version) != __init__.py ($init_version)"
        mismatches=$((mismatches + 1))
    else
        print_status "PASS" "__init__.py version synchronized: $init_version"
    fi

    if [ "$pyproject_version" != "$cli_version" ]; then
        print_status "WARN" "Version mismatch: pyproject.toml ($pyproject_version) != cli.py ($cli_version)"
        mismatches=$((mismatches + 1))
    else
        print_status "PASS" "CLI version synchronized: $cli_version"
    fi

    if [ "$readme_version" = "none" ]; then
        print_status "WARN" "README.md version not found (regex pattern may be incorrect)"
        mismatches=$((mismatches + 1))
    elif [ "$pyproject_version" != "$readme_version" ]; then
        print_status "WARN" "Version mismatch: pyproject.toml ($pyproject_version) != README.md ($readme_version)"
        mismatches=$((mismatches + 1))
    else
        print_status "PASS" "README.md version synchronized: $readme_version"
    fi

    if [ $mismatches -eq 0 ]; then
        print_status "PASS" "All version files are synchronized"
    else
        print_status "WARN" "Found $mismatches version synchronization issue(s)"
    fi

    return $mismatches
}

# Run quality checks (linting + formatting + tests)
run_quality_checks() {
    local auto_fix=${1:-false}
    local python_cmd=$(get_python_cmd)
    local python_exec=$(get_python_exec)

    print_status "INFO" "Checking Python environment..."
    check_python_env

    # Check if dependencies are available
    local env=$(detect_python_env)
    if [ "$env" = "system" ]; then
        print_status "WARN" "Using system Python - ensure dependencies are installed"
    fi

    # Linting
    print_status "INFO" "Running linting..."
    if [ "$auto_fix" = true ]; then
        $python_cmd ruff check src/ --fix
    else
        $python_cmd ruff check src/
    fi

    if [ $? -ne 0 ]; then
        print_status "FAIL" "Linting failed"
        return 1
    fi

    # Formatting
    print_status "INFO" "Checking code formatting..."
    if $python_cmd black --check src/; then
        print_status "PASS" "Code formatting is correct"
    else
        if [ "$auto_fix" = true ]; then
            print_status "AUTO" "Auto-formatting code..."
            $python_cmd black src/
        else
            print_status "FAIL" "Code formatting check failed (use --fix to auto-format)"
            return 1
        fi
    fi

    # Tests
    print_status "INFO" "Running tests..."
    if $python_cmd pytest -v; then
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

# CHANGELOG Management Functions

# Function to extract [Unreleased] section content

# Function to recover CHANGELOG structure when corrupted
recover_changelog_structure() {
    local changelog_file="CHANGELOG.md"
    local temp_file=$(mktemp)

    echo "🔧 Recovering CHANGELOG structure..."

    # Create proper Keep a Changelog structure
    cat > "$temp_file" << 'EOF'
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [Unreleased]

EOF

    # Preserve existing version sections if they exist
    if grep -q "^## \[[0-9]" "$changelog_file"; then
        echo "" >> "$temp_file"
        # Extract all version sections
        grep -A 1000 "^## \[[0-9]" "$changelog_file" >> "$temp_file" 2>/dev/null || true
    else
        echo "# No previous versions found - starting fresh" >> "$temp_file"
    fi

    # Replace original file
    mv "$temp_file" "$changelog_file"
    echo "✅ CHANGELOG structure recovered successfully"
}

# Commitizen wrapper functions
commitizen_bump_version() {
    local bump_type="$1"

    echo "🚀 Using Commitizen for version bump: $bump_type"

    # Run commitizen bump
    if cz bump --yes --changelog --increment "$bump_type"; then
        echo "✅ Commitizen version bump completed successfully"
        return 0
    else
        echo "❌ Commitizen version bump failed"
        return 1
    fi
}

commitizen_check_commits() {
    echo "🔍 Validating commits with Commitizen..."

    if cz check --rev-range HEAD~10..HEAD; then
        echo "✅ All commits follow conventional commit format"
        return 0
    else
        echo "⚠️  Some commits don't follow conventional commit format"
        echo "   Consider using 'cz commit' for future commits"
        return 1
    fi
}

commitizen_commit() {
    echo "📝 Using Commitizen for commit creation..."

    if cz commit; then
        echo "✅ Commitizen commit created successfully"
        return 0
    else
        echo "❌ Commitizen commit failed"
        return 1
    fi
}

