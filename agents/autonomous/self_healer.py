"""
Self-Healing Agent
==================

Automatically detects and recovers from errors.
Monitors system health and takes corrective action.
"""

import logging
import traceback
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from datetime import timedelta
from datetime import timezone
import json
from typing import List
from typing import Optional
from typing import Any
from typing import Tuple

logger = logging.getLogger(__name__)


@dataclass
class HealthCheck:
    """Result of a health check."""
    component: str
    status: str  # healthy, degraded, failed
    message: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    can_auto_heal: bool = False
    heal_action: Optional[str] = None


@dataclass
class HealingAction:
    """A healing action taken."""
    component: str
    issue: str
    action: str
    success: bool
    timestamp: datetime
    details: Optional[str] = None


class SelfHealerAgent:
    """
    Autonomous self-healing system.

    Capabilities:
    - Monitor critical components
    - Detect failures and errors
    - Automatic recovery actions
    - Restart services if needed
    - Fix common issues
    - Alert on unrecoverable errors
    """

    def __init__(self):
        self.name = "self_healer"
        self.project_root = Path(__file__).parent.parent.parent

        # Healing history
        self.healing_history: List[HealingAction] = []

        # Health status
        self.health_status: Dict[str, HealthCheck] = {}

        # Configuration
        self.config = {
            "max_heal_attempts": 3,
            "heal_cooldown_seconds": 300,  # 5 minutes between attempts
            "auto_heal_enabled": True,
        }

        # Healing strategies
        self.healing_strategies = {
            "database": self._heal_database,
            "imports": self._heal_imports,
            "syntax": self._heal_syntax,
            "dependencies": self._heal_dependencies,
            "config": self._heal_config,
            "permissions": self._heal_permissions,
            "disk_space": self._heal_disk_space,
        }

        # Track recent heal attempts to prevent loops
        self.recent_heals: Dict[str, datetime] = {}

    async def run_health_checks(self) -> Dict[str, HealthCheck]:
        """Run all health checks."""
        checks = {}

        # Check database
        checks["database"] = await self._check_database()

        # Check imports
        checks["imports"] = await self._check_imports()

        # Check config
        checks["config"] = await self._check_config()

        # Check dependencies
        checks["dependencies"] = await self._check_dependencies()

        # Check disk space
        checks["disk_space"] = await self._check_disk_space()

        # Check syntax of critical files
        checks["syntax"] = await self._check_syntax()

        self.health_status = checks

        return checks

    async def auto_heal(self) -> Dict[str, Any]:
        """Automatically heal all detected issues."""
        if not self.config["auto_heal_enabled"]:
            return {"status": "disabled", "healed": 0}

        # Run health checks first
        checks = await self.run_health_checks()

        healed = 0
        failed = 0
        actions = []

        for component, check in checks.items():
            if check.status == "healthy":
                continue

            if not check.can_auto_heal:
                continue

            # Check cooldown
            if component in self.recent_heals:
                last_heal = self.recent_heals[component]
                if (datetime.now(timezone.utc) - last_heal).seconds < self.config["heal_cooldown_seconds"]:
                    continue

            # Attempt healing
            success, message = await self._attempt_heal(component, check)

            action = HealingAction(
                component=component,
                issue=check.message,
                action=check.heal_action or "auto",
                success=success,
                timestamp=datetime.now(timezone.utc),
                details=message,
            )

            self.healing_history.append(action)
            actions.append(action)

            if success:
                healed += 1
                self.recent_heals[component] = datetime.now(timezone.utc)
            else:
                failed += 1

        return {
            "status": "completed",
            "healed": healed,
            "failed": failed,
            "actions": [
                {
                    "component": a.component,
                    "issue": a.issue,
                    "success": a.success,
                    "details": a.details,
                }
                for a in actions
            ],
        }

    async def _attempt_heal(self, component: str, check: HealthCheck) -> Tuple[bool, str]:
        """Attempt to heal a component."""
        strategy = self.healing_strategies.get(component)

        if not strategy:
            return False, f"No healing strategy for {component}"

        try:
            return await strategy(check)
        except Exception as e:
            logger.error(f"Healing failed for {component}: {e}")
            return False, str(e)

    # ============ Health Checks ============

    async def _check_database(self) -> HealthCheck:
        """Check database health."""
        try:
            db_path = self.project_root / "instance" / "qunextrade.db"

            if not db_path.exists():
                return HealthCheck(
                    component="database",
                    status="failed",
                    message="Database file not found",
                    can_auto_heal=True,
                    heal_action="create_database",
                )

            # Try to connect
            import sqlite3
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            conn.close()

            return HealthCheck(
                component="database",
                status="healthy",
                message="Database is accessible",
            )

        except Exception as e:
            return HealthCheck(
                component="database",
                status="failed",
                message=str(e),
                can_auto_heal=True,
                heal_action="repair_database",
            )

    async def _check_imports(self) -> HealthCheck:
        """Check if all imports work."""
        failed_imports = []

        critical_modules = [
            "flask",
            "flask_login",
            "sqlalchemy",
            "requests",
        ]

        for module in critical_modules:
            try:
                __import__(module)
            except ImportError:
                failed_imports.append(module)

        if failed_imports:
            return HealthCheck(
                component="imports",
                status="failed",
                message=f"Missing modules: {', '.join(failed_imports)}",
                can_auto_heal=True,
                heal_action="install_dependencies",
            )

        return HealthCheck(
            component="imports",
            status="healthy",
            message="All critical imports work",
        )

    async def _check_config(self) -> HealthCheck:
        """Check configuration."""
        issues = []

        # Check for .env file
        env_file = self.project_root / ".env"
        if not env_file.exists():
            issues.append("Missing .env file")

        # Check for config.py
        config_file = self.project_root / "web" / "config.py"
        if not config_file.exists():
            issues.append("Missing config.py")

        if issues:
            return HealthCheck(
                component="config",
                status="degraded",
                message="; ".join(issues),
                can_auto_heal=len(issues) == 1 and "Missing .env" in issues[0],
                heal_action="create_env_template",
            )

        return HealthCheck(
            component="config",
            status="healthy",
            message="Configuration files exist",
        )

    async def _check_dependencies(self) -> HealthCheck:
        """Check Python dependencies."""
        try:
            requirements_file = self.project_root / "requirements.txt"

            if not requirements_file.exists():
                return HealthCheck(
                    component="dependencies",
                    status="degraded",
                    message="requirements.txt not found",
                )

            # Basic check - just verify file exists and is readable
            content = requirements_file.read_text()
            package_count = len([l for l in content.split('\n') if l.strip() and not l.startswith('#')])

            return HealthCheck(
                component="dependencies",
                status="healthy",
                message=f"{package_count} packages in requirements.txt",
            )

        except Exception as e:
            return HealthCheck(
                component="dependencies",
                status="degraded",
                message=str(e),
            )

    async def _check_disk_space(self) -> HealthCheck:
        """Check disk space."""
        try:
            import shutil

            total, used, free = shutil.disk_usage(str(self.project_root))

            free_percent = (free / total) * 100

            if free_percent < 5:
                return HealthCheck(
                    component="disk_space",
                    status="failed",
                    message=f"Critical: Only {free_percent:.1f}% disk space free",
                    can_auto_heal=True,
                    heal_action="cleanup_disk",
                )
            elif free_percent < 15:
                return HealthCheck(
                    component="disk_space",
                    status="degraded",
                    message=f"Low: {free_percent:.1f}% disk space free",
                    can_auto_heal=True,
                    heal_action="cleanup_disk",
                )

            return HealthCheck(
                component="disk_space",
                status="healthy",
                message=f"{free_percent:.1f}% disk space free",
            )

        except Exception as e:
            return HealthCheck(
                component="disk_space",
                status="degraded",
                message=str(e),
            )

    async def _check_syntax(self) -> HealthCheck:
        """Check syntax of Python files."""
        import ast

        errors = []

        critical_files = [
            "web/app.py",
            "web/database.py",
            "run.py",
            "agents/__init__.py",
        ]

        for file_path in critical_files:
            full_path = self.project_root / file_path

            if not full_path.exists():
                continue

            try:
                content = full_path.read_text(encoding='utf-8')
                ast.parse(content)
            except SyntaxError as e:
                errors.append(f"{file_path}: {e.msg} (line {e.lineno})")

        if errors:
            return HealthCheck(
                component="syntax",
                status="failed",
                message=f"{len(errors)} syntax error(s): {errors[0]}",
                can_auto_heal=True,
                heal_action="fix_syntax",
            )

        return HealthCheck(
            component="syntax",
            status="healthy",
            message="No syntax errors in critical files",
        )

    # ============ Healing Strategies ============

    async def _heal_database(self, check: HealthCheck) -> Tuple[bool, str]:
        """Heal database issues."""
        db_path = self.project_root / "instance" / "qunextrade.db"

        if "not found" in check.message:
            # Create database
            try:
                db_path.parent.mkdir(parents=True, exist_ok=True)

                # Run init_db script if it exists
                init_script = self.project_root / "init_db.py"
                if init_script.exists():
                    result = subprocess.run(
                        [sys.executable, str(init_script)],
                        cwd=str(self.project_root),
                        capture_output=True,
                        text=True,
                    )

                    if result.returncode == 0:
                        return True, "Database created via init_db.py"
                    else:
                        return False, result.stderr

                # Create empty database
                import sqlite3
                conn = sqlite3.connect(str(db_path))
                conn.close()

                return True, "Created empty database"

            except Exception as e:
                return False, str(e)

        return False, "Cannot auto-heal this database issue"

    async def _heal_imports(self, check: HealthCheck) -> Tuple[bool, str]:
        """Heal import issues by installing missing packages."""
        try:
            # Extract missing module names
            import re
            match = re.search(r"Missing modules: (.+)", check.message)

            if not match:
                return False, "Cannot determine missing modules"

            modules = [m.strip() for m in match.group(1).split(',')]

            # Map module names to package names
            module_to_package = {
                "flask": "flask",
                "flask_login": "flask-login",
                "sqlalchemy": "sqlalchemy",
                "requests": "requests",
            }

            packages = [module_to_package.get(m, m) for m in modules]

            # Install packages
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install"] + packages,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                return True, f"Installed: {', '.join(packages)}"
            else:
                return False, result.stderr

        except Exception as e:
            return False, str(e)

    async def _heal_syntax(self, check: HealthCheck) -> Tuple[bool, str]:
        """Attempt to fix syntax errors."""
        try:
            from agents.autonomous.fixer import FixerAgent

            fixer = FixerAgent()

            # Find the file with syntax error
            import re
            match = re.search(r"(\S+\.py):", check.message)

            if not match:
                return False, "Cannot determine file with syntax error"

            file_path = self.project_root / match.group(1)

            if not file_path.exists():
                return False, f"File not found: {file_path}"

            content = file_path.read_text(encoding='utf-8')

            # Try common fixes
            fixed = content

            # Fix common syntax issues
            fixed = fixer._fix_bare_except(fixed, None)

            # Try to parse
            import ast
            try:
                ast.parse(fixed)
                file_path.write_text(fixed, encoding='utf-8')
                return True, f"Fixed syntax in {match.group(1)}"
            except SyntaxError:
                return False, "Could not auto-fix syntax error"

        except Exception as e:
            return False, str(e)

    async def _heal_dependencies(self, check: HealthCheck) -> Tuple[bool, str]:
        """Heal dependency issues."""
        try:
            requirements_file = self.project_root / "requirements.txt"

            if requirements_file.exists():
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)],
                    capture_output=True,
                    text=True,
                )

                if result.returncode == 0:
                    return True, "Dependencies installed from requirements.txt"
                else:
                    return False, result.stderr

            return False, "requirements.txt not found"

        except Exception as e:
            return False, str(e)

    async def _heal_config(self, check: HealthCheck) -> Tuple[bool, str]:
        """Heal configuration issues."""
        if "Missing .env" in check.message:
            try:
                env_template = '''# Environment Configuration
# Copy this to .env and fill in your values

# Flask
SECRET_KEY=your-secret-key-here
FLASK_ENV=development

# Database
DATABASE_URL=sqlite:///instance/qunextrade.db

# API Keys (get from respective providers)
POLYGON_API_KEY=
FINNHUB_API_KEY=

# Optional
DEBUG=False
'''

                env_file = self.project_root / ".env.template"
                env_file.write_text(env_template)

                return True, "Created .env.template - copy to .env and configure"

            except Exception as e:
                return False, str(e)

        return False, "Cannot auto-heal this config issue"

    async def _heal_permissions(self, check: HealthCheck) -> Tuple[bool, str]:
        """Heal permission issues."""
        return False, "Permission issues require manual intervention"

    async def _heal_disk_space(self, check: HealthCheck) -> Tuple[bool, str]:
        """Heal disk space issues by cleaning up."""
        try:
            cleaned = 0

            # Clean __pycache__ directories
            for pycache in self.project_root.rglob("__pycache__"):
                import shutil
                shutil.rmtree(pycache)
                cleaned += 1

            # Clean old log files
            for log_file in self.project_root.rglob("*.log"):
                if log_file.stat().st_mtime < (datetime.now().timestamp() - 7 * 86400):
                    log_file.unlink()
                    cleaned += 1

            # Clean old agent reports
            reports_dir = self.project_root / "data" / "agent_reports"
            if reports_dir.exists():
                cutoff = datetime.now() - timedelta(days=7)
                for report in reports_dir.glob("*.json"):
                    if report.stat().st_mtime < cutoff.timestamp():
                        report.unlink()
                        cleaned += 1

            return True, f"Cleaned {cleaned} files/directories"

        except Exception as e:
            return False, str(e)

    def get_status(self) -> Dict[str, Any]:
        """Get self-healer status."""
        return {
            "enabled": self.config["auto_heal_enabled"],
            "health_checks": len(self.health_status),
            "healthy": len([c for c in self.health_status.values() if c.status == "healthy"]),
            "degraded": len([c for c in self.health_status.values() if c.status == "degraded"]),
            "failed": len([c for c in self.health_status.values() if c.status == "failed"]),
            "recent_heals": len(self.healing_history),
            "last_check": max((c.timestamp for c in self.health_status.values()), default=None),
        }

    def get_health_report(self) -> Dict[str, Any]:
        """Get detailed health report."""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": {
                name: {
                    "status": check.status,
                    "message": check.message,
                    "can_auto_heal": check.can_auto_heal,
                }
                for name, check in self.health_status.items()
            },
            "recent_actions": [
                {
                    "component": a.component,
                    "issue": a.issue,
                    "action": a.action,
                    "success": a.success,
                    "timestamp": a.timestamp.isoformat(),
                }
                for a in self.healing_history[-10:]
            ],
        }

