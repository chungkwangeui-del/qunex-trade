"""
Fixer Agent (The Support Engineer)
==================================

Automatically fixes detected issues:
- Security vulnerabilities
- Bug fixes
- Configuration issues
- Dependency problems
- Code quality issues
"""

import re
import ast
import os
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple, Callable
from pathlib import Path

from agents.autonomous.task_queue import Task, TaskChange, TaskStatus, TaskType
from agents.project_scanner import ProjectScanner

logger = logging.getLogger(__name__)


# ============ Fix Pattern Registry ============

class FixPattern:
    """A reusable fix pattern."""

    def __init__(
        self,
        name: str,
        description: str,
        file_types: List[str],
        detect: Callable[[str], List[Tuple[int, str]]],  # Returns [(line_num, matched_text)]
        fix: Callable[[str, int], str],  # Takes content and line_num, returns fixed content
        category: str = "quality",
    ):
        self.name = name
        self.description = description
        self.file_types = file_types
        self.detect = detect
        self.fix = fix
        self.category = category


def create_fix_patterns() -> List[FixPattern]:
    """Create all available fix patterns."""
    patterns = []

    # 1. Bare except -> except Exception:
    def detect_bare_except(content: str) -> List[Tuple[int, str]]:
        matches = []
        for i, line in enumerate(content.split('\n'), 1):
            if re.search(r'\bexcept\s*:', line):
                matches.append((i, line.strip()))
        return matches

    def fix_bare_except(content: str, line_num: int) -> str:
        lines = content.split('\n')
        lines[line_num - 1] = re.sub(r'\bexcept\s*:', 'except Exception:', lines[line_num - 1])
        return '\n'.join(lines)

    patterns.append(FixPattern(
        "bare_except",
        "Replace bare except with except Exception",
        [".py"],
        detect_bare_except,
        fix_bare_except,
        "quality",
    ))

    # 2. Add CSRF token to forms
    def detect_csrf_missing(content: str) -> List[Tuple[int, str]]:
        matches = []
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            if re.search(r'<form[^>]*method=["\']post["\']', line, re.I):
                # Check next 5 lines for csrf
                form_section = '\n'.join(lines[i-1:i+5])
                if 'csrf' not in form_section.lower():
                    matches.append((i, line.strip()))
        return matches

    def fix_csrf_missing(content: str, line_num: int) -> str:
        lines = content.split('\n')
        form_line = lines[line_num - 1]
        indent = len(form_line) - len(form_line.lstrip()) + 4
        csrf_line = ' ' * indent + '{{ csrf_token() }}'
        lines.insert(line_num, csrf_line)
        return '\n'.join(lines)

    patterns.append(FixPattern(
        "csrf_missing",
        "Add CSRF token to POST forms",
        [".html"],
        detect_csrf_missing,
        fix_csrf_missing,
        "security",
    ))

    # 3. Add missing imports
    def detect_undefined_name(content: str) -> List[Tuple[int, str]]:
        # This is simplified - real implementation would use AST
        matches = []
        common_missing = {
            'datetime': 'from datetime import datetime',
            'timedelta': 'from datetime import timedelta',
            'timezone': 'from datetime import timezone',
            'Dict': 'from typing import Dict',
            'List': 'from typing import List',
            'Optional': 'from typing import Optional',
            'Any': 'from typing import Any',
            'Tuple': 'from typing import Tuple',
            'Union': 'from typing import Union',
            'Path': 'from pathlib import Path',
            'json': 'import json',
            'os': 'import os',
            're': 'import re',
            'logging': 'import logging',
        }

        for name, import_stmt in common_missing.items():
            if name in content and import_stmt not in content and f'import {name}' not in content:
                # Basic check if it's actually used
                if re.search(rf'\b{name}\b', content):
                    matches.append((1, import_stmt))

        return matches

    def fix_add_import(content: str, line_num: int) -> str:
        # line_num is actually the import statement to add in this case
        return content  # Handled separately

    # 4. Convert print to logging
    def detect_print_statements(content: str) -> List[Tuple[int, str]]:
        if 'logger' in content:  # Already has logging
            return []
        # Don't convert in CLI files (they need print for output)
        if 'argparse' in content or 'cli' in content.lower():
            return []
        matches = []
        for i, line in enumerate(content.split('\n'), 1):
            if re.search(r'^\s*print\s*\(', line):
                matches.append((i, line.strip()))
        return matches

    def fix_print_to_logging(content: str, line_num: int) -> str:
        lines = content.split('\n')

        # Add logging import if not present
        if 'import logging' not in content:
            # Find last import
            last_import = 0
            for i, line in enumerate(lines):
                if line.startswith('import ') or line.startswith('from '):
                    last_import = i

            logging_setup = [
                'import logging',
                '',
                'logger = logging.getLogger(__name__)',
                '',
            ]
            lines = lines[:last_import+1] + logging_setup + lines[last_import+1:]

        # Convert print to logger.info
        for i, line in enumerate(lines):
            if re.search(r'^\s*print\s*\(', line):
                lines[i] = re.sub(r'print\s*\(', 'logger.info(', line)

        return '\n'.join(lines)

    patterns.append(FixPattern(
        "print_to_logging",
        "Convert print statements to logging",
        [".py"],
        detect_print_statements,
        fix_print_to_logging,
        "quality",
    ))

    # 5. Fix hardcoded debug mode
    def detect_debug_true(content: str) -> List[Tuple[int, str]]:
        matches = []
        for i, line in enumerate(content.split('\n'), 1):
            if re.search(r'DEBUG\s*=\s*True', line, re.I):
                matches.append((i, line.strip()))
        return matches

    def fix_debug_mode(content: str, line_num: int) -> str:
        lines = content.split('\n')

        # Add os import if needed
        if 'import os' not in content:
            for i, line in enumerate(lines):
                if line.startswith('import ') or line.startswith('from '):
                    lines.insert(i, 'import os')
                    break

        # Replace DEBUG = True
        for i, line in enumerate(lines):
            if re.search(r'DEBUG\s*=\s*True', line, re.I):
                indent = len(line) - len(line.lstrip())
                lines[i] = ' ' * indent + 'DEBUG = os.getenv("DEBUG", "False").lower() == "true"'

        return '\n'.join(lines)

    patterns.append(FixPattern(
        "debug_mode",
        "Replace hardcoded DEBUG=True with environment variable",
        [".py"],
        detect_debug_true,
        fix_debug_mode,
        "security",
    ))

    # 6. Fix shell=True in subprocess
    def detect_shell_true(content: str) -> List[Tuple[int, str]]:
        matches = []
        for i, line in enumerate(content.split('\n'), 1):
            if 'shell=True' in line and 'subprocess' in content:
                matches.append((i, line.strip()))
        return matches

    def fix_shell_true(content: str, line_num: int) -> str:
        lines = content.split('\n')
        lines[line_num - 1] = lines[line_num - 1].replace('shell=True', 'shell=False')
        return '\n'.join(lines)

    patterns.append(FixPattern(
        "shell_injection",
        "Change subprocess shell=True to shell=False",
        [".py"],
        detect_shell_true,
        fix_shell_true,
        "security",
    ))

    # 7. Add try/except to Flask routes
    def detect_unprotected_route(content: str) -> List[Tuple[int, str]]:
        if '@' not in content or 'route' not in content.lower():
            return []

        matches = []
        lines = content.split('\n')

        for i, line in enumerate(lines):
            if '@' in line and 'route' in line.lower():
                # Check the function body
                func_start = None
                for j in range(i+1, min(i+5, len(lines))):
                    if lines[j].strip().startswith('def '):
                        func_start = j
                        break

                if func_start:
                    # Check if function has try block
                    has_try = False
                    for k in range(func_start+1, min(func_start+10, len(lines))):
                        if 'try:' in lines[k]:
                            has_try = True
                            break
                        if lines[k].strip() and not lines[k].strip().startswith('#') and not lines[k].strip().startswith('"""'):
                            break

                    if not has_try:
                        matches.append((func_start + 1, lines[func_start].strip()))

        return matches

    # 8. Remove unused imports
    def detect_unused_imports(content: str) -> List[Tuple[int, str]]:
        matches = []

        # Don't detect if content has logger usage (logging is indirectly used)
        if 'logger' in content and 'logging' in content:
            return []

        try:
            tree = ast.parse(content)
            imported = {}
            used = set()

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        name = alias.asname or alias.name.split('.')[0]
                        imported[name] = node.lineno
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        for alias in node.names:
                            if alias.name != '*':
                                name = alias.asname or alias.name
                                imported[name] = node.lineno
                elif isinstance(node, ast.Name):
                    used.add(node.id)
                elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                    used.add(node.value.id)

            # Don't report logging as unused if logger is used
            if 'logger' in used and 'logging' in imported:
                del imported['logging']

            for name, line_num in imported.items():
                if name not in used and not name.startswith('_'):
                    matches.append((line_num, f'Unused import: {name}'))
        except SyntaxError:
            pass

        return matches

    def fix_unused_import(content: str, line_num: int) -> str:
        lines = content.split('\n')
        line = lines[line_num - 1].strip()

        # Simple case: remove entire line if it's a single import
        if line.startswith('import ') and ',' not in line:
            lines[line_num - 1] = ''

        # Clean up empty lines
        result = []
        prev_empty = False
        for line in lines:
            is_empty = not line.strip()
            if is_empty and prev_empty:
                continue
            result.append(line)
            prev_empty = is_empty

        return '\n'.join(result)

    patterns.append(FixPattern(
        "unused_import",
        "Remove unused imports",
        [".py"],
        detect_unused_imports,
        fix_unused_import,
        "quality",
    ))

    return patterns


class FixerAgent:
    """
    The Fixer Agent automatically fixes issues.

    Specializes in:
    - Security fixes (CSRF, XSS, SQL injection)
    - Code quality fixes (bare except, unused imports)
    - Configuration fixes (missing settings)
    - Quick bug fixes
    - Code style improvements
    """

    def __init__(self):
        self.name = "fixer"
        self.project_root = Path(__file__).parent.parent.parent
        self.scanner = ProjectScanner()

        # Load all fix patterns
        self.patterns = create_fix_patterns()

        # Legacy fix patterns (for backward compatibility)
        self.fix_patterns = {
            "bare_except": self._fix_bare_except,
            "missing_csrf": self._fix_missing_csrf,
            "hardcoded_secret": self._fix_hardcoded_secret,
            "debug_mode": self._fix_debug_mode,
            "missing_docstring": self._fix_missing_docstring,
            "unused_import": self._fix_unused_import,
            "deprecated_code": self._fix_deprecated_code,
        }

        # Statistics
        self.stats = {
            "files_scanned": 0,
            "issues_found": 0,
            "issues_fixed": 0,
            "fixes_by_category": {},
        }

    async def process_task(self, task: Task) -> Tuple[bool, str]:
        """Process a fix task"""
        logger.info(f"Fixer processing task: {task.id} - {task.title}")

        try:
            # Determine fix type from task
            fix_type = self._determine_fix_type(task)

            if fix_type and fix_type in self.fix_patterns:
                return await self._apply_fix(task, fix_type)

            # Try generic fix
            return await self._generic_fix(task)

        except Exception as e:
            logger.error(f"Fixer task failed: {e}")
            return False, str(e)

    def _determine_fix_type(self, task: Task) -> Optional[str]:
        """Determine what type of fix is needed"""
        description = task.description.lower()

        if "bare except" in description or "except Exception:" in description:
            return "bare_except"
        elif "csrf" in description:
            return "missing_csrf"
        elif "secret" in description or "password" in description:
            return "hardcoded_secret"
        elif "debug" in description:
            return "debug_mode"
        elif "docstring" in description:
            return "missing_docstring"
        elif "unused import" in description:
            return "unused_import"
        elif "deprecated" in description:
            return "deprecated_code"

        return None

    async def _apply_fix(self, task: Task, fix_type: str) -> Tuple[bool, str]:
        """Apply a specific type of fix"""
        fix_function = self.fix_patterns.get(fix_type)
        if not fix_function:
            return False, f"Unknown fix type: {fix_type}"

        fixes_applied = 0

        for file_path in task.target_files:
            full_path = self.project_root / file_path

            if not full_path.exists():
                continue

            original_content = full_path.read_text(encoding='utf-8')
            new_content = fix_function(original_content, task)

            if new_content != original_content:
                # Validate Python files
                if file_path.endswith(".py"):
                    try:
                        ast.parse(new_content)
                    except SyntaxError as e:
                        logger.error(f"Fix caused syntax error: {e}")
                        continue

                # Apply change
                change = TaskChange(
                    file_path=str(full_path),
                    change_type="modify",
                    original_content=original_content,
                    new_content=new_content,
                    description=f"Auto-fix: {fix_type}",
                )

                full_path.write_text(new_content, encoding='utf-8')
                change.applied = True
                task.changes.append(change)
                fixes_applied += 1

        if fixes_applied > 0:
            return True, f"Applied {fixes_applied} {fix_type} fix(es)"
        return False, f"No {fix_type} fixes could be applied"

    async def _generic_fix(self, task: Task) -> Tuple[bool, str]:
        """Try to apply a generic fix based on task description"""
        fixes_applied = 0

        for file_path in task.target_files:
            full_path = self.project_root / file_path

            if not full_path.exists():
                continue

            original_content = full_path.read_text(encoding='utf-8')
            new_content = original_content

            # Try all applicable fixes
            if file_path.endswith(".py"):
                new_content = self._fix_bare_except(new_content, task)
                new_content = self._fix_missing_docstring(new_content, task)
            elif file_path.endswith(".html"):
                new_content = self._fix_missing_csrf(new_content, task)

            if new_content != original_content:
                # Validate
                if file_path.endswith(".py"):
                    try:
                        ast.parse(new_content)
                    except SyntaxError:
                        continue

                change = TaskChange(
                    file_path=str(full_path),
                    change_type="modify",
                    original_content=original_content,
                    new_content=new_content,
                    description="Auto-fix: generic",
                )

                full_path.write_text(new_content, encoding='utf-8')
                change.applied = True
                task.changes.append(change)
                fixes_applied += 1

        if fixes_applied > 0:
            return True, f"Applied {fixes_applied} fix(es)"
        return False, "No fixes could be applied"

    # ============ Fix Functions ============

    def _fix_bare_except(self, content: str, task: Task) -> str:
        """Fix bare except clauses"""
        return re.sub(r'\bexcept\s*:', 'except Exception:', content)

    def _fix_missing_csrf(self, content: str, task: Task) -> str:
        """Add CSRF tokens to forms"""
        if '{{ csrf_token() }}' in content or '{{ form.hidden_tag() }}' in content:
            return content

        def add_token(match):
            return match.group(0) + '\n        {{ csrf_token() }}'

        return re.sub(
            r'<form[^>]*method=["\']post["\'][^>]*>',
            add_token,
            content,
            flags=re.IGNORECASE
        )

    def _fix_hardcoded_secret(self, content: str, task: Task) -> str:
        """Replace hardcoded secrets with environment variables"""
        # Find hardcoded secrets
        patterns = [
            (r"SECRET_KEY\s*=\s*['\"]([^'\"]{20,})['\"]",
             'SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))'),
            (r"password\s*=\s*['\"]([^'\"]+)['\"]",
             'password = os.getenv("DB_PASSWORD", "")'),
            (r"api_key\s*=\s*['\"]([^'\"]+)['\"]",
             'api_key = os.getenv("API_KEY", "")'),
        ]

        for pattern, replacement in patterns:
            if re.search(pattern, content, re.I):
                content = re.sub(pattern, replacement, content, flags=re.I)

                # Add import if needed
                if "os.getenv" in replacement and "import os" not in content:
                    content = "import os\n" + content
                if "secrets.token_hex" in replacement and "import secrets" not in content:
                    content = "import secrets\n" + content

        return content

    def _fix_debug_mode(self, content: str, task: Task) -> str:
        """Fix hardcoded debug mode"""
        # Replace DEBUG = True with environment variable
        pattern = r"DEBUG\s*=\s*True"
        replacement = 'DEBUG = os.getenv("DEBUG", "False").lower() == "true"'

        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)

            if "import os" not in content:
                content = "import os\n" + content

        return content

    def _fix_missing_docstring(self, content: str, task: Task) -> str:
        """Add basic docstrings to functions without them"""
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return content

        lines = content.split('\n')
        insertions = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Check if has docstring
                has_docstring = (
                    node.body and
                    isinstance(node.body[0], ast.Expr) and
                    isinstance(node.body[0].value, ast.Constant) and
                    isinstance(node.body[0].value.value, str)
                )

                if not has_docstring and not node.name.startswith('_'):
                    # Calculate indentation
                    func_line = lines[node.lineno - 1]
                    indent = len(func_line) - len(func_line.lstrip()) + 4
                    indent_str = ' ' * indent

                    docstring = f'{indent_str}"""TODO: Document {node.name}"""'

                    # Find the line after the function definition
                    insert_line = node.lineno
                    for i, line in enumerate(lines[node.lineno - 1:], start=node.lineno):
                        if line.rstrip().endswith(':'):
                            insert_line = i
                            break

                    insertions.append((insert_line, docstring))

        # Insert docstrings (reverse order)
        for line_no, docstring in sorted(insertions, reverse=True):
            lines.insert(line_no, docstring)

        return '\n'.join(lines)

    def _fix_unused_import(self, content: str, task: Task) -> str:
        """Remove unused imports"""
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return content

        # Collect all imported names
        imported_names = set()
        import_lines = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname or alias.name
                    imported_names.add(name.split('.')[0])
                    import_lines.add(node.lineno)
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    name = alias.asname or alias.name
                    imported_names.add(name)
                    import_lines.add(node.lineno)

        # Collect all used names
        used_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                used_names.add(node.id)
            elif isinstance(node, ast.Attribute):
                if isinstance(node.value, ast.Name):
                    used_names.add(node.value.id)

        # Find unused imports
        unused = imported_names - used_names

        if not unused:
            return content

        # Remove unused imports (be conservative - only remove single imports)
        lines = content.split('\n')
        new_lines = []

        for i, line in enumerate(lines, 1):
            if i in import_lines:
                # Check if this is a single import that's unused
                stripped = line.strip()
                if stripped.startswith('import '):
                    module = stripped[7:].split()[0].split('.')[0]
                    if module in unused:
                        continue
                elif stripped.startswith('from '):
                    # More complex - skip for safety
                    pass
            new_lines.append(line)

        return '\n'.join(new_lines)

    def _fix_deprecated_code(self, content: str, task: Task) -> str:
        """Fix deprecated code patterns"""
        # Common deprecated patterns and their replacements
        replacements = [
            (r'\.iteritems\(\)', '.items()'),  # Python 2 to 3
            (r'\.iterkeys\(\)', '.keys()'),
            (r'\.itervalues\(\)', '.values()'),
            (r'print\s+([^(])', r'print(\1)'),  # print(s)tatement to function
            (r'xrange\(', 'range('),
            (r'raw_input\(', 'input('),
        ]

        for pattern, replacement in replacements:
            content = re.sub(pattern, replacement, content)

        return content

    async def scan_and_fix_all(self) -> Dict[str, Any]:
        """Scan entire project and fix what can be fixed"""
        results = {
            "scanned_files": 0,
            "fixed_files": 0,
            "fixes": [],
            "by_category": {},
        }

        # Scan Python files
        for py_file in self.project_root.rglob("*.py"):
            if self._should_skip(py_file):
                continue

            results["scanned_files"] += 1

            try:
                original = py_file.read_text(encoding='utf-8')
                fixed = original
                fixes_applied = []

                # Apply pattern-based fixes
                for pattern in self.patterns:
                    if ".py" not in pattern.file_types:
                        continue

                    detections = pattern.detect(fixed)
                    for line_num, matched in detections:
                        try:
                            new_fixed = pattern.fix(fixed, line_num)
                            if new_fixed != fixed:
                                fixed = new_fixed
                                fixes_applied.append(pattern.name)
                        except Exception as e:
                            logger.debug(f"Fix failed for {pattern.name}: {e}")

                # Apply legacy fixes
                fixed = self._fix_bare_except(fixed, None)
                fixed = self._fix_deprecated_code(fixed, None)

                if fixed != original:
                    # Validate
                    try:
                        ast.parse(fixed)
                        py_file.write_text(fixed, encoding='utf-8')
                        results["fixed_files"] += 1
                        relative_path = str(py_file.relative_to(self.project_root))
                        results["fixes"].append({
                            "file": relative_path,
                            "patterns": fixes_applied,
                        })

                        # Track by category
                        for fix_name in fixes_applied:
                            results["by_category"][fix_name] = results["by_category"].get(fix_name, 0) + 1

                    except SyntaxError as e:
                        logger.debug(f"Fix introduced syntax error in {py_file}: {e}")

            except Exception as e:
                logger.error(f"Error fixing {py_file}: {e}")

        # Scan HTML files
        for html_file in self.project_root.rglob("*.html"):
            if self._should_skip(html_file):
                continue

            results["scanned_files"] += 1

            try:
                original = html_file.read_text(encoding='utf-8')
                fixed = original
                fixes_applied = []

                # Apply pattern-based fixes
                for pattern in self.patterns:
                    if ".html" not in pattern.file_types:
                        continue

                    detections = pattern.detect(fixed)
                    for line_num, matched in detections:
                        try:
                            new_fixed = pattern.fix(fixed, line_num)
                            if new_fixed != fixed:
                                fixed = new_fixed
                                fixes_applied.append(pattern.name)
                        except Exception as e:
                            logger.debug(f"Fix failed for {pattern.name}: {e}")

                # Apply legacy CSRF fix
                fixed = self._fix_missing_csrf(fixed, None)

                if fixed != original:
                    html_file.write_text(fixed, encoding='utf-8')
                    results["fixed_files"] += 1
                    results["fixes"].append({
                        "file": str(html_file.relative_to(self.project_root)),
                        "patterns": fixes_applied,
                    })

            except Exception as e:
                logger.error(f"Error fixing {html_file}: {e}")

        return results

    def _should_skip(self, file_path: Path) -> bool:
        """Check if file should be skipped."""
        skip_patterns = ['.git', '__pycache__', 'node_modules', '.venv', 'venv', 'migrations']
        return any(pattern in str(file_path) for pattern in skip_patterns)

    async def smart_fix(self, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Intelligently fix a list of issues.
        Returns report of what was fixed.
        """
        results = {
            "attempted": len(issues),
            "fixed": 0,
            "failed": 0,
            "details": [],
        }

        # Group issues by file
        by_file = {}
        for issue in issues:
            file_path = issue.get("file_path") or issue.get("file")
            if file_path:
                if file_path not in by_file:
                    by_file[file_path] = []
                by_file[file_path].append(issue)

        # Process each file
        for file_path, file_issues in by_file.items():
            full_path = self.project_root / file_path

            if not full_path.exists():
                continue

            try:
                original = full_path.read_text(encoding='utf-8')
                fixed = original

                for issue in file_issues:
                    issue_type = issue.get("title", "").lower()

                    # Match issue to fix pattern
                    if "bare except" in issue_type:
                        fixed = self._fix_bare_except(fixed, None)
                    elif "csrf" in issue_type:
                        fixed = self._fix_missing_csrf(fixed, None)
                    elif "debug" in issue_type:
                        fixed = self._fix_debug_mode(fixed, None)
                    elif "print" in issue_type:
                        # Use pattern-based fix
                        for pattern in self.patterns:
                            if pattern.name == "print_to_logging":
                                detections = pattern.detect(fixed)
                                for line_num, _ in detections:
                                    fixed = pattern.fix(fixed, line_num)
                                break
                    elif "unused import" in issue_type:
                        fixed = self._fix_unused_import(fixed, None)

                if fixed != original:
                    # Validate Python files
                    if file_path.endswith('.py'):
                        try:
                            ast.parse(fixed)
                        except SyntaxError:
                            results["failed"] += len(file_issues)
                            continue

                    full_path.write_text(fixed, encoding='utf-8')
                    results["fixed"] += len(file_issues)
                    results["details"].append({
                        "file": file_path,
                        "issues_fixed": len(file_issues),
                    })
                else:
                    results["failed"] += len(file_issues)

            except Exception as e:
                logger.error(f"Smart fix error for {file_path}: {e}")
                results["failed"] += len(file_issues)

        return results

    def get_fix_capabilities(self) -> List[Dict[str, str]]:
        """Return list of what this agent can fix."""
        capabilities = []

        for pattern in self.patterns:
            capabilities.append({
                "name": pattern.name,
                "description": pattern.description,
                "category": pattern.category,
                "file_types": pattern.file_types,
            })

        # Add legacy capabilities
        capabilities.extend([
            {"name": "hardcoded_secret", "description": "Replace hardcoded secrets with env vars", "category": "security"},
            {"name": "deprecated_code", "description": "Update deprecated Python patterns", "category": "quality"},
            {"name": "missing_docstring", "description": "Add docstrings to functions", "category": "quality"},
        ])

        return capabilities

    def can_handle_task(self, task: Task) -> bool:
        """Check if this agent can handle a task"""
        return task.task_type in [TaskType.BUG_FIX, TaskType.SECURITY_FIX]

