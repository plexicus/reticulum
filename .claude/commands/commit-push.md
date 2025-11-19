# Intelligent Commit and Push

Creates a commit in English and optionally pushes to remote. Focuses on commit creation without CHANGELOG management.

## Environment Setup

First, let's ensure we're in the project root:

```bash
# Check project environment
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

# Check if we're in the project root
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Not in Reticulum project root directory"
    exit 1
fi

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "❌ Not a git repository"
    exit 1
fi

echo "✅ Project environment validated"
echo "📁 Project root: $PROJECT_ROOT"
echo ""
```

## Argument Parsing

Parse command line arguments:

```bash
COMMIT_MESSAGE=""
PUSH_REMOTE=true

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --push)
            PUSH_REMOTE=true
            shift
            ;;
        --no-push)
            PUSH_REMOTE=false
            shift
            ;;
        --help|-h)
            echo "Intelligent Commit and Push with CHANGELOG Automation"
            echo "===================================================="
            echo ""
            echo "Usage: /commit-push [COMMIT_MESSAGE] [--push|--no-push]"
            echo ""
            echo "Commands:"
            echo "  COMMIT_MESSAGE  - Commit message (optional, will ask if not provided)"
            echo "  --push          - Push to remote after commit"
            echo "  --no-push       - Don't push to remote (default)"
            echo ""
            echo "Examples:"
            echo "  /commit-push \"Implement user authentication\""
            echo "  /commit-push \"Fix security vulnerability\" --push"
            echo "  /commit-push  # Interactive mode - asks for details"
            exit 0
            ;;
        -*)
            echo "❌ Unknown option: $1"
            exit 1
            ;;
        *)
            if [[ -z "$COMMIT_MESSAGE" ]]; then
                COMMIT_MESSAGE="$1"
            else
                echo "❌ Too many arguments"
                exit 1
            fi
            shift
            ;;
    esac
done
```

## Function Definitions

Define helper functions:

```bash
# Function to validate English text
validate_english() {
    local text="$1"
    # Basic English validation - check for common non-English patterns
    if echo "$text" | grep -q -E '[áéíóúÁÉÍÓÚñÑ]'; then
        return 1
    fi
    return 0
}
```

## Main Execution Logic

Now let's execute the main logic:

```bash
echo "🚀 Intelligent Commit and Push"
echo "============================="
echo ""

# Check for uncommitted changes
if git diff --cached --quiet && git diff --quiet; then
    echo "ℹ️  No changes to commit"
    exit 0
fi

# Interactive mode if no commit message provided
if [[ -z "$COMMIT_MESSAGE" ]]; then
    # Show git status
    echo "📋 Current changes:"
    git status --short
    echo ""

    # Ask for commit message
    read -p "📝 Enter commit message: " COMMIT_MESSAGE

    if [[ -z "$COMMIT_MESSAGE" ]]; then
        echo "❌ Commit message is required"
        exit 1
    fi

    # Validate English
    if ! validate_english "$COMMIT_MESSAGE"; then
        echo "❌ Commit message must be in English"
        exit 1
    fi

    # Ask for push preference
    read -p "🚀 Push to remote? [y/N]: " push_input
    if [[ "$push_input" =~ ^[Yy]$ ]]; then
        PUSH_REMOTE=true
    else
        PUSH_REMOTE=false
    fi
else
    # Validate English for provided commit message
    if ! validate_english "$COMMIT_MESSAGE"; then
        echo "❌ Commit message must be in English"
        exit 1
    fi
fi

# Skip CHANGELOG analysis (now handled by Commitizen)
echo ""
echo "ℹ️  CHANGELOG management is now handled by Commitizen"
echo "   Use 'cz commit' for conventional commits with automatic CHANGELOG updates"

# Stage all changes
echo ""
echo "📦 Staging changes..."
git add .

# Create commit
echo "💾 Creating commit..."
if git commit -m "$COMMIT_MESSAGE"; then
    echo "✅ Commit created successfully"
else
    echo "❌ Failed to create commit"
    exit 1
fi

# Push if requested
if [[ "$PUSH_REMOTE" == true ]]; then
    echo ""
    echo "🚀 Pushing to remote..."
    if git push; then
        echo "✅ Successfully pushed to remote"
    else
        echo "❌ Failed to push to remote"
        exit 1
    fi
else
    echo ""
    echo "ℹ️  Changes committed but not pushed. Use 'git push' to push to remote."
fi

echo ""
echo "🎉 Commit process completed successfully!"
```