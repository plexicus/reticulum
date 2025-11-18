#!/bin/bash

# Intelligent Commit and Push
# Creates commits in English and optionally pushes to remote

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"

# Function to display usage
show_usage() {
    echo "Intelligent Commit and Push"
    echo "==========================="
    echo ""
    echo "Usage: $0 [COMMIT_MESSAGE] [--push|--no-push]"
    echo ""
    echo "Commands:"
    echo "  COMMIT_MESSAGE  - Commit message (optional, will ask if not provided)"
    echo "  --push          - Push to remote after commit"
    echo "  --no-push       - Don't push to remote (default)"
    echo ""
    echo "Examples:"
    echo "  $0 \"Implement user authentication\""
    echo "  $0 \"Fix security vulnerability\" --push"
    echo "  $0  # Interactive mode - asks for details"
    echo ""
    echo "Note: CHANGELOG management is handled by Commitizen (cz commit)"
}

# Function to validate English text
validate_english() {
    local text="$1"
    # Basic English validation - check for common non-English patterns
    if echo "$text" | grep -q -E '[áéíóúÁÉÍÓÚñÑ]'; then
        return 1
    fi
    return 0
}

# Main function
main() {
    local commit_message=""
    local push_remote=false

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --push)
                push_remote=true
                shift
                ;;
            --no-push)
                push_remote=false
                shift
                ;;
            --help|-h)
                show_usage
                exit 0
                ;;
            -*)
                echo "❌ Unknown option: $1"
                show_usage
                exit 1
                ;;
            *)
                if [[ -z "$commit_message" ]]; then
                    commit_message="$1"
                else
                    echo "❌ Too many arguments"
                    show_usage
                    exit 1
                fi
                shift
                ;;
        esac
    done

    # Check if we're in a git repository
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        echo "❌ Not a git repository"
        exit 1
    fi

    # Check for uncommitted changes
    if git diff --cached --quiet && git diff --quiet; then
        echo "ℹ️  No changes to commit"
        exit 0
    fi

    # Interactive mode if no commit message provided
    if [[ -z "$commit_message" ]]; then
        echo "🚀 Intelligent Commit and Push"
        echo "============================="
        echo ""

        # Show git status
        echo "📋 Current changes:"
        git status --short
        echo ""

        # Ask for commit message
        read -p "📝 Enter commit message: " commit_message

        if [[ -z "$commit_message" ]]; then
            echo "❌ Commit message is required"
            exit 1
        fi

        # Validate English
        if ! validate_english "$commit_message"; then
            echo "❌ Commit message must be in English"
            exit 1
        fi

        # Ask for push preference
        read -p "🚀 Push to remote? [y/N]: " push_input
        if [[ "$push_input" =~ ^[Yy]$ ]]; then
            push_remote=true
        else
            push_remote=false
        fi
    else
        # Validate English for provided commit message
        if ! validate_english "$commit_message"; then
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
    if git commit -m "$commit_message"; then
        echo "✅ Commit created successfully"
    else
        echo "❌ Failed to create commit"
        exit 1
    fi

    # Push if requested
    if [[ "$push_remote" == true ]]; then
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
}

# Run main function
main "$@"