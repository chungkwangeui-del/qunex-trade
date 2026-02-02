"""
Smart Analyzer
==============

Deep code analysis that understands patterns, identifies problems,
and provides intelligent suggestions for fixes and improvements.
"""

import ast
import re

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Set, Tuple
from pathlib import Path
from collections import defaultdict
from datetime import timezone
import os
from typing import List
from typing import Optional
from typing import Any
from typing import Tuple

logger = logging.getLogger(__name__)

@dataclass
class CodeIssue:
    """Represents a detected code issue."""
    file_path: str
    line_number: int
    category: str  # security, quality, performance, style, bug
    severity: str  # critical, high, medium, low, info
    title: str
    description: str
    suggestion: Optional[str] = None
    auto_fixable: bool = False
    fix_code: Optional[str] = None  # The fix to apply
    context_before: Optional[str] = None
    context_after: Optional[str] = None

@dataclass
class FileAnalysis:
    """Analysis results for a single file."""
    file_path: str
    issues: List[CodeIssue] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    suggestions: List[str] = field(default_factory=list)

class SmartAnalyzer:
    """
    Intelligent code analyzer that understands patterns and context.

    Capabilities:
    - Security vulnerability detection
    - Code quality analysis
    - Performance issue detection
    - Dead code detection
    - Complexity analysis
    - Pattern recognition
    """

    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent

        # Security patterns to check
        # NOTE: auto_fixable should ONLY be True if RealFixerAgent can actually fix it!
        # Currently RealFixerAgent only fixes Python SYNTAX errors.
        self.security_patterns = [
            {
                "name": "hardcoded_secret",
                "pattern": r"(password|secret|api_key|apikey|token)\s*=\s*['\"][^'\"]{8,}['\"]",
                "severity": "critical",
                "suggestion": "Move to environment variable",
                "auto_fixable": False,  # Requires manual refactoring
            },
            {
                "name": "sql_injection",
                "pattern": r"execute\([^%]*%[^%]*\)|execute\([^+]*\+[^+]*\)|f['\"].*SELECT.*{.*}",
                "severity": "critical",
                "suggestion": "Use parameterized queries",
                "auto_fixable": False,  # Requires code rewrite
            },
            {
                "name": "debug_enabled",
                "pattern": r"DEBUG\s*=\s*True|debug\s*=\s*True",
                "severity": "high",
                "suggestion": "Set DEBUG=False in production",
                "auto_fixable": False,  # May be intentional for dev
            },
            {
                "name": "weak_random",
                "pattern": r"import random\b(?!.*secrets)",
                "severity": "medium",
                "suggestion": "Use secrets module for security",
                "auto_fixable": False,
            },
            {
                "name": "pickle_load",
                "pattern": r"pickle\.load\(|pickle\.loads\(",
                "severity": "high",
                "suggestion": "Pickle can execute arbitrary code",
                "auto_fixable": False,
            },
            {
                "name": "eval_usage",
                "pattern": r"\beval\s*\(|\bexec\s*\(",
                "severity": "critical",
                "suggestion": "Avoid eval/exec - use ast.literal_eval",
                "auto_fixable": False,
            },
            {
                "name": "shell_injection",
                "pattern": r"subprocess\..*shell\s*=\s*True|os\.system\(",
                "severity": "high",
                "suggestion": "Use subprocess with shell=False",
                "auto_fixable": False,  # Requires code restructure
            },
        ]

        # Quality patterns
        # NOTE: auto_fixable=False for all - RealFixerAgent only fixes syntax errors
        self.quality_patterns = [
            {
                "name": "bare_except",
                "pattern": r"except\s*:",
                "severity": "medium",
                "suggestion": "Use except Exception:",
                "auto_fixable": False,  # Simple but risky auto-replace
            },
            {
                "name": "pass_in_except",
                "pattern": r"except.*:\s*\n\s*pass\s*$",
                "severity": "medium",
                "suggestion": "Log exceptions instead of silencing",
                "auto_fixable": False,
            },
            {
                "name": "print_statement",
                "pattern": r"^\s*print\s*\(",
                "severity": "low",
                "suggestion": "Use logging instead of print",
                "auto_fixable": False,  # Removing prints can break things
            },
            {
                "name": "magic_number",
                "pattern": r"(?<!['\"\w])\b(?!0\b|1\b|2\b)([3-9]|\d{2,})\b(?!['\"\w])",
                "severity": "low",
                "suggestion": "Use named constants for clarity",
                "auto_fixable": False,
            },
            {
                "name": "long_line",
                "pattern": r"^.{121,}$",
                "severity": "info",
                "suggestion": "Line exceeds 120 characters",
                "auto_fixable": False,
            },
            {
                "name": "todo_fixme",
                "pattern": r"#\s*(TODO|FIXME|XXX|HACK)\b",
                "severity": "info",
                "suggestion": "Address TODO/FIXME items",
                "auto_fixable": False,
            },
        ]

        # Flask-specific patterns
        # NOTE: All False - requires careful manual review
        self.flask_patterns = [
            {
                "name": "missing_csrf",
                "pattern": r"<form[^>]*method=['\"]post['\"][^>]*>(?!.*csrf)",
                "severity": "high",
                "suggestion": "Add CSRF token to form",
                "auto_fixable": False,  # HTML modification risky
            },
            {
                "name": "unprotected_route",
                "pattern": r"@\w+\.route\([^)]+\)\s*\n(?!.*@login_required)def",
                "severity": "medium",
                "suggestion": "Consider adding @login_required",
                "auto_fixable": False,
            },
            {
                "name": "missing_error_handler",
                "pattern": r"@\w+\.route.*\ndef \w+\([^)]*\):\s*\n(?!\s*try:)",
                "severity": "low",
                "suggestion": "Add try/except for error handling",
                "auto_fixable": False,  # Adding try/except needs context
            },
        ]

        # Import patterns
        self.import_patterns = [
            {
                "name": "star_import",
                "pattern": r"from \w+ import \*",
                "severity": "medium",
                "suggestion": "Avoid star imports",
                "auto_fixable": False,
            },
            {
                "name": "unused_import",
                "pattern": None,  # Checked via AST
                "severity": "low",
                "suggestion": "Remove unused import",
                "auto_fixable": False,  # Requires AST analysis
            },
        ]

    def analyze_project(self) -> Dict[str, Any]:
        """Analyze entire project and return comprehensive report."""
        results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "files_analyzed": 0,
            "total_issues": 0,
            "issues_by_severity": defaultdict(int),
            "issues_by_category": defaultdict(int),
            "auto_fixable_count": 0,
            "files": {},
            "top_issues": [],
            "health_score": 100,
        }

        py_files = list(self.project_root.rglob("*.py"))
        html_files = list(self.project_root.rglob("*.html"))

        # Analyze Python files
        for py_file in py_files:
            if self._should_skip(py_file):
                continue

            analysis = self.analyze_file(py_file)
            if analysis.issues:
                results["files"][str(py_file.relative_to(self.project_root))] = {
                    "issues": [self._issue_to_dict(i) for i in analysis.issues],
                    "metrics": analysis.metrics,
                }

                for issue in analysis.issues:
                    results["total_issues"] += 1
                    results["issues_by_severity"][issue.severity] += 1
                    results["issues_by_category"][issue.category] += 1
                    if issue.auto_fixable:
                        results["auto_fixable_count"] += 1

            results["files_analyzed"] += 1

        # Analyze HTML files for security issues
        for html_file in html_files:
            if self._should_skip(html_file):
                continue

            analysis = self.analyze_html_file(html_file)
            if analysis.issues:
                results["files"][str(html_file.relative_to(self.project_root))] = {
                    "issues": [self._issue_to_dict(i) for i in analysis.issues],
                }

                for issue in analysis.issues:
                    results["total_issues"] += 1
                    results["issues_by_severity"][issue.severity] += 1
                    results["issues_by_category"][issue.category] += 1
                    if issue.auto_fixable:
                        results["auto_fixable_count"] += 1

            results["files_analyzed"] += 1

        # Calculate health score
        results["health_score"] = self._calculate_health_score(results)

        # Get top issues
        all_issues = []
        for file_data in results["files"].values():
            all_issues.extend(file_data.get("issues", []))

        # Sort by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        all_issues.sort(key=lambda x: severity_order.get(x["severity"], 5))
        results["top_issues"] = all_issues[:20]

        return results

    def analyze_file(self, file_path: Path) -> FileAnalysis:
        """Analyze a single Python file."""
        analysis = FileAnalysis(file_path=str(file_path))

        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.split('\n')
            relative_path = str(file_path.relative_to(self.project_root))

            # Calculate metrics
            analysis.metrics = self._calculate_metrics(content, lines)

            # Check security patterns
            for pattern_info in self.security_patterns:
                self._check_pattern(content, lines, relative_path, pattern_info, "security", analysis)

            # Check quality patterns
            for pattern_info in self.quality_patterns:
                self._check_pattern(content, lines, relative_path, pattern_info, "quality", analysis)

            # Check Flask patterns
            if 'flask' in content.lower() or '@' in content and 'route' in content:
                for pattern_info in self.flask_patterns:
                    self._check_pattern(content, lines, relative_path, pattern_info, "security", analysis)

            # AST-based analysis
            self._ast_analysis(content, relative_path, analysis)

        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {e}")

        return analysis

    def analyze_html_file(self, file_path: Path) -> FileAnalysis:
        """Analyze an HTML file for security issues."""
        analysis = FileAnalysis(file_path=str(file_path))

        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.split('\n')
            relative_path = str(file_path.relative_to(self.project_root))

            # Check for forms without CSRF
            for i, line in enumerate(lines, 1):
                if '<form' in line.lower() and 'method' in line.lower() and 'post' in line.lower():
                    # Check next few lines for csrf_token
                    form_content = '\n'.join(lines[i-1:i+10])
                    if 'csrf' not in form_content.lower():
                        analysis.issues.append(CodeIssue(
                            file_path=relative_path,
                            line_number=i,
                            category="security",
                            severity="high",
                            title="Form missing CSRF token",
                            description=f"POST form at line {i} doesn't have CSRF protection",
                            suggestion="Add {{ csrf_token() }} inside the form",
                            auto_fixable=True,
                        ))

            # Check for inline JavaScript
            if '<script>' in content and ('onclick=' in content or 'javascript:' in content):
                analysis.issues.append(CodeIssue(
                    file_path=relative_path,
                    line_number=1,
                    category="quality",
                    severity="low",
                    title="Inline JavaScript detected",
                    description="Consider moving JavaScript to external files",
                    auto_fixable=False,
                ))

        except Exception as e:
            logger.error(f"Error analyzing HTML {file_path}: {e}")

        return analysis

    def _check_pattern(
        self,
        content: str,
        lines: List[str],
        file_path: str,
        pattern_info: Dict,
        category: str,
        analysis: FileAnalysis,
    ) -> None:
        """Check a pattern against file content."""
        if pattern_info.get("pattern") is None:
            return

        try:
            matches = re.finditer(pattern_info["pattern"], content, re.MULTILINE | re.IGNORECASE)

            for match in matches:
                # Find line number
                line_num = content[:match.start()].count('\n') + 1

                # Get context
                context_start = max(0, line_num - 2)
                context_end = min(len(lines), line_num + 2)

                analysis.issues.append(CodeIssue(
                    file_path=file_path,
                    line_number=line_num,
                    category=category,
                    severity=pattern_info["severity"],
                    title=pattern_info["name"].replace("_", " ").title(),
                    description=f"Found {pattern_info['name']} pattern",
                    suggestion=pattern_info.get("suggestion"),
                    auto_fixable=pattern_info.get("auto_fixable", False),
                    context_before='\n'.join(lines[context_start:line_num-1]),
                    context_after='\n'.join(lines[line_num:context_end]),
                ))
        except re.error as e:
            logger.debug(f"Regex error for pattern {pattern_info['name']}: {e}")

    def _ast_analysis(self, content: str, file_path: str, analysis: FileAnalysis) -> None:
        """Perform AST-based code analysis."""
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            analysis.issues.append(CodeIssue(
                file_path=file_path,
                line_number=e.lineno or 1,
                category="bug",
                severity="critical",
                title="Syntax Error",
                description=str(e.msg),
                auto_fixable=False,
            ))
            return

        # Collect imports
        imported_names = set()
        used_names = set()

        for node in ast.walk(tree):
            # Track imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname or alias.name.split('.')[0]
                    imported_names.add((name, node.lineno))
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name != '*':
                        name = alias.asname or alias.name
                        imported_names.add((name, node.lineno))

            # Track name usage
            elif isinstance(node, ast.Name):
                used_names.add(node.id)
            elif isinstance(node, ast.Attribute):
                if isinstance(node.value, ast.Name):
                    used_names.add(node.value.id)

            # Check for complexity
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                complexity = self._calculate_complexity(node)
                if complexity > 10:
                    analysis.issues.append(CodeIssue(
                        file_path=file_path,
                        line_number=node.lineno,
                        category="quality",
                        severity="medium" if complexity < 20 else "high",
                        title=f"High complexity: {node.name}",
                        description=f"Function has cyclomatic complexity of {complexity}",
                        suggestion="Break into smaller functions",
                        auto_fixable=False,
                    ))

                # Check for too many arguments
                if len(node.args.args) > 5:
                    analysis.issues.append(CodeIssue(
                        file_path=file_path,
                        line_number=node.lineno,
                        category="quality",
                        severity="low",
                        title=f"Too many arguments: {node.name}",
                        description=f"Function has {len(node.args.args)} arguments",
                        suggestion="Consider using a data class or config object",
                        auto_fixable=False,
                    ))

        # Check for unused imports
        for name, line_num in imported_names:
            if name not in used_names and not name.startswith('_'):
                analysis.issues.append(CodeIssue(
                    file_path=file_path,
                    line_number=line_num,
                    category="quality",
                    severity="low",
                    title=f"Unused import: {name}",
                    description=f"'{name}' is imported but not used",
                    suggestion="Remove unused import",
                    auto_fixable=True,
                ))

    def _calculate_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity of a function."""
        complexity = 1

        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif isinstance(child, (ast.And, ast.Or)):
                complexity += 1

        return complexity

    def _calculate_metrics(self, content: str, lines: List[str]) -> Dict[str, Any]:
        """Calculate file metrics."""
        return {
            "lines": len(lines),
            "non_empty_lines": len([l for l in lines if l.strip()]),
            "comment_lines": len([l for l in lines if l.strip().startswith('#')]),
            "docstring_lines": content.count('"""') // 2 + content.count("'''") // 2,
        }

    def _calculate_health_score(self, results: Dict[str, Any]) -> int:
        """Calculate overall health score (0-100)."""
        score = 100

        # Deduct for issues by severity
        severity_weights = {
            "critical": 10,
            "high": 5,
            "medium": 2,
            "low": 1,
            "info": 0,
        }

        for severity, count in results["issues_by_severity"].items():
            score -= severity_weights.get(severity, 0) * count

        return max(0, min(100, score))

    def _issue_to_dict(self, issue: CodeIssue) -> Dict[str, Any]:
        """Convert CodeIssue to dictionary."""
        return {
            "file_path": issue.file_path,
            "line_number": issue.line_number,
            "category": issue.category,
            "severity": issue.severity,
            "title": issue.title,
            "description": issue.description,
            "suggestion": issue.suggestion,
            "auto_fixable": issue.auto_fixable,
        }

    def _should_skip(self, file_path: Path) -> bool:
        """Check if file should be skipped."""
        skip_patterns = ['.git', '__pycache__', 'node_modules', '.venv', 'venv', 'env', 'migrations']
        return any(pattern in str(file_path) for pattern in skip_patterns)

    def get_auto_fixable_issues(self) -> List[CodeIssue]:
        """Get all issues that can be automatically fixed."""
        results = self.analyze_project()
        auto_fixable = []

        for file_data in results["files"].values():
            for issue in file_data.get("issues", []):
                if issue.get("auto_fixable"):
                    auto_fixable.append(CodeIssue(
                        file_path=issue["file_path"],
                        line_number=issue["line_number"],
                        category=issue["category"],
                        severity=issue["severity"],
                        title=issue["title"],
                        description=issue["description"],
                        suggestion=issue.get("suggestion"),
                        auto_fixable=True,
                    ))

        return auto_fixable

