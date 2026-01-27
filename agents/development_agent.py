"""
Development Agent
=================

Assists with development tasks including:
- Code quality analysis
- Feature suggestions
- Test coverage
- Documentation status
"""

import asyncio
import logging
import os
import glob
from datetime import datetime, timezone
from typing import Dict, Any, List
from pathlib import Path

from agents.base import BaseAgent, AgentResult, AgentStatus, AgentTask, TaskType

logger = logging.getLogger(__name__)


class DevelopmentAgent(BaseAgent):
    """
    Agent for assisting with development tasks.
    
    Provides:
    - Code quality analysis
    - Feature development suggestions
    - Test coverage analysis
    - Documentation status
    - Dependency analysis
    """
    
    def __init__(self):
        super().__init__(
            name="development",
            category="Development",
            description="Assists with code quality, testing, and feature development"
        )
        self.project_root = Path(__file__).parent.parent
    
    def _register_tasks(self) -> None:
        """Register development tasks."""
        self.register_task(AgentTask(
            id="code_quality",
            name="Code Quality Analysis",
            task_type=TaskType.STATUS_CHECK,
            description="Analyze code quality and potential issues",
            handler=self._check_code_quality,
            interval_seconds=3600,
        ))
        
        self.register_task(AgentTask(
            id="test_coverage",
            name="Test Coverage Status",
            task_type=TaskType.STATUS_CHECK,
            description="Check test coverage across modules",
            handler=self._check_test_coverage,
            interval_seconds=3600,
        ))
        
        self.register_task(AgentTask(
            id="dependency_status",
            name="Dependency Status",
            task_type=TaskType.STATUS_CHECK,
            description="Check for outdated or vulnerable dependencies",
            handler=self._check_dependencies,
            interval_seconds=86400,  # Daily
        ))
        
        self.register_task(AgentTask(
            id="api_endpoints",
            name="API Endpoints Analysis",
            task_type=TaskType.STATUS_CHECK,
            description="Analyze API endpoint coverage and documentation",
            handler=self._check_api_endpoints,
            interval_seconds=3600,
        ))
        
        self.register_task(AgentTask(
            id="feature_suggestions",
            name="Feature Suggestions",
            task_type=TaskType.DEVELOPMENT,
            description="Generate feature development suggestions",
            handler=self._generate_feature_suggestions,
            interval_seconds=86400,
        ))
    
    async def check_status(self) -> AgentResult:
        """Run development status checks."""
        results = await self.run_all_tasks(TaskType.STATUS_CHECK)
        
        all_healthy = all(r.status == AgentStatus.HEALTHY for r in results.values())
        has_errors = any(r.status in [AgentStatus.ERROR, AgentStatus.CRITICAL] for r in results.values())
        
        if all_healthy:
            status = AgentStatus.HEALTHY
            message = "Development environment healthy"
        elif has_errors:
            status = AgentStatus.ERROR
            message = "Development issues detected"
        else:
            status = AgentStatus.WARNING
            message = "Development warnings detected"
        
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
        """Diagnose development issues."""
        issues = []
        suggestions = []
        
        # Check for missing tests
        test_result = await self._check_test_coverage()
        if test_result.data:
            untested = test_result.data.get("modules_without_tests", [])
            if untested:
                issues.append(f"{len(untested)} modules without tests")
                suggestions.append("Add tests for untested modules")
        
        # Check for outdated dependencies
        dep_result = await self._check_dependencies()
        if dep_result.status != AgentStatus.HEALTHY:
            issues.append("Dependency issues detected")
            suggestions.extend(dep_result.suggestions)
        
        return AgentResult(
            success=len(issues) == 0,
            status=AgentStatus.HEALTHY if not issues else AgentStatus.WARNING,
            message=f"Found {len(issues)} issue(s)" if issues else "No issues detected",
            errors=issues,
            suggestions=list(set(suggestions))
        )
    
    async def fix_errors(self, auto_fix: bool = False) -> AgentResult:
        """Suggest development fixes."""
        fixes_available = [
            "Run linting: flake8 web/",
            "Format code: black web/",
            "Run tests: pytest tests/",
            "Update dependencies: pip install -U -r requirements.txt",
        ]
        
        return AgentResult(
            success=True,
            status=AgentStatus.WARNING,
            message=f"{len(fixes_available)} development tasks available",
            suggestions=fixes_available,
            data={"fixes_available": fixes_available}
        )
    
    async def get_development_suggestions(self) -> AgentResult:
        """Get comprehensive development suggestions."""
        result = await self._generate_feature_suggestions()
        return result
    
    async def _check_code_quality(self) -> AgentResult:
        """Analyze code quality."""
        try:
            python_files = list(self.project_root.glob("**/*.py"))
            python_files = [f for f in python_files if "__pycache__" not in str(f)]
            
            total_lines = 0
            large_files = []
            
            for file in python_files:
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        lines = len(f.readlines())
                        total_lines += lines
                        if lines > 500:
                            large_files.append((str(file.relative_to(self.project_root)), lines))
                except Exception:
                    continue
            
            warnings = []
            if large_files:
                for file, lines in large_files[:5]:
                    warnings.append(f"{file}: {lines} lines (consider splitting)")
            
            return AgentResult(
                success=True,
                status=AgentStatus.WARNING if warnings else AgentStatus.HEALTHY,
                message=f"Analyzed {len(python_files)} Python files ({total_lines:,} total lines)",
                warnings=warnings[:5],
                data={
                    "python_files": len(python_files),
                    "total_lines": total_lines,
                    "large_files_count": len(large_files)
                }
            )
        except Exception as e:
            return AgentResult(
                success=False,
                status=AgentStatus.ERROR,
                message=f"Code quality check failed: {e}",
                errors=[str(e)]
            )
    
    async def _check_test_coverage(self) -> AgentResult:
        """Check test coverage."""
        try:
            # Get all main modules
            web_modules = list((self.project_root / "web").glob("*.py"))
            web_modules = [f.stem for f in web_modules if f.stem != "__init__"]
            
            # Get test files
            test_files = list((self.project_root / "tests").glob("test_*.py"))
            tested_patterns = []
            for tf in test_files:
                # Extract what's being tested
                tested_patterns.append(tf.stem.replace("test_", ""))
            
            # Find modules without tests
            modules_without_tests = []
            for module in web_modules:
                # Simplify matching
                has_test = any(
                    module in pattern or pattern in module 
                    for pattern in tested_patterns
                )
                if not has_test and module not in ["__init__"]:
                    modules_without_tests.append(module)
            
            coverage_pct = ((len(web_modules) - len(modules_without_tests)) / len(web_modules) * 100) if web_modules else 0
            
            if coverage_pct < 50:
                status = AgentStatus.WARNING
                message = f"Low test coverage: {coverage_pct:.1f}%"
            else:
                status = AgentStatus.HEALTHY
                message = f"Test coverage: {coverage_pct:.1f}%"
            
            return AgentResult(
                success=True,
                status=status,
                message=message,
                data={
                    "total_modules": len(web_modules),
                    "test_files": len(test_files),
                    "coverage_estimate": coverage_pct,
                    "modules_without_tests": modules_without_tests[:10]
                },
                suggestions=["Add tests for: " + ", ".join(modules_without_tests[:5])] if modules_without_tests else []
            )
        except Exception as e:
            return AgentResult(
                success=False,
                status=AgentStatus.ERROR,
                message=f"Test coverage check failed: {e}",
                errors=[str(e)]
            )
    
    async def _check_dependencies(self) -> AgentResult:
        """Check dependency status."""
        try:
            requirements_path = self.project_root / "requirements.txt"
            
            if not requirements_path.exists():
                return AgentResult(
                    success=False,
                    status=AgentStatus.ERROR,
                    message="requirements.txt not found",
                    errors=["Missing requirements.txt"]
                )
            
            with open(requirements_path, 'r') as f:
                dependencies = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            
            # Count pinned vs unpinned
            pinned = [d for d in dependencies if '==' in d]
            unpinned = [d for d in dependencies if '==' not in d and d]
            
            warnings = []
            if unpinned:
                warnings.append(f"{len(unpinned)} dependencies without version pins")
            
            return AgentResult(
                success=True,
                status=AgentStatus.WARNING if warnings else AgentStatus.HEALTHY,
                message=f"Found {len(dependencies)} dependencies ({len(pinned)} pinned)",
                warnings=warnings,
                data={
                    "total_dependencies": len(dependencies),
                    "pinned_count": len(pinned),
                    "unpinned": unpinned[:5] if unpinned else []
                },
                suggestions=["Pin all dependency versions for reproducibility"] if unpinned else []
            )
        except Exception as e:
            return AgentResult(
                success=False,
                status=AgentStatus.ERROR,
                message=f"Dependency check failed: {e}",
                errors=[str(e)]
            )
    
    async def _check_api_endpoints(self) -> AgentResult:
        """Analyze API endpoints."""
        try:
            api_files = list((self.project_root / "web").glob("api_*.py"))
            
            endpoint_counts = {}
            total_endpoints = 0
            
            for api_file in api_files:
                try:
                    with open(api_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Count route decorators
                        routes = content.count('@') - content.count('@login_required')
                        endpoint_counts[api_file.stem] = routes
                        total_endpoints += routes
                except Exception:
                    continue
            
            return AgentResult(
                success=True,
                status=AgentStatus.HEALTHY,
                message=f"Found {len(api_files)} API modules with ~{total_endpoints} endpoints",
                data={
                    "api_modules": len(api_files),
                    "total_endpoints_estimate": total_endpoints,
                    "by_module": endpoint_counts
                }
            )
        except Exception as e:
            return AgentResult(
                success=False,
                status=AgentStatus.ERROR,
                message=f"API analysis failed: {e}",
                errors=[str(e)]
            )
    
    async def _generate_feature_suggestions(self) -> AgentResult:
        """Generate feature development suggestions."""
        suggestions = {
            "High Priority": [
                "Add real-time WebSocket price updates",
                "Implement automated alerting system (email/push)",
                "Add backtesting engine for trading strategies",
                "Create mobile-responsive trading interface",
            ],
            "Medium Priority": [
                "Add dark pool flow visualization",
                "Implement options Greeks calculator",
                "Create custom indicator builder",
                "Add portfolio correlation analysis",
                "Implement trade copier for paper trading",
            ],
            "Nice to Have": [
                "Add social trading features (follow traders)",
                "Implement trade replay for education",
                "Create personalized AI trading coach",
                "Add multi-language support",
                "Implement crypto trading support",
            ],
            "Technical Improvements": [
                "Add comprehensive API documentation (OpenAPI/Swagger)",
                "Implement database migrations with Alembic",
                "Add end-to-end testing with Playwright",
                "Create CI/CD pipeline with GitHub Actions",
                "Add error tracking with Sentry",
            ]
        }
        
        all_suggestions = []
        for priority, items in suggestions.items():
            for item in items:
                all_suggestions.append(f"[{priority}] {item}")
        
        return AgentResult(
            success=True,
            status=AgentStatus.HEALTHY,
            message=f"Generated {len(all_suggestions)} development suggestions",
            suggestions=all_suggestions,
            data={"by_priority": suggestions}
        )

