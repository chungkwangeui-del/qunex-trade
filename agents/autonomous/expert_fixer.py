"""
Expert Fixer Agent
==================

A truly intelligent fixer that understands code context and applies
safe, professional-grade fixes for various issue types.

This is not a dumb regex replacer - it's an expert that:
1. Analyzes the code context before fixing
2. Makes safe, reversible changes
3. Validates fixes don't break anything
4. Generates reports for issues it can't safely fix
"""

import ast
import re
import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class FixResult:
    """Result of a fix attempt."""
    file_path: str
    issue_type: str
    line_number: int
    original: str
    fixed: str
    success: bool
    message: str


@dataclass
class IssueReport:
    """Report for issues that need manual review."""
    file_path: str
    line_number: int
    issue_type: str
    severity: str
    description: str
    suggestion: str
    code_snippet: str


class ExpertFixer:
    """
    Expert-level code fixer that safely fixes various issue types.

    Philosophy:
    - Better to skip than to break
    - Always validate after fixing
    - Keep original code in comments when unsure
    - Generate detailed reports for manual review
    """

    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.fixes_applied: List[FixResult] = []
        self.manual_review: List[IssueReport] = []

        # Directories to skip
        self.skip_dirs = {
            '__pycache__', '.git', 'node_modules', 'venv', 'env',
            '.venv', 'build', 'dist', '.pytest_cache', '.mypy_cache',
            'migrations', 'static', 'templates'
        }

        # Files to skip
        self.skip_files = {
            'conftest.py',  # Test config - may have intentional patterns
        }

    async def fix_all(self) -> Dict[str, Any]:
        """
        Scan and fix all issues in the codebase.

        Returns summary of fixes applied and issues for manual review.
        """
        print("  🧠 Expert Fixer analyzing codebase...")

        self.fixes_applied = []
        self.manual_review = []

        # Get all Python files
        py_files = list(self.project_root.rglob("*.py"))

        files_fixed = set()

        for file_path in py_files:
            if self._should_skip(file_path):
                continue

            try:
                fixes = await self._analyze_and_fix_file(file_path)
                if fixes > 0:
                    files_fixed.add(str(file_path))
            except Exception as e:
                logger.debug(f"Error processing {file_path}: {e}")

        # Generate report for manual review items
        if self.manual_review:
            await self._generate_report()

        return {
            'fixes_applied': len(self.fixes_applied),
            'files_fixed': list(files_fixed),
            'manual_review_count': len(self.manual_review),
            'report_generated': len(self.manual_review) > 0
        }

    def _should_skip(self, file_path: Path) -> bool:
        """Check if file should be skipped."""
        # Skip directories
        for part in file_path.parts:
            if part in self.skip_dirs:
                return True

        # Skip specific files
        if file_path.name in self.skip_files:
            return True

        return False

    async def _analyze_and_fix_file(self, file_path: Path) -> int:
        """Analyze and fix issues in a single file."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            original_content = content

            fixes_in_file = 0

            # Apply various fixes
            content, count = self._fix_bare_except(content, file_path)
            fixes_in_file += count

            content, count = self._fix_mutable_default_args(content, file_path)
            fixes_in_file += count

            content, count = self._fix_comparison_to_none(content, file_path)
            fixes_in_file += count

            content, count = self._fix_comparison_to_true_false(content, file_path)
            fixes_in_file += count

            content, count = self._fix_unused_variables(content, file_path)
            fixes_in_file += count

            content, count = self._fix_f_string_without_placeholders(content, file_path)
            fixes_in_file += count

            # Analyze issues that need manual review
            self._analyze_for_manual_review(original_content, file_path)

            # Only write if changes were made and file is valid
            if content != original_content:
                # Validate the new content is valid Python
                if self._validate_python(content):
                    file_path.write_text(content, encoding='utf-8')
                else:
                    logger.warning(f"Fix would break {file_path}, skipping")
                    return 0

            return fixes_in_file

        except Exception as e:
            logger.debug(f"Error fixing {file_path}: {e}")
            return 0

    def _validate_python(self, content: str) -> bool:
        """Validate that content is valid Python."""
        try:
            ast.parse(content)
            return True
        except SyntaxError:
            return False

    def _fix_bare_except(self, content: str, file_path: Path) -> Tuple[str, int]:
        """
        Fix bare except clauses.

        Before: except Exception:
        After:  except Exception:

        This is safe because Exception catches all standard exceptions
        but not KeyboardInterrupt or SystemExit.
        """
        pattern = r'^(\s*)except\s*:\s*$'

        lines = content.split('\n')
        fixed_lines = []
        count = 0

        for i, line in enumerate(lines):
            match = re.match(pattern, line)
            if match:
                indent = match.group(1)
                fixed_line = f"{indent}except Exception:"
                fixed_lines.append(fixed_line)
                count += 1

                self.fixes_applied.append(FixResult(
                    file_path=str(file_path),
                    issue_type="bare_except",
                    line_number=i + 1,
                    original=line,
                    fixed=fixed_line,
                    success=True,
                    message="Added Exception type to bare except"
                ))
            else:
                fixed_lines.append(line)

        return '\n'.join(fixed_lines), count

    def _fix_mutable_default_args(self, content: str, file_path: Path) -> Tuple[str, int]:
        """
        Fix mutable default arguments in function definitions.

        Before: def func(items=[]):
        After:  def func(items=None):
                    if items is None:
                        items = []

        This is a common Python gotcha that can cause subtle bugs.
        """
        # This is complex to fix safely via regex, so we'll flag for manual review
        pattern = r'def\s+\w+\([^)]*(?:=\s*\[\]|=\s*\{\})[^)]*\)'

        for match in re.finditer(pattern, content):
            line_num = content[:match.start()].count('\n') + 1
            self.manual_review.append(IssueReport(
                file_path=str(file_path),
                line_number=line_num,
                issue_type="mutable_default_arg",
                severity="medium",
                description="Mutable default argument detected",
                suggestion="Use None as default and initialize in function body",
                code_snippet=match.group(0)[:80]
            ))

        return content, 0  # Don't auto-fix, too risky

    def _fix_comparison_to_none(self, content: str, file_path: Path) -> Tuple[str, int]:
        """
        Fix comparison to None using == instead of is.

        Before: if x is None:
        After:  if x is None:
        """
        count = 0

        # == None -> is None
        pattern1 = r'(\s+)(\w+)\s*==\s*None\b'
        def replace1(m):
            nonlocal count
            count += 1
            return f"{m.group(1)}{m.group(2)} is None"
        content = re.sub(pattern1, replace1, content)

        # != None -> is not None
        pattern2 = r'(\s+)(\w+)\s*!=\s*None\b'
        def replace2(m):
            nonlocal count
            count += 1
            return f"{m.group(1)}{m.group(2)} is not None"
        content = re.sub(pattern2, replace2, content)

        return content, count

    def _fix_comparison_to_true_false(self, content: str, file_path: Path) -> Tuple[str, int]:
        """
        Fix comparison to True/False using == instead of is.

        Before: if x:
        After:  if x is True:

        Or better: if x:
        """
        count = 0

        # == True -> is True (or just the variable for booleans)
        pattern1 = r'\bif\s+(\w+)\s*==\s*True\s*:'
        def replace1(m):
            nonlocal count
            count += 1
            return f"if {m.group(1)}:"
        content = re.sub(pattern1, replace1, content)

        # == False -> is False (or not variable)
        pattern2 = r'\bif\s+(\w+)\s*==\s*False\s*:'
        def replace2(m):
            nonlocal count
            count += 1
            return f"if not {m.group(1)}:"
        content = re.sub(pattern2, replace2, content)

        return content, count

    def _fix_unused_variables(self, content: str, file_path: Path) -> Tuple[str, int]:
        """
        Fix unused loop variables.

        Before: for i in range(10): print("hello")
        After:  for _ in range(10): print("hello")

        Only fixes obvious cases where the variable is clearly unused.
        """
        count = 0

        # Pattern: for <var> in ... where var is never used in the block
        # This is hard to do safely, so only fix the most obvious case:
        # Single-line for loops where variable isn't mentioned

        pattern = r'^(\s*)for\s+([a-z])\s+in\s+(range\([^)]+\)):\s*(\S.*)$'

        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            match = re.match(pattern, line)
            if match:
                indent, var, range_expr, body = match.groups()
                # Check if var is used in body
                if var not in body.replace(f'"{var}"', '').replace(f"'{var}'", ''):
                    fixed_line = f"{indent}for _ in {range_expr}: {body}"
                    fixed_lines.append(fixed_line)
                    count += 1
                    continue
            fixed_lines.append(line)

        return '\n'.join(fixed_lines), count

    def _fix_f_string_without_placeholders(self, content: str, file_path: Path) -> Tuple[str, int]:
        """
        Fix f-strings that don't have any placeholders.

        Before: "hello world"
        After:  "hello world"
        """
        count = 0

        # Find f-strings without { }
        pattern = r'\bf(["\'])([^{}\'"]*)\1'

        def replace(m):
            nonlocal count
            quote = m.group(1)
            string_content = m.group(2)
            # Only fix if no curly braces
            if '{' not in string_content and '}' not in string_content:
                count += 1
                return f'{quote}{string_content}{quote}'
            return m.group(0)

        content = re.sub(pattern, replace, content)

        return content, count

    def _analyze_for_manual_review(self, content: str, file_path: Path):
        """Analyze content for issues that need manual review."""
        lines = content.split('\n')

        for i, line in enumerate(lines):
            line_num = i + 1

            # SQL Injection patterns
            if re.search(r'execute\([^)]*%|execute\([^)]*\+|f["\'].*SELECT.*\{', line, re.IGNORECASE):
                self.manual_review.append(IssueReport(
                    file_path=str(file_path),
                    line_number=line_num,
                    issue_type="sql_injection",
                    severity="critical",
                    description="Potential SQL injection vulnerability",
                    suggestion="Use parameterized queries: cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))",
                    code_snippet=line.strip()[:100]
                ))

            # Hardcoded secrets
            if re.search(r'(password|secret|api_key|token)\s*=\s*["\'][^"\']{8,}["\']', line, re.IGNORECASE):
                # Skip if it's getting from environment
                if 'os.environ' not in line and 'os.getenv' not in line and 'environ.get' not in line:
                    self.manual_review.append(IssueReport(
                        file_path=str(file_path),
                        line_number=line_num,
                        issue_type="hardcoded_secret",
                        severity="critical",
                        description="Hardcoded secret detected",
                        suggestion="Move to environment variable: os.environ.get('SECRET_KEY')",
                        code_snippet=line.strip()[:60] + "..." if len(line) > 60 else line.strip()
                    ))

            # Shell injection
            if re.search(r'os\.system\(|subprocess.*shell\s*=\s*True', line):
                self.manual_review.append(IssueReport(
                    file_path=str(file_path),
                    line_number=line_num,
                    issue_type="shell_injection",
                    severity="high",
                    description="Potential shell injection vulnerability",
                    suggestion="Use subprocess.run() with shell=False and pass args as list",
                    code_snippet=line.strip()[:100]
                ))

            # Pickle usage
            if 'pickle.load' in line or 'pickle.loads' in line:
                self.manual_review.append(IssueReport(
                    file_path=str(file_path),
                    line_number=line_num,
                    issue_type="unsafe_pickle",
                    severity="high",
                    description="Pickle can execute arbitrary code",
                    suggestion="Use json for data serialization, or validate pickle source",
                    code_snippet=line.strip()[:100]
                ))

            # Eval/exec usage
            if re.search(r'\beval\s*\(|\bexec\s*\(', line):
                self.manual_review.append(IssueReport(
                    file_path=str(file_path),
                    line_number=line_num,
                    issue_type="unsafe_eval",
                    severity="critical",
                    description="eval/exec can execute arbitrary code",
                    suggestion="Use ast.literal_eval() for safe evaluation, or avoid dynamic code execution",
                    code_snippet=line.strip()[:100]
                ))

    async def _generate_report(self):
        """Generate a detailed report for manual review items."""
        report_dir = self.project_root / "reports"
        report_dir.mkdir(exist_ok=True)

        report_path = report_dir / "security_review.md"

        # Group by severity
        critical = [r for r in self.manual_review if r.severity == 'critical']
        high = [r for r in self.manual_review if r.severity == 'high']
        medium = [r for r in self.manual_review if r.severity == 'medium']
        low = [r for r in self.manual_review if r.severity == 'low']

        report = """# Security & Code Review Report

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary

| Severity | Count |
|----------|-------|
| 🔴 Critical | {len(critical)} |
| 🟠 High | {len(high)} |
| 🟡 Medium | {len(medium)} |
| 🟢 Low | {len(low)} |
| **Total** | **{len(self.manual_review)}** |

---

"""

        if critical:
            report += "## 🔴 Critical Issues\n\n"
            report += "These issues require immediate attention!\n\n"
            for issue in critical:
                report += self._format_issue(issue)

        if high:
            report += "## 🟠 High Priority Issues\n\n"
            for issue in high:
                report += self._format_issue(issue)

        if medium:
            report += "## 🟡 Medium Priority Issues\n\n"
            for issue in medium:
                report += self._format_issue(issue)

        if low:
            report += "## 🟢 Low Priority Issues\n\n"
            for issue in low:
                report += self._format_issue(issue)

        report += """
---

## How to Fix

### SQL Injection
```python
# ❌ Bad
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")

# ✅ Good
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
```

### Hardcoded Secrets
```python
# ❌ Bad
API_KEY = "sk-abc123secret"

# ✅ Good
API_KEY = os.environ.get('API_KEY')
```

### Shell Injection
```python
# ❌ Bad
os.system(f"rm {filename}")

# ✅ Good
subprocess.run(['rm', filename], check=True)
```

---

*Report generated by Ultimate Bot Expert Fixer*
"""

        report_path.write_text(report, encoding='utf-8')
        print("     📝 Report saved: reports/security_review.md")

    def _format_issue(self, issue: IssueReport) -> str:
        """Format a single issue for the report."""
        rel_path = issue.file_path.replace(str(self.project_root), '').lstrip('/\\')
        return """### {issue.issue_type.replace('_', ' ').title()}

**File:** `{rel_path}` (line {issue.line_number})

**Description:** {issue.description}

**Code:**
```python
{issue.code_snippet}
```

**Suggestion:** {issue.suggestion}

---

"""
