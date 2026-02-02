"""
Master Agent (The CEO)
======================

The decision maker and coordinator of all autonomous agents.
Responsible for:
- Analyzing system state
- Prioritizing work
- Assigning tasks to agents
- Monitoring progress
- Making high-level decisions
- Escalating issues that require human intervention
"""

import logging

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from agents.base import AgentResult, AgentStatus
from agents.orchestrator import AgentOrchestrator
from agents.project_scanner import ProjectScanner
from agents.codebase_knowledge import CodebaseKnowledge
from agents.autonomous.task_queue import (
    TaskQueue, Task, TaskPriority, TaskStatus, TaskType
)
from agents.autonomous.escalation import (
    EscalationManager, Escalation, EscalationReason, EscalationPriority, ManualStep,
    escalate_missing_api_key, escalate_database_issue, escalate_security_issue,
    escalate_complex_refactor, escalate_architecture_decision,
)

logger = logging.getLogger(__name__)

class MasterAgent:
    """
    The Master Agent coordinates all autonomous development.

    Workflow:
    1. Analyze current system state
    2. Identify issues and opportunities
    3. Create prioritized tasks
    4. Delegate to specialized agents
    5. Monitor and validate results
    6. Report on progress
    """

    def __init__(self):
        self.name = "master"
        self.orchestrator = AgentOrchestrator.get_instance()
        self.scanner = ProjectScanner()
        self.knowledge = CodebaseKnowledge()
        self.task_queue = TaskQueue.get_instance()
        self.escalation_manager = EscalationManager.get_instance()
        self.project_root = Path(__file__).parent.parent.parent

        # State
        self.last_analysis: Optional[datetime] = None
        self.last_report: Dict[str, Any] = {}
        self.running = False

        # Track issues that couldn't be auto-fixed
        self.unfixable_issues: List[Dict[str, Any]] = []

    async def analyze_system(self) -> Dict[str, Any]:
        """
        Comprehensive system analysis.
        Returns prioritized list of issues and opportunities.
        """
        analysis = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "health": {},
            "issues": [],
            "opportunities": [],
            "metrics": {},
        }

        # 1. Run all agent status checks
        try:
            status_results = await self.orchestrator.check_all_status()

            healthy_count = 0
            warning_count = 0
            error_count = 0

            for agent_name, result in status_results.items():
                if result.status == AgentStatus.HEALTHY:
                    healthy_count += 1
                elif result.status == AgentStatus.WARNING:
                    warning_count += 1
                else:
                    error_count += 1

                # Collect issues from each agent
                if result.errors:
                    for error in result.errors:
                        analysis["issues"].append({
                            "source": agent_name,
                            "severity": "error",
                            "message": error,
                            "priority": TaskPriority.HIGH,
                        })

                if result.warnings:
                    for warning in result.warnings:
                        analysis["issues"].append({
                            "source": agent_name,
                            "severity": "warning",
                            "message": warning,
                            "priority": TaskPriority.MEDIUM,
                        })

            analysis["health"] = {
                "healthy": healthy_count,
                "warnings": warning_count,
                "errors": error_count,
                "score": int((healthy_count / max(len(status_results), 1)) * 100),
            }

        except Exception as e:
            logger.error(f"Failed to get agent status: {e}")

        # 2. Run code scanner
        try:
            scan_result = self.scanner.scan_all()

            for issue in scan_result.get("issues", []):
                priority = TaskPriority.HIGH if issue["severity"] == "error" else TaskPriority.MEDIUM
                if issue["severity"] == "critical":
                    priority = TaskPriority.CRITICAL

                analysis["issues"].append({
                    "source": "scanner",
                    "severity": issue["severity"],
                    "category": issue["category"],
                    "message": issue["message"],
                    "file": issue.get("file"),
                    "line": issue.get("line"),
                    "suggestion": issue.get("suggestion"),
                    "auto_fixable": issue.get("auto_fixable", False),
                    "priority": priority,
                })

            analysis["metrics"]["code"] = scan_result.get("summary", {})

        except Exception as e:
            logger.error(f"Failed to scan code: {e}")

        # 3. Get development suggestions
        try:
            suggestions = await self.orchestrator.get_all_suggestions()

            for agent_name, result in suggestions.items():
                for suggestion in (result.suggestions or []):
                    analysis["opportunities"].append({
                        "source": agent_name,
                        "suggestion": suggestion,
                        "priority": TaskPriority.LOW,
                    })

        except Exception as e:
            logger.error(f"Failed to get suggestions: {e}")

        # 4. Check task queue status
        analysis["metrics"]["tasks"] = self.task_queue.get_stats()

        # 5. Sort issues by priority
        analysis["issues"].sort(key=lambda x: x.get("priority", TaskPriority.LOW).value)

        self.last_analysis = datetime.now(timezone.utc)
        self.last_report = analysis

        return analysis

    async def create_tasks_from_analysis(self, analysis: Dict[str, Any]) -> List[Task]:
        """
        Convert analysis results into actionable tasks.
        """
        created_tasks = []

        # Process issues
        for issue in analysis.get("issues", []):
            # Skip if similar task already exists
            if self._task_exists_for_issue(issue):
                continue

            # Determine task type
            category = issue.get("category", "").lower()
            if "security" in category:
                task_type = TaskType.SECURITY_FIX
            elif issue["severity"] == "error":
                task_type = TaskType.BUG_FIX
            elif "test" in category:
                task_type = TaskType.TEST
            else:
                task_type = TaskType.IMPROVEMENT

            # Create task
            task = self.task_queue.create_task(
                title=self._generate_task_title(issue),
                description=self._generate_task_description(issue),
                task_type=task_type,
                priority=issue.get("priority", TaskPriority.MEDIUM),
                target_files=[issue["file"]] if issue.get("file") else [],
                tags=[issue.get("category", "general"), issue["severity"]],
                created_by="master_agent",
            )
            created_tasks.append(task)

        # Process high-priority opportunities (limit)
        high_priority_opportunities = [
            o for o in analysis.get("opportunities", [])
            if "high priority" in o.get("suggestion", "").lower()
            or "critical" in o.get("suggestion", "").lower()
        ][:5]  # Limit to 5

        for opportunity in high_priority_opportunities:
            if self._task_exists_for_suggestion(opportunity["suggestion"]):
                continue

            task = self.task_queue.create_task(
                title=f"Implement: {opportunity['suggestion'][:50]}...",
                description=opportunity["suggestion"],
                task_type=TaskType.FEATURE,
                priority=TaskPriority.MEDIUM,
                tags=["improvement", opportunity["source"]],
                created_by="master_agent",
            )
            created_tasks.append(task)

        return created_tasks

    def _task_exists_for_issue(self, issue: Dict[str, Any]) -> bool:
        """Check if a task already exists for this issue"""
        message = issue.get("message", "").lower()
        file_path = issue.get("file", "")

        for task in self.task_queue.get_pending_tasks():
            if file_path and file_path in task.target_files:
                if message[:50] in task.description.lower():
                    return True
        return False

    def _task_exists_for_suggestion(self, suggestion: str) -> bool:
        """Check if a task already exists for this suggestion"""
        suggestion_lower = suggestion.lower()[:50]

        for task in self.task_queue.get_pending_tasks():
            if suggestion_lower in task.description.lower():
                return True
        return False

    def _generate_task_title(self, issue: Dict[str, Any]) -> str:
        """Generate a clear task title"""
        severity = issue.get("severity", "issue").upper()
        category = issue.get("category", "General")

        if issue.get("file"):
            file_name = Path(issue["file"]).name
            return f"[{severity}] Fix {category} issue in {file_name}"

        return f"[{severity}] Fix {category}: {issue.get('message', 'Unknown')[:40]}"

    def _generate_task_description(self, issue: Dict[str, Any]) -> str:
        """Generate detailed task description"""
        parts = [f"**Issue:** {issue.get('message', 'No description')}"]

        if issue.get("file"):
            parts.append(f"**File:** {issue['file']}")
        if issue.get("line"):
            parts.append(f"**Line:** {issue['line']}")
        if issue.get("suggestion"):
            parts.append(f"**Suggested Fix:** {issue['suggestion']}")

        parts.append(f"**Source:** {issue.get('source', 'unknown')}")
        parts.append(f"**Auto-fixable:** {'Yes' if issue.get('auto_fixable') else 'No'}")

        return "\n".join(parts)

    async def delegate_task(self, task: Task) -> Tuple[str, bool]:
        """
        Delegate a task to the appropriate agent.
        Returns (agent_name, success)
        """
        # Determine which agent should handle this
        if task.task_type == TaskType.SECURITY_FIX:
            agent_name = "fixer"  # Security fixes go to fixer
        elif task.task_type == TaskType.BUG_FIX:
            agent_name = "fixer"
        elif task.task_type in [TaskType.FEATURE, TaskType.IMPROVEMENT]:
            agent_name = "developer"
        elif task.task_type == TaskType.REFACTOR:
            agent_name = "improver"
        elif task.task_type == TaskType.TEST:
            agent_name = "developer"
        else:
            agent_name = "developer"

        task.assigned_agent = agent_name
        task.status = TaskStatus.IN_PROGRESS
        task.started_at = datetime.now(timezone.utc)
        self.task_queue.update_task(task)

        return agent_name, True

    async def review_completed_task(self, task: Task) -> Tuple[bool, List[str]]:
        """
        Review a completed task before finalizing.
        Returns (approved, review_notes)
        """
        review_notes = []
        approved = True

        # Check if changes were made
        if not task.changes:
            review_notes.append("No changes were made")
            return True, review_notes

        # Verify each change
        for change in task.changes:
            if not change.applied:
                review_notes.append(f"Change not applied: {change.file_path}")
                approved = False

            # Check file exists after change
            if change.change_type != "delete":
                if not Path(change.file_path).exists():
                    review_notes.append(f"File missing after change: {change.file_path}")
                    approved = False

        # Run quick syntax check on modified Python files
        for change in task.changes:
            if change.file_path.endswith(".py") and change.applied:
                try:
                    import ast
                    content = Path(change.file_path).read_text(encoding='utf-8')
                    ast.parse(content)
                    review_notes.append(f"Syntax OK: {change.file_path}")
                except SyntaxError as e:
                    review_notes.append(f"Syntax error in {change.file_path}: {e}")
                    approved = False

        return approved, review_notes

    async def run_cycle(self) -> Dict[str, Any]:
        """
        Run one complete autonomous cycle.

        1. Analyze system
        2. Create tasks from issues (or escalations for unfixable ones)
        3. Process pending tasks
        4. Review completed work
        5. Create escalations for failed tasks
        6. Generate report
        """
        cycle_report = {
            "start_time": datetime.now(timezone.utc).isoformat(),
            "analysis": {},
            "tasks_created": 0,
            "tasks_processed": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "escalations_created": 0,
            "human_action_required": [],
            "errors": [],
        }

        try:
            # 1. Analyze system
            analysis = await self.analyze_system()
            cycle_report["analysis"] = {
                "health_score": analysis["health"].get("score", 0),
                "issues_found": len(analysis["issues"]),
                "opportunities": len(analysis["opportunities"]),
            }

            # 2. Process issues - create tasks for fixable, escalations for unfixable
            for issue in analysis.get("issues", []):
                escalation = self._analyze_and_escalate_issue(issue)
                if escalation:
                    cycle_report["escalations_created"] += 1
                    cycle_report["human_action_required"].append({
                        "id": escalation.id,
                        "title": escalation.title,
                        "priority": escalation.priority.name,
                    })

            # 3. Create tasks for auto-fixable issues
            new_tasks = await self.create_tasks_from_analysis(analysis)
            cycle_report["tasks_created"] = len(new_tasks)

            # 4. Process pending tasks (limit per cycle)
            pending = self.task_queue.get_pending_tasks()[:5]  # Max 5 per cycle

            for task in pending:
                try:
                    agent_name, delegated = await self.delegate_task(task)
                    if delegated:
                        cycle_report["tasks_processed"] += 1

                except Exception as e:
                    cycle_report["errors"].append(f"Task {task.id}: {str(e)}")

            # 5. Review completed tasks
            in_progress = self.task_queue.get_in_progress_tasks()
            for task in in_progress:
                if task.changes:  # Has changes to review
                    approved, notes = await self.review_completed_task(task)
                    task.review_notes = notes

                    if approved:
                        self.task_queue.complete_task(task.id, success=True)
                        cycle_report["tasks_completed"] += 1
                    else:
                        # Rollback and retry or fail
                        if task.retry_count < task.max_retries:
                            self.task_queue.rollback_task(task.id)
                            self.task_queue.retry_task(task.id)
                        else:
                            # Create escalation for failed task
                            error_msg = "\n".join(notes) if notes else "Unknown error"
                            escalation = await self.process_failed_task(task, error_msg)

                            self.task_queue.complete_task(task.id, success=False,
                                error_message=error_msg)
                            cycle_report["tasks_failed"] += 1
                            cycle_report["escalations_created"] += 1
                            cycle_report["human_action_required"].append({
                                "id": escalation.id,
                                "title": escalation.title,
                                "priority": escalation.priority.name,
                            })

        except Exception as e:
            cycle_report["errors"].append(str(e))
            logger.error(f"Cycle error: {e}")

        cycle_report["end_time"] = datetime.now(timezone.utc).isoformat()

        # Add escalation summary
        pending_escalations = self.escalation_manager.get_pending_escalations()
        cycle_report["total_pending_escalations"] = len(pending_escalations)

        return cycle_report

    def get_status(self) -> Dict[str, Any]:
        """Get current master agent status"""
        queue_stats = self.task_queue.get_stats()

        return {
            "name": self.name,
            "running": self.running,
            "last_analysis": self.last_analysis.isoformat() if self.last_analysis else None,
            "queue": queue_stats,
            "health": self.last_report.get("health", {}),
        }

    def get_report(self) -> Dict[str, Any]:
        """Get detailed report"""
        return {
            "status": self.get_status(),
            "last_analysis": self.last_report,
            "pending_tasks": [t.to_dict() for t in self.task_queue.get_pending_tasks()[:10]],
            "recent_completed": [t.to_dict() for t in self.task_queue.get_completed_tasks(10)],
            "escalations": [e.to_dict() for e in self.escalation_manager.get_pending_escalations()],
        }

    def _analyze_and_escalate_issue(self, issue: Dict[str, Any]) -> Optional[Escalation]:
        """
        Analyze an issue and create an escalation if it can't be auto-fixed.
        Returns the escalation if created, None if auto-fixable.
        """
        message = issue.get("message", "").lower()
        category = issue.get("category", "").lower()
        auto_fixable = issue.get("auto_fixable", False)
        severity = issue.get("severity", "info")

        # Skip if auto-fixable and not critical
        if auto_fixable and severity not in ["critical"]:
            return None

        # Check for known patterns that require human intervention

        # API Key issues
        if "polygon" in message and ("api" in message or "key" in message or "missing" in message):
            return escalate_missing_api_key("Polygon", "master")
        if "alpha vantage" in message or "alphavantage" in message:
            return escalate_missing_api_key("Alpha Vantage", "master")
        if ("api" in message or "key" in message) and ("missing" in message or "not set" in message or "not configured" in message):
            api_name = self._extract_api_name(message)
            return escalate_missing_api_key(api_name, "master")

        # Environment variable issues
        if "environment" in message or "env" in message or ".env" in message:
            if "missing" in message or "not set" in message:
                return self._create_env_var_escalation(issue)

        # Database issues
        if "database" in message and ("migration" in message or "schema" in message):
            return escalate_database_issue("Schema Change", issue.get("message", ""), "master")
        if "database" in message and ("connection" in message or "error" in message):
            return escalate_database_issue("Connection Issue", issue.get("message", ""), "master")

        # Security issues that need manual review
        if category == "security":
            if severity in ["error", "critical"]:
                return escalate_security_issue(
                    issue.get("message", "Security issue"),
                    issue.get("file", "unknown"),
                    "master"
                )
            elif "secret" in message or "password" in message or "hardcoded" in message:
                return escalate_security_issue(
                    issue.get("message", "Security issue"),
                    issue.get("file", "unknown"),
                    "master"
                )

        # Complex code issues
        if "refactor" in message or "architecture" in message or "restructure" in message:
            files = [issue.get("file")] if issue.get("file") else []
            return escalate_complex_refactor(
                issue.get("message", "Refactoring needed"),
                files,
                "master"
            )

        # Configuration issues
        if "config" in category or "configuration" in message:
            if severity in ["error", "critical"]:
                return self._create_config_escalation(issue)

        # If we can't auto-fix critical/error issues, escalate
        if severity in ["error", "critical"] and not auto_fixable:
            return self._create_generic_escalation(issue)

        return None

    def _create_env_var_escalation(self, issue: Dict[str, Any]) -> Escalation:
        """Create escalation for missing environment variable."""
        message = issue.get("message", "")

        steps = [
            ManualStep(1, "Open your .env file in the project root",
                      file_to_edit=".env"),
            ManualStep(2, "Add the missing environment variable",
                      notes=f"Check the issue: {message[:80]}"),
            ManualStep(3, "Restart the application for changes to take effect",
                      command="python run.py"),
        ]

        return self.escalation_manager.create_escalation(
            title="Missing Environment Variable",
            description=message,
            reason=EscalationReason.CONFIG_CHANGE,
            priority=EscalationPriority.HIGH,
            source_agent="master",
            affected_files=[".env"],
            why_not_auto="Environment variables contain sensitive configuration that only you can provide.",
            manual_steps=steps,
        )

    def _create_config_escalation(self, issue: Dict[str, Any]) -> Escalation:
        """Create escalation for configuration issues."""
        message = issue.get("message", "")
        file_path = issue.get("file", "config.py")

        steps = [
            ManualStep(1, f"Review the configuration issue in {file_path}",
                      file_to_edit=file_path),
            ManualStep(2, f"Issue: {message[:100]}"),
            ManualStep(3, "Update the configuration according to your requirements"),
            ManualStep(4, "Restart the application to apply changes"),
        ]

        return self.escalation_manager.create_escalation(
            title=f"Configuration Issue: {message[:40]}",
            description=message,
            reason=EscalationReason.CONFIG_CHANGE,
            priority=EscalationPriority.MEDIUM,
            source_agent="master",
            affected_files=[file_path],
            why_not_auto="Configuration changes require understanding your specific requirements and deployment setup.",
            manual_steps=steps,
        )

    def _extract_api_name(self, message: str) -> str:
        """Extract API name from error message."""
        known_apis = ["polygon", "alpha vantage", "finnhub", "iex", "yahoo", "news"]
        for api in known_apis:
            if api in message.lower():
                return api.title()
        return "External API"

    def _create_generic_escalation(self, issue: Dict[str, Any]) -> Escalation:
        """Create a generic escalation for issues without specific templates."""
        steps = []

        # Build generic steps based on issue type
        file_path = issue.get("file")
        line_no = issue.get("line")
        suggestion = issue.get("suggestion")

        step_num = 1

        if file_path:
            steps.append(ManualStep(
                step_num, f"Open the file: {file_path}",
                notes=f"Line {line_no}" if line_no else None
            ))
            step_num += 1

        steps.append(ManualStep(
            step_num, f"Review the issue: {issue.get('message', 'Unknown issue')}"
        ))
        step_num += 1

        if suggestion:
            steps.append(ManualStep(
                step_num, f"Suggested fix: {suggestion}"
            ))
            step_num += 1

        steps.append(ManualStep(
            step_num, "Test the fix thoroughly before committing"
        ))

        # Determine priority
        severity = issue.get("severity", "warning")
        if severity == "critical":
            priority = EscalationPriority.CRITICAL
        elif severity == "error":
            priority = EscalationPriority.HIGH
        else:
            priority = EscalationPriority.MEDIUM

        # Determine reason
        category = issue.get("category", "").lower()
        if "security" in category:
            reason = EscalationReason.SECURITY_SENSITIVE
        elif "config" in category:
            reason = EscalationReason.CONFIG_CHANGE
        else:
            reason = EscalationReason.COMPLEX_REFACTOR

        return self.escalation_manager.create_escalation(
            title=f"{issue.get('category', 'Issue')}: {issue.get('message', 'Unknown')[:50]}",
            description=issue.get("message", "An issue was detected that requires manual review."),
            reason=reason,
            priority=priority,
            source_agent="master",
            affected_files=[file_path] if file_path else [],
            why_not_auto="This issue is too complex or risky for automatic fixing. "
                        "Manual review ensures the fix is correct and doesn't break other functionality.",
            manual_steps=steps,
        )

    async def process_failed_task(self, task: Task, error_message: str) -> Escalation:
        """Create an escalation when a task fails."""
        steps = [
            ManualStep(1, f"Review the failed task: {task.title}"),
            ManualStep(2, f"Error encountered: {error_message}"),
        ]

        if task.target_files:
            steps.append(ManualStep(
                3, f"Check affected files: {', '.join(task.target_files[:3])}"
            ))

        steps.append(ManualStep(
            len(steps) + 1,
            "Fix the issue manually and mark as resolved",
            command="python -m agents.cli queue"
        ))

        return self.escalation_manager.create_escalation(
            title=f"Task Failed: {task.title}",
            description=f"Automatic processing failed after {task.retry_count} retries.\n"
                       f"Error: {error_message}",
            reason=EscalationReason.COMPLEX_REFACTOR,
            priority=EscalationPriority.HIGH if task.priority.value <= 2 else EscalationPriority.MEDIUM,
            source_agent=task.assigned_agent or "master",
            affected_files=task.target_files,
            why_not_auto=f"The automated agent could not complete this task: {error_message}",
            manual_steps=steps,
        )

    def get_human_action_required(self) -> Dict[str, Any]:
        """
        Get a summary of all issues requiring human intervention.
        This is the main method to call when the user wants to know what they need to do.
        """
        pending_escalations = self.escalation_manager.get_pending_escalations()

        result = {
            "total_issues": len(pending_escalations),
            "by_priority": {
                "critical": [],
                "high": [],
                "medium": [],
                "low": [],
            },
            "by_category": {
                "credentials": [],
                "security": [],
                "database": [],
                "configuration": [],
                "code_changes": [],
                "other": [],
            },
        }

        for esc in pending_escalations:
            # Add to priority bucket
            priority_name = esc.priority.name.lower()
            if priority_name in result["by_priority"]:
                result["by_priority"][priority_name].append(esc.to_dict())

            # Add to category bucket
            if esc.reason == EscalationReason.REQUIRES_CREDENTIALS:
                result["by_category"]["credentials"].append(esc.to_dict())
            elif esc.reason == EscalationReason.SECURITY_SENSITIVE:
                result["by_category"]["security"].append(esc.to_dict())
            elif esc.reason == EscalationReason.DATABASE_MIGRATION:
                result["by_category"]["database"].append(esc.to_dict())
            elif esc.reason in [EscalationReason.CONFIG_CHANGE, EscalationReason.REQUIRES_EXTERNAL]:
                result["by_category"]["configuration"].append(esc.to_dict())
            elif esc.reason in [EscalationReason.COMPLEX_REFACTOR, EscalationReason.REQUIRES_DECISION]:
                result["by_category"]["code_changes"].append(esc.to_dict())
            else:
                result["by_category"]["other"].append(esc.to_dict())

        return result
