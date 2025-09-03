@echo off
REM Integration Test Runner Script for Russian Trading System
REM Task 12.3: Comprehensive integration testing automation

setlocal enabledelayedexpansion

REM Default values
set CONFIG_FILE=integration_test_config.json
set LOG_FILE=integration_test_run.log
set PYTHON_CMD=python

REM Colors (Windows doesn't support colors in batch easily, so we'll use echo)
set "INFO_PREFIX=[INFO]"
set "SUCCESS_PREFIX=[SUCCESS]"
set "WARNING_PREFIX=[WARNING]"
set "ERROR_PREFIX=[ERROR]"

REM Function to print status messages
:print_status
echo %INFO_PREFIX% %~1
goto :eof

:print_success
echo %SUCCESS_PREFIX% %~1
goto :eof

:print_warning
echo %WARNING_PREFIX% %~1
goto :eof

:print_error
echo %ERROR_PREFIX% %~1
goto :eof

REM Function to check prerequisites
:check_prerequisites
call :print_status "Checking prerequisites..."

REM Check Python
%PYTHON_CMD% --version >nul 2>&1
if errorlevel 1 (
    call :print_error "Python is not installed or not in PATH"
    exit /b 1
)

REM Check pytest
%PYTHON_CMD% -m pytest --version >nul 2>&1
if errorlevel 1 (
    call :print_error "pytest is not installed. Install with: pip install pytest"
    exit /b 1
)

REM Check psutil for system monitoring
%PYTHON_CMD% -c "import psutil" >nul 2>&1
if errorlevel 1 (
    call :print_warning "psutil not installed. System monitoring will be limited."
    call :print_status "Install with: pip install psutil"
)

REM Check if test files exist
if not exist "test_integration_comprehensive_workflow.py" (
    call :print_error "Integration test file not found: test_integration_comprehensive_workflow.py"
    exit /b 1
)

if not exist "integration_test_runner.py" (
    call :print_error "Integration test runner not found: integration_test_runner.py"
    exit /b 1
)

call :print_success "Prerequisites check passed"
goto :eof

REM Function to show usage
:show_usage
echo Usage: %~nx0 [OPTIONS]
echo.
echo Options:
echo   -h, --help              Show this help message
echo   -c, --config FILE       Use custom configuration file (default: %CONFIG_FILE%)
echo   -l, --log FILE          Log file path (default: %LOG_FILE%)
echo   --continuous            Run tests continuously
echo   --interval MINUTES      Interval for continuous mode (default: 120)
echo   --max-runs NUMBER       Maximum runs in continuous mode
echo   --fail-fast             Stop on first critical failure
echo   --parallel              Run non-resource-intensive tests in parallel
echo   --stress-only           Run only stress tests
echo   --critical-only         Run only critical tests
echo   --report-only           Generate report from existing results
echo   --quick                 Run quick test suite (reduced timeouts)
echo   --verbose               Enable verbose output
echo.
echo Examples:
echo   %~nx0                      # Run all integration tests
echo   %~nx0 --critical-only      # Run only critical tests
echo   %~nx0 --stress-only        # Run only stress tests
echo   %~nx0 --continuous         # Run continuously every 2 hours
echo   %~nx0 --quick --parallel   # Quick parallel run
goto :eof

REM Function to setup test environment
:setup_environment
call :print_status "Setting up test environment..."

REM Create logs directory if it doesn't exist
if not exist "logs" mkdir logs

REM Set environment variables for integration tests
set INTEGRATION_TEST_MODE=1
set PYTHONPATH=%PYTHONPATH%;%CD%\..\..

REM Create temporary directories for test data
if not exist "temp_test_data" mkdir temp_test_data

call :print_success "Test environment setup complete"
goto :eof

REM Function to cleanup after tests
:cleanup_environment
call :print_status "Cleaning up test environment..."

REM Remove temporary test data
if exist "temp_test_data" rmdir /s /q temp_test_data

REM Archive old log files
if exist "%LOG_FILE%" (
    for /f "tokens=1-4 delims=/ " %%a in ('date /t') do set DATE_STAMP=%%c%%a%%b
    for /f "tokens=1-2 delims=: " %%a in ('time /t') do set TIME_STAMP=%%a%%b
    set TIMESTAMP=!DATE_STAMP!_!TIME_STAMP!
    move "%LOG_FILE%" "logs\integration_test_!TIMESTAMP!.log" >nul
    call :print_status "Log file archived to logs\integration_test_!TIMESTAMP!.log"
)

call :print_success "Cleanup complete"
goto :eof

REM Function to generate summary report
:generate_summary
call :print_status "Generating test summary..."

if exist "%LOG_FILE%" (
    echo.
    echo === INTEGRATION TEST SUMMARY ===
    
    REM Extract key metrics from log (simplified for Windows batch)
    findstr /c:"PASSED" /c:"FAILED" "%LOG_FILE%" >nul 2>&1
    if not errorlevel 1 (
        echo Test results found in log file
    ) else (
        echo No test results found in log file
    )
    
    REM Show any critical failures
    findstr /c:"CRITICAL FAILURE" "%LOG_FILE%" >nul 2>&1
    if not errorlevel 1 (
        echo.
        echo CRITICAL FAILURES DETECTED:
        findstr /c:"CRITICAL FAILURE" "%LOG_FILE%"
    )
    
    echo === END SUMMARY ===
    echo.
)
goto :eof

REM Main script logic
:main
set continuous=false
set interval=120
set max_runs=
set fail_fast=false
set parallel=false
set stress_only=false
set critical_only=false
set report_only=false
set quick=false
set verbose=false

REM Parse command line arguments (simplified for Windows batch)
:parse_args
if "%~1"=="" goto :args_parsed
if "%~1"=="-h" goto :show_help
if "%~1"=="--help" goto :show_help
if "%~1"=="-c" (
    set CONFIG_FILE=%~2
    shift
    shift
    goto :parse_args
)
if "%~1"=="--config" (
    set CONFIG_FILE=%~2
    shift
    shift
    goto :parse_args
)
if "%~1"=="-l" (
    set LOG_FILE=%~2
    shift
    shift
    goto :parse_args
)
if "%~1"=="--log" (
    set LOG_FILE=%~2
    shift
    shift
    goto :parse_args
)
if "%~1"=="--continuous" (
    set continuous=true
    shift
    goto :parse_args
)
if "%~1"=="--interval" (
    set interval=%~2
    shift
    shift
    goto :parse_args
)
if "%~1"=="--max-runs" (
    set max_runs=%~2
    shift
    shift
    goto :parse_args
)
if "%~1"=="--fail-fast" (
    set fail_fast=true
    shift
    goto :parse_args
)
if "%~1"=="--parallel" (
    set parallel=true
    shift
    goto :parse_args
)
if "%~1"=="--stress-only" (
    set stress_only=true
    shift
    goto :parse_args
)
if "%~1"=="--critical-only" (
    set critical_only=true
    shift
    goto :parse_args
)
if "%~1"=="--report-only" (
    set report_only=true
    shift
    goto :parse_args
)
if "%~1"=="--quick" (
    set quick=true
    shift
    goto :parse_args
)
if "%~1"=="--verbose" (
    set verbose=true
    shift
    goto :parse_args
)
call :print_error "Unknown option: %~1"
goto :show_help

:show_help
call :show_usage
exit /b 1

:args_parsed

REM Check prerequisites
call :check_prerequisites
if errorlevel 1 exit /b 1

REM Setup environment
call :setup_environment

REM Prepare arguments for Python script
set python_args=

if exist "%CONFIG_FILE%" (
    set python_args=!python_args! --config "%CONFIG_FILE%"
)

if "%continuous%"=="true" (
    set python_args=!python_args! --continuous --interval %interval%
    if not "%max_runs%"=="" (
        set python_args=!python_args! --max-runs %max_runs%
    )
)

if "%fail_fast%"=="true" (
    set python_args=!python_args! --fail-fast
)

if "%parallel%"=="true" (
    set python_args=!python_args! --parallel
)

if "%stress_only%"=="true" (
    set python_args=!python_args! --stress-only
)

if "%critical_only%"=="true" (
    set python_args=!python_args! --critical-only
)

if "%report_only%"=="true" (
    set python_args=!python_args! --report-only
)

REM Run the tests
call :print_status "Starting Russian Trading System Integration Tests"
call :print_status "Configuration: %CONFIG_FILE%"
call :print_status "Log file: %LOG_FILE%"

%PYTHON_CMD% integration_test_runner.py %python_args% 2>&1 | tee "%LOG_FILE%"
set test_exit_code=%errorlevel%

call :cleanup_environment
call :generate_summary

if %test_exit_code% equ 0 (
    call :print_success "Integration test run completed successfully"
    exit /b 0
) else (
    call :print_error "Integration test run failed"
    exit /b 1
)

REM Call main function
call :main %*