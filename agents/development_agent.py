"""
Development Agent
=================

Smart agent that analyzes the codebase and provides:
- Code quality analysis
- Performance suggestions
- Feature recommendations
- Bug detection
- Auto-fix capabilities

This agent knows the codebase structure deeply and can make
intelligent recommendations based on actual code analysis.
"""

import re
import ast
import logging

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from agents.base import BaseAgent, AgentResult, AgentStatus, AgentTask, TaskType
from agents.codebase_knowledge import CodebaseKnowledge, get_knowledge
from agents.project_scanner import ProjectScanner, get_scanner
from datetime import timezone
from typing import List
from typing import Optional
from typing import Any
from typing import Tuple

logger = logging.getLogger(__name__)

class DevelopmentAgent(BaseAgent):
    """
    Smart development agent with deep codebase understanding.

    Capabilities:
    - Code quality analysis
    - Test coverage checking
    - Dependency status monitoring
    - API endpoint analysis
    - Feature gap detection
    - Security vulnerability scanning
    - Performance optimization suggestions
    - Auto-fix for common issues
    """

    def __init__(self):
        super().__init__(
            name="development",
            category="Development",
            description="Analyzes codebase and provides smart development suggestions"
        )
        self.knowledge = get_knowledge()
        self.scanner = get_scanner()
        self.project_root = Path(__file__).parent.parent
        self.scan_cache: Optional[Dict[str, Any]] = None
        self.last_scan_time: Optional[datetime] = None

    def _register_tasks(self) -> None:
        """Register development tasks."""
        self.register_task(AgentTask(
            id="code_quality",
            name="Code Quality Analysis",
            task_type=TaskType.STATUS_CHECK,
            description="Analyze code quality, syntax, and style",
            handler=self._check_code_quality,
            interval_seconds=3600,  # Every hour
        ))

        self.register_task(AgentTask(
            id="test_coverage",
            name="Test Coverage Check",
            task_type=TaskType.STATUS_CHECK,
            description="Check test coverage and missing tests",
            handler=self._check_test_coverage,
            interval_seconds=3600,
        ))

        self.register_task(AgentTask(
            id="dependency_check",
            name="Dependency Analysis",
            task_type=TaskType.STATUS_CHECK,
            description="Check dependencies for updates and vulnerabilities",
            handler=self._check_dependencies,
            interval_seconds=86400,  # Daily
        ))

        self.register_task(AgentTask(
            id="api_analysis",
            name="API Endpoint Analysis",
            task_type=TaskType.MONITORING,
            description="Analyze API endpoints for consistency and documentation",
            handler=self._analyze_api_endpoints,
            interval_seconds=3600,
        ))

        self.register_task(AgentTask(
            id="feature_gap",
            name="Feature Gap Analysis",
            task_type=TaskType.MONITORING,
            description="Identify missing features based on codebase patterns",
            handler=self._analyze_feature_gaps,
            interval_seconds=86400,
        ))

        self.register_task(AgentTask(
            id="performance_scan",
            name="Performance Analysis",
            task_type=TaskType.MONITORING,
            description="Identify performance bottlenecks and optimization opportunities",
            handler=self._analyze_performance,
            interval_seconds=3600,
        ))

        self.register_task(AgentTask(
            id="security_scan",
            name="Security Scan",
            task_type=TaskType.STATUS_CHECK,
            description="Scan for security vulnerabilities",
            handler=self._scan_security,
            interval_seconds=3600,
        ))

    def _run_scan_if_needed(self) -> Dict[str, Any]:
        """Run project scan if cache is stale."""
        now = datetime.now(timezone.utc)
        if (self.scan_cache is None or
            self.last_scan_time is None or
            (now - self.last_scan_time).total_seconds() > 300):  # 5 min cache
            self.scan_cache = self.scanner.scan_all()
            self.last_scan_time = now
        return self.scan_cache

    async def check_status(self) -> AgentResult:
        """Run all development checks."""
        results = await self.run_all_tasks(TaskType.STATUS_CHECK)

        all_healthy = all(r.status == AgentStatus.HEALTHY for r in results.values())
        has_errors = any(r.status in [AgentStatus.ERROR, AgentStatus.CRITICAL] for r in results.values())

        if all_healthy:
            status = AgentStatus.HEALTHY
            message = "Codebase healthy - no critical issues"
        elif has_errors:
            status = AgentStatus.ERROR
            message = "Codebase issues detected - review recommended"
        else:
            status = AgentStatus.WARNING
            message = "Codebase has warnings - improvements available"

        self.status = status

        return AgentResult(
            success=not has_errors,
            status=status,
            message=message,
            data={
                "checks": {k: v.to_dict() for k, v in results.items()},
            }
        )

    async def diagnose_issues(self) -> AgentResult:
        """Deep diagnosis of codebase issues."""
        issues = []
        suggestions = []

        # Run fresh scan
        scan_result = self._run_scan_if_needed()

        # Categorize issues by severity
        for issue in scan_result.get("issues", []):
            if issue["severity"] in ["error", "critical"]:
                issues.append(f"[{issue['category']}] {issue['message']}" +
                            (f" in {issue['file']}" if issue.get('file') else ""))

            if issue.get("suggestion"):
                suggestions.append(issue["suggestion"])

        # Add task results
        await self.check_status()
        for task_id, task in self.tasks.items():
            if task.last_result and task.last_result.status != AgentStatus.HEALTHY:
                if task.last_result.errors:
                    issues.extend(task.last_result.errors)
                if task.last_result.suggestions:
                    suggestions.extend(task.last_result.suggestions)

        # Remove duplicates
        issues = list(dict.fromkeys(issues))
        suggestions = list(dict.fromkeys(suggestions))

        return AgentResult(
            success=len(issues) == 0,
            status=AgentStatus.HEALTHY if not issues else AgentStatus.WARNING,
            message=f"Found {len(issues)} issue(s)" if issues else "No issues detected",
            errors=issues[:20],  # Limit to top 20
            suggestions=suggestions[:15],  # Limit to top 15
            data={
                "scan_summary": scan_result.get("summary", {}),
                "total_issues": len(issues),
                "total_suggestions": len(suggestions),
            }
        )

    async def fix_errors(self, auto_fix: bool = False) -> AgentResult:
        """Auto-fix detected issues."""
        fixes_available = []
        fixes_applied = []

        scan_result = self._run_scan_if_needed()

        # Get auto-fixable issues
        for issue in scan_result.get("issues", []):
            if issue.get("auto_fixable") and issue.get("fix_code"):
                fix_info = {
                    "file": issue.get("file"),
                    "line": issue.get("line"),
                    "message": issue["message"],
                    "fix_code": issue["fix_code"],
                }
                fixes_available.append(fix_info)

                if auto_fix and issue.get("file"):
                    try:
                        if self.scanner.apply_fix(
                            issue["file"],
                            issue["fix_code"],
                            issue.get("line")
                        ):
                            fixes_applied.append(f"Fixed: {issue['message']}")
                    except Exception as e:
                        logger.error(f"Failed to apply fix: {e}")

        # Additional auto-fixes

        # Fix: Create missing __init__.py files
        for directory in ["agents", "scripts", "web/main"]:
            init_path = self.project_root / directory / "__init__.py"
            if not init_path.exists() and (self.project_root / directory).exists():
                fixes_available.append({
                    "file": f"{directory}/__init__.py",
                    "message": f"Missing __init__.py in {directory}",
                })
                if auto_fix:
                    try:
                        init_path.write_text('"""Package initialization."""\n', encoding='utf-8')
                        fixes_applied.append(f"Created {directory}/__init__.py")
                    except Exception as e:
                        logger.error(f"Failed to create __init__.py: {e}")

        if not fixes_available:
            return AgentResult(
                success=True,
                status=AgentStatus.HEALTHY,
                message="No auto-fixable issues found"
            )

        return AgentResult(
            success=True,
            status=AgentStatus.HEALTHY if auto_fix and fixes_applied else AgentStatus.WARNING,
            message=f"Applied {len(fixes_applied)} fix(es)" if auto_fix else f"{len(fixes_available)} fix(es) available",
            suggestions=[f["message"] for f in fixes_available] if not auto_fix else [],
            data={
                "fixes_available": len(fixes_available),
                "fixes_applied": fixes_applied,
            }
        )

    async def get_development_suggestions(self) -> AgentResult:
        """Get intelligent development suggestions based on codebase analysis."""
        suggestions = []
        priority_suggestions = []

        # Run analysis
        scan_result = self._run_scan_if_needed()

        # 1. Based on codebase structure
        knowledge = self.knowledge

        # Check for missing common features
        feature_checks = [
            ("web/admin_views.py", "Create admin management interface (Flask-Admin)", "high"),
            ("web/api_v2.py", "Create versioned API endpoints for mobile apps", "medium"),
            ("web/websocket_handler.py", "Add real-time WebSocket price updates", "high"),
            ("web/rate_limiter.py", "Implement API rate limiting for security", "high"),
            ("web/cache_service.py", "Add Redis caching for performance", "medium"),
            ("web/background_tasks.py", "Add Celery background task processing", "medium"),
        ]

        for filepath, suggestion, priority in feature_checks:
            if not knowledge.file_exists(filepath):
                item = {
                    "priority": priority,
                    "category": "Feature",
                    "suggestion": suggestion,
                    "file": filepath,
                }
                if priority == "high":
                    priority_suggestions.append(item)
                else:
                    suggestions.append(item)

        # 2. Based on scan results
        summary = scan_result.get("summary", {})

        if summary.get("health_score", 100) < 70:
            priority_suggestions.append({
                "priority": "high",
                "category": "Quality",
                "suggestion": f"Code health score is {summary.get('health_score')}% - fix critical issues first",
            })

        # 3. Test coverage
        test_count = len(list((self.project_root / "tests").glob("test_*.py"))) if (self.project_root / "tests").exists() else 0
        if test_count < 10:
            priority_suggestions.append({
                "priority": "high",
                "category": "Testing",
                "suggestion": f"Only {test_count} test files - aim for 80% coverage",
            })

        # 4. Performance suggestions based on file analysis
        large_files = [i for i in scan_result.get("issues", []) if i.get("type") == "large_file"]
        if large_files:
            suggestions.append({
                "priority": "medium",
                "category": "Refactoring",
                "suggestion": f"Split {len(large_files)} large files (>500 lines) into modules",
                "files": [f["file"] for f in large_files],
            })

        # 5. Security suggestions
        security_issues = [i for i in scan_result.get("issues", []) if i["category"] == "Security"]
        if security_issues:
            priority_suggestions.append({
                "priority": "critical",
                "category": "Security",
                "suggestion": f"Fix {len(security_issues)} security issues immediately",
                "issues": [i["message"] for i in security_issues[:5]],
            })

        # 6. Trading platform specific suggestions
        trading_suggestions = [
            {
                "priority": "medium",
                "category": "Trading",
                "suggestion": "Add real-time portfolio P&L tracking with WebSocket",
            },
            {
                "priority": "medium",
                "category": "Trading",
                "suggestion": "Implement automated trade alerts via email/SMS",
            },
            {
                "priority": "low",
                "category": "Trading",
                "suggestion": "Add TradingView chart embedding for advanced analysis",
            },
            {
                "priority": "low",
                "category": "Trading",
                "suggestion": "Implement backtesting engine for strategy validation",
            },
            {
                "priority": "medium",
                "category": "Trading",
                "suggestion": "Add options Greeks calculator (Delta, Gamma, Theta, Vega)",
            },
            {
                "priority": "low",
                "category": "Trading",
                "suggestion": "Create social trading feature - share trades with community",
            },
        ]
        suggestions.extend(trading_suggestions)

        # 7. Infrastructure suggestions
        infra_suggestions = [
            {
                "priority": "high",
                "category": "Infrastructure",
                "suggestion": "Add health check endpoint at /health for monitoring",
            },
            {
                "priority": "medium",
                "category": "Infrastructure",
                "suggestion": "Implement structured logging with JSON format",
            },
            {
                "priority": "medium",
                "category": "Infrastructure",
                "suggestion": "Add APM (Application Performance Monitoring)",
            },
        ]

        # Check if health endpoint exists
        try:
            with open(self.project_root / "web" / "app.py", "r", encoding="utf-8") as f:
                if "/health" not in f.read():
                    suggestions.extend(infra_suggestions)
        except Exception:
            suggestions.extend(infra_suggestions)

        # Combine and sort by priority
        all_suggestions = priority_suggestions + suggestions
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        all_suggestions.sort(key=lambda x: priority_order.get(x.get("priority", "low"), 4))

        return AgentResult(
            success=True,
            status=AgentStatus.HEALTHY,
            message=f"{len(all_suggestions)} development suggestions",
            suggestions=[s["suggestion"] for s in all_suggestions[:20]],
            data={
                "total_suggestions": len(all_suggestions),
                "by_priority": {
                    "critical": len([s for s in all_suggestions if s.get("priority") == "critical"]),
                    "high": len([s for s in all_suggestions if s.get("priority") == "high"]),
                    "medium": len([s for s in all_suggestions if s.get("priority") == "medium"]),
                    "low": len([s for s in all_suggestions if s.get("priority") == "low"]),
                },
                "by_category": {},
                "detailed": all_suggestions[:20],
            }
        )

    async def _check_code_quality(self) -> AgentResult:
        """Check overall code quality."""
        scan_result = self._run_scan_if_needed()
        summary = scan_result.get("summary", {})

        health_score = summary.get("health_score", 0)
        total_issues = summary.get("total_issues", 0)

        if health_score >= 80:
            status = AgentStatus.HEALTHY
            message = f"Code quality good: {health_score}% health score"
        elif health_score >= 60:
            status = AgentStatus.WARNING
            message = f"Code quality acceptable: {health_score}% health score"
        else:
            status = AgentStatus.ERROR
            message = f"Code quality needs improvement: {health_score}% health score"

        return AgentResult(
            success=health_score >= 60,
            status=status,
            message=message,
            data={
                "health_score": health_score,
                "total_issues": total_issues,
                "issues_by_severity": summary.get("by_severity", {}),
                "python_files": scan_result.get("stats", {}).get("python_files", 0),
                "total_lines": scan_result.get("stats", {}).get("total_lines", 0),
            }
        )

    async def _check_test_coverage(self) -> AgentResult:
        """Check test coverage."""
        tests_dir = self.project_root / "tests"
        web_dir = self.project_root / "web"

        if not tests_dir.exists():
            return AgentResult(
                success=False,
                status=AgentStatus.ERROR,
                message="No tests directory found",
                errors=["Missing tests/ directory"],
                suggestions=["Create tests/ directory with test files"]
            )

        test_files = list(tests_dir.glob("test_*.py"))
        web_modules = [f for f in web_dir.glob("*.py") if not f.name.startswith("__")]

        # Calculate coverage ratio
        coverage_ratio = len(test_files) / max(len(web_modules), 1)

        if coverage_ratio >= 0.5:
            status = AgentStatus.HEALTHY
            message = f"Test coverage adequate: {len(test_files)} tests for {len(web_modules)} modules"
        elif coverage_ratio >= 0.25:
            status = AgentStatus.WARNING
            message = f"Test coverage low: {len(test_files)} tests for {len(web_modules)} modules"
        else:
            status = AgentStatus.ERROR
            message = f"Test coverage critical: only {len(test_files)} tests for {len(web_modules)} modules"

        # Find untested modules
        tested_modules = set()
        for tf in test_files:
            # Extract module name from test file (test_xyz.py -> xyz)
            module_name = tf.stem.replace("test_", "")
            tested_modules.add(module_name)

        untested = []
        for module in web_modules:
            module_name = module.stem
            if module_name not in tested_modules and not module_name.startswith("api_"):
                untested.append(module_name)

        return AgentResult(
            success=coverage_ratio >= 0.25,
            status=status,
            message=message,
            warnings=[f"Missing tests for: {', '.join(untested[:5])}"] if untested else [],
            suggestions=[f"Add tests for: {m}" for m in untested[:5]],
            data={
                "test_files": len(test_files),
                "web_modules": len(web_modules),
                "coverage_ratio": coverage_ratio,
                "untested_modules": untested[:10],
            }
        )

    async def _check_dependencies(self) -> AgentResult:
        """Check project dependencies."""
        req_file = self.project_root / "requirements.txt"

        if not req_file.exists():
            return AgentResult(
                success=False,
                status=AgentStatus.ERROR,
                message="requirements.txt not found",
                errors=["Missing requirements.txt"],
                suggestions=["Create requirements.txt with pip freeze > requirements.txt"]
            )

        content = req_file.read_text(encoding='utf-8')
        lines = [l.strip() for l in content.splitlines() if l.strip() and not l.startswith("#")]

        total_deps = len(lines)
        pinned = sum(1 for l in lines if "==" in l)
        unpinned = total_deps - pinned

        issues = []
        if unpinned > 0:
            issues.append(f"{unpinned} dependencies without pinned versions")

        # Check for known critical packages
        critical_packages = ["flask", "sqlalchemy", "gunicorn", "psutil"]
        missing_critical = [p for p in critical_packages if not any(p in l.lower() for l in lines)]

        if missing_critical:
            issues.append(f"Potentially missing packages: {', '.join(missing_critical)}")

        if issues:
            return AgentResult(
                success=True,
                status=AgentStatus.WARNING,
                message=f"Dependencies have {len(issues)} warning(s)",
                warnings=issues,
                data={
                    "total_dependencies": total_deps,
                    "pinned": pinned,
                    "unpinned": unpinned,
                }
            )

        return AgentResult(
            success=True,
            status=AgentStatus.HEALTHY,
            message=f"Dependencies healthy: {total_deps} packages, {pinned} pinned",
            data={
                "total_dependencies": total_deps,
                "pinned": pinned,
            }
        )

    async def _analyze_api_endpoints(self) -> AgentResult:
        """Analyze API endpoints for consistency."""
        web_dir = self.project_root / "web"
        api_files = list(web_dir.glob("api_*.py"))

        endpoints = []
        issues = []

        for api_file in api_files:
            try:
                content = api_file.read_text(encoding='utf-8')

                # Find all route definitions
                routes = re.findall(r'@\w+\.route\([\'"]([^"\']+)[\'"]', content)
                endpoints.extend([(api_file.stem, r) for r in routes])

                # Check for proper error handling
                if "try:" not in content:
                    issues.append(f"{api_file.stem}: No error handling found")

                # Check for authentication
                if "@login_required" not in content and "public" not in api_file.stem:
                    issues.append(f"{api_file.stem}: No authentication decorators")

            except Exception as e:
                issues.append(f"{api_file.stem}: Could not analyze - {e}")

        if issues:
            return AgentResult(
                success=True,
                status=AgentStatus.WARNING,
                message=f"API analysis: {len(issues)} potential issue(s)",
                warnings=issues[:10],
                data={
                    "total_api_files": len(api_files),
                    "total_endpoints": len(endpoints),
                }
            )

        return AgentResult(
            success=True,
            status=AgentStatus.HEALTHY,
            message=f"API endpoints healthy: {len(endpoints)} routes in {len(api_files)} files",
            data={
                "total_api_files": len(api_files),
                "total_endpoints": len(endpoints),
            }
        )

    async def _analyze_feature_gaps(self) -> AgentResult:
        """Identify missing features based on common trading platform patterns."""
        existing_features = set()
        missing_features = []

        # Check for existing features
        feature_checks = {
            "watchlist": "web/api_watchlist.py",
            "portfolio": "web/api_portfolio.py",
            "paper_trading": "web/api_paper.py",
            "scalping": "web/api_scalp.py",
            "swing_trading": "web/api_swing.py",
            "patterns": "web/api_patterns.py",
            "sentiment": "web/api_sentiment.py",
            "options": "web/api_options.py",
            "chat": "web/api_chat.py",
            "journal": "web/api_journal.py",
            "leaderboard": "web/api_leaderboard.py",
            "analytics": "web/api_analytics.py",
        }

        for feature, filepath in feature_checks.items():
            if self.knowledge.file_exists(filepath):
                existing_features.add(feature)

        # Common trading platform features that might be missing
        suggested_features = {
            "alerts": "Price alert system with email/push notifications",
            "social": "Social trading - follow other traders' portfolios",
            "education": "Trading education content and tutorials",
            "scanner": "Stock screener with custom filters",
            "backtesting": "Strategy backtesting engine",
            "automation": "Automated trading rules and bot support",
            "mobile_api": "Dedicated mobile app API endpoints",
            "crypto": "Cryptocurrency trading support",
        }

        for feature, description in suggested_features.items():
            if feature not in existing_features:
                missing_features.append({
                    "feature": feature,
                    "description": description,
                })

        return AgentResult(
            success=True,
            status=AgentStatus.HEALTHY,
            message=f"{len(existing_features)} features active, {len(missing_features)} suggested",
            suggestions=[f"Add {f['feature']}: {f['description']}" for f in missing_features[:5]],
            data={
                "existing_features": list(existing_features),
                "missing_features": missing_features,
            }
        )

    async def _analyze_performance(self) -> AgentResult:
        """Identify performance optimization opportunities."""
        issues = []
        suggestions = []

        web_dir = self.project_root / "web"

        # Check for N+1 query patterns
        for py_file in web_dir.glob("*.py"):
            try:
                content = py_file.read_text(encoding='utf-8')

                # Check for potential N+1 queries
                if ".query.all()" in content and "for " in content:
                    # Simplified check - might have N+1
                    if "joinedload" not in content and "subqueryload" not in content:
                        issues.append(f"{py_file.stem}: Potential N+1 query pattern")
                        suggestions.append(f"Use eager loading in {py_file.stem}")

                # Check for sync external calls in routes
                if "requests.get" in content or "requests.post" in content:
                    if "async" not in content:
                        issues.append(f"{py_file.stem}: Synchronous HTTP calls")
                        suggestions.append(f"Use async HTTP client in {py_file.stem}")

            except Exception:
                pass

        # Check for caching
        if not self.knowledge.file_exists("web/cache_service.py"):
            suggestions.append("Implement caching layer for frequent queries")

        if issues:
            return AgentResult(
                success=True,
                status=AgentStatus.WARNING,
                message=f"Performance: {len(issues)} potential issue(s)",
                warnings=issues[:10],
                suggestions=suggestions[:10],
                data={"issues_count": len(issues)}
            )

        return AgentResult(
            success=True,
            status=AgentStatus.HEALTHY,
            message="No obvious performance issues detected",
            suggestions=suggestions[:5] if suggestions else [],
            data={"issues_count": 0}
        )

    async def _scan_security(self) -> AgentResult:
        """Scan for security vulnerabilities."""
        issues = []
        critical = []

        scan_result = self._run_scan_if_needed()

        # Get security issues from scan
        for issue in scan_result.get("issues", []):
            if issue.get("category") == "Security":
                if issue.get("severity") == "critical":
                    critical.append(issue["message"])
                else:
                    issues.append(issue["message"])

        # Additional security checks
        config_file = self.project_root / "web" / "config.py"
        if config_file.exists():
            content = config_file.read_text(encoding='utf-8')

            # Check for secure cookie settings
            if "SESSION_COOKIE_SECURE" not in content:
                issues.append("SESSION_COOKIE_SECURE not configured")

            if "SESSION_COOKIE_HTTPONLY" not in content:
                issues.append("SESSION_COOKIE_HTTPONLY not configured")

        if critical:
            return AgentResult(
                success=False,
                status=AgentStatus.CRITICAL,
                message=f"Security: {len(critical)} critical issue(s)!",
                errors=critical,
                warnings=issues,
                suggestions=["Fix critical security issues immediately"]
            )

        if issues:
            return AgentResult(
                success=True,
                status=AgentStatus.WARNING,
                message=f"Security: {len(issues)} issue(s) found",
                warnings=issues[:10],
                suggestions=["Review and fix security warnings"]
            )

        return AgentResult(
            success=True,
            status=AgentStatus.HEALTHY,
            message="No security vulnerabilities detected",
            data={"scanned_files": scan_result.get("stats", {}).get("python_files", 0)}
        )
