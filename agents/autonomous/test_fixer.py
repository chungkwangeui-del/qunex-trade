"""
🧪 Test Fixer
Automatically analyzes and fixes failing tests.
"""
import re
import subprocess
import json
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class TestFailure:
    """Information about a test failure."""
    test_name: str
    test_file: str
    error_type: str
    error_message: str
    line_number: int = 0
    expected: str = ""
    actual: str = ""
    fixable: bool = False
    fix_suggestion: str = ""


@dataclass
class TestFixResult:
    """Result of attempting to fix a test."""
    test_name: str
    fixed: bool
    action: str
    details: str = ""


class TestFixer:
    """
    Analyzes failing tests and attempts to fix them.
    """

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
        self.failures: list[TestFailure] = []
        self.fixes: list[TestFixResult] = []

    def run_tests(self) -> tuple:
        """Run tests and capture failures."""
        try:
            result = subprocess.run(
                ['python', '-m', 'pytest', '-v', '--tb=short', '-q'],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=self.project_root
            )

            return result.returncode, result.stdout + result.stderr

        except subprocess.TimeoutExpired:
            return -1, "Tests timed out"
        except FileNotFoundError:
            return -1, "pytest not found"
        except Exception as e:
            return -1, str(e)

    def parse_failures(self, output: str) -> list[TestFailure]:
        """Parse test output to extract failures."""
        failures = []

        # Pattern for test failures
        # Match patterns like: FAILED tests/test_foo.py::test_bar - AssertionError
        failure_pattern = r'FAILED\s+([\w/\\.-]+)::(\w+)\s*[-–]\s*(\w+)'

        for match in re.finditer(failure_pattern, output):
            file_path, test_name, error_type = match.groups()

            failure = TestFailure(
                test_name=test_name,
                test_file=file_path,
                error_type=error_type,
                error_message=""
            )

            # Try to extract more details
            # Look for assertion messages
            assertion_pattern = rf'{test_name}.*?(?:AssertionError|assert)\s*[:]\s*([^\n]+)'
            assertion_match = re.search(assertion_pattern, output, re.DOTALL | re.IGNORECASE)
            if assertion_match:
                failure.error_message = assertion_match.group(1).strip()

            # Look for expected/actual values
            expected_pattern = r'(?:expected|Expected)\s*[:=]\s*([^\n]+)'
            actual_pattern = r'(?:actual|Actual|got|Got)\s*[:=]\s*([^\n]+)'

            exp_match = re.search(expected_pattern, output)
            act_match = re.search(actual_pattern, output)

            if exp_match:
                failure.expected = exp_match.group(1).strip()
            if act_match:
                failure.actual = act_match.group(1).strip()

            # Determine if fixable and suggest fix
            failure = self._analyze_fixability(failure)

            failures.append(failure)

        self.failures = failures
        return failures

    def _analyze_fixability(self, failure: TestFailure) -> TestFailure:
        """Analyze if a failure is automatically fixable."""

        # Import errors are often fixable
        if failure.error_type == 'ImportError' or failure.error_type == 'ModuleNotFoundError':
            failure.fixable = True
            failure.fix_suggestion = "Check import paths and ensure module exists"

        # Type errors might be fixable
        elif failure.error_type == 'TypeError':
            if 'missing' in failure.error_message.lower() and 'argument' in failure.error_message.lower():
                failure.fixable = True
                failure.fix_suggestion = "Add missing argument to function call"
            elif 'unexpected keyword argument' in failure.error_message.lower():
                failure.fixable = True
                failure.fix_suggestion = "Remove unexpected keyword argument"

        # Attribute errors
        elif failure.error_type == 'AttributeError':
            failure.fixable = False
            failure.fix_suggestion = "Check if attribute exists or is misspelled"

        # Assertion errors
        elif failure.error_type == 'AssertionError':
            if failure.expected and failure.actual:
                # Could potentially update expected value
                failure.fixable = False
                failure.fix_suggestion = f"Expected: {failure.expected}, Got: {failure.actual}"
            else:
                failure.fixable = False
                failure.fix_suggestion = "Review assertion logic"

        return failure

    def attempt_fix(self, failure: TestFailure) -> TestFixResult:
        """Attempt to fix a single test failure."""
        result = TestFixResult(
            test_name=failure.test_name,
            fixed=False,
            action="none"
        )

        if not failure.fixable:
            result.action = "skip"
            result.details = "Not automatically fixable"
            return result

        test_file = self.project_root / failure.test_file
        if not test_file.exists():
            result.action = "error"
            result.details = f"Test file not found: {failure.test_file}"
            return result

        try:
            content = test_file.read_text(encoding='utf-8')
            original_content = content

            # Try different fix strategies based on error type
            if failure.error_type == 'ImportError' or failure.error_type == 'ModuleNotFoundError':
                # Try to fix import paths
                content = self._fix_imports(content, failure)

            elif failure.error_type == 'TypeError':
                # Try to fix function calls
                content = self._fix_type_errors(content, failure)

            if content != original_content:
                test_file.write_text(content, encoding='utf-8')
                result.fixed = True
                result.action = "fixed"
                result.details = f"Applied fix for {failure.error_type}"
            else:
                result.action = "no_change"
                result.details = "Could not determine automatic fix"

        except Exception as e:
            result.action = "error"
            result.details = str(e)

        return result

    def _fix_imports(self, content: str, failure: TestFailure) -> str:
        """Try to fix import errors."""
        # Common import fixes
        fixes = [
            # Fix relative imports
            (r'from (\w+) import', r'from . import'),
            # Add missing __init__.py detection (logging only)
        ]

        # For now, just log what needs to be fixed
        logger.info(f"Import error in {failure.test_file}: {failure.error_message}")

        return content

    def _fix_type_errors(self, content: str, failure: TestFailure) -> str:
        """Try to fix type errors."""
        # Extract function name from error if possible
        match = re.search(r"(\w+)\(\)", failure.error_message)
        if match:
            func_name = match.group(1)
            logger.info(f"TypeError in function {func_name}: {failure.error_message}")

        return content

    def fix_all(self) -> dict:
        """Run tests, analyze failures, and attempt fixes."""
        print("  🧪 Running tests and analyzing failures...")

        # Run tests
        return_code, output = self.run_tests()

        if return_code == 0:
            print("     ✅ All tests passed!")
            return {
                'status': 'all_passed',
                'failures': 0,
                'fixed': 0
            }

        if return_code == 5:
            print("     ⚠️ No tests found")
            return {
                'status': 'no_tests',
                'failures': 0,
                'fixed': 0
            }

        # Parse failures
        failures = self.parse_failures(output)

        if not failures:
            print(f"     ⚠️ Tests failed but couldn't parse failures")
            return {
                'status': 'parse_error',
                'failures': 0,
                'fixed': 0
            }

        print(f"     📋 Found {len(failures)} failing tests")

        # Attempt fixes
        fixed_count = 0
        for failure in failures:
            result = self.attempt_fix(failure)
            self.fixes.append(result)

            if result.fixed:
                fixed_count += 1
                print(f"     ✅ Fixed: {failure.test_name}")
            elif failure.fixable:
                print(f"     ⚠️ Could not fix: {failure.test_name}")

        # Re-run tests if any were fixed
        if fixed_count > 0:
            print(f"     🔄 Re-running tests after {fixed_count} fixes...")
            return_code, _ = self.run_tests()

            if return_code == 0:
                print("     ✅ All tests now passing!")

        return {
            'status': 'completed',
            'failures': len(failures),
            'fixed': fixed_count,
            'still_failing': len(failures) - fixed_count
        }

    def generate_report(self, output_path: Optional[Path] = None) -> str:
        """Generate test analysis report."""
        output = output_path or Path("reports/test_analysis.md")
        output.parent.mkdir(parents=True, exist_ok=True)

        report = """# 🧪 Test Analysis Report

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary

| Metric | Value |
|--------|-------|
| Total Failures | {len(self.failures)} |
| Auto-fixable | {sum(1 for f in self.failures if f.fixable)} |
| Fixed | {sum(1 for f in self.fixes if f.fixed)} |

## Test Failures

"""
        for failure in self.failures:
            fixable_icon = "🔧" if failure.fixable else "📝"

            report += """### {fixable_icon} {failure.test_name}

- **File:** `{failure.test_file}`
- **Error:** {failure.error_type}
- **Message:** {failure.error_message or 'N/A'}
- **Fixable:** {'Yes' if failure.fixable else 'No'}
- **Suggestion:** {failure.fix_suggestion}

"""
            if failure.expected and failure.actual:
                report += f"- **Expected:** `{failure.expected}`\n"
                report += f"- **Actual:** `{failure.actual}`\n\n"

        if self.fixes:
            report += "## Fix Attempts\n\n"
            for fix in self.fixes:
                status_icon = "✅" if fix.fixed else "❌"
                report += f"- {status_icon} **{fix.test_name}**: {fix.action} - {fix.details}\n"

        report += "\n---\n*Report generated by Test Fixer*\n"

        output.write_text(report, encoding='utf-8')
        return str(output)


# Singleton instance
_fixer: Optional[TestFixer] = None

def get_test_fixer(project_root: Optional[Path] = None) -> TestFixer:
    """Get or create test fixer instance."""
    global _fixer
    if _fixer is None:
        _fixer = TestFixer(project_root)
    return _fixer


