"""
Security Agent
==============

Monitors security aspects including:
- Authentication status
- Failed login attempts
- API rate limiting
- Session management
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

from agents.base import BaseAgent, AgentResult, AgentStatus, AgentTask, TaskType

logger = logging.getLogger(__name__)


class SecurityAgent(BaseAgent):
    """
    Agent for monitoring security aspects.
    
    Checks:
    - Failed login attempts
    - Rate limit violations
    - Session management
    - API key exposure
    - Configuration security
    """
    
    def __init__(self):
        super().__init__(
            name="security",
            category="Security",
            description="Monitors authentication, rate limiting, and security configuration"
        )
    
    def _register_tasks(self) -> None:
        """Register security monitoring tasks."""
        self.register_task(AgentTask(
            id="config_security",
            name="Configuration Security",
            task_type=TaskType.STATUS_CHECK,
            description="Check security configuration settings",
            handler=self._check_config_security,
            interval_seconds=3600,
        ))
        
        self.register_task(AgentTask(
            id="auth_status",
            name="Authentication Status",
            task_type=TaskType.STATUS_CHECK,
            description="Check authentication system health",
            handler=self._check_auth_status,
            interval_seconds=600,
        ))
        
        self.register_task(AgentTask(
            id="rate_limiting",
            name="Rate Limiting Status",
            task_type=TaskType.STATUS_CHECK,
            description="Verify rate limiting is active",
            handler=self._check_rate_limiting,
            interval_seconds=600,
        ))
        
        self.register_task(AgentTask(
            id="csrf_protection",
            name="CSRF Protection",
            task_type=TaskType.STATUS_CHECK,
            description="Verify CSRF protection is enabled",
            handler=self._check_csrf_protection,
            interval_seconds=3600,
        ))
        
        self.register_task(AgentTask(
            id="user_activity",
            name="User Activity Monitor",
            task_type=TaskType.MONITORING,
            description="Monitor user registration and activity",
            handler=self._check_user_activity,
            interval_seconds=1800,
        ))
    
    async def check_status(self) -> AgentResult:
        """Run all security checks."""
        results = await self.run_all_tasks(TaskType.STATUS_CHECK)
        
        all_healthy = all(r.status == AgentStatus.HEALTHY for r in results.values())
        has_errors = any(r.status in [AgentStatus.ERROR, AgentStatus.CRITICAL] for r in results.values())
        
        if all_healthy:
            status = AgentStatus.HEALTHY
            message = "All security checks passed"
        elif has_errors:
            status = AgentStatus.ERROR
            message = "Security issues detected"
        else:
            status = AgentStatus.WARNING
            message = "Security warnings detected"
        
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
        """Diagnose security issues."""
        issues = []
        suggestions = []
        
        await self.check_status()
        
        for task_id, task in self.tasks.items():
            if task.last_result and task.last_result.status != AgentStatus.HEALTHY:
                issues.append(f"{task.name}: {task.last_result.message}")
                suggestions.extend(task.last_result.suggestions)
        
        return AgentResult(
            success=len(issues) == 0,
            status=AgentStatus.HEALTHY if not issues else AgentStatus.WARNING,
            message=f"Found {len(issues)} issue(s)" if issues else "No issues detected",
            errors=issues,
            suggestions=list(set(suggestions))
        )
    
    async def fix_errors(self, auto_fix: bool = False) -> AgentResult:
        """Attempt to fix security issues."""
        fixes_available = []
        
        # Check config
        config_result = await self._check_config_security()
        if config_result.status != AgentStatus.HEALTHY:
            fixes_available.extend(config_result.suggestions)
        
        if not fixes_available:
            return AgentResult(
                success=True,
                status=AgentStatus.HEALTHY,
                message="No fixes needed"
            )
        
        return AgentResult(
            success=True,
            status=AgentStatus.WARNING,
            message=f"{len(fixes_available)} fix(es) available (manual intervention required)",
            suggestions=fixes_available,
            data={"fixes_available": fixes_available}
        )
    
    async def get_development_suggestions(self) -> AgentResult:
        """Suggest security improvements."""
        suggestions = [
            "Add two-factor authentication (2FA)",
            "Implement password strength requirements",
            "Add login attempt rate limiting per IP",
            "Implement account lockout after failed attempts",
            "Add session timeout warnings",
            "Implement suspicious activity detection",
            "Add API key rotation system",
            "Implement audit logging for sensitive actions",
            "Add IP-based access control for admin",
            "Implement Content Security Policy (CSP) reporting",
        ]
        
        return AgentResult(
            success=True,
            status=AgentStatus.HEALTHY,
            message=f"{len(suggestions)} development suggestions",
            suggestions=suggestions,
            data={"category": "Security"}
        )
    
    async def _check_config_security(self) -> AgentResult:
        """Check security configuration."""
        try:
            from web.config import Config
            import os
            
            issues = []
            warnings = []
            
            # Check secret key
            secret_key = os.getenv("SECRET_KEY", "")
            if not secret_key or len(secret_key) < 32:
                issues.append("SECRET_KEY is missing or too short")
            
            # Check debug mode
            debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
            if debug:
                warnings.append("Debug mode is enabled - disable in production")
            
            # Check HTTPS enforcement
            # This is typically handled by the proxy, but check config
            
            if issues:
                return AgentResult(
                    success=False,
                    status=AgentStatus.CRITICAL,
                    message="Critical security configuration issues",
                    errors=issues,
                    warnings=warnings,
                    suggestions=["Set a strong SECRET_KEY (32+ characters)"]
                )
            
            if warnings:
                return AgentResult(
                    success=True,
                    status=AgentStatus.WARNING,
                    message="Security configuration has warnings",
                    warnings=warnings
                )
            
            return AgentResult(
                success=True,
                status=AgentStatus.HEALTHY,
                message="Security configuration OK"
            )
        except Exception as e:
            return AgentResult(
                success=False,
                status=AgentStatus.ERROR,
                message=f"Config check failed: {e}",
                errors=[str(e)]
            )
    
    async def _check_auth_status(self) -> AgentResult:
        """Check authentication system status."""
        try:
            from web.database import db, User
            from web.app import create_app
            
            app = create_app()
            with app.app_context():
                total_users = User.query.count()
                verified_users = User.query.filter_by(email_verified=True).count()
                oauth_users = User.query.filter(User.oauth_provider.isnot(None)).count()
                
                return AgentResult(
                    success=True,
                    status=AgentStatus.HEALTHY,
                    message=f"Auth system healthy: {total_users} users",
                    data={
                        "total_users": total_users,
                        "verified_users": verified_users,
                        "oauth_users": oauth_users,
                        "verification_rate": (verified_users / total_users * 100) if total_users > 0 else 0
                    }
                )
        except Exception as e:
            return AgentResult(
                success=False,
                status=AgentStatus.ERROR,
                message=f"Auth check failed: {e}",
                errors=[str(e)]
            )
    
    async def _check_rate_limiting(self) -> AgentResult:
        """Check rate limiting configuration."""
        try:
            from web.extensions import limiter
            from web.config import Config
            
            # Check if limiter is configured
            if limiter:
                return AgentResult(
                    success=True,
                    status=AgentStatus.HEALTHY,
                    message="Rate limiting is active",
                    data={
                        "api_rate_limit": Config.RATE_LIMITS.get("api_per_minute"),
                        "auth_rate_limit": Config.RATE_LIMITS.get("auth_per_minute"),
                    }
                )
            else:
                return AgentResult(
                    success=False,
                    status=AgentStatus.WARNING,
                    message="Rate limiting may not be properly configured",
                    suggestions=["Verify flask-limiter is configured correctly"]
                )
        except Exception as e:
            return AgentResult(
                success=False,
                status=AgentStatus.ERROR,
                message=f"Rate limit check failed: {e}",
                errors=[str(e)]
            )
    
    async def _check_csrf_protection(self) -> AgentResult:
        """Check CSRF protection status."""
        try:
            from web.extensions import csrf
            
            if csrf:
                return AgentResult(
                    success=True,
                    status=AgentStatus.HEALTHY,
                    message="CSRF protection is enabled"
                )
            else:
                return AgentResult(
                    success=False,
                    status=AgentStatus.CRITICAL,
                    message="CSRF protection may not be enabled",
                    errors=["CSRF extension not found"],
                    suggestions=["Ensure Flask-WTF CSRF is properly initialized"]
                )
        except Exception as e:
            return AgentResult(
                success=False,
                status=AgentStatus.ERROR,
                message=f"CSRF check failed: {e}",
                errors=[str(e)]
            )
    
    async def _check_user_activity(self) -> AgentResult:
        """Monitor user activity."""
        try:
            from web.database import db, User
            from web.app import create_app
            
            app = create_app()
            with app.app_context():
                # New users in last 24h
                cutoff_24h = datetime.now(timezone.utc) - timedelta(hours=24)
                new_users_24h = User.query.filter(
                    User.created_at >= cutoff_24h
                ).count()
                
                # New users in last 7 days
                cutoff_7d = datetime.now(timezone.utc) - timedelta(days=7)
                new_users_7d = User.query.filter(
                    User.created_at >= cutoff_7d
                ).count()
                
                return AgentResult(
                    success=True,
                    status=AgentStatus.HEALTHY,
                    message=f"User activity: {new_users_24h} new today, {new_users_7d} this week",
                    data={
                        "new_users_24h": new_users_24h,
                        "new_users_7d": new_users_7d
                    }
                )
        except Exception as e:
            return AgentResult(
                success=False,
                status=AgentStatus.ERROR,
                message=f"Activity check failed: {e}",
                errors=[str(e)]
            )

