"""
Scheduler Agent
===============

Automated scheduling for agent tasks and maintenance.
Runs tasks on intervals, at specific times, or on triggers.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path
from datetime import timedelta
from datetime import timezone
from typing import List
from typing import Optional
from typing import Any

logger = logging.getLogger(__name__)


class ScheduleType(Enum):
    INTERVAL = "interval"  # Run every X seconds
    DAILY = "daily"  # Run at specific time each day
    HOURLY = "hourly"  # Run at specific minute each hour
    CRON = "cron"  # Cron-like scheduling
    ONCE = "once"  # Run once at specific time
    ON_CHANGE = "on_change"  # Run when files change


@dataclass
class ScheduledTask:
    """A scheduled task."""
    id: str
    name: str
    description: str
    schedule_type: ScheduleType
    handler: str  # Function name to call
    config: Dict[str, Any]
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    last_result: Optional[str] = None
    last_error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "schedule_type": self.schedule_type.value,
            "handler": self.handler,
            "config": self.config,
            "enabled": self.enabled,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "run_count": self.run_count,
            "last_result": self.last_result,
            "last_error": self.last_error,
        }


class SchedulerAgent:
    """
    Automated task scheduler for agents.

    Capabilities:
    - Schedule recurring maintenance tasks
    - Run code analysis on intervals
    - Auto-commit at end of day
    - Database cleanup schedules
    - Performance monitoring
    - Backup automation
    """

    def __init__(self):
        self.name = "scheduler"
        self.project_root = Path(__file__).parent.parent.parent
        self.data_file = self.project_root / "data" / "agents" / "scheduler.json"

        # Scheduled tasks
        self.tasks: Dict[str, ScheduledTask] = {}

        # Task handlers
        self.handlers: Dict[str, Callable] = {}

        # Running state
        self.running = False
        self.check_interval = 60  # Check every 60 seconds

        # Stats
        self.stats = {
            "tasks_executed": 0,
            "tasks_failed": 0,
            "uptime_start": None,
        }

        # Load saved tasks
        self._load_tasks()

        # Register default handlers
        self._register_default_handlers()

        # Create default tasks
        self._create_default_tasks()

    def _register_default_handlers(self):
        """Register default task handlers."""
        self.handlers = {
            "run_health_check": self._handler_health_check,
            "run_code_analysis": self._handler_code_analysis,
            "run_auto_fix": self._handler_auto_fix,
            "cleanup_old_data": self._handler_cleanup,
            "generate_report": self._handler_report,
            "backup_database": self._handler_backup,
            "update_ai_scores": self._handler_ai_scores,
            "git_auto_commit": self._handler_git_commit,
            "clear_old_memories": self._handler_clear_memories,
            "run_tests": self._handler_run_tests,
        }

    def _create_default_tasks(self):
        """Create default scheduled tasks."""
        defaults = [
            ScheduledTask(
                id="health_check_hourly",
                name="Hourly Health Check",
                description="Check system health every hour",
                schedule_type=ScheduleType.INTERVAL,
                handler="run_health_check",
                config={"interval_seconds": 3600},
            ),
            ScheduledTask(
                id="code_analysis_daily",
                name="Daily Code Analysis",
                description="Analyze codebase for issues daily",
                schedule_type=ScheduleType.DAILY,
                handler="run_code_analysis",
                config={"hour": 2, "minute": 0},  # 2 AM
            ),
            ScheduledTask(
                id="auto_fix_daily",
                name="Daily Auto-Fix",
                description="Run auto-fixer on safe issues",
                schedule_type=ScheduleType.DAILY,
                handler="run_auto_fix",
                config={"hour": 3, "minute": 0},  # 3 AM
            ),
            ScheduledTask(
                id="cleanup_weekly",
                name="Weekly Cleanup",
                description="Clean up old data and logs",
                schedule_type=ScheduleType.DAILY,
                handler="cleanup_old_data",
                config={"hour": 4, "minute": 0, "day_of_week": 0},  # Monday 4 AM
            ),
            ScheduledTask(
                id="report_daily",
                name="Daily Report",
                description="Generate daily agent report",
                schedule_type=ScheduleType.DAILY,
                handler="generate_report",
                config={"hour": 6, "minute": 0},  # 6 AM
            ),
            ScheduledTask(
                id="memory_cleanup",
                name="Memory Cleanup",
                description="Clear old agent memories",
                schedule_type=ScheduleType.DAILY,
                handler="clear_old_memories",
                config={"hour": 5, "minute": 0},  # 5 AM
            ),
        ]

        for task in defaults:
            if task.id not in self.tasks:
                self.tasks[task.id] = task
                self._calculate_next_run(task)

        self._save_tasks()

    def add_task(
        self,
        task_id: str,
        name: str,
        description: str,
        schedule_type: ScheduleType,
        handler: str,
        config: Dict[str, Any],
    ) -> ScheduledTask:
        """Add a new scheduled task."""
        task = ScheduledTask(
            id=task_id,
            name=name,
            description=description,
            schedule_type=schedule_type,
            handler=handler,
            config=config,
        )

        self._calculate_next_run(task)
        self.tasks[task_id] = task
        self._save_tasks()

        return task

    def remove_task(self, task_id: str) -> bool:
        """Remove a scheduled task."""
        if task_id in self.tasks:
            del self.tasks[task_id]
            self._save_tasks()
            return True
        return False

    def enable_task(self, task_id: str) -> bool:
        """Enable a task."""
        if task_id in self.tasks:
            self.tasks[task_id].enabled = True
            self._calculate_next_run(self.tasks[task_id])
            self._save_tasks()
            return True
        return False

    def disable_task(self, task_id: str) -> bool:
        """Disable a task."""
        if task_id in self.tasks:
            self.tasks[task_id].enabled = False
            self._save_tasks()
            return True
        return False

    def run_task_now(self, task_id: str) -> Dict[str, Any]:
        """Run a task immediately."""
        if task_id not in self.tasks:
            return {"success": False, "error": "Task not found"}

        task = self.tasks[task_id]
        return asyncio.run(self._execute_task(task))

    async def start(self):
        """Start the scheduler."""
        self.running = True
        self.stats["uptime_start"] = datetime.now(timezone.utc)

        logger.info("Scheduler started")

        while self.running:
            now = datetime.now(timezone.utc)

            for task in self.tasks.values():
                if not task.enabled:
                    continue

                if task.next_run and task.next_run <= now:
                    try:
                        await self._execute_task(task)
                    except Exception as e:
                        logger.error(f"Task execution error: {e}")
                        task.last_error = str(e)

            await asyncio.sleep(self.check_interval)

    def stop(self):
        """Stop the scheduler."""
        self.running = False
        logger.info("Scheduler stopped")

    async def _execute_task(self, task: ScheduledTask) -> Dict[str, Any]:
        """Execute a scheduled task."""
        logger.info(f"Executing task: {task.name}")

        start_time = datetime.now(timezone.utc)
        result = {"success": False, "task_id": task.id}

        try:
            handler = self.handlers.get(task.handler)

            if not handler:
                result["error"] = f"Handler not found: {task.handler}"
                task.last_error = result["error"]
            else:
                if asyncio.iscoroutinefunction(handler):
                    handler_result = await handler(task.config)
                else:
                    handler_result = handler(task.config)

                result["success"] = True
                result["result"] = handler_result
                task.last_result = str(handler_result)[:500]
                task.last_error = None
                self.stats["tasks_executed"] += 1

        except Exception as e:
            result["error"] = str(e)
            task.last_error = str(e)
            self.stats["tasks_failed"] += 1
            logger.error(f"Task {task.id} failed: {e}")

        # Update task state
        task.last_run = start_time
        task.run_count += 1
        self._calculate_next_run(task)
        self._save_tasks()

        result["duration_ms"] = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

        return result

    def _calculate_next_run(self, task: ScheduledTask):
        """Calculate next run time for a task."""
        now = datetime.now(timezone.utc)

        if task.schedule_type == ScheduleType.INTERVAL:
            interval = task.config.get("interval_seconds", 3600)
            if task.last_run:
                task.next_run = task.last_run + timedelta(seconds=interval)
            else:
                task.next_run = now + timedelta(seconds=60)  # First run in 1 minute

        elif task.schedule_type == ScheduleType.DAILY:
            hour = task.config.get("hour", 0)
            minute = task.config.get("minute", 0)

            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

            if next_run <= now:
                next_run += timedelta(days=1)

            # Check day of week if specified
            day_of_week = task.config.get("day_of_week")
            if day_of_week is not None:
                while next_run.weekday() != day_of_week:
                    next_run += timedelta(days=1)

            task.next_run = next_run

        elif task.schedule_type == ScheduleType.HOURLY:
            minute = task.config.get("minute", 0)

            next_run = now.replace(minute=minute, second=0, microsecond=0)

            if next_run <= now:
                next_run += timedelta(hours=1)

            task.next_run = next_run

        elif task.schedule_type == ScheduleType.ONCE:
            run_at = task.config.get("run_at")
            if run_at:
                task.next_run = datetime.fromisoformat(run_at)
            else:
                task.enabled = False

        else:
            # Default to 1 hour from now
            task.next_run = now + timedelta(hours=1)

    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        return {
            "running": self.running,
            "total_tasks": len(self.tasks),
            "enabled_tasks": len([t for t in self.tasks.values() if t.enabled]),
            "stats": self.stats,
            "uptime": (datetime.now(timezone.utc) - self.stats["uptime_start"]).total_seconds()
                if self.stats["uptime_start"] else 0,
        }

    def get_upcoming_tasks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get upcoming scheduled tasks."""
        enabled = [t for t in self.tasks.values() if t.enabled and t.next_run]
        upcoming = sorted(enabled, key=lambda t: t.next_run)

        return [
            {
                "id": t.id,
                "name": t.name,
                "next_run": t.next_run.isoformat(),
                "handler": t.handler,
            }
            for t in upcoming[:limit]
        ]

    def _load_tasks(self):
        """Load tasks from disk."""
        if not self.data_file.exists():
            return

        try:
            data = json.loads(self.data_file.read_text(encoding='utf-8'))

            for task_data in data.get("tasks", []):
                task = ScheduledTask(
                    id=task_data["id"],
                    name=task_data["name"],
                    description=task_data["description"],
                    schedule_type=ScheduleType(task_data["schedule_type"]),
                    handler=task_data["handler"],
                    config=task_data["config"],
                    enabled=task_data.get("enabled", True),
                    run_count=task_data.get("run_count", 0),
                    last_result=task_data.get("last_result"),
                    last_error=task_data.get("last_error"),
                )

                if task_data.get("last_run"):
                    task.last_run = datetime.fromisoformat(task_data["last_run"])

                self._calculate_next_run(task)
                self.tasks[task.id] = task

            self.stats = data.get("stats", self.stats)

        except Exception as e:
            logger.error(f"Error loading scheduler tasks: {e}")

    def _save_tasks(self):
        """Save tasks to disk."""
        try:
            self.data_file.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "tasks": [t.to_dict() for t in self.tasks.values()],
                "stats": self.stats,
                "saved_at": datetime.now(timezone.utc).isoformat(),
            }

            self.data_file.write_text(
                json.dumps(data, indent=2, default=str),
                encoding='utf-8'
            )

        except Exception as e:
            logger.error(f"Error saving scheduler tasks: {e}")

    # ============ Task Handlers ============

    async def _handler_health_check(self, config: Dict) -> Dict[str, Any]:
        """Run system health check."""
        from agents.orchestrator import AgentOrchestrator

        orchestrator = AgentOrchestrator()
        result = orchestrator.check_all_status()

        return {
            "status": result.get("overall_status"),
            "agents_checked": len(result.get("agents", {})),
        }

    async def _handler_code_analysis(self, config: Dict) -> Dict[str, Any]:
        """Run code analysis."""
        from agents.autonomous.smart_analyzer import SmartAnalyzer

        analyzer = SmartAnalyzer()
        result = analyzer.analyze_project()

        return {
            "files_analyzed": result.get("files_analyzed", 0),
            "issues_found": result.get("total_issues", 0),
            "health_score": result.get("health_score", 0),
        }

    async def _handler_auto_fix(self, config: Dict) -> Dict[str, Any]:
        """Run auto-fixer."""
        from agents.autonomous.fixer import FixerAgent

        fixer = FixerAgent()
        result = await fixer.scan_and_fix_all()

        return {
            "files_scanned": result.get("scanned_files", 0),
            "files_fixed": result.get("fixed_files", 0),
        }

    async def _handler_cleanup(self, config: Dict) -> Dict[str, Any]:
        """Clean up old data."""
        cleaned = {
            "old_reports": 0,
            "old_logs": 0,
        }

        # Clean old agent reports
        reports_dir = self.project_root / "data" / "agent_reports"
        if reports_dir.exists():
            cutoff = datetime.now(timezone.utc) - timedelta(days=30)

            for report_file in reports_dir.glob("*.json"):
                if report_file.stat().st_mtime < cutoff.timestamp():
                    report_file.unlink()
                    cleaned["old_reports"] += 1

        return cleaned

    async def _handler_report(self, config: Dict) -> Dict[str, Any]:
        """Generate daily report."""
        from agents.orchestrator import AgentOrchestrator

        orchestrator = AgentOrchestrator()
        status = orchestrator.check_all_status()

        report = {
            "date": datetime.now(timezone.utc).isoformat(),
            "status": status.get("overall_status"),
            "agents": len(status.get("agents", {})),
            "tasks_scheduled": len(self.tasks),
        }

        # Save report
        report_file = self.project_root / "data" / "agent_reports" / f"daily_{datetime.now().strftime('%Y%m%d')}.json"
        report_file.parent.mkdir(parents=True, exist_ok=True)
        report_file.write_text(json.dumps(report, indent=2), encoding='utf-8')

        return report

    async def _handler_backup(self, config: Dict) -> Dict[str, Any]:
        """Backup database."""
        import shutil

        db_path = self.project_root / "instance" / "qunextrade.db"

        if db_path.exists():
            backup_dir = self.project_root / "data" / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)

            backup_name = f"db_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            shutil.copy2(db_path, backup_dir / backup_name)

            return {"backup": backup_name}

        return {"error": "Database not found"}

    async def _handler_ai_scores(self, config: Dict) -> Dict[str, Any]:
        """Update AI scores."""
        # This would call the AI score update script
        return {"status": "skipped", "reason": "Manual trigger required"}

    async def _handler_git_commit(self, config: Dict) -> Dict[str, Any]:
        """Auto-commit changes."""
        from agents.autonomous.git_agent import GitAgent

        git = GitAgent()
        result = await git.smart_commit_session()

        return result

    async def _handler_clear_memories(self, config: Dict) -> Dict[str, Any]:
        """Clear old memories."""
        from agents.autonomous.memory import get_memory

        memory = get_memory()
        forgotten = memory.forget_old(days=30)

        return {"memories_cleared": forgotten}

    async def _handler_run_tests(self, config: Dict) -> Dict[str, Any]:
        """Run tests."""
        from agents.autonomous.test_runner import TestRunnerAgent

        runner = TestRunnerAgent()
        report = await runner.run_all_tests()

        return {
            "total": report.total_tests,
            "passed": report.passed,
            "failed": report.failed,
        }

