"""
Test Runner Agent
=================

Automatically runs tests and reports results.
Can be integrated with the autonomous pipeline.
"""

import subprocess
import logging

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import dataclass, field
from datetime import timezone
from typing import List
from typing import Optional
from typing import Any

logger = logging.getLogger(__name__)

@dataclass
class TestResult:
    """Result of a test run."""
    test_name: str
    passed: bool
    duration_ms: float
    error_message: Optional[str] = None
    output: Optional[str] = None

@dataclass
class TestReport:
    """Report from a test run."""
    timestamp: datetime
    total_tests: int
    passed: int
    failed: int
    errors: int
    skipped: int
    duration_seconds: float
    results: List[TestResult] = field(default_factory=list)
    coverage_percent: Optional[float] = None

class TestRunnerAgent:
    """
    Runs tests and reports results.

    Capabilities:
    - Run pytest tests
    - Generate coverage reports
    - Detect test failures
    - Suggest fixes for failing tests
    """

    def __init__(self):
        self.name = "test_runner"
        self.project_root = Path(__file__).parent.parent.parent
        self.tests_dir = self.project_root / "tests"

        # Configuration
        self.config = {
            "test_command": "python -m pytest",
            "coverage_enabled": True,
            "timeout_seconds": 300,
            "fail_fast": False,
        }

        # State
        self.last_report: Optional[TestReport] = None

    async def run_all_tests(self) -> TestReport:
        """Run all tests and return report."""
        start_time = datetime.now(timezone.utc)

        cmd = [
            "python", "-m", "pytest",
            str(self.tests_dir),
            "-v",
            "--tb=short",
        ]

        if self.config["coverage_enabled"]:
            cmd.extend(["--cov=web", "--cov-report=term-missing"])

        if self.config["fail_fast"]:
            cmd.append("-x")

        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=self.config["timeout_seconds"],
            )

            report = self._parse_pytest_output(result.stdout, result.stderr)
            report.timestamp = start_time
            report.duration_seconds = (datetime.now(timezone.utc) - start_time).total_seconds()

            self.last_report = report
            return report

        except subprocess.TimeoutExpired:
            return TestReport(
                timestamp=start_time,
                total_tests=0,
                passed=0,
                failed=0,
                errors=1,
                skipped=0,
                duration_seconds=self.config["timeout_seconds"],
                results=[TestResult(
                    test_name="all",
                    passed=False,
                    duration_ms=self.config["timeout_seconds"] * 1000,
                    error_message="Test run timed out",
                )],
            )
        except FileNotFoundError:
            return TestReport(
                timestamp=start_time,
                total_tests=0,
                passed=0,
                failed=0,
                errors=1,
                skipped=0,
                duration_seconds=0,
                results=[TestResult(
                    test_name="setup",
                    passed=False,
                    duration_ms=0,
                    error_message="pytest not found - install with: pip install pytest",
                )],
            )
        except Exception as e:
            return TestReport(
                timestamp=start_time,
                total_tests=0,
                passed=0,
                failed=0,
                errors=1,
                skipped=0,
                duration_seconds=0,
                results=[TestResult(
                    test_name="setup",
                    passed=False,
                    duration_ms=0,
                    error_message=str(e),
                )],
            )

    async def run_specific_tests(self, test_paths: List[str]) -> TestReport:
        """Run specific test files."""
        start_time = datetime.now(timezone.utc)

        cmd = ["python", "-m", "pytest", "-v", "--tb=short"] + test_paths

        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=self.config["timeout_seconds"],
            )

            report = self._parse_pytest_output(result.stdout, result.stderr)
            report.timestamp = start_time
            report.duration_seconds = (datetime.now(timezone.utc) - start_time).total_seconds()

            return report

        except Exception as e:
            return TestReport(
                timestamp=start_time,
                total_tests=0,
                passed=0,
                failed=0,
                errors=1,
                skipped=0,
                duration_seconds=0,
                results=[TestResult(
                    test_name="run",
                    passed=False,
                    duration_ms=0,
                    error_message=str(e),
                )],
            )

    def _parse_pytest_output(self, stdout: str, stderr: str) -> TestReport:
        """Parse pytest output into a TestReport."""
        total = 0
        passed = 0
        failed = 0
        errors = 0
        skipped = 0
        results = []
        coverage = None

        lines = stdout.split('\n')

        for line in lines:
            # Parse test results
            if '::' in line and (' PASSED' in line or ' FAILED' in line or ' ERROR' in line or ' SKIPPED' in line):
                test_name = line.split('::')[1].split()[0] if '::' in line else line

                if ' PASSED' in line:
                    passed += 1
                    results.append(TestResult(test_name=test_name, passed=True, duration_ms=0))
                elif ' FAILED' in line:
                    failed += 1
                    results.append(TestResult(test_name=test_name, passed=False, duration_ms=0, error_message="Test failed"))
                elif ' ERROR' in line:
                    errors += 1
                    results.append(TestResult(test_name=test_name, passed=False, duration_ms=0, error_message="Test error"))
                elif ' SKIPPED' in line:
                    skipped += 1

            # Parse summary line
            if 'passed' in line.lower() or 'failed' in line.lower():
                import re
                numbers = re.findall(r'(\d+)\s+(passed|failed|error|skipped)', line.lower())
                for num, status in numbers:
                    if status == 'passed':
                        passed = int(num)
                    elif status == 'failed':
                        failed = int(num)
                    elif status == 'error':
                        errors = int(num)
                    elif status == 'skipped':
                        skipped = int(num)

            # Parse coverage
            if 'TOTAL' in line and '%' in line:
                import re
                match = re.search(r'(\d+)%', line)
                if match:
                    coverage = float(match.group(1))

        total = passed + failed + errors + skipped

        return TestReport(
            timestamp=datetime.now(timezone.utc),
            total_tests=total,
            passed=passed,
            failed=failed,
            errors=errors,
            skipped=skipped,
            duration_seconds=0,
            results=results,
            coverage_percent=coverage,
        )

    def get_test_files(self) -> List[str]:
        """Get list of test files in the project."""
        test_files = []

        if self.tests_dir.exists():
            for test_file in self.tests_dir.rglob("test_*.py"):
                test_files.append(str(test_file.relative_to(self.project_root)))

        return test_files

    def get_uncovered_modules(self) -> List[str]:
        """Get list of modules without tests."""
        # Get all Python modules
        all_modules = set()
        for py_file in (self.project_root / "web").rglob("*.py"):
            if "__pycache__" not in str(py_file):
                module_name = py_file.stem
                if not module_name.startswith("_"):
                    all_modules.add(module_name)

        # Get tested modules
        tested_modules = set()
        for test_file in self.get_test_files():
            # test_xyz.py -> xyz
            module_name = Path(test_file).stem.replace("test_", "")
            tested_modules.add(module_name)

        return list(all_modules - tested_modules)

    async def quick_check(self) -> Dict[str, Any]:
        """Run a quick test check without full test suite."""
        return {
            "test_files": len(self.get_test_files()),
            "uncovered_modules": self.get_uncovered_modules()[:10],
            "last_run": self.last_report.timestamp.isoformat() if self.last_report else None,
            "last_result": {
                "passed": self.last_report.passed,
                "failed": self.last_report.failed,
                "coverage": self.last_report.coverage_percent,
            } if self.last_report else None,
        }

    def get_status(self) -> Dict[str, Any]:
        """Get test runner status."""
        return {
            "name": self.name,
            "tests_dir": str(self.tests_dir),
            "test_files_count": len(self.get_test_files()),
            "last_run": self.last_report.timestamp.isoformat() if self.last_report else None,
            "config": self.config,
        }

