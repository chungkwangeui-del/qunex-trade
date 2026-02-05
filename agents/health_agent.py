"""
Health Agent
============

Monitors overall system health including:
- Database connectivity
- API endpoints availability
- External services status
- Memory and resource usage
"""

import logging
import psutil
import os
from datetime import datetime, timezone
from typing import Dict, Any, List

from agents.base import BaseAgent, AgentResult, AgentStatus, AgentTask, TaskType
from datetime import timezone
from typing import List
from typing import Any

logger = logging.getLogger(__name__)

class HealthAgent(BaseAgent):
    """
    Agent for monitoring overall system health.

    Checks:
    - Database connectivity and performance
    - API endpoint availability
    - External service connectivity (Polygon, Finnhub, etc.)
    - System resources (CPU, memory, disk)
    """

    def __init__(self):
        super().__init__(
            name="health",
            category="System",
            description="Monitors overall system health, database connectivity, and resource usage"
        )
        self.check_results: Dict[str, AgentResult] = {}

    def _register_tasks(self) -> None:
        """Register health monitoring tasks."""
        self.register_task(AgentTask(
            id="db_health",
            name="Database Health Check",
            task_type=TaskType.STATUS_CHECK,
            description="Check database connectivity and query performance",
            handler=self._check_database_health,
            interval_seconds=60,
        ))

        self.register_task(AgentTask(
            id="api_health",
            name="API Endpoints Health",
            task_type=TaskType.STATUS_CHECK,
            description="Verify all API endpoints are responding correctly",
            handler=self._check_api_health,
            interval_seconds=120,
        ))

        self.register_task(AgentTask(
            id="external_services",
            name="External Services Check",
            task_type=TaskType.STATUS_CHECK,
            description="Check connectivity to external APIs (Polygon, Finnhub)",
            handler=self._check_external_services,
            interval_seconds=300,
        ))

        self.register_task(AgentTask(
            id="system_resources",
            name="System Resources Check",
            task_type=TaskType.MONITORING,
            description="Monitor CPU, memory, and disk usage",
            handler=self._check_system_resources,
            interval_seconds=60,
        ))

    async def check_status(self) -> AgentResult:
        """Run all health checks and return overall status."""
        results = await self.run_all_tasks(TaskType.STATUS_CHECK)

        # Aggregate results
        all_healthy = all(r.status == AgentStatus.HEALTHY for r in results.values())
        has_errors = any(r.status in [AgentStatus.ERROR, AgentStatus.CRITICAL] for r in results.values())
        has_warnings = any(r.status == AgentStatus.WARNING for r in results.values())

        if all_healthy:
            status = AgentStatus.HEALTHY
            message = "All health checks passed"
        elif has_errors:
            status = AgentStatus.ERROR
            message = "One or more health checks failed"
        elif has_warnings:
            status = AgentStatus.WARNING
            message = "Some health checks have warnings"
        else:
            status = AgentStatus.UNKNOWN
            message = "Unable to determine health status"

        self.status = status

        return AgentResult(
            success=not has_errors,
            status=status,
            message=message,
            data={
                "checks": {k: v.to_dict() for k, v in results.items()},
                "summary": {
                    "total": len(results),
                    "healthy": sum(1 for r in results.values() if r.status == AgentStatus.HEALTHY),
                    "warnings": sum(1 for r in results.values() if r.status == AgentStatus.WARNING),
                    "errors": sum(1 for r in results.values() if r.status in [AgentStatus.ERROR, AgentStatus.CRITICAL]),
                }
            }
        )

    async def diagnose_issues(self) -> AgentResult:
        """Diagnose potential health issues."""
        issues = []
        suggestions = []

        # Run all checks first
        await self.check_status()

        # Analyze results
        for task_id, task in self.tasks.items():
            if task.last_result and task.last_result.status != AgentStatus.HEALTHY:
                issues.append(f"{task.name}: {task.last_result.message}")
                if task.last_result.suggestions:
                    suggestions.extend(task.last_result.suggestions)

        if not issues:
            return AgentResult(
                success=True,
                status=AgentStatus.HEALTHY,
                message="No issues detected",
                data={"issues_count": 0}
            )

        return AgentResult(
            success=False,
            status=AgentStatus.WARNING,
            message=f"Found {len(issues)} issue(s)",
            errors=issues,
            suggestions=suggestions,
            data={"issues_count": len(issues)}
        )

    async def fix_errors(self, auto_fix: bool = False) -> AgentResult:
        """Attempt to fix detected errors."""
        fixes_available = []
        fixes_applied = []

        # Check database connection
        db_result = await self._check_database_health()
        if db_result.status != AgentStatus.HEALTHY:
            fixes_available.append("Restart database connection pool")
            if auto_fix:
                try:
                    # Attempt to reconnect to database
                    from web.database import db
                    db.session.rollback()  # Clear any pending transactions
                    db.session.remove()    # Remove session from pool
                    fixes_applied.append("Database session cleared")
                except Exception as e:
                    return AgentResult(
                        success=False,
                        status=AgentStatus.ERROR,
                        message=f"Failed to fix database: {e}",
                        errors=[str(e)]
                    )

        if not fixes_available:
            return AgentResult(
                success=True,
                status=AgentStatus.HEALTHY,
                message="No fixes needed"
            )

        if auto_fix:
            return AgentResult(
                success=len(fixes_applied) > 0,
                status=AgentStatus.HEALTHY if len(fixes_applied) == len(fixes_available) else AgentStatus.WARNING,
                message=f"Applied {len(fixes_applied)}/{len(fixes_available)} fixes",
                data={"fixes_applied": fixes_applied, "fixes_available": fixes_available}
            )

        return AgentResult(
            success=True,
            status=AgentStatus.WARNING,
            message=f"{len(fixes_available)} fix(es) available",
            suggestions=fixes_available,
            data={"fixes_available": fixes_available}
        )

    async def get_development_suggestions(self) -> AgentResult:
        """Suggest health monitoring improvements."""
        suggestions = [
            "Add Prometheus metrics endpoint for monitoring",
            "Implement alerting via Slack/Discord webhooks",
            "Add memory leak detection over time",
            "Create uptime tracking and SLA reporting",
            "Add distributed tracing with OpenTelemetry",
            "Implement circuit breakers for external services",
        ]

        return AgentResult(
            success=True,
            status=AgentStatus.HEALTHY,
            message=f"{len(suggestions)} development suggestions",
            suggestions=suggestions,
            data={"category": "Health Monitoring"}
        )

    async def _check_database_health(self) -> AgentResult:
        """Check database connectivity and performance."""
        try:
            from web.database import db
            from web.app import create_app

            app = create_app()
            with app.app_context():
                start = datetime.now(timezone.utc)
                # Simple query to check connectivity
                result = db.session.execute(db.text("SELECT 1")).scalar()
                query_time = (datetime.now(timezone.utc) - start).total_seconds() * 1000

                if result == 1:
                    # Check query time
                    if query_time > 1000:
                        return AgentResult(
                            success=True,
                            status=AgentStatus.WARNING,
                            message=f"Database slow: {query_time:.2f}ms",
                            warnings=[f"Query took {query_time:.2f}ms (threshold: 1000ms)"],
                            suggestions=["Consider database optimization or connection pooling"],
                            data={"query_time_ms": query_time}
                        )

                    return AgentResult(
                        success=True,
                        status=AgentStatus.HEALTHY,
                        message=f"Database healthy ({query_time:.2f}ms)",
                        data={"query_time_ms": query_time}
                    )
                else:
                    return AgentResult(
                        success=False,
                        status=AgentStatus.ERROR,
                        message="Unexpected database response",
                        errors=["Expected 1, got: " + str(result)]
                    )
        except Exception as e:
            return AgentResult(
                success=False,
                status=AgentStatus.CRITICAL,
                message=f"Database connection failed: {e}",
                errors=[str(e)],
                suggestions=["Check database configuration", "Verify database server is running"]
            )

    async def _check_api_health(self) -> AgentResult:
        """Check API endpoints health."""
        endpoints = [
            ("Health Endpoint", "/health"),
            ("Main Page", "/"),
            ("Login Page", "/login"),
        ]

        results = []
        errors = []

        try:
            from web.app import create_app
            app = create_app()
            client = app.test_client()

            for name, endpoint in endpoints:
                try:
                    response = client.get(endpoint)
                    if response.status_code < 400:
                        results.append(f"{name}: OK ({response.status_code})")
                    else:
                        errors.append(f"{name}: {response.status_code}")
                except Exception as e:
                    errors.append(f"{name}: {str(e)}")

            if not errors:
                return AgentResult(
                    success=True,
                    status=AgentStatus.HEALTHY,
                    message=f"All {len(endpoints)} endpoints healthy",
                    data={"endpoints": results}
                )

            return AgentResult(
                success=False,
                status=AgentStatus.ERROR,
                message=f"{len(errors)}/{len(endpoints)} endpoints have issues",
                errors=errors,
                data={"healthy": results, "failed": errors}
            )
        except Exception as e:
            return AgentResult(
                success=False,
                status=AgentStatus.CRITICAL,
                message=f"API health check failed: {e}",
                errors=[str(e)]
            )

    async def _check_external_services(self) -> AgentResult:
        """Check external API connectivity."""
        services = []
        errors = []
        warnings = []

        # Check Polygon API
        try:
            from web.polygon_service import PolygonService
            polygon = PolygonService()
            # Just verify the service can be initialized
            services.append("Polygon API: Configured")
        except Exception as e:
            errors.append(f"Polygon API: {e}")

        # Check Finnhub
        try:
            from web.finnhub_service import FinnhubService
            finnhub = FinnhubService()
            services.append("Finnhub API: Configured")
        except Exception as e:
            warnings.append(f"Finnhub API: {e}")

        if errors:
            return AgentResult(
                success=False,
                status=AgentStatus.ERROR,
                message=f"{len(errors)} external service(s) unavailable",
                errors=errors,
                warnings=warnings,
                data={"healthy": services}
            )

        if warnings:
            return AgentResult(
                success=True,
                status=AgentStatus.WARNING,
                message="Some optional services have issues",
                warnings=warnings,
                data={"healthy": services}
            )

        return AgentResult(
            success=True,
            status=AgentStatus.HEALTHY,
            message=f"All {len(services)} external services OK",
            data={"services": services}
        )

    async def _check_system_resources(self) -> AgentResult:
        """Check system resource usage."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            warnings = []
            errors = []

            # CPU check
            if cpu_percent > 90:
                errors.append(f"CPU usage critical: {cpu_percent}%")
            elif cpu_percent > 70:
                warnings.append(f"CPU usage high: {cpu_percent}%")

            # Memory check
            if memory.percent > 90:
                errors.append(f"Memory usage critical: {memory.percent}%")
            elif memory.percent > 80:
                warnings.append(f"Memory usage high: {memory.percent}%")

            # Disk check
            if disk.percent > 95:
                errors.append(f"Disk usage critical: {disk.percent}%")
            elif disk.percent > 85:
                warnings.append(f"Disk usage high: {disk.percent}%")

            data = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "disk_percent": disk.percent,
                "disk_free_gb": disk.free / (1024**3),
            }

            if errors:
                return AgentResult(
                    success=False,
                    status=AgentStatus.CRITICAL,
                    message="System resources critical",
                    errors=errors,
                    warnings=warnings,
                    data=data
                )

            if warnings:
                return AgentResult(
                    success=True,
                    status=AgentStatus.WARNING,
                    message="System resources have warnings",
                    warnings=warnings,
                    data=data
                )

            return AgentResult(
                success=True,
                status=AgentStatus.HEALTHY,
                message="System resources healthy",
                data=data
            )
        except Exception as e:
            return AgentResult(
                success=False,
                status=AgentStatus.ERROR,
                message=f"Failed to check resources: {e}",
                errors=[str(e)]
            )
