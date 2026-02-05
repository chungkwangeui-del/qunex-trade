"""
Autonomous Pipeline
===================

The main execution pipeline that runs all autonomous agents.
This is the entry point for fully automated operation.
"""

import asyncio
import logging
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path

from agents.autonomous.master import MasterAgent
from agents.autonomous.developer import DeveloperAgent
from agents.autonomous.reviewer import ReviewerAgent
from agents.autonomous.fixer import FixerAgent
from agents.autonomous.improver import ImproverAgent
from agents.autonomous.task_queue import (
    TaskQueue, Task, TaskStatus, TaskType, TaskPriority
)

logger = logging.getLogger(__name__)

class AutoPipeline:
    """
    Fully autonomous development pipeline.

    Workflow:
    1. Master analyzes system → creates tasks
    2. Appropriate agent processes each task
    3. Reviewer validates changes
    4. Changes are applied or rolled back
    5. Report is generated

    Can run continuously or as one-shot.
    """

    def __init__(self):
        self.master = MasterAgent()
        self.developer = DeveloperAgent()
        self.reviewer = ReviewerAgent()
        self.fixer = FixerAgent()
        self.improver = ImproverAgent()
        self.task_queue = TaskQueue.get_instance()

        self.project_root = Path(__file__).parent.parent.parent
        self.reports_dir = self.project_root / "data" / "agent_reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        self.running = False
        self.cycle_count = 0
        self.last_cycle: Optional[datetime] = None

        # Configuration
        self.config = {
            "cycle_interval_seconds": 300,  # 5 minutes between cycles
            "max_tasks_per_cycle": 5,
            "auto_apply_fixes": True,
            "require_review": True,
            "min_review_score": 70,
            "max_retries": 3,
            "auto_commit": True,  # Commit changes after each cycle
            "auto_push": True,    # Push to GitHub after commits
        }

    def get_agent_for_task(self, task: Task):
        """Get the appropriate agent for a task"""
        if task.task_type == TaskType.SECURITY_FIX:
            return self.fixer
        elif task.task_type == TaskType.BUG_FIX:
            return self.fixer
        elif task.task_type in [TaskType.FEATURE, TaskType.TEST]:
            return self.developer
        elif task.task_type in [TaskType.IMPROVEMENT, TaskType.REFACTOR]:
            return self.improver
        else:
            return self.developer

    async def run_single_cycle(self) -> Dict[str, Any]:
        """
        Run one complete automation cycle.

        Returns detailed report of actions taken.
        """
        cycle_start = datetime.now(timezone.utc)
        self.cycle_count += 1

        report = {
            "cycle_number": self.cycle_count,
            "start_time": cycle_start.isoformat(),
            "phases": {},
            "tasks_processed": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "changes_applied": 0,
            "changes_rolled_back": 0,
            "errors": [],
        }

        try:
            # ========== PHASE 1: Analysis ==========
            logger.info("Phase 1: System Analysis")
            report["phases"]["analysis"] = {}

            analysis = await self.master.analyze_system()
            report["phases"]["analysis"] = {
                "health_score": analysis["health"].get("score", 0),
                "issues_found": len(analysis.get("issues", [])),
                "opportunities_found": len(analysis.get("opportunities", [])),
            }

            # ========== PHASE 2: Task Creation ==========
            logger.info("Phase 2: Task Creation")

            new_tasks = await self.master.create_tasks_from_analysis(analysis)
            report["phases"]["task_creation"] = {
                "tasks_created": len(new_tasks),
            }

            # ========== PHASE 3: Task Processing ==========
            logger.info("Phase 3: Task Processing")
            report["phases"]["processing"] = {"tasks": []}

            # Get pending tasks
            pending_tasks = self.task_queue.get_pending_tasks()
            tasks_to_process = pending_tasks[:self.config["max_tasks_per_cycle"]]

            for task in tasks_to_process:
                task_report = await self._process_task(task)
                report["phases"]["processing"]["tasks"].append(task_report)
                report["tasks_processed"] += 1

                if task_report.get("success"):
                    report["tasks_completed"] += 1
                    report["changes_applied"] += task_report.get("changes_applied", 0)
                else:
                    if task_report.get("rolled_back"):
                        report["tasks_failed"] += 1
                        report["changes_rolled_back"] += task_report.get("changes_rolled_back", 0)

            # ========== PHASE 4: Quick Fixes ==========
            if self.config["auto_apply_fixes"]:
                logger.info("Phase 4: Auto Fixes")

                fix_result = await self.fixer.scan_and_fix_all()
                report["phases"]["auto_fixes"] = fix_result
                report["changes_applied"] += fix_result.get("fixed_files", 0)

            # ========== PHASE 4.5: Real Fixer (aggressive) ==========
            try:
                from agents.autonomous.real_fixer import RealFixerAgent

                logger.info("Phase 4.5: Real Fixer")
                real_fixer = RealFixerAgent()
                real_fix_result = await real_fixer.fix_all_errors()

                report["phases"]["real_fixes"] = {
                    "errors_found": real_fix_result.get("errors_found", 0),
                    "errors_fixed": real_fix_result.get("errors_fixed", 0),
                    "files_fixed": len(real_fix_result.get("fixed_files", [])),
                }
                report["changes_applied"] += len(real_fix_result.get("fixed_files", []))

            except Exception as real_fix_error:
                logger.error(f"Real fixer error: {real_fix_error}")

            # ========== PHASE 5: Git Commit & Push ==========
            if self.config.get("auto_commit") and report["changes_applied"] > 0:
                logger.info("Phase 5: Git Commit & Push")

                try:
                    from agents.autonomous.git_agent import GitAgent

                    git = GitAgent()
                    git.config["auto_push"] = self.config.get("auto_push", True)

                    git_result = await git.smart_commit_session()
                    report["phases"]["git"] = {
                        "committed": len(git_result.get("commits", [])) > 0,
                        "pushed": git_result.get("pushed", False),
                        "commits": len(git_result.get("commits", [])),
                    }
                except Exception as git_error:
                    logger.error(f"Git error: {git_error}")
                    report["phases"]["git"] = {"error": str(git_error)}

        except Exception as e:
            logger.error(f"Cycle error: {e}")
            report["errors"].append(str(e))

        # Finalize report
        cycle_end = datetime.now(timezone.utc)
        report["end_time"] = cycle_end.isoformat()
        report["duration_seconds"] = (cycle_end - cycle_start).total_seconds()

        self.last_cycle = cycle_end

        # Save report
        self._save_report(report)

        return report

    async def _process_task(self, task: Task) -> Dict[str, Any]:
        """Process a single task through the full pipeline"""
        task_report = {
            "task_id": task.id,
            "title": task.title,
            "type": task.task_type.value,
            "success": False,
            "changes_applied": 0,
            "changes_rolled_back": 0,
            "review_score": None,
            "error": None,
        }

        try:
            # Mark task as in progress
            task.status = TaskStatus.IN_PROGRESS
            task.started_at = datetime.now(timezone.utc)
            self.task_queue.update_task(task)

            # Get appropriate agent
            agent = self.get_agent_for_task(task)
            task.assigned_agent = agent.name

            # Process task
            success, message = await agent.process_task(task)
            task_report["process_message"] = message

            if not success:
                task_report["error"] = message
                self.task_queue.complete_task(task.id, success=False, error_message=message)
                return task_report

            # Review changes if required
            if self.config["require_review"] and task.changes:
                task.status = TaskStatus.REVIEW
                self.task_queue.update_task(task)

                review_result = await self.reviewer.review_task(task)
                task_report["review_score"] = review_result.score
                task_report["review_issues"] = len(review_result.issues)

                if not review_result.approved or review_result.score < self.config["min_review_score"]:
                    # Rollback changes
                    self.task_queue.rollback_task(task.id)
                    task_report["rolled_back"] = True
                    task_report["changes_rolled_back"] = len(task.changes)
                    task_report["error"] = f"Review failed (score: {review_result.score})"

                    # Retry if allowed
                    if task.retry_count < self.config["max_retries"]:
                        self.task_queue.retry_task(task.id)
                    else:
                        self.task_queue.complete_task(task.id, success=False,
                            error_message="Failed review after max retries")

                    return task_report

            # Success!
            task_report["success"] = True
            task_report["changes_applied"] = len(task.changes)
            self.task_queue.complete_task(task.id, success=True)

        except Exception as e:
            logger.error(f"Task processing error: {e}")
            task_report["error"] = str(e)
            self.task_queue.complete_task(task.id, success=False, error_message=str(e))

        return task_report

    async def run_continuous(self, max_cycles: Optional[int] = None):
        """
        Run continuous automation.

        Args:
            max_cycles: Stop after this many cycles (None for infinite)
        """
        self.running = True
        cycles_completed = 0

        logger.info("Starting continuous automation...")
        print("\n" + "=" * 60)
        print("  AUTONOMOUS AGENT PIPELINE - RUNNING")
        print("=" * 60)
        print(f"  Cycle interval: {self.config['cycle_interval_seconds']}s")
        print(f"  Max tasks per cycle: {self.config['max_tasks_per_cycle']}")
        print(f"  Auto-apply fixes: {self.config['auto_apply_fixes']}")
        print("=" * 60 + "\n")

        try:
            while self.running:
                if max_cycles and cycles_completed >= max_cycles:
                    break

                print(f"\n[Cycle {cycles_completed + 1}] Starting...")

                report = await self.run_single_cycle()
                cycles_completed += 1

                # Print summary
                print(f"[Cycle {cycles_completed}] Complete:")
                print(f"  - Tasks processed: {report['tasks_processed']}")
                print(f"  - Tasks completed: {report['tasks_completed']}")
                print(f"  - Changes applied: {report['changes_applied']}")
                if report['errors']:
                    print(f"  - Errors: {len(report['errors'])}")

                # Wait before next cycle
                if self.running and (not max_cycles or cycles_completed < max_cycles):
                    await asyncio.sleep(self.config["cycle_interval_seconds"])

        except KeyboardInterrupt:
            print("\n\nStopping automation...")
        finally:
            self.running = False

        print(f"\nAutomation stopped after {cycles_completed} cycles.")
        return cycles_completed

    def stop(self):
        """Stop continuous automation"""
        self.running = False

    def _save_report(self, report: Dict[str, Any]) -> None:
        """Save cycle report to file"""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        report_file = self.reports_dir / f"cycle_{timestamp}.json"

        try:
            report_file.write_text(
                json.dumps(report, indent=2, default=str),
                encoding='utf-8'
            )
        except Exception as e:
            logger.error(f"Failed to save report: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get current pipeline status"""
        queue_stats = self.task_queue.get_stats()

        return {
            "running": self.running,
            "cycle_count": self.cycle_count,
            "last_cycle": self.last_cycle.isoformat() if self.last_cycle else None,
            "config": self.config,
            "queue": queue_stats,
            "agents": {
                "master": "ready",
                "developer": "ready",
                "reviewer": "ready",
                "fixer": "ready",
                "improver": "ready",
            },
        }

    def get_recent_reports(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent cycle reports"""
        reports = []

        report_files = sorted(
            self.reports_dir.glob("cycle_*.json"),
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )

        for report_file in report_files[:limit]:
            try:
                report = json.loads(report_file.read_text(encoding='utf-8'))
                reports.append(report)
            except Exception:
                pass

        return reports

# ============ CLI Entry Point ============

async def main():
    """Run the autonomous pipeline from command line"""
    import argparse

    parser = argparse.ArgumentParser(description="Autonomous Agent Pipeline")
    parser.add_argument("--once", action="store_true", help="Run single cycle")
    parser.add_argument("--cycles", type=int, help="Run specific number of cycles")
    parser.add_argument("--status", action="store_true", help="Show status")
    parser.add_argument("--reports", action="store_true", help="Show recent reports")

    args = parser.parse_args()

    # Suppress logging for clean output
    logging.disable(logging.WARNING)

    pipeline = AutoPipeline()

    if args.status:
        status = pipeline.get_status()
        print("\n" + "=" * 50)
        print("  PIPELINE STATUS")
        print("=" * 50)
        print(f"  Running: {status['running']}")
        print(f"  Cycles completed: {status['cycle_count']}")
        print(f"  Last cycle: {status['last_cycle'] or 'Never'}")
        print("\n  Queue:")
        print(f"    Pending: {status['queue']['pending']}")
        print(f"    In Progress: {status['queue']['in_progress']}")
        print(f"    Completed: {status['queue']['completed']}")
        print("=" * 50)
        return

    if args.reports:
        reports = pipeline.get_recent_reports(5)
        print("\n" + "=" * 50)
        print("  RECENT REPORTS")
        print("=" * 50)
        for report in reports:
            print(f"\n  Cycle {report.get('cycle_number', '?')} - {report.get('start_time', '')[:19]}")
            print(f"    Tasks processed: {report.get('tasks_processed', 0)}")
            print(f"    Tasks completed: {report.get('tasks_completed', 0)}")
            print(f"    Changes applied: {report.get('changes_applied', 0)}")
        print("=" * 50)
        return

    if args.once:
        report = await pipeline.run_single_cycle()
        print("\n" + "=" * 50)
        print("  CYCLE COMPLETE")
        print("=" * 50)
        print(f"  Tasks processed: {report['tasks_processed']}")
        print(f"  Tasks completed: {report['tasks_completed']}")
        print(f"  Changes applied: {report['changes_applied']}")
        if report['errors']:
            print(f"  Errors: {report['errors']}")
        print("=" * 50)
        return

    # Run continuous (default or with specified cycles)
    cycles = args.cycles or None
    await pipeline.run_continuous(max_cycles=cycles)

if __name__ == "__main__":
    asyncio.run(main())

