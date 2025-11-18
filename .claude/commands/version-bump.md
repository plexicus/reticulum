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

## CHANGELOG Management

Before executing the version bump, let's manage the CHANGELOG.md file:

```bash
echo "📝 Managing CHANGELOG.md..."

# Function to extract [Unreleased] section content
extract_unreleased_section() {
    local changelog_file="CHANGELOG.md"
    local in_unreleased=false
    local unreleased_content=""
    local current_category=""

    while IFS= read -r line; do
        if [[ "$line" == "## [Unreleased]" ]]; then
            in_unreleased=true
            continue
        elif [[ "$in_unreleased" == true && "$line" =~ ^##\ \[[0-9]+\.[0-9]+\.[0-9]+\] ]]; then
            # Reached next version section, stop extracting
            break
        elif [[ "$in_unreleased" == true ]]; then
            if [[ "$line" =~ ^###\ (Added|Changed|Fixed|Removed|Notes)$ ]]; then
                current_category="${BASH_REMATCH[1]}"
                unreleased_content+="$line\n"
            elif [[ -n "$current_category" && -n "$line" ]]; then
                unreleased_content+="$line\n"
            fi
        fi
    done < "$changelog_file"

    echo "$unreleased_content"
}

# Function to update CHANGELOG with new version section
update_changelog_with_version() {
    local new_version="$1"
    local unreleased_content="$2"
    local changelog_file="CHANGELOG.md"
    local temp_file=$(mktemp)

    # Get current date in YYYY-MM-DD format
    local current_date=$(date +%Y-%m-%d)

    # Create new version section
    local new_version_section="## [$new_version] - $current_date\n\n"

    # Process unreleased content
    if [[ -n "$unreleased_content" ]]; then
        local in_category=false
        local current_category=""

        while IFS= read -r line; do
            if [[ "$line" =~ ^###\ (Added|Changed|Fixed|Removed|Notes)$ ]]; then
                if [[ "$in_category" == true ]]; then
                    new_version_section+="\n"
                fi
                current_category="${BASH_REMATCH[1]}"
                new_version_section+="$line\n"
                in_category=true
            elif [[ -n "$line" && "$in_category" == true ]]; then
                new_version_section+="$line\n"
            fi
        done <<< "$unreleased_content"
    else
        new_version_section+="### Added\n- No changes documented\n\n"
    fi

    # Read current CHANGELOG and restructure with [Unreleased] at top
    local in_header=true
    local header_lines=""
    local version_sections=""
    local in_unreleased=false

    while IFS= read -r line; do
        # Capture header lines (before first version section)
        if [[ "$in_header" == true && ! "$line" =~ ^##\ \[ ]]; then
            header_lines+="$line\n"
        elif [[ "$line" =~ ^##\ \[ ]]; then
            in_header=false
            # Skip [Unreleased] section - we'll create a fresh one at the top
            if [[ "$line" == "## [Unreleased]" ]]; then
                in_unreleased=true
                continue
            fi
            # Add version sections to the collection
            if [[ "$in_unreleased" == false ]]; then
                version_sections+="$line\n"
            fi
        elif [[ "$in_unreleased" == true ]]; then
            # Skip content of [Unreleased] section - we'll create a fresh one
            if [[ "$line" =~ ^##\ \[[0-9]+\.[0-9]+\.[0-9]+\] ]]; then
                in_unreleased=false
                version_sections+="$line\n"
            fi
        else
            version_sections+="$line\n"
        fi
    done < "$changelog_file"

    # Write the restructured CHANGELOG
    echo -n "$header_lines" >> "$temp_file"
    echo "## [Unreleased]" >> "$temp_file"
    echo "" >> "$temp_file"
    echo -n "$new_version_section" >> "$temp_file"
    echo -n "$version_sections" >> "$temp_file"

    # Replace original file
    mv "$temp_file" "$changelog_file"

    echo "✅ Updated CHANGELOG.md with version $new_version"
}

# Extract unreleased content
UNRELEASED_CONTENT=$(extract_unreleased_section)

if [[ -n "$UNRELEASED_CONTENT" ]]; then
    echo "📋 Found unreleased changes to move to version $NEW_VERSION"
else
    echo "⚠️  No unreleased changes found in CHANGELOG.md"
fi

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

    # Update CHANGELOG.md with new version section
    update_changelog_with_version "$NEW_VERSION" "$UNRELEASED_CONTENT"

    EXIT_CODE=0
fi

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "🎉 Version bump completed successfully!"
    echo "📦 New version: $NEW_VERSION"
    echo ""

    # Commit the version and CHANGELOG changes
    echo "💾 Committing version and CHANGELOG changes..."

    # Check if there are changes to commit
    if git diff --quiet && git diff --cached --quiet; then
        echo "⚠️  No changes to commit"
    else
        # Create commit message based on bump type and CHANGELOG content
        COMMIT_SUBJECT=""
        case $BUMP_TYPE in
            "patch") COMMIT_SUBJECT="fix" ;;
            "minor") COMMIT_SUBJECT="feat" ;;
            "major") COMMIT_SUBJECT="feat" ;;
            *) COMMIT_SUBJECT="chore" ;;
        esac

        # Check if there were actual changes in the unreleased section
        if [[ -n "$UNRELEASED_CONTENT" ]]; then
            CHANGELOG_SUMMARY=" with CHANGELOG updates"
        else
            CHANGELOG_SUMMARY=""
        fi

        COMMIT_MESSAGE="$COMMIT_SUBJECT: bump version to $NEW_VERSION$CHANGELOG_SUMMARY"

        # Stage all changes
        git add pyproject.toml src/reticulum/__init__.py CHANGELOG.md

        # Create commit
        if git commit -m "$COMMIT_MESSAGE"; then
            echo "✅ Changes committed successfully"
            echo "📝 Commit message: $COMMIT_MESSAGE"
        else
            echo "❌ Failed to commit changes"
        fi
    fi

    echo ""
    echo "📋 Next steps:"
    echo "   1. Verify all version files are synchronized: make release-sync"
    echo "   2. Run tests: make test-all"
    echo "   3. Consider creating a git tag: git tag v$NEW_VERSION"
    echo "   4. Push changes to remote if needed: git push"
else
    echo "❌ Version bump failed with exit code $EXIT_CODE"
    exit $EXIT_CODE
fi
```