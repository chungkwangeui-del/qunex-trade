"""
Project Scanner
===============

Real-time codebase analysis and health checking.
This module scans the project for issues, errors, and improvement opportunities.
"""

import os
import re
import ast
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
from datetime import timezone
from typing import List
from typing import Optional
from typing import Any
from typing import Tuple

logger = logging.getLogger(__name__)


@dataclass
class ScanResult:
    """Result of a scan operation"""
    category: str
    severity: str  # info, warning, error, critical
    file: Optional[str] = None
    line: Optional[int] = None
    message: str = ""
    suggestion: str = ""
    auto_fixable: bool = False
    fix_code: Optional[str] = None


class ProjectScanner:
    """
    Scans the project for issues and improvements.

    Features:
    - Python syntax validation
    - Import error detection
    - Unused variable detection
    - Code style issues
    - Security vulnerabilities
    - Performance concerns
    - Missing files detection
    """

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.issues: List[ScanResult] = []
        self.stats: Dict[str, Any] = {}

    def scan_all(self) -> Dict[str, Any]:
        """Run all scans and return comprehensive report."""
        self.issues = []
        self.stats = {
            "total_files": 0,
            "total_lines": 0,
            "python_files": 0,
            "template_files": 0,
            "static_files": 0,
            "scan_time": datetime.now(timezone.utc).isoformat(),
        }

        # Run all scans
        self._scan_python_files()
        self._scan_templates()
        self._scan_config()
        self._scan_security()
        self._scan_database_models()
        self._scan_api_routes()

        return {
            "issues": [self._result_to_dict(r) for r in self.issues],
            "stats": self.stats,
            "summary": self._generate_summary(),
        }

    def _result_to_dict(self, result: ScanResult) -> Dict[str, Any]:
        return {
            "category": result.category,
            "severity": result.severity,
            "file": result.file,
            "line": result.line,
            "message": result.message,
            "suggestion": result.suggestion,
            "auto_fixable": result.auto_fixable,
            "fix_code": result.fix_code,
        }

    def _scan_python_files(self) -> None:
        """Scan all Python files for issues."""
        web_dir = self.project_root / "web"
        agents_dir = self.project_root / "agents"
        scripts_dir = self.project_root / "scripts"

        for directory in [web_dir, agents_dir, scripts_dir]:
            if directory.exists():
                for py_file in directory.rglob("*.py"):
                    self.stats["python_files"] = self.stats.get("python_files", 0) + 1
                    self._analyze_python_file(py_file)

    def _analyze_python_file(self, filepath: Path) -> None:
        """Analyze a single Python file."""
        try:
            content = filepath.read_text(encoding='utf-8')
            lines = content.splitlines()
            self.stats["total_lines"] = self.stats.get("total_lines", 0) + len(lines)

            relative_path = str(filepath.relative_to(self.project_root))

            # Check syntax
            try:
                tree = ast.parse(content)
            except SyntaxError as e:
                self.issues.append(ScanResult(
                    category="Syntax",
                    severity="error",
                    file=relative_path,
                    line=e.lineno,
                    message=f"Syntax error: {e.msg}",
                    suggestion="Fix the syntax error before running the code",
                    auto_fixable=False,
                ))
                return  # Can't continue if syntax error

            # Check for common issues
            self._check_imports(tree, relative_path, content)
            self._check_function_size(tree, relative_path)
            self._check_exception_handling(tree, relative_path)
            self._check_hardcoded_secrets(content, relative_path, lines)
            self._check_todo_comments(content, relative_path, lines)

            # Check file size
            if len(lines) > 500:
                self.issues.append(ScanResult(
                    category="Code Quality",
                    severity="warning",
                    file=relative_path,
                    message=f"File has {len(lines)} lines - consider splitting into modules",
                    suggestion="Split large files into smaller, focused modules",
                ))

        except Exception as e:
            self.issues.append(ScanResult(
                category="Scanner",
                severity="info",
                file=str(filepath),
                message=f"Could not analyze: {e}",
            ))

    def _check_imports(self, tree: ast.AST, filepath: str, content: str) -> None:
        """Check for import issues."""
        imported_names = set()
        import_lines = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_names.add(alias.asname or alias.name)
                    import_lines.append((alias.name, node.lineno))
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for alias in node.names:
                        imported_names.add(alias.asname or alias.name)
                        import_lines.append((f"{node.module}.{alias.name}", node.lineno))

        # Check for common missing imports
        if "logging" in content and "import logging" not in content and "from logging" not in content:
            self.issues.append(ScanResult(
                category="Import",
                severity="warning",
                file=filepath,
                message="Using 'logging' but not imported",
                suggestion="Add 'import logging' at the top",
                auto_fixable=True,
                fix_code="import logging\n",
            ))

    def _check_function_size(self, tree: ast.AST, filepath: str) -> None:
        """Check for overly long functions."""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_lines = node.end_lineno - node.lineno if node.end_lineno else 0
                if func_lines > 50:
                    self.issues.append(ScanResult(
                        category="Code Quality",
                        severity="warning",
                        file=filepath,
                        line=node.lineno,
                        message=f"Function '{node.name}' is {func_lines} lines - consider breaking it up",
                        suggestion="Split into smaller, focused functions",
                    ))

    def _check_exception_handling(self, tree: ast.AST, filepath: str) -> None:
        """Check for bare except clauses."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    self.issues.append(ScanResult(
                        category="Code Quality",
                        severity="warning",
                        file=filepath,
                        line=node.lineno,
                        message="Bare 'except Exception:' clause catches all exceptions including KeyboardInterrupt",
                        suggestion="Use 'except Exception:' or specific exception types",
                        auto_fixable=True,
                    ))

    def _check_hardcoded_secrets(self, content: str, filepath: str, lines: List[str]) -> None:
        """Check for hardcoded secrets/passwords."""
        secret_patterns = [
            (r'password\s*=\s*["\'][^"\']+["\']', "Hardcoded password detected"),
            (r'api_key\s*=\s*["\'][^"\']+["\']', "Hardcoded API key detected"),
            (r'secret\s*=\s*["\'][a-zA-Z0-9]{20,}["\']', "Possible hardcoded secret"),
            (r'token\s*=\s*["\'][^"\']+["\']', "Hardcoded token detected"),
        ]

        for i, line in enumerate(lines):
            line_lower = line.lower()
            for pattern, message in secret_patterns:
                if re.search(pattern, line_lower) and "os.getenv" not in line and "os.environ" not in line:
                    self.issues.append(ScanResult(
                        category="Security",
                        severity="error",
                        file=filepath,
                        line=i + 1,
                        message=message,
                        suggestion="Use environment variables for secrets",
                        auto_fixable=False,
                    ))
                    break

    def _check_todo_comments(self, content: str, filepath: str, lines: List[str]) -> None:
        """Find TODO/FIXME comments."""
        for i, line in enumerate(lines):
            if "# TODO" in line or "# FIXME" in line or "# XXX" in line:
                comment = line.split("#", 1)[1].strip()
                self.issues.append(ScanResult(
                    category="TODO",
                    severity="info",
                    file=filepath,
                    line=i + 1,
                    message=comment,
                ))

    def _scan_templates(self) -> None:
        """Scan HTML templates for issues."""
        templates_dir = self.project_root / "web" / "templates"
        if not templates_dir.exists():
            self.issues.append(ScanResult(
                category="Templates",
                severity="error",
                message="Templates directory not found",
            ))
            return

        for html_file in templates_dir.rglob("*.html"):
            self.stats["template_files"] = self.stats.get("template_files", 0) + 1
            relative_path = str(html_file.relative_to(self.project_root))

            try:
                content = html_file.read_text(encoding='utf-8')

                # Check for missing CSRF tokens in forms
                if "<form" in content.lower() and "method=\"post\"" in content.lower():
                    if "csrf_token" not in content and "hidden_tag" not in content:
                        self.issues.append(ScanResult(
                            category="Security",
                            severity="error",
                            file=relative_path,
                            message="Form missing CSRF token",
                            suggestion="Add {{ form.hidden_tag() }} or {{ csrf_token() }}",
                            auto_fixable=False,
                        ))

                # Check for deprecated tags
                deprecated = ["<center>", "<font>", "<marquee>"]
                for tag in deprecated:
                    if tag in content.lower():
                        self.issues.append(ScanResult(
                            category="HTML",
                            severity="warning",
                            file=relative_path,
                            message=f"Deprecated HTML tag: {tag}",
                            suggestion="Use CSS for styling instead",
                        ))

            except Exception as e:
                pass

    def _scan_config(self) -> None:
        """Scan configuration for issues."""
        # Check requirements.txt
        req_file = self.project_root / "requirements.txt"
        if req_file.exists():
            content = req_file.read_text(encoding='utf-8')
            lines = content.splitlines()

            for i, line in enumerate(lines):
                line = line.strip()
                if line and not line.startswith("#"):
                    # Check for unpinned versions
                    if "==" not in line and ">=" not in line and "<=" not in line:
                        if line and not line.startswith("-"):
                            self.issues.append(ScanResult(
                                category="Dependencies",
                                severity="warning",
                                file="requirements.txt",
                                line=i + 1,
                                message=f"Package '{line}' has no version pinned",
                                suggestion="Pin versions for reproducible builds (e.g., package==1.0.0)",
                            ))
        else:
            self.issues.append(ScanResult(
                category="Configuration",
                severity="error",
                message="requirements.txt not found",
            ))

        # Check for .env file
        env_file = self.project_root / ".env"
        if not env_file.exists():
            self.issues.append(ScanResult(
                category="Configuration",
                severity="info",
                message=".env file not found - using environment variables or defaults",
            ))

    def _scan_security(self) -> None:
        """Scan for security issues."""
        config_file = self.project_root / "web" / "config.py"
        if config_file.exists():
            content = config_file.read_text(encoding='utf-8')

            # Check for DEBUG mode in config
            if "DEBUG = True" in content:
                self.issues.append(ScanResult(
                    category="Security",
                    severity="error",
                    file="web/config.py",
                    message="DEBUG mode is hardcoded to True",
                    suggestion="Use environment variable: DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'",
                ))

            # Check for weak secret key
            if "SECRET_KEY = " in content and "os.getenv" not in content.split("SECRET_KEY")[1].split("\n")[0]:
                self.issues.append(ScanResult(
                    category="Security",
                    severity="error",
                    file="web/config.py",
                    message="SECRET_KEY may be hardcoded",
                    suggestion="Use environment variable: SECRET_KEY = os.getenv('SECRET_KEY', secrets.token_hex(32))",
                ))

    def _scan_database_models(self) -> None:
        """Scan database models for issues."""
        db_file = self.project_root / "web" / "database.py"
        if not db_file.exists():
            self.issues.append(ScanResult(
                category="Database",
                severity="error",
                message="database.py not found",
            ))
            return

        try:
            content = db_file.read_text(encoding='utf-8')

            # Check for missing indexes on foreign keys
            fk_pattern = r'ForeignKey\([\'"]([^"\']+)[\'"]\)'
            fks = re.findall(fk_pattern, content)

            if fks:
                # Just info - not necessarily an issue
                pass

            # Check for missing __tablename__
            class_pattern = r'class\s+(\w+)\(.*Model.*\):'
            classes = re.findall(class_pattern, content)

            for class_name in classes:
                # Extract class body and check for __tablename__
                class_start = content.find(f"class {class_name}")
                if class_start != -1:
                    next_class = content.find("class ", class_start + 1)
                    class_body = content[class_start:next_class] if next_class != -1 else content[class_start:]

                    if "__tablename__" not in class_body:
                        self.issues.append(ScanResult(
                            category="Database",
                            severity="warning",
                            file="web/database.py",
                            message=f"Model '{class_name}' missing explicit __tablename__",
                            suggestion="Add __tablename__ = 'table_name' for clarity",
                        ))

        except Exception as e:
            logger.error(f"Error scanning database.py: {e}")

    def _scan_api_routes(self) -> None:
        """Scan API routes for issues."""
        web_dir = self.project_root / "web"

        for api_file in web_dir.glob("api_*.py"):
            try:
                content = api_file.read_text(encoding='utf-8')
                relative_path = str(api_file.relative_to(self.project_root))

                # Check for routes without authentication
                if "@login_required" not in content and "@jwt_required" not in content:
                    # Check if this is a public API
                    if "Blueprint" in content:
                        self.issues.append(ScanResult(
                            category="Security",
                            severity="info",
                            file=relative_path,
                            message="API blueprint(h)as no @login_required decorators - ensure this is intentional",
                            suggestion="Add @login_required to protected endpoints",
                        ))

                # Check for proper error handling
                if "try:" not in content and "except" not in content:
                    self.issues.append(ScanResult(
                        category="Error Handling",
                        severity="info",
                        file=relative_path,
                        message="No exception handling in API file",
                        suggestion="Add try/except blocks for robust error handling",
                    ))

            except Exception:
                pass

    def _generate_summary(self) -> Dict[str, Any]:
        """Generate summary of scan results."""
        severity_counts = {"error": 0, "warning": 0, "info": 0, "critical": 0}
        category_counts = {}

        for issue in self.issues:
            severity_counts[issue.severity] = severity_counts.get(issue.severity, 0) + 1
            category_counts[issue.category] = category_counts.get(issue.category, 0) + 1

        return {
            "total_issues": len(self.issues),
            "by_severity": severity_counts,
            "by_category": category_counts,
            "health_score": self._calculate_health_score(severity_counts),
            "fixable_issues": sum(1 for i in self.issues if i.auto_fixable),
        }

    def _calculate_health_score(self, severity_counts: Dict[str, int]) -> int:
        """Calculate a health score 0-100."""
        # Start at 100, deduct for issues
        score = 100
        score -= severity_counts.get("critical", 0) * 25
        score -= severity_counts.get("error", 0) * 10
        score -= severity_counts.get("warning", 0) * 3
        score -= severity_counts.get("info", 0) * 1

        return max(0, min(100, score))

    def get_auto_fixes(self) -> List[Dict[str, Any]]:
        """Get all auto-fixable issues."""
        return [
            self._result_to_dict(issue)
            for issue in self.issues
            if issue.auto_fixable
        ]

    def apply_fix(self, filepath: str, fix_code: str, line: Optional[int] = None) -> bool:
        """Apply an auto-fix to a file."""
        try:
            full_path = self.project_root / filepath
            if not full_path.exists():
                return False

            content = full_path.read_text(encoding='utf-8')

            if line:
                lines = content.splitlines()
                lines.insert(line - 1, fix_code)
                content = "\n".join(lines)
            else:
                # Prepend to file
                content = fix_code + content

            full_path.write_text(content, encoding='utf-8')
            return True

        except Exception as e:
            logger.error(f"Failed to apply fix: {e}")
            return False


# Singleton for easy access
_scanner = None

def get_scanner() -> ProjectScanner:
    """Get the project scanner singleton."""
    global _scanner
    if _scanner is None:
        _scanner = ProjectScanner()
    return _scanner


