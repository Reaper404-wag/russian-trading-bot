#!/bin/bash

# Integration Test Runner Script for Russian Trading System
# Task 12.3: Comprehensive integration testing automation

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
CONFIG_FILE="integration_test_config.json"
LOG_FILE="integration_test_run.log"
PYTHON_CMD="python3"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check Python
    if ! command -v $PYTHON_CMD &> /dev/null; then
        print_error "Python 3 is not installed or not in PATH"
        exit 1
    fi
    
    # Check pytest
    if ! $PYTHON_CMD -m pytest --version &> /dev/null; then
        print_error "pytest is not installed. Install with: pip install pytest"
        exit 1
    fi
    
    # Check psutil for system monitoring
    if ! $PYTHON_CMD -c "import psutil" &> /dev/null; then
        print_warning "psutil not installed. System monitoring will be limited."
        print_status "Install with: pip install psutil"
    fi
    
    # Check if test files exist
    if [ ! -f "test_integration_comprehensive_workflow.py" ]; then
        print_error "Integration test file not found: test_integration_comprehensive_workflow.py"
        exit 1
    fi
    
    if [ ! -f "integration_test_runner.py" ]; then
        print_error "Integration test runner not found: integration_test_runner.py"
        exit 1
    fi
    
    print_success "Prerequisites check passed"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help              Show this help message"
    echo "  -c, --config FILE       Use custom configuration file (default: $CONFIG_FILE)"
    echo "  -l, --log FILE          Log file path (default: $LOG_FILE)"
    echo "  --continuous            Run tests continuously"
    echo "  --interval MINUTES      Interval for continuous mode (default: 120)"
    echo "  --max-runs NUMBER       Maximum runs in continuous mode"
    echo "  --fail-fast             Stop on first critical failure"
    echo "  --parallel              Run non-resource-intensive tests in parallel"
    echo "  --stress-only           Run only stress tests"
    echo "  --critical-only         Run only critical tests"
    echo "  --report-only           Generate report from existing results"
    echo "  --quick                 Run quick test suite (reduced timeouts)"
    echo "  --verbose               Enable verbose output"
    echo ""
    echo "Examples:"
    echo "  $0                      # Run all integration tests"
    echo "  $0 --critical-only      # Run only critical tests"
    echo "  $0 --stress-only        # Run only stress tests"
    echo "  $0 --continuous         # Run continuously every 2 hours"
    echo "  $0 --quick --parallel   # Quick parallel run"
}

# Function to run integration tests
run_integration_tests() {
    local args=()
    
    # Add configuration file if it exists
    if [ -f "$CONFIG_FILE" ]; then
        args+=("--config" "$CONFIG_FILE")
    fi
    
    # Add other arguments
    for arg in "$@"; do
        args+=("$arg")
    done
    
    print_status "Starting integration tests with arguments: ${args[*]}"
    
    # Run the integration test runner
    $PYTHON_CMD integration_test_runner.py "${args[@]}" 2>&1 | tee "$LOG_FILE"
    
    local exit_code=${PIPESTATUS[0]}
    
    if [ $exit_code -eq 0 ]; then
        print_success "Integration tests completed successfully"
    else
        print_error "Integration tests failed with exit code $exit_code"
        print_status "Check log file: $LOG_FILE"
    fi
    
    return $exit_code
}

# Function to setup test environment
setup_environment() {
    print_status "Setting up test environment..."
    
    # Create logs directory if it doesn't exist
    mkdir -p logs
    
    # Set environment variables for integration tests
    export INTEGRATION_TEST_MODE=1
    export PYTHONPATH="${PYTHONPATH}:$(pwd)/../.."
    
    # Create temporary directories for test data
    mkdir -p temp_test_data
    
    print_success "Test environment setup complete"
}

# Function to cleanup after tests
cleanup_environment() {
    print_status "Cleaning up test environment..."
    
    # Remove temporary test data
    rm -rf temp_test_data
    
    # Archive old log files
    if [ -f "$LOG_FILE" ]; then
        timestamp=$(date +"%Y%m%d_%H%M%S")
        mv "$LOG_FILE" "logs/integration_test_${timestamp}.log"
        print_status "Log file archived to logs/integration_test_${timestamp}.log"
    fi
    
    print_success "Cleanup complete"
}

# Function to generate summary report
generate_summary() {
    print_status "Generating test summary..."
    
    if [ -f "$LOG_FILE" ]; then
        echo ""
        echo "=== INTEGRATION TEST SUMMARY ==="
        
        # Extract key metrics from log
        local total_tests=$(grep -c "PASSED\|FAILED" "$LOG_FILE" 2>/dev/null || echo "0")
        local passed_tests=$(grep -c "PASSED" "$LOG_FILE" 2>/dev/null || echo "0")
        local failed_tests=$(grep -c "FAILED" "$LOG_FILE" 2>/dev/null || echo "0")
        
        echo "Total Tests: $total_tests"
        echo "Passed: $passed_tests"
        echo "Failed: $failed_tests"
        
        if [ "$total_tests" -gt 0 ]; then
            local success_rate=$((passed_tests * 100 / total_tests))
            echo "Success Rate: ${success_rate}%"
        fi
        
        # Show any critical failures
        if grep -q "CRITICAL FAILURE" "$LOG_FILE" 2>/dev/null; then
            echo ""
            echo "CRITICAL FAILURES DETECTED:"
            grep "CRITICAL FAILURE" "$LOG_FILE" || true
        fi
        
        echo "=== END SUMMARY ==="
        echo ""
    fi
}

# Main script logic
main() {
    local continuous=false
    local interval=120
    local max_runs=""
    local fail_fast=false
    local parallel=false
    local stress_only=false
    local critical_only=false
    local report_only=false
    local quick=false
    local verbose=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -c|--config)
                CONFIG_FILE="$2"
                shift 2
                ;;
            -l|--log)
                LOG_FILE="$2"
                shift 2
                ;;
            --continuous)
                continuous=true
                shift
                ;;
            --interval)
                interval="$2"
                shift 2
                ;;
            --max-runs)
                max_runs="$2"
                shift 2
                ;;
            --fail-fast)
                fail_fast=true
                shift
                ;;
            --parallel)
                parallel=true
                shift
                ;;
            --stress-only)
                stress_only=true
                shift
                ;;
            --critical-only)
                critical_only=true
                shift
                ;;
            --report-only)
                report_only=true
                shift
                ;;
            --quick)
                quick=true
                shift
                ;;
            --verbose)
                verbose=true
                shift
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Check prerequisites
    check_prerequisites
    
    # Setup environment
    setup_environment
    
    # Prepare arguments for Python script
    local python_args=()
    
    if [ "$continuous" = true ]; then
        python_args+=("--continuous")
        python_args+=("--interval" "$interval")
        if [ -n "$max_runs" ]; then
            python_args+=("--max-runs" "$max_runs")
        fi
    fi
    
    if [ "$fail_fast" = true ]; then
        python_args+=("--fail-fast")
    fi
    
    if [ "$parallel" = true ]; then
        python_args+=("--parallel")
    fi
    
    if [ "$stress_only" = true ]; then
        python_args+=("--stress-only")
    fi
    
    if [ "$critical_only" = true ]; then
        python_args+=("--critical-only")
    fi
    
    if [ "$report_only" = true ]; then
        python_args+=("--report-only")
    fi
    
    # Set up trap for cleanup
    trap cleanup_environment EXIT
    
    # Run the tests
    print_status "Starting Russian Trading System Integration Tests"
    print_status "Configuration: $CONFIG_FILE"
    print_status "Log file: $LOG_FILE"
    
    if run_integration_tests "${python_args[@]}"; then
        generate_summary
        print_success "Integration test run completed successfully"
        exit 0
    else
        generate_summary
        print_error "Integration test run failed"
        exit 1
    fi
}

# Run main function with all arguments
main "$@"