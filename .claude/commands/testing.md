# Testing Command

Run comprehensive tests for the Reticulum project with interactive category selection and detailed result summaries.

## Environment Setup

First, let's ensure we're in the project root and dependencies are available:

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

# Check if Poetry is available
if ! command -v poetry >/dev/null 2>&1; then
    echo "❌ Poetry not found. Please install Poetry first."
    exit 1
fi

# Check if dependencies are installed
if [ ! -d ".venv" ] && [ ! -f "poetry.lock" ]; then
    echo "⚠️  Dependencies may not be installed. Run 'poetry install' if needed."
fi

echo "✅ Project environment validated"
echo "📁 Project root: $PROJECT_ROOT"
echo ""
```

## Current Status

Let's check the current git status and project state:

```bash
# Show current git status
current_branch=$(git branch --show-current)
commit_hash=$(git rev-parse --short HEAD)
modified_files=$(git status --short | wc -l)

echo "📊 Current Project Status:"
echo "=========================="
echo "🌿 Branch: $current_branch"
echo "🔗 Commit: $commit_hash"
echo "📝 Modified files: $modified_files"

if [ "$modified_files" -gt 0 ]; then
    echo ""
    echo "⚠️  You have uncommitted changes:"
    git status --short
    echo ""
    echo "💡 Consider committing changes before extensive testing:"
    echo "   git add . && git commit -m 'your message'"
fi

echo ""
```

## Test Category Selection

Now let's choose what type of testing to perform:

```bash
# Parse arguments
AUTO_FIX=false
TEST_CATEGORY=""

# Check for auto-fix flag
if [ "$1" = "--fix" ]; then
    AUTO_FIX=true
    shift
fi

# Check if category was provided as argument
if [ -n "$1" ]; then
    case $1 in
        "quick"|"dev-check") TEST_CATEGORY="quick" ;;
        "basic"|"test") TEST_CATEGORY="basic" ;;
        "advanced"|"advanced-tests") TEST_CATEGORY="advanced" ;;
        "complete"|"test-all") TEST_CATEGORY="complete" ;;
        "custom") TEST_CATEGORY="custom" ;;
        *) TEST_CATEGORY="" ;;
    esac
fi

# If no category provided, show interactive menu
if [ -z "$TEST_CATEGORY" ]; then
    echo "🧪 Reticulum Testing Menu"
    echo "========================"
    echo ""
    echo "Choose a testing category:"
    echo ""
    echo "1. 🚀 Quick Check (make dev-check)"
    echo "   → Daily development quality checks (linting + formatting + tests)"
    echo "   → Best for: Pre-commit validation, daily development"
    echo ""
    echo "2. 🔍 Basic Tests (make test)"
    echo "   → Core functionality validation only"
    echo "   → Best for: Quick verification, basic functionality testing"
    echo ""
    echo "3. 🧪 Advanced Scenarios (make advanced-tests)"
    echo "   → Complex integration testing against advanced test repository"
    echo "   → Best for: Performance testing, complex scenarios, edge cases"
    echo ""
    echo "4. ✅ Complete Suite (make test-all)"
    echo "   → Full test suite (basic + advanced)"
    echo "   → Best for: Pre-release validation, comprehensive testing"
    echo ""
    echo "5. 🎯 Custom Selection"
    echo "   → Interactive pytest marker selection"
    echo "   → Best for: Specific test categories, targeted testing"
    echo ""

    read -p "Enter choice (1-5) or press Enter for Quick Check: " choice

    case $choice in
        "1") TEST_CATEGORY="quick" ;;
        "2") TEST_CATEGORY="basic" ;;
        "3") TEST_CATEGORY="advanced" ;;
        "4") TEST_CATEGORY="complete" ;;
        "5") TEST_CATEGORY="custom" ;;
        *) TEST_CATEGORY="quick" ;;
    esac
fi

# Handle auto-fix mode
if [ "$AUTO_FIX" = true ]; then
    echo ""
    echo "🔧 Auto-fix mode enabled"
fi

echo ""
echo "✅ Selected test category: $TEST_CATEGORY"
echo ""
```

## Test Execution

Now let's execute the selected test category:

```bash
# Start timer
START_TIME=$(date +%s)

case $TEST_CATEGORY in
    "quick")
        echo "🚀 Running Quick Check (make dev-check)..."
        echo "=========================================="
        echo ""
        if [ "$AUTO_FIX" = true ]; then
            make dev-check-fix
        else
            make dev-check
        fi
        TEST_RESULT=$?
        ;;

    "basic")
        echo "🔍 Running Basic Tests (make test)..."
        echo "===================================="
        echo ""
        make test
        TEST_RESULT=$?
        ;;

    "advanced")
        echo "🧪 Running Advanced Scenarios (make advanced-tests)..."
        echo "===================================================="
        echo ""
        make advanced-tests
        TEST_RESULT=$?
        ;;

    "complete")
        echo "✅ Running Complete Test Suite (make test-all)..."
        echo "================================================"
        echo ""
        make test-all
        TEST_RESULT=$?
        ;;

    "custom")
        echo "🎯 Custom Test Selection"
        echo "======================="
        echo ""
        echo "Available pytest markers:"
        echo "- advanced: Complex integration scenarios"
        echo "- performance: Performance benchmarks"
        echo "- edge_cases: Boundary conditions"
        echo "- integration: Component interaction testing"
        echo "- slow: Long-running tests"
        echo ""
        read -p "Enter marker(s) to run (comma-separated): " markers

        if [ -n "$markers" ]; then
            echo ""
            echo "Running tests with markers: $markers"
            poetry run pytest tests/test_advanced_scenarios.py -m "$markers" -v
            TEST_RESULT=$?
        else
            echo "❌ No markers selected. Running all advanced tests."
            make advanced-tests
            TEST_RESULT=$?
        fi
        ;;

    *)
        echo "❌ Invalid test category"
        exit 1
        ;;
esac

# Calculate execution time
END_TIME=$(date +%s)
EXECUTION_TIME=$((END_TIME - START_TIME))
```

## Result Summary

Let's generate a comprehensive test result summary:

```bash
# Create results directory
RESULTS_DIR="test-results/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RESULTS_DIR"

# Generate summary
SUMMARY_FILE="$RESULTS_DIR/summary.txt"
{
    echo "Reticulum Test Results Summary"
    echo "=============================="
    echo "Timestamp: $(date)"
    echo "Test Category: $TEST_CATEGORY"
    echo "Execution Time: ${EXECUTION_TIME}s"
    echo "Auto-fix: $AUTO_FIX"
    echo "Git Branch: $current_branch"
    echo "Git Commit: $commit_hash"
    echo "Modified Files: $modified_files"
    echo ""
    echo "Result: $(if [ $TEST_RESULT -eq 0 ]; then echo "✅ SUCCESS"; else echo "❌ FAILED"; fi)"
    echo ""
    echo "Performance Validation:"
    if [ $EXECUTION_TIME -lt 60 ]; then
        echo "✅ Execution time: ${EXECUTION_TIME}s (< 60s threshold)"
    else
        echo "⚠️  Execution time: ${EXECUTION_TIME}s (consider optimizing)"
    fi
} > "$SUMMARY_FILE"

echo ""
echo "📊 Test Results Summary"
echo "======================"
cat "$SUMMARY_FILE"

echo ""
echo "📁 Results archived to: $RESULTS_DIR/"

# Final status
if [ $TEST_RESULT -eq 0 ]; then
    echo ""
    echo "🎉 All tests completed successfully!"
    echo ""
    echo "💡 Next Steps:"
    case $TEST_CATEGORY in
        "quick")
            echo "   - Ready for development/commit"
            echo "   - Consider running 'make test-all' before release"
            ;;
        "basic")
            echo "   - Core functionality validated"
            echo "   - Run 'make advanced-tests' for complex scenarios"
            ;;
        "advanced")
            echo "   - Complex scenarios validated"
            echo "   - Performance benchmarks met"
            echo "   - Ready for release consideration"
            ;;
        "complete")
            echo "   - ✅ All tests passed"
            echo "   - ✅ Performance validated"
            echo "   - ✅ Ready for release"
            ;;
        "custom")
            echo "   - Custom test selection completed"
            echo "   - Review results for specific categories"
            ;;
    esac
else
    echo ""
    echo "❌ Some tests failed. Please review the output above."
    echo ""
    echo "🔧 Troubleshooting Steps:"
    echo "   1. Check test logs in $RESULTS_DIR/"
    echo "   2. Run individual test files to isolate issues"
    echo "   3. Verify dependencies: poetry install"
    echo "   4. Check for environment issues"
fi

echo ""
```