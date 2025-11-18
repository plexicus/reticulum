# Version Bump Command

Create a new version bump for the project following the guidelines in DEVELOPER.md. This command provides an interactive version bump process using the unified release system.

## Current Version Check

First, let's check the current version across all version files to ensure consistency:

```bash
# Check current version in pyproject.toml
current_version=$(grep -E '^version = "[0-9]+\.[0-9]+\.[0-9]+"' pyproject.toml | head -1 | sed 's/version = "//' | sed 's/"//')
echo "📦 Current version (pyproject.toml): $current_version"

# Check reticulum/__init__.py for consistency
init_version=$(grep -E '__version__ = "[0-9]+\.[0-9]+\.[0-9]+"' src/reticulum/__init__.py | head -1 | sed 's/__version__ = "//' | sed 's/"//')
echo "🐍 Init version (__init__.py): $init_version"

# Check if versions are synchronized
if [ "$current_version" != "$init_version" ]; then
    echo "⚠️  WARNING: Version files are out of sync!"
    echo "   Run 'make release-sync' to synchronize versions first."
    exit 1
fi

echo "✅ All version files are synchronized"
```

## Pre-Bump Checks

Before proceeding with version bump, let's run the project's quality checks:

```bash
# Run quality checks as specified in DEVELOPER.md
echo "🔍 Running quality checks..."
if command -v make >/dev/null 2>&1; then
    make check
    if [ $? -ne 0 ]; then
        echo "❌ Quality checks failed. Please fix issues before version bump."
        exit 1
    fi
    echo "✅ Quality checks passed"
else
    echo "⚠️  Make not available, skipping quality checks"
fi
```

## Version Bump Selection

Now let's determine what type of version bump to perform:

$ARGUMENTS

If no arguments are provided, default to minor release:

```bash
BUMP_TYPE=""

# Check if argument was provided
if [ -n "$1" ] && [[ "$1" =~ ^(patch|minor|major)$ ]]; then
    BUMP_TYPE="$1"
    echo "🎯 Using provided bump type: $BUMP_TYPE"
else
    # Default to minor release unless specifically requested otherwise
    echo ""
    echo "🎯 Defaulting to minor release (new features, backward compatible)"
    echo "   Example: $current_version → $(echo $current_version | awk -F. '{$2 = $2 + 1; $3 = 0; print $0}' OFS=".")"
    echo ""
    echo "📝 Note: In most cases, use minor releases unless specifically requested"
    echo "   - patch: Bug fixes and minor changes"
    echo "   - minor: New features, backward compatible (DEFAULT)"
    echo "   - major: Breaking changes"
    echo ""

    # Optional: Allow override via prompt
    read -p "Press Enter to continue with minor release, or type 'patch' or 'major': " override
    case $override in
        "patch") BUMP_TYPE="patch" ;;
        "major") BUMP_TYPE="major" ;;
        *) BUMP_TYPE="minor" ;;
    esac
fi

echo ""
echo "✅ Selected bump type: $BUMP_TYPE"
```

## User Confirmation

```bash
# Get user confirmation before proceeding
read -p "🚀 Proceed with version bump? (y/N): " confirm
if [[ ! $confirm =~ ^[Yy]$ ]]; then
    echo "❌ Version bump cancelled."
    exit 0
fi

echo ""
echo "🔄 Starting version bump process..."
echo "ℹ️  Using Commitizen for automated version management and CHANGELOG updates"
```

## Execute Version Bump

```bash
# Use project's release script
if [ -f "scripts/release.sh" ]; then
    echo "📜 Using project release script..."
    ./scripts/release.sh $BUMP_TYPE
    EXIT_CODE=$?
else
    echo "❌ Release script not found: scripts/release.sh"
    echo "   Please ensure the release automation system is available"
    exit 1
fi

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "🎉 Version bump completed successfully!"
    echo ""
    echo "✅ Git tag created automatically"
    echo "✅ GitHub Actions release workflow triggered"
    echo ""
    echo "📋 Next steps:"
    echo "   • Monitor GitHub Actions: https://github.com/plexicus/reticulum/actions"
    echo "   • Check PyPI for new release: https://pypi.org/project/reticulum/"
else
    echo "❌ Version bump failed with exit code $EXIT_CODE"
    exit $EXIT_CODE
fi
```