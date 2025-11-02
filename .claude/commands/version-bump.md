# Version Bump Command

Create a new version bump for the project following the guidelines in DEVELOPER.md. This command provides an interactive version bump process.

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
# Run pre-release checks as specified in DEVELOPER.md
echo "🔍 Running pre-release checks..."
if command -v make >/dev/null 2>&1; then
    make check
    if [ $? -ne 0 ]; then
        echo "❌ Pre-release checks failed. Please fix issues before version bump."
        exit 1
    fi
    echo "✅ Pre-release checks passed"
else
    echo "⚠️  Make not available, skipping pre-release checks"
fi
```

## Version Bump Selection

Now let's determine what type of version bump to perform:

$ARGUMENTS

If no arguments are provided, present an interactive selection:

```bash
BUMP_TYPE=""

# Check if argument was provided
if [ -n "$1" ] && [[ "$1" =~ ^(patch|minor|major)$ ]]; then
    BUMP_TYPE="$1"
    echo "🎯 Using provided bump type: $BUMP_TYPE"
else
    # Interactive selection
    echo ""
    echo "🎯 Please select version bump type:"
    echo ""
    echo "1) patch - Bug fixes and minor changes"
    echo "   Example: $current_version → $(echo $current_version | awk -F. '{$NF = $NF + 1; print $0}' OFS=".")"
    echo ""
    echo "2) minor - New features, backward compatible"
    echo "   Example: $current_version → $(echo $current_version | awk -F. '{$2 = $2 + 1; $3 = 0; print $0}' OFS=".")"
    echo ""
    echo "3) major - Breaking changes"
    echo "   Example: $current_version → $(echo $current_version | awk -F. '{$1 = $1 + 1; $2 = 0; $3 = 0; print $0}' OFS=".")"
    echo ""

    while true; do
        read -p "Enter choice (1-3): " choice
        case $choice in
            1) BUMP_TYPE="patch"; break ;;
            2) BUMP_TYPE="minor"; break ;;
            3) BUMP_TYPE="major"; break ;;
            *) echo "❌ Invalid choice. Please enter 1, 2, or 3." ;;
        esac
    done
fi

echo ""
echo "✅ Selected bump type: $BUMP_TYPE"
```

## Calculate New Version

```bash
# Calculate new version based on current version and bump type
IFS='.' read -r major minor patch <<< "$current_version"

case $BUMP_TYPE in
    "patch")
        NEW_PATCH=$((patch + 1))
        NEW_VERSION="$major.$minor.$NEW_PATCH"
        ;;
    "minor")
        NEW_MINOR=$((minor + 1))
        NEW_VERSION="$major.$NEW_MINOR.0"
        ;;
    "major")
        NEW_MAJOR=$((major + 1))
        NEW_VERSION="$NEW_MAJOR.0.0"
        ;;
    *)
        echo "❌ Invalid bump type"
        exit 1
        ;;
esac

echo "📊 Version change: $current_version → $NEW_VERSION"
echo ""
```

## User Confirmation

```bash
# Get user confirmation before proceeding
read -p "🚀 Proceed with version bump to $NEW_VERSION? (y/N): " confirm
if [[ ! $confirm =~ ^[Yy]$ ]]; then
    echo "❌ Version bump cancelled."
    exit 0
fi

echo ""
echo "🔄 Starting version bump process..."
```

## Execute Version Bump

```bash
# Use project's release script if available
if [ -f "scripts/release.sh" ]; then
    echo "📜 Using project release script..."
    ./scripts/release.sh $BUMP_TYPE
    EXIT_CODE=$?
else
    echo "📝 Manual version update required..."

    # Update pyproject.toml
    sed -i '' "s/^version = \"$current_version\"/version = \"$NEW_VERSION\"/" pyproject.toml

    # Update src/reticulum/__init__.py
    sed -i '' "s/__version__ = \"$current_version\"/__version__ = \"$NEW_VERSION\"/" src/reticulum/__init__.py

    echo "✅ Updated pyproject.toml to version $NEW_VERSION"
    echo "✅ Updated src/reticulum/__init__.py to version $NEW_VERSION"

    EXIT_CODE=0
fi

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "🎉 Version bump completed successfully!"
    echo "📦 New version: $NEW_VERSION"
    echo ""
    echo "📋 Next steps:"
    echo "   1. Verify all version files are synchronized: make release-sync"
    echo "   2. Run tests: make test-all"
    echo "   3. Consider creating a git tag: git tag v$NEW_VERSION"
    echo "   4. Update CHANGELOG.md with changes"
    echo "   5. Commit the version changes"
else
    echo "❌ Version bump failed with exit code $EXIT_CODE"
    exit $EXIT_CODE
fi
```