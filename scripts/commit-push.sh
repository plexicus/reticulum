#!/bin/bash

# Intelligent Commit and Push with CHANGELOG Automation
# Automatically updates CHANGELOG.md with intelligent change detection

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"

# Function to display usage
show_usage() {
    echo "Intelligent Commit and Push with CHANGELOG Automation"
    echo "===================================================="
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

# Function to detect change categories
detect_changes() {
    local changes=""

    # Get git status
    local git_status=$(git status --porcelain)

    # Analyze changes
    while IFS= read -r line; do
        if [[ -n "$line" ]]; then
            local status="${line:0:2}"
            local file="${line:3}"

            case "$status" in
                "A "|"??")
                    if [[ "$file" == *.py ]]; then
                        changes+="- **Added**: New Python file: \`$file\`\n"
                    elif [[ "$file" == *.md ]]; then
                        changes+="- **Added**: New documentation: \`$file\`\n"
                    elif [[ "$file" == test* ]] || [[ "$file" == *test* ]]; then
                        changes+="- **Added**: New test: \`$file\`\n"
                    else
                        changes+="- **Added**: New file: \`$file\`\n"
                    fi
                    ;;
                "M ")
                    if [[ "$file" == *.py ]]; then
                        changes+="- **Changed**: Modified Python file: \`$file\`\n"
                    elif [[ "$file" == *.md ]]; then
                        changes+="- **Documentation**: Updated: \`$file\`\n"
                    elif [[ "$file" == test* ]] || [[ "$file" == *test* ]]; then
                        changes+="- **Tests**: Updated: \`$file\`\n"
                    else
                        changes+="- **Changed**: Modified: \`$file\`\n"
                    fi
                    ;;
                "D ")
                    changes+="- **Removed**: Deleted: \`$file\`\n"
                    ;;
            esac
        fi
    done <<< "$git_status"

    echo "$changes"
}

# Function to update CHANGELOG.md
update_changelog() {
    local commit_message="$1"
    local changes="$2"

    if [[ -z "$changes" ]]; then
        echo "No changes detected to add to CHANGELOG.md"
        return 0
    fi

    # Create temporary file
    local temp_file=$(mktemp)

    # Read current CHANGELOG.md and update [Unreleased] section
    local in_unreleased=false
    local unreleased_updated=false

    while IFS= read -r line; do
        if [[ "$line" == "## [Unreleased]" ]]; then
            in_unreleased=true
            echo "$line" >> "$temp_file"
            echo "" >> "$temp_file"
            echo "### Added" >> "$temp_file"
            echo "$changes" >> "$temp_file"
            unreleased_updated=true
        elif [[ "$in_unreleased" == true && "$line" =~ ^##\ \[.*\]$ ]]; then
            in_unreleased=false
            echo "" >> "$temp_file"
            echo "$line" >> "$temp_file"
        elif [[ "$in_unreleased" == false || "$unreleased_updated" == false ]]; then
            echo "$line" >> "$temp_file"
        fi
    done < "CHANGELOG.md"

    # If [Unreleased] section wasn't found, add it
    if [[ "$unreleased_updated" == false ]]; then
        echo "## [Unreleased]" >> "$temp_file"
        echo "" >> "$temp_file"
        echo "### Added" >> "$temp_file"
        echo "$changes" >> "$temp_file"
        echo "" >> "$temp_file"
    fi

    # Replace original file
    mv "$temp_file" "CHANGELOG.md"

    echo "✅ CHANGELOG.md updated with detected changes"
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

    # Detect changes for CHANGELOG
    echo ""
    echo "🔍 Analyzing changes for CHANGELOG.md..."
    local changes=$(detect_changes)

    if [[ -n "$changes" ]]; then
        echo "📝 Changes detected:"
        echo "$changes"
        echo ""

        # Ask for confirmation to update CHANGELOG
        read -p "✅ Update CHANGELOG.md with these changes? [Y/n]: " changelog_confirm
        if [[ "$changelog_confirm" =~ ^[Nn]$ ]]; then
            echo "ℹ️  Skipping CHANGELOG update"
        else
            update_changelog "$commit_message" "$changes"
        fi
    else
        echo "ℹ️  No changes detected for CHANGELOG.md"
    fi

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