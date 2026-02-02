"""
Reviewer Agent (QA Lead)
========================

Reviews code changes for quality, security, and correctness.
Acts as the gatekeeper before changes are applied.
"""

import ast
import re
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from agents.autonomous.task_queue import Task, TaskChange
from datetime import timezone
import os
from typing import List
from typing import Optional
from typing import Any
from typing import Tuple

logger = logging.getLogger(__name__)

class ReviewResult:
    """Result of a code review"""

    def __init__(self):
        self.approved = True
        self.score = 100  # 0-100
        self.issues = []
        self.warnings = []
        self.suggestions = []

    def add_issue(self, message: str, severity: str = "error"):
        """Add an issue that blocks approval"""
        self.issues.append({"message": message, "severity": severity})
        self.approved = False
        self.score -= 20

    def add_warning(self, message: str):
        """Add a warning (doesn't block)"""
        self.warnings.append(message)
        self.score -= 5

    def add_suggestion(self, message: str):
        """Add a suggestion for improvement"""
        self.suggestions.append(message)
        self.score -= 2

    def to_dict(self) -> Dict[str, Any]:
        return {
            "approved": self.approved,
            "score": max(0, self.score),
            "issues": self.issues,
            "warnings": self.warnings,
            "suggestions": self.suggestions,
        }

class ReviewerAgent:
    """
    The Reviewer Agent validates code changes.

    Reviews for:
    - Syntax correctness
    - Security vulnerabilities
    - Code style
    - Best practices
    - Test coverage
    """

    def __init__(self):
        self.name = "reviewer"
        self.project_root = Path(__file__).parent.parent.parent

        # Security patterns to check
        self.security_patterns = [
            (r'eval\s*\(', "Dangerous eval() usage"),
            (r'exec\s*\(', "Dangerous exec() usage"),
            (r'__import__\s*\(', "Dynamic import - potential security risk"),
            (r'subprocess\.call\s*\([^)]*shell\s*=\s*True', "Shell injection risk"),
            (r'os\.system\s*\(', "Shell command execution risk"),
            (r'pickle\.loads?\s*\(', "Pickle deserialization risk"),
            (r'yaml\.load\s*\([^)]*\)', "Unsafe YAML load"),
        ]

        # Code smell patterns
        self.code_smells = [
            (r'except\s*:', "Bare except clause"),
            (r'# TODO', "Unresolved TODO"),
            (r'# FIXME', "Unresolved FIXME"),
            (r'# HACK', "Hack in code"),
            (r'password\s*=\s*["\'][^"\']+["\']', "Potential hardcoded password"),
            (r'api_key\s*=\s*["\'][^"\']+["\']', "Potential hardcoded API key"),
        ]

    async def review_task(self, task: Task) -> ReviewResult:
        """
        Review a completed task.
        Returns ReviewResult with approval status and notes.
        """
        result = ReviewResult()

        if not task.changes:
            result.add_warning("No changes to review")
            return result

        for change in task.changes:
            change_result = await self._review_change(change)

            # Merge results
            for issue in change_result.issues:
                result.add_issue(f"{change.file_path}: {issue['message']}", issue['severity'])

            for warning in change_result.warnings:
                result.add_warning(f"{change.file_path}: {warning}")

            for suggestion in change_result.suggestions:
                result.add_suggestion(f"{change.file_path}: {suggestion}")

        return result

    async def _review_change(self, change: TaskChange) -> ReviewResult:
        """Review a single file change"""
        result = ReviewResult()

        if not change.new_content:
            return result

        file_path = change.file_path
        content = change.new_content

        # Python-specific checks
        if file_path.endswith('.py'):
            result = await self._review_python(content, result)

        # HTML-specific checks
        elif file_path.endswith('.html'):
            result = await self._review_html(content, result)

        # JavaScript checks
        elif file_path.endswith('.js'):
            result = await self._review_javascript(content, result)

        # General security check
        result = self._check_security(content, result)

        return result

    async def _review_python(self, content: str, result: ReviewResult) -> ReviewResult:
        """Review Python code"""

        # 1. Syntax check
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            result.add_issue(f"Syntax error: {e}", "critical")
            return result  # Can't continue with syntax error

        # 2. Check for code smells
        for pattern, message in self.code_smells:
            if re.search(pattern, content, re.IGNORECASE):
                result.add_warning(message)

        # 3. Function complexity check
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Check function length
                func_lines = (node.end_lineno or 0) - node.lineno
                if func_lines > 100:
                    result.add_issue(f"Function {node.name} is too long ({func_lines} lines)")
                elif func_lines > 50:
                    result.add_warning(f"Function {node.name} is long ({func_lines} lines)")

                # Check nesting depth
                max_depth = self._get_max_nesting(node)
                if max_depth > 5:
                    result.add_warning(f"Function {node.name} has deep nesting (depth: {max_depth})")

                # Check parameter count
                param_count = len(node.args.args) + len(node.args.kwonlyargs)
                if param_count > 7:
                    result.add_warning(f"Function {node.name} has too many parameters ({param_count})")

        # 4. Check for missing docstrings (public functions only)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.startswith('_'):
                    has_docstring = (
                        node.body and
                        isinstance(node.body[0], ast.Expr) and
                        isinstance(node.body[0].value, ast.Constant) and
                        isinstance(node.body[0].value.value, str)
                    )
                    if not has_docstring:
                        result.add_suggestion(f"Function {node.name} lacks docstring")

        # 5. Check imports
        import_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    import_names.add(alias.asname or alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    import_names.add(alias.asname or alias.name)

        # Check for unused imports (basic check)
        used_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                used_names.add(node.id)

        unused = import_names - used_names
        for name in unused:
            if not name.startswith('_'):
                result.add_suggestion(f"Potentially unused import: {name}")

        return result

    async def _review_html(self, content: str, result: ReviewResult) -> ReviewResult:
        """Review HTML templates"""

        # Check for CSRF tokens in forms
        if '<form' in content.lower() and 'method="post"' in content.lower():
            if 'csrf_token' not in content and 'hidden_tag' not in content:
                result.add_issue("Form missing CSRF protection", "security")

        # Check for XSS vulnerabilities (basic)
        if '{{ ' in content:
            # Check for |safe without sanitization
            if '|safe' in content and 'bleach' not in content:
                result.add_warning("Using |safe filter - ensure content is sanitized")

        # Check for inline JavaScript
        if '<script>' in content.lower():
            result.add_suggestion("Consider moving JavaScript to separate files")

        # Check for inline styles
        if 'style="' in content.lower():
            result.add_suggestion("Consider using CSS classes instead of inline styles")

        return result

    async def _review_javascript(self, content: str, result: ReviewResult) -> ReviewResult:
        """Review JavaScript code"""

        # Check for eval
        if 'eval(' in content:
            result.add_issue("Dangerous eval() usage", "security")

        # Check for innerHTML
        if '.innerHTML' in content:
            result.add_warning("innerHTML usage - ensure content is sanitized")

        # Check for console.log (should be removed in production)
        if 'console.log' in content:
            result.add_suggestion("Remove console.log before production")

        # Check for var (should use let/const)
        if re.search(r'\bvar\s+', content):
            result.add_suggestion("Use let/const instead of var")

        return result

    def _check_security(self, content: str, result: ReviewResult) -> ReviewResult:
        """Check for security issues in any file"""

        for pattern, message in self.security_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                result.add_issue(message, "security")

        return result

    def _get_max_nesting(self, node: ast.AST, current_depth: int = 0) -> int:
        """Get maximum nesting depth of a function"""
        max_depth = current_depth

        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                child_depth = self._get_max_nesting(child, current_depth + 1)
                max_depth = max(max_depth, child_depth)
            else:
                child_depth = self._get_max_nesting(child, current_depth)
                max_depth = max(max_depth, child_depth)

        return max_depth

    async def review_file(self, file_path: Path) -> ReviewResult:
        """Review a single file"""
        result = ReviewResult()

        if not file_path.exists():
            result.add_issue(f"File not found: {file_path}")
            return result

        try:
            content = file_path.read_text(encoding='utf-8')

            change = TaskChange(
                file_path=str(file_path),
                change_type="review",
                new_content=content,
            )

            return await self._review_change(change)

        except Exception as e:
            result.add_issue(f"Error reading file: {e}")
            return result

    async def full_codebase_review(self) -> Dict[str, Any]:
        """Review entire codebase"""
        results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "files_reviewed": 0,
            "total_score": 0,
            "issues": [],
            "warnings": [],
            "suggestions": [],
            "by_file": {},
        }

        file_count = 0
        total_score = 0

        for py_file in self.project_root.rglob("*.py"):
            if ".git" in str(py_file) or "__pycache__" in str(py_file):
                continue

            relative_path = str(py_file.relative_to(self.project_root))
            review = await self.review_file(py_file)

            file_count += 1
            total_score += review.score

            results["by_file"][relative_path] = review.to_dict()
            results["issues"].extend([f"{relative_path}: {i['message']}" for i in review.issues])
            results["warnings"].extend([f"{relative_path}: {w}" for w in review.warnings])
            results["suggestions"].extend([f"{relative_path}: {s}" for s in review.suggestions])

        results["files_reviewed"] = file_count
        results["total_score"] = int(total_score / max(file_count, 1))

        return results

