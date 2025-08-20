#!/bin/bash

# Advanced Test Runner for Reticulum Scanner
# This script runs comprehensive tests against the advanced test repository

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ADVANCED_TEST_DIR="$PROJECT_ROOT/tests/advanced-test-repo"
TEST_RESULTS_DIR="$PROJECT_ROOT/test-results"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Header
echo "🔍 RETICULUM ADVANCED TEST RUNNER"
echo "=================================="
echo "Timestamp: $TIMESTAMP"
echo "Project Root: $PROJECT_ROOT"
echo "Advanced Test Dir: $ADVANCED_TEST_DIR"
echo ""

# Check if we're in the right directory
if [[ ! -f "$PROJECT_ROOT/pyproject.toml" ]]; then
    log_error "Not in project root directory. Please run from the project root."
    exit 1
fi

# Check if advanced test repository exists
if [[ ! -d "$ADVANCED_TEST_DIR" ]]; then
    log_error "Advanced test repository not found at $ADVANCED_TEST_DIR"
    log_info "Please ensure the advanced-test-repo is copied to tests/advanced-test-repo"
    exit 1
fi

# Create test results directory
mkdir -p "$TEST_RESULTS_DIR"

# Function to run tests with timing
run_tests() {
    local test_name="$1"
    local test_command="$2"
    local output_file="$3"
    
    log_info "Running $test_name..."
    echo "Test: $test_name" >> "$output_file"
    echo "Command: $test_command" >> "$output_file"
    echo "Timestamp: $(date)" >> "$output_file"
    echo "----------------------------------------" >> "$output_file"
    
    local start_time=$(date +%s.%N)
    
    if eval "$test_command" >> "$output_file" 2>&1; then
        local end_time=$(date +%s.%N)
        local duration=$(echo "$end_time - $start_time" | bc -l)
        log_success "$test_name completed in ${duration}s"
        echo "Result: PASSED (${duration}s)" >> "$output_file"
        return 0
    else
        local end_time=$(date +%s.%N)
        local duration=$(echo "$end_time - $start_time" | bc -l)
        log_error "$test_name failed after ${duration}s"
        echo "Result: FAILED (${duration}s)" >> "$output_file"
        return 1
    fi
}

# Main test execution
log_info "Starting advanced test suite..."

# Test results file
TEST_LOG="$TEST_RESULTS_DIR/advanced-tests_$TIMESTAMP.log"
SUMMARY_LOG="$TEST_RESULTS_DIR/advanced-tests_$TIMESTAMP_summary.log"

# Initialize summary log
echo "RETICULUM ADVANCED TEST SUMMARY" > "$SUMMARY_LOG"
echo "===============================" >> "$SUMMARY_LOG"
echo "Timestamp: $TIMESTAMP" >> "$SUMMARY_LOG"
echo "" >> "$SUMMARY_LOG"

# Test counter
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Test 1: Basic repository structure validation
TOTAL_TESTS=$((TOTAL_TESTS + 1))
if run_tests "Repository Structure Validation" \
    "cd '$ADVANCED_TEST_DIR' && find . -type f -name '*.yaml' | wc -l" \
    "$TEST_LOG"; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
    echo "✅ Repository Structure Validation: PASSED" >> "$SUMMARY_LOG"
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
    echo "❌ Repository Structure Validation: FAILED" >> "$SUMMARY_LOG"
fi

# Test 2: Chart count validation
TOTAL_TESTS=$((TOTAL_TESTS + 1))
if run_tests "Chart Count Validation" \
    "cd '$ADVANCED_TEST_DIR/charts' && ls -1 | wc -l" \
    "$TEST_LOG"; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
    echo "✅ Chart Count Validation: PASSED" >> "$SUMMARY_LOG"
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
    echo "❌ Chart Count Validation: FAILED" >> "$SUMMARY_LOG"
fi

# Test 3: Scanner execution test
TOTAL_TESTS=$((TOTAL_TESTS + 1))
if run_tests "Scanner Execution Test" \
    "cd '$PROJECT_ROOT' && poetry run python -m reticulum '$ADVANCED_TEST_DIR' --json > '$TEST_RESULTS_DIR/scan_results_$TIMESTAMP.json'" \
    "$TEST_LOG"; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
    echo "✅ Scanner Execution Test: PASSED" >> "$SUMMARY_LOG"
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
    echo "❌ Scanner Execution Test: FAILED" >> "$SUMMARY_LOG"
fi

# Test 4: Results validation
TOTAL_TESTS=$((TOTAL_TESTS + 1))
if [[ -f "$TEST_RESULTS_DIR/scan_results_$TIMESTAMP.json" ]]; then
    if run_tests "Results Validation" \
        "cd '$ADVANCED_TEST_DIR' && poetry run python validate_results.py '$TEST_RESULTS_DIR/scan_results_$TIMESTAMP.json'" \
        "$TEST_LOG"; then
        PASSED_TESTS=$((PASSED_TESTS + 1))
        echo "✅ Results Validation: PASSED" >> "$SUMMARY_LOG"
    else
        FAILED_TESTS=$((FAILED_TESTS + 1))
        echo "❌ Results Validation: FAILED" >> "$SUMMARY_LOG"
    fi
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
    echo "❌ Results Validation: FAILED (no scan results file)" >> "$SUMMARY_LOG"
fi

# Test 5: Performance benchmark
TOTAL_TESTS=$((TOTAL_TESTS + 1))
if [[ -f "$TEST_RESULTS_DIR/scan_results_$TIMESTAMP.json" ]]; then
    SCAN_TIME=$(grep "Scan Time:" "$TEST_LOG" | tail -1 | grep -o '[0-9.]*s' | grep -o '[0-9.]*' || echo "0")
    if (( $(echo "$SCAN_TIME < 30" | bc -l) )); then
        PASSED_TESTS=$((PASSED_TESTS + 1))
        echo "✅ Performance Benchmark: PASSED (${SCAN_TIME}s < 30s)" >> "$SUMMARY_LOG"
    else
        FAILED_TESTS=$((FAILED_TESTS + 1))
        echo "❌ Performance Benchmark: FAILED (${SCAN_TIME}s >= 30s)" >> "$SUMMARY_LOG"
    fi
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
    echo "❌ Performance Benchmark: FAILED (no scan results file)" >> "$SUMMARY_LOG"
fi

# Test 6: Pytest integration tests
TOTAL_TESTS=$((TOTAL_TESTS + 1))
if run_tests "Pytest Integration Tests" \
    "cd '$PROJECT_ROOT' && poetry run pytest tests/test_advanced_scenarios.py -v" \
    "$TEST_LOG"; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
    echo "✅ Pytest Integration Tests: PASSED" >> "$SUMMARY_LOG"
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
    echo "❌ Pytest Integration Tests: FAILED" >> "$SUMMARY_LOG"
fi

# Summary
echo "" >> "$SUMMARY_LOG"
echo "TEST SUMMARY" >> "$SUMMARY_LOG"
echo "============" >> "$SUMMARY_LOG"
echo "Total Tests: $TOTAL_TESTS" >> "$SUMMARY_LOG"
echo "Passed: $PASSED_TESTS" >> "$SUMMARY_LOG"
echo "Failed: $FAILED_TESTS" >> "$SUMMARY_LOG"
echo "Success Rate: $((PASSED_TESTS * 100 / TOTAL_TESTS))%" >> "$SUMMARY_LOG"

# Print summary to console
echo ""
echo "📊 TEST EXECUTION SUMMARY"
echo "========================="
echo "Total Tests: $TOTAL_TESTS"
echo "Passed: $PASSED_TESTS"
echo "Failed: $FAILED_TESTS"
echo "Success Rate: $((PASSED_TESTS * 100 / TOTAL_TESTS))%"

# Final result
if [[ $FAILED_TESTS -eq 0 ]]; then
    log_success "All advanced tests passed! 🎉"
    echo "🎉 ALL TESTS PASSED!" >> "$SUMMARY_LOG"
    exit 0
else
    log_error "$FAILED_TESTS test(s) failed. Check logs for details."
    echo "❌ $FAILED_TESTS TEST(S) FAILED" >> "$SUMMARY_LOG"
    exit 1
fi
