#!/usr/bin/env python3
"""
Enhanced Integration Test Runner for Russian Trading System - Task 12.3
Automated testing pipeline for continuous validation
"""

import subprocess
import sys
import time
import json
import os
import argparse
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import concurrent.futures
import threading
import psutil

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('integration_test_automation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class IntegrationTestSuite:
    """Integration test suite configuration"""
    name: str
    test_files: List[str]
    timeout_seconds: int = 600  # 10 minutes default for integration tests
    critical: bool = False
    retry_count: int = 1
    parallel: bool = False
    stress_test: bool = False
    resource_intensive: bool = False


@dataclass
class IntegrationTestResult:
    """Integration test execution result"""
    suite_name: str
    status: str  # 'passed', 'failed', 'timeout', 'error'
    duration: float
    tests_run: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    memory_peak_mb: float = 0.0
    cpu_avg_percent: float = 0.0
    error_message: Optional[str] = None
    timestamp: datetime = None
    performance_metrics: Dict[str, float] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.performance_metrics is None:
            self.performance_metrics = {}


class ResourceMonitor:
    """Monitor system resources during test execution"""
    
    def __init__(self):
        self.monitoring = False
        self.memory_samples = []
        self.cpu_samples = []
        self.monitor_thread = None
        
    def start_monitoring(self):
        """Start resource monitoring"""
        self.monitoring = True
        self.memory_samples = []
        self.cpu_samples = []
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
    def stop_monitoring(self) -> Tuple[float, float]:
        """Stop monitoring and return peak memory and average CPU"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        
        peak_memory = max(self.memory_samples) if self.memory_samples else 0
        avg_cpu = sum(self.cpu_samples) / len(self.cpu_samples) if self.cpu_samples else 0
        
        return peak_memory, avg_cpu
    
    def _monitor_loop(self):
        """Monitor system resources in background"""
        while self.monitoring:
            try:
                # Monitor current process and children
                current_process = psutil.Process()
                memory_mb = current_process.memory_info().rss / 1024 / 1024
                cpu_percent = current_process.cpu_percent()
                
                # Include child processes
                for child in current_process.children(recursive=True):
                    try:
                        memory_mb += child.memory_info().rss / 1024 / 1024
                        cpu_percent += child.cpu_percent()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                
                self.memory_samples.append(memory_mb)
                self.cpu_samples.append(cpu_percent)
                
            except Exception as e:
                logger.warning(f"Resource monitoring error: {e}")
            
            time.sleep(1)


class IntegrationTestRunner:
    """Enhanced test runner for integration tests"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file
        self.test_suites = self._load_test_suites()
        self.results_history = []
        self.notification_callbacks = []
        self.resource_monitor = ResourceMonitor()
        
    def _load_test_suites(self) -> List[IntegrationTestSuite]:
        """Load integration test suite configurations"""
        default_suites = [
            IntegrationTestSuite(
                name="end_to_end_workflow",
                test_files=["test_integration_comprehensive_workflow.py::TestEndToEndWorkflow"],
                timeout_seconds=300,
                critical=True,
                retry_count=2,
                resource_intensive=True
            ),
            IntegrationTestSuite(
                name="broker_api_integration",
                test_files=["test_integration_comprehensive_workflow.py::TestBrokerAPIIntegration"],
                timeout_seconds=240,
                critical=True,
                retry_count=1
            ),
            IntegrationTestSuite(
                name="stress_testing",
                test_files=["test_integration_comprehensive_workflow.py::TestStressTesting"],
                timeout_seconds=600,
                critical=False,
                retry_count=1,
                stress_test=True,
                resource_intensive=True
            ),
            IntegrationTestSuite(
                name="automated_pipeline",
                test_files=["test_integration_comprehensive_workflow.py::TestAutomatedPipeline"],
                timeout_seconds=180,
                critical=False,
                retry_count=1
            ),
            IntegrationTestSuite(
                name="performance_benchmarks",
                test_files=["test_integration_comprehensive_workflow.py::TestPerformanceBenchmarks"],
                timeout_seconds=300,
                critical=False,
                retry_count=1,
                resource_intensive=True
            ),
            IntegrationTestSuite(
                name="system_monitoring",
                test_files=["test_integration_comprehensive_workflow.py::TestSystemMonitoring"],
                timeout_seconds=120,
                critical=False,
                retry_count=1
            )
        ]
        
        if self.config_file and os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    return [IntegrationTestSuite(**suite_config) for suite_config in config_data['test_suites']]
            except Exception as e:
                logger.warning(f"Failed to load config file {self.config_file}: {e}")
                logger.info("Using default integration test suite configuration")
        
        return default_suites
    
    def run_test_suite(self, suite: IntegrationTestSuite) -> IntegrationTestResult:
        """Run a single integration test suite with resource monitoring"""
        logger.info(f"Running integration test suite: {suite.name}")
        start_time = time.time()
        
        # Start resource monitoring
        self.resource_monitor.start_monitoring()
        
        try:
            # Prepare pytest command for integration tests
            cmd = [
                sys.executable, "-m", "pytest",
                "-v",
                "--tb=short",
                "--maxfail=5",  # Allow more failures for integration tests
                f"--timeout={suite.timeout_seconds}",
                "--capture=no",  # Show output for integration tests
                "-s"  # Don't capture stdout
            ]
            
            # Add markers for different test types
            if suite.stress_test:
                cmd.extend(["-m", "not slow"])  # Skip slow tests in stress testing
            
            # Add test files
            valid_test_files = []
            for test_file in suite.test_files:
                if "::" in test_file:
                    # Specific test class
                    file_path = test_file.split("::")[0]
                    if os.path.exists(file_path):
                        valid_test_files.append(test_file)
                    else:
                        logger.warning(f"Test file not found: {file_path}")
                else:
                    # Entire file
                    if os.path.exists(test_file):
                        valid_test_files.append(test_file)
                    else:
                        logger.warning(f"Test file not found: {test_file}")
            
            if not valid_test_files:
                peak_memory, avg_cpu = self.resource_monitor.stop_monitoring()
                return IntegrationTestResult(
                    suite_name=suite.name,
                    status="error",
                    duration=0,
                    error_message="No valid test files found",
                    memory_peak_mb=peak_memory,
                    cpu_avg_percent=avg_cpu
                )
            
            cmd.extend(valid_test_files)
            
            # Set environment variables for integration tests
            env = os.environ.copy()
            env['PYTEST_CURRENT_TEST'] = suite.name
            env['INTEGRATION_TEST_MODE'] = '1'
            
            # Run tests
            logger.info(f"Executing: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=suite.timeout_seconds + 120,  # Extra buffer for integration tests
                env=env
            )
            
            duration = time.time() - start_time
            peak_memory, avg_cpu = self.resource_monitor.stop_monitoring()
            
            # Parse pytest output for integration tests
            output_lines = result.stdout.split('\n')
            tests_run = 0
            tests_passed = 0
            tests_failed = 0
            
            # Look for pytest summary line
            for line in output_lines:
                if "failed" in line and "passed" in line:
                    # Parse line like "5 failed, 10 passed in 2.34s"
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == "failed," and i > 0:
                            tests_failed = int(parts[i-1])
                        elif part == "passed" and i > 0:
                            tests_passed = int(parts[i-1])
                elif line.strip().endswith(" passed"):
                    # Parse line like "15 passed in 1.23s"
                    parts = line.split()
                    if len(parts) >= 2 and parts[1] == "passed":
                        tests_passed = int(parts[0])
                elif line.strip().endswith(" failed"):
                    # Parse line like "3 failed in 1.23s"
                    parts = line.split()
                    if len(parts) >= 2 and parts[1] == "failed":
                        tests_failed = int(parts[0])
            
            tests_run = tests_passed + tests_failed
            
            # Determine status
            if result.returncode == 0:
                status = "passed"
            else:
                status = "failed"
            
            # Extract performance metrics from output
            performance_metrics = self._extract_performance_metrics(result.stdout)
            
            return IntegrationTestResult(
                suite_name=suite.name,
                status=status,
                duration=duration,
                tests_run=tests_run,
                tests_passed=tests_passed,
                tests_failed=tests_failed,
                memory_peak_mb=peak_memory,
                cpu_avg_percent=avg_cpu,
                error_message=result.stderr if result.stderr else None,
                performance_metrics=performance_metrics
            )
        
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            peak_memory, avg_cpu = self.resource_monitor.stop_monitoring()
            return IntegrationTestResult(
                suite_name=suite.name,
                status="timeout",
                duration=duration,
                error_message=f"Integration test suite timed out after {suite.timeout_seconds} seconds",
                memory_peak_mb=peak_memory,
                cpu_avg_percent=avg_cpu
            )
        
        except Exception as e:
            duration = time.time() - start_time
            peak_memory, avg_cpu = self.resource_monitor.stop_monitoring()
            return IntegrationTestResult(
                suite_name=suite.name,
                status="error",
                duration=duration,
                error_message=str(e),
                memory_peak_mb=peak_memory,
                cpu_avg_percent=avg_cpu
            )
    
    def _extract_performance_metrics(self, output: str) -> Dict[str, float]:
        """Extract performance metrics from test output"""
        metrics = {}
        
        # Look for performance indicators in output
        lines = output.split('\n')
        for line in lines:
            if "trades_per_second" in line:
                try:
                    value = float(line.split(":")[-1].strip())
                    metrics["trades_per_second"] = value
                except:
                    pass
            elif "data_points_per_second" in line:
                try:
                    value = float(line.split(":")[-1].strip())
                    metrics["data_points_per_second"] = value
                except:
                    pass
            elif "api_calls_per_second" in line:
                try:
                    value = float(line.split(":")[-1].strip())
                    metrics["api_calls_per_second"] = value
                except:
                    pass
        
        return metrics
    
    def run_all_suites(self, fail_fast: bool = False, parallel: bool = False) -> List[IntegrationTestResult]:
        """Run all integration test suites"""
        logger.info("Starting comprehensive integration test run")
        results = []
        
        if parallel:
            # Run non-resource-intensive tests in parallel
            resource_intensive_suites = [s for s in self.test_suites if s.resource_intensive]
            other_suites = [s for s in self.test_suites if not s.resource_intensive]
            
            # Run other suites in parallel first
            if other_suites:
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                    future_to_suite = {executor.submit(self._run_suite_with_retries, suite): suite 
                                     for suite in other_suites}
                    
                    for future in concurrent.futures.as_completed(future_to_suite):
                        suite = future_to_suite[future]
                        try:
                            result = future.result()
                            results.append(result)
                            
                            if fail_fast and suite.critical and result.status != "passed":
                                logger.error(f"Critical test suite {suite.name} failed, stopping execution")
                                return results
                        except Exception as e:
                            logger.error(f"Error running suite {suite.name}: {e}")
            
            # Run resource-intensive suites sequentially
            for suite in resource_intensive_suites:
                result = self._run_suite_with_retries(suite)
                results.append(result)
                
                if fail_fast and suite.critical and result.status != "passed":
                    logger.error(f"Critical test suite {suite.name} failed, stopping execution")
                    break
        else:
            # Run all suites sequentially
            for suite in self.test_suites:
                result = self._run_suite_with_retries(suite)
                results.append(result)
                
                if fail_fast and suite.critical and result.status != "passed":
                    logger.error(f"Critical test suite {suite.name} failed, stopping execution")
                    break
        
        self.results_history.extend(results)
        self._notify_results(results)
        
        return results
    
    def _run_suite_with_retries(self, suite: IntegrationTestSuite) -> IntegrationTestResult:
        """Run suite with retry logic"""
        for attempt in range(suite.retry_count + 1):
            if attempt > 0:
                logger.info(f"Retrying {suite.name} (attempt {attempt + 1})")
                time.sleep(10)  # Longer delay for integration tests
            
            result = self.run_test_suite(suite)
            
            if result.status == "passed" or attempt == suite.retry_count:
                return result
            
            logger.warning(f"Integration test suite {suite.name} failed, retrying...")
        
        return result
    
    def run_continuous_validation(self, interval_minutes: int = 120, max_runs: Optional[int] = None):
        """Run continuous integration validation (longer intervals for integration tests)"""
        logger.info(f"Starting continuous integration validation with {interval_minutes} minute intervals")
        
        run_count = 0
        
        while True:
            if max_runs and run_count >= max_runs:
                logger.info(f"Reached maximum runs ({max_runs}), stopping")
                break
                
            run_count += 1
            logger.info(f"Starting integration validation run #{run_count}")
            
            try:
                results = self.run_all_suites(parallel=True)  # Use parallel execution for continuous runs
                self._save_results(results, run_count)
                
                # Check for critical failures
                critical_failures = [r for r in results 
                                   if r.status != "passed" and 
                                   any(s.critical for s in self.test_suites if s.name == r.suite_name)]
                
                if critical_failures:
                    logger.error(f"Critical integration test failures detected in run #{run_count}")
                    for failure in critical_failures:
                        logger.error(f"CRITICAL FAILURE: {failure.suite_name} - {failure.error_message}")
                
                # Log performance summary
                self._log_performance_summary(results)
                
            except Exception as e:
                logger.error(f"Error during integration validation run #{run_count}: {e}")
            
            if max_runs and run_count >= max_runs:
                break
                
            logger.info(f"Waiting {interval_minutes} minutes until next integration validation run...")
            time.sleep(interval_minutes * 60)
    
    def _log_performance_summary(self, results: List[IntegrationTestResult]):
        """Log performance summary"""
        total_duration = sum(r.duration for r in results)
        avg_memory = sum(r.memory_peak_mb for r in results) / len(results)
        avg_cpu = sum(r.cpu_avg_percent for r in results) / len(results)
        
        logger.info(f"Performance Summary - Duration: {total_duration:.1f}s, "
                   f"Avg Memory: {avg_memory:.1f}MB, Avg CPU: {avg_cpu:.1f}%")
    
    def _save_results(self, results: List[IntegrationTestResult], run_number: int):
        """Save integration test results to file"""
        results_data = {
            'run_number': run_number,
            'timestamp': datetime.now().isoformat(),
            'test_type': 'integration',
            'results': [asdict(result) for result in results]
        }
        
        filename = f"integration_test_results_run_{run_number:04d}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results_data, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Integration test results saved to {filename}")
        
        except Exception as e:
            logger.error(f"Failed to save integration test results: {e}")
    
    def _notify_results(self, results: List[IntegrationTestResult]):
        """Send notifications about integration test results"""
        for callback in self.notification_callbacks:
            try:
                callback(results)
            except Exception as e:
                logger.error(f"Integration test notification callback failed: {e}")
    
    def add_notification_callback(self, callback):
        """Add notification callback function"""
        self.notification_callbacks.append(callback)
    
    def generate_comprehensive_report(self, results: List[IntegrationTestResult]) -> str:
        """Generate comprehensive integration test report"""
        report = "ОТЧЕТ ПО ИНТЕГРАЦИОННОМУ ТЕСТИРОВАНИЮ РОССИЙСКОЙ ТОРГОВОЙ СИСТЕМЫ\n"
        report += "=" * 80 + "\n\n"
        
        # Executive Summary
        total_suites = len(results)
        passed_suites = sum(1 for r in results if r.status == "passed")
        failed_suites = sum(1 for r in results if r.status == "failed")
        error_suites = sum(1 for r in results if r.status == "error")
        timeout_suites = sum(1 for r in results if r.status == "timeout")
        
        report += "ИСПОЛНИТЕЛЬНОЕ РЕЗЮМЕ\n"
        report += "-" * 20 + "\n"
        report += f"Всего наборов интеграционных тестов: {total_suites}\n"
        report += f"Пройдено успешно: {passed_suites}\n"
        report += f"Провалено: {failed_suites}\n"
        report += f"Ошибки выполнения: {error_suites}\n"
        report += f"Превышение времени: {timeout_suites}\n"
        report += f"Общий процент успеха: {(passed_suites / total_suites * 100):.1f}%\n\n"
        
        # Performance Summary
        total_duration = sum(r.duration for r in results)
        total_tests = sum(r.tests_run for r in results)
        avg_memory = sum(r.memory_peak_mb for r in results) / len(results)
        avg_cpu = sum(r.cpu_avg_percent for r in results) / len(results)
        
        report += "СВОДКА ПО ПРОИЗВОДИТЕЛЬНОСТИ\n"
        report += "-" * 30 + "\n"
        report += f"Общее время выполнения: {total_duration:.1f} секунд\n"
        report += f"Всего тестов выполнено: {total_tests}\n"
        report += f"Среднее пиковое использование памяти: {avg_memory:.1f} МБ\n"
        report += f"Средняя загрузка CPU: {avg_cpu:.1f}%\n"
        report += f"Тестов в секунду: {total_tests / total_duration:.2f}\n\n"
        
        # Critical Issues
        critical_failures = [r for r in results if r.status != "passed" and 
                           any(s.critical for s in self.test_suites if s.name == r.suite_name)]
        
        if critical_failures:
            report += "КРИТИЧЕСКИЕ ПРОБЛЕМЫ\n"
            report += "-" * 20 + "\n"
            for failure in critical_failures:
                report += f"❌ {failure.suite_name}: {failure.error_message}\n"
            report += "\n"
        
        # Detailed Results
        report += "ДЕТАЛЬНЫЕ РЕЗУЛЬТАТЫ\n"
        report += "-" * 20 + "\n"
        
        for result in results:
            status_icon = "✅" if result.status == "passed" else "❌"
            report += f"{status_icon} НАБОР ТЕСТОВ: {result.suite_name}\n"
            report += f"   Статус: {result.status.upper()}\n"
            report += f"   Длительность: {result.duration:.2f} сек\n"
            report += f"   Тестов выполнено: {result.tests_run}\n"
            report += f"   Тестов пройдено: {result.tests_passed}\n"
            report += f"   Тестов провалено: {result.tests_failed}\n"
            report += f"   Пиковая память: {result.memory_peak_mb:.1f} МБ\n"
            report += f"   Средняя загрузка CPU: {result.cpu_avg_percent:.1f}%\n"
            
            if result.performance_metrics:
                report += "   Метрики производительности:\n"
                for metric, value in result.performance_metrics.items():
                    report += f"     {metric}: {value:.2f}\n"
            
            if result.error_message:
                report += f"   Ошибка: {result.error_message[:200]}...\n"
            
            report += f"   Время выполнения: {result.timestamp}\n"
            report += "\n"
        
        # Recommendations
        report += "РЕКОМЕНДАЦИИ\n"
        report += "-" * 15 + "\n"
        
        if failed_suites > 0:
            report += f"• Исследовать и исправить {failed_suites} проваленных набора(ов) тестов\n"
        
        if timeout_suites > 0:
            report += f"• Оптимизировать производительность для {timeout_suites} набора(ов) с превышением времени\n"
        
        if avg_memory > 1000:  # More than 1GB
            report += "• Рассмотреть оптимизацию использования памяти\n"
        
        if avg_cpu > 80:
            report += "• Рассмотреть оптимизацию загрузки CPU\n"
        
        if passed_suites == total_suites:
            report += "• Все интеграционные тесты прошли успешно! Система готова к продакшену.\n"
        
        return report


def integration_notification_callback(results: List[IntegrationTestResult]):
    """Notification callback for integration test results"""
    failed_results = [r for r in results if r.status != "passed"]
    critical_failures = [r for r in failed_results if "end_to_end" in r.suite_name or "broker_api" in r.suite_name]
    
    if critical_failures:
        logger.error(f"CRITICAL: {len(critical_failures)} critical integration test failures!")
        for result in critical_failures:
            logger.error(f"CRITICAL FAILURE: {result.suite_name} - {result.error_message}")
    elif failed_results:
        logger.warning(f"Integration test failures: {len(failed_results)} non-critical failures")
    else:
        logger.info("All integration tests passed successfully! 🎉")


def main():
    """Main function for command-line usage"""
    parser = argparse.ArgumentParser(description="Integration test runner for Russian trading system")
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--continuous", action="store_true", help="Run continuously")
    parser.add_argument("--interval", type=int, default=120, help="Interval in minutes for continuous mode")
    parser.add_argument("--max-runs", type=int, help="Maximum number of runs in continuous mode")
    parser.add_argument("--fail-fast", action="store_true", help="Stop on first critical failure")
    parser.add_argument("--parallel", action="store_true", help="Run non-resource-intensive tests in parallel")
    parser.add_argument("--report-only", action="store_true", help="Generate report from existing results")
    parser.add_argument("--stress-only", action="store_true", help="Run only stress tests")
    parser.add_argument("--critical-only", action="store_true", help="Run only critical tests")
    
    args = parser.parse_args()
    
    runner = IntegrationTestRunner(config_file=args.config)
    
    # Add notification callback
    runner.add_notification_callback(integration_notification_callback)
    
    # Filter test suites based on arguments
    if args.stress_only:
        runner.test_suites = [s for s in runner.test_suites if s.stress_test]
    elif args.critical_only:
        runner.test_suites = [s for s in runner.test_suites if s.critical]
    
    if args.report_only:
        # Generate report from existing results
        if runner.results_history:
            report = runner.generate_comprehensive_report(runner.results_history[-len(runner.test_suites):])
            print(report)
        else:
            print("No integration test results available for reporting")
        return
    
    if args.continuous:
        runner.run_continuous_validation(interval_minutes=args.interval, max_runs=args.max_runs)
    else:
        results = runner.run_all_suites(fail_fast=args.fail_fast, parallel=args.parallel)
        report = runner.generate_comprehensive_report(results)
        print(report)
        
        # Exit with error code if any critical tests failed
        critical_failures = [r for r in results if r.status != "passed" and 
                           any(s.critical for s in runner.test_suites if s.name == r.suite_name)]
        
        if critical_failures:
            logger.error("Exiting with error code due to critical test failures")
            sys.exit(1)
        else:
            logger.info("All integration tests completed successfully")


if __name__ == "__main__":
    main()