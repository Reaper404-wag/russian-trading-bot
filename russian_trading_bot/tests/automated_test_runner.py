"""
Automated test runner for continuous validation of Russian trading system
"""

import subprocess
import sys
import time
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_automation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class TestSuite:
    """Test suite configuration"""
    name: str
    test_files: List[str]
    timeout_seconds: int = 300
    critical: bool = False
    retry_count: int = 1
    parallel: bool = False


@dataclass
class TestResult:
    """Test execution result"""
    suite_name: str
    status: str  # 'passed', 'failed', 'timeout', 'error'
    duration: float
    tests_run: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    error_message: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class AutomatedTestRunner:
    """Automated test runner for continuous integration"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file
        self.test_suites = self._load_test_suites()
        self.results_history = []
        self.notification_callbacks = []
    
    def _load_test_suites(self) -> List[TestSuite]:
        """Load test suite configurations"""
        # Default test suites for Russian trading system
        default_suites = [
            TestSuite(
                name="unit_tests",
                test_files=[
                    "test_moex_client.py",
                    "test_news_aggregator.py",
                    "test_sentiment_analyzer.py",
                    "test_technical_analyzer.py",
                    "test_ai_decision_engine.py",
                    "test_risk_manager.py",
                    "test_portfolio_manager.py"
                ],
                timeout_seconds=180,
                critical=True,
                retry_count=2
            ),
            TestSuite(
                name="integration_tests",
                test_files=[
                    "test_integration_workflow.py",
                    "test_broker_integration.py"
                ],
                timeout_seconds=300,
                critical=True,
                retry_count=1
            ),
            TestSuite(
                name="comprehensive_integration",
                test_files=[
                    "test_comprehensive_integration.py"
                ],
                timeout_seconds=600,
                critical=False,
                retry_count=1
            ),
            TestSuite(
                name="performance_tests",
                test_files=[
                    "test_backtesting_engine.py",
                    "test_paper_trading_engine.py"
                ],
                timeout_seconds=900,
                critical=False,
                retry_count=1
            )
        ]
        
        if self.config_file and os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    return [TestSuite(**suite_config) for suite_config in config_data['test_suites']]
            except Exception as e:
                logger.warning(f"Failed to load config file {self.config_file}: {e}")
                logger.info("Using default test suite configuration")
        
        return default_suites
    
    def run_test_suite(self, suite: TestSuite) -> TestResult:
        """Run a single test suite"""
        logger.info(f"Running test suite: {suite.name}")
        start_time = time.time()
        
        try:
            # Prepare pytest command
            cmd = [
                sys.executable, "-m", "pytest",
                "-v",
                "--tb=short",
                "--maxfail=10",
                f"--timeout={suite.timeout_seconds}"
            ]
            
            # Add test files
            for test_file in suite.test_files:
                if os.path.exists(test_file):
                    cmd.append(test_file)
                else:
                    logger.warning(f"Test file not found: {test_file}")
            
            if not any(os.path.exists(f) for f in suite.test_files):
                return TestResult(
                    suite_name=suite.name,
                    status="error",
                    duration=0,
                    error_message="No test files found"
                )
            
            # Run tests
            logger.info(f"Executing: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=suite.timeout_seconds + 60  # Extra buffer
            )
            
            duration = time.time() - start_time
            
            # Parse pytest output
            output_lines = result.stdout.split('\n')
            tests_run = 0
            tests_passed = 0
            tests_failed = 0
            
            for line in output_lines:
                if "passed" in line and "failed" in line:
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
            
            tests_run = tests_passed + tests_failed
            
            # Determine status
            if result.returncode == 0:
                status = "passed"
            else:
                status = "failed"
            
            return TestResult(
                suite_name=suite.name,
                status=status,
                duration=duration,
                tests_run=tests_run,
                tests_passed=tests_passed,
                tests_failed=tests_failed,
                error_message=result.stderr if result.stderr else None
            )
        
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return TestResult(
                suite_name=suite.name,
                status="timeout",
                duration=duration,
                error_message=f"Test suite timed out after {suite.timeout_seconds} seconds"
            )
        
        except Exception as e:
            duration = time.time() - start_time
            return TestResult(
                suite_name=suite.name,
                status="error",
                duration=duration,
                error_message=str(e)
            )
    
    def run_all_suites(self, fail_fast: bool = False) -> List[TestResult]:
        """Run all test suites"""
        logger.info("Starting automated test run")
        results = []
        
        for suite in self.test_suites:
            # Run with retries
            for attempt in range(suite.retry_count + 1):
                if attempt > 0:
                    logger.info(f"Retrying {suite.name} (attempt {attempt + 1})")
                
                result = self.run_test_suite(suite)
                
                if result.status == "passed" or attempt == suite.retry_count:
                    results.append(result)
                    break
                
                logger.warning(f"Test suite {suite.name} failed, retrying...")
                time.sleep(5)  # Brief delay before retry
            
            # Check if we should stop on critical failures
            if fail_fast and suite.critical and result.status != "passed":
                logger.error(f"Critical test suite {suite.name} failed, stopping execution")
                break
        
        self.results_history.extend(results)
        self._notify_results(results)
        
        return results
    
    def run_continuous(self, interval_minutes: int = 60, max_runs: Optional[int] = None):
        """Run tests continuously at specified intervals"""
        logger.info(f"Starting continuous testing with {interval_minutes} minute intervals")
        
        run_count = 0
        
        while True:
            if max_runs and run_count >= max_runs:
                logger.info(f"Reached maximum runs ({max_runs}), stopping")
                break
            
            run_count += 1
            logger.info(f"Starting test run #{run_count}")
            
            try:
                results = self.run_all_suites()
                self._save_results(results, run_count)
                
                # Check if all critical tests passed
                critical_failures = [r for r in results 
                                   if r.status != "passed" and 
                                   any(s.critical for s in self.test_suites if s.name == r.suite_name)]
                
                if critical_failures:
                    logger.error(f"Critical test failures detected: {[r.suite_name for r in critical_failures]}")
                
            except Exception as e:
                logger.error(f"Error during test run #{run_count}: {e}")
            
            if max_runs and run_count >= max_runs:
                break
            
            # Wait for next run
            logger.info(f"Waiting {interval_minutes} minutes until next run...")
            time.sleep(interval_minutes * 60)
    
    def _save_results(self, results: List[TestResult], run_number: int):
        """Save test results to file"""
        results_data = {
            'run_number': run_number,
            'timestamp': datetime.now().isoformat(),
            'results': [asdict(result) for result in results]
        }
        
        filename = f"test_results_run_{run_number:04d}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results_data, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Test results saved to {filename}")
        
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
    
    def _notify_results(self, results: List[TestResult]):
        """Send notifications about test results"""
        for callback in self.notification_callbacks:
            try:
                callback(results)
            except Exception as e:
                logger.error(f"Notification callback failed: {e}")
    
    def add_notification_callback(self, callback):
        """Add notification callback function"""
        self.notification_callbacks.append(callback)
    
    def generate_report(self, results: List[TestResult]) -> str:
        """Generate test execution report"""
        report = "ОТЧЕТ ПО АВТОМАТИЗИРОВАННОМУ ТЕСТИРОВАНИЮ\n"
        report += "=" * 50 + "\n\n"
        
        # Summary
        total_suites = len(results)
        passed_suites = sum(1 for r in results if r.status == "passed")
        failed_suites = sum(1 for r in results if r.status == "failed")
        error_suites = sum(1 for r in results if r.status == "error")
        timeout_suites = sum(1 for r in results if r.status == "timeout")
        
        report += f"Всего наборов тестов: {total_suites}\n"
        report += f"Пройдено успешно: {passed_suites}\n"
        report += f"Провалено: {failed_suites}\n"
        report += f"Ошибки: {error_suites}\n"
        report += f"Превышение времени: {timeout_suites}\n"
        report += f"Процент успеха: {(passed_suites / total_suites * 100):.1f}%\n\n"
        
        # Detailed results
        for result in results:
            report += f"НАБОР ТЕСТОВ: {result.suite_name}\n"
            report += f"Статус: {result.status.upper()}\n"
            report += f"Длительность: {result.duration:.2f} сек\n"
            
            if result.tests_run > 0:
                report += f"Тестов выполнено: {result.tests_run}\n"
                report += f"Тестов пройдено: {result.tests_passed}\n"
                report += f"Тестов провалено: {result.tests_failed}\n"
            
            if result.error_message:
                report += f"Ошибка: {result.error_message[:200]}...\n"
            
            report += f"Время выполнения: {result.timestamp}\n"
            report += "-" * 30 + "\n\n"
        
        return report
    
    def get_health_status(self) -> Dict:
        """Get current system health status based on recent test results"""
        if not self.results_history:
            return {'status': 'unknown', 'message': 'No test results available'}
        
        # Get recent results (last 24 hours)
        recent_cutoff = datetime.now() - timedelta(hours=24)
        recent_results = [r for r in self.results_history if r.timestamp >= recent_cutoff]
        
        if not recent_results:
            return {'status': 'stale', 'message': 'No recent test results'}
        
        # Check critical test suites
        critical_suite_names = [s.name for s in self.test_suites if s.critical]
        recent_critical_results = [r for r in recent_results if r.suite_name in critical_suite_names]
        
        if not recent_critical_results:
            return {'status': 'unknown', 'message': 'No recent critical test results'}
        
        # Determine health status
        failed_critical = [r for r in recent_critical_results if r.status != "passed"]
        
        if not failed_critical:
            return {'status': 'healthy', 'message': 'All critical tests passing'}
        elif len(failed_critical) <= len(recent_critical_results) * 0.2:  # 20% threshold
            return {'status': 'degraded', 'message': f'{len(failed_critical)} critical test failures'}
        else:
            return {'status': 'unhealthy', 'message': f'Multiple critical test failures: {[r.suite_name for r in failed_critical]}'}


def email_notification_callback(results: List[TestResult]):
    """Example email notification callback"""
    failed_results = [r for r in results if r.status != "passed"]
    
    if failed_results:
        logger.info(f"Would send email notification for {len(failed_results)} failed test suites")
        # In a real implementation, this would send an actual email
        for result in failed_results:
            logger.warning(f"Test failure notification: {result.suite_name} - {result.status}")


def slack_notification_callback(results: List[TestResult]):
    """Example Slack notification callback"""
    critical_failures = [r for r in results if r.status != "passed" and r.suite_name in ["unit_tests", "integration_tests"]]
    
    if critical_failures:
        logger.info(f"Would send Slack notification for {len(critical_failures)} critical failures")
        # In a real implementation, this would send to Slack webhook
        for result in critical_failures:
            logger.error(f"Critical test failure: {result.suite_name}")


def main():
    """Main function for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Automated test runner for Russian trading system")
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--continuous", action="store_true", help="Run continuously")
    parser.add_argument("--interval", type=int, default=60, help="Interval in minutes for continuous mode")
    parser.add_argument("--max-runs", type=int, help="Maximum number of runs in continuous mode")
    parser.add_argument("--fail-fast", action="store_true", help="Stop on first critical failure")
    parser.add_argument("--report-only", action="store_true", help="Generate report from existing results")
    
    args = parser.parse_args()
    
    runner = AutomatedTestRunner(config_file=args.config)
    
    # Add notification callbacks
    runner.add_notification_callback(email_notification_callback)
    runner.add_notification_callback(slack_notification_callback)
    
    if args.report_only:
        # Generate report from existing results
        if runner.results_history:
            report = runner.generate_report(runner.results_history[-len(runner.test_suites):])
            print(report)
        else:
            print("No test results available for reporting")
        return
    
    if args.continuous:
        runner.run_continuous(interval_minutes=args.interval, max_runs=args.max_runs)
    else:
        results = runner.run_all_suites(fail_fast=args.fail_fast)
        report = runner.generate_report(results)
        print(report)
        
        # Exit with error code if any critical tests failed
        critical_failures = [r for r in results if r.status != "passed" and 
                           any(s.critical for s in runner.test_suites if s.name == r.suite_name)]
        
        if critical_failures:
            sys.exit(1)


if __name__ == "__main__":
    main()