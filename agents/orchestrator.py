"""
Agent Orchestrator
==================

Central management for all automated agents.
Coordinates agent execution, scheduling, and reporting.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from agents.base import BaseAgent, AgentResult, AgentStatus, AgentRegistry, TaskType
from datetime import timezone
from typing import List
from typing import Optional
from typing import Any

logger = logging.getLogger(__name__)

class AgentOrchestrator:
    """
    Central coordinator for all automated agents.

    Features:
    - Agent lifecycle management
    - Scheduled task execution
    - Comprehensive status reporting
    - Cross-agent diagnostics
    """

    _instance = None

    def __init__(self):
        self.registry = AgentRegistry.get_instance()
        self._is_running = False
        self._scheduler_task = None
        self._start_time: Optional[datetime] = None
        self.logger = logging.getLogger("agents.orchestrator")

        # Initialize and register all agents
        self._initialize_agents()

    @classmethod
    def get_instance(cls) -> 'AgentOrchestrator':
        """Get singleton instance of orchestrator."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _initialize_agents(self) -> None:
        """Initialize and register all agents."""
        from agents.health_agent import HealthAgent
        from agents.market_agent import MarketDataAgent
        from agents.trading_agent import TradingAgent
        from agents.analysis_agent import AnalysisAgent
        from agents.database_agent import DatabaseAgent
        from agents.security_agent import SecurityAgent
        from agents.development_agent import DevelopmentAgent

        agents = [
            HealthAgent(),
            MarketDataAgent(),
            TradingAgent(),
            AnalysisAgent(),
            DatabaseAgent(),
            SecurityAgent(),
            DevelopmentAgent(),
        ]

        for agent in agents:
            self.registry.register(agent)
            agent.start()

    async def check_all_status(self) -> Dict[str, AgentResult]:
        """Run status checks on all agents."""
        results = {}

        for agent in self.registry.get_all():
            try:
                result = await agent.check_status()
                results[agent.name] = result
            except Exception as e:
                results[agent.name] = AgentResult(
                    success=False,
                    status=AgentStatus.ERROR,
                    message=f"Agent check failed: {e}",
                    errors=[str(e)]
                )

        return results

    async def diagnose_all(self) -> Dict[str, AgentResult]:
        """Run diagnostics on all agents."""
        results = {}

        for agent in self.registry.get_all():
            try:
                result = await agent.diagnose_issues()
                results[agent.name] = result
            except Exception as e:
                results[agent.name] = AgentResult(
                    success=False,
                    status=AgentStatus.ERROR,
                    message=f"Diagnosis failed: {e}",
                    errors=[str(e)]
                )

        return results

    async def fix_all_errors(self, auto_fix: bool = False) -> Dict[str, AgentResult]:
        """Attempt to fix errors across all agents."""
        results = {}

        for agent in self.registry.get_all():
            try:
                result = await agent.fix_errors(auto_fix=auto_fix)
                results[agent.name] = result
            except Exception as e:
                results[agent.name] = AgentResult(
                    success=False,
                    status=AgentStatus.ERROR,
                    message=f"Fix failed: {e}",
                    errors=[str(e)]
                )

        return results

    async def get_all_suggestions(self) -> Dict[str, AgentResult]:
        """Get development suggestions from all agents."""
        results = {}

        for agent in self.registry.get_all():
            try:
                result = await agent.get_development_suggestions()
                results[agent.name] = result
            except Exception as e:
                results[agent.name] = AgentResult(
                    success=False,
                    status=AgentStatus.ERROR,
                    message=f"Suggestions failed: {e}",
                    errors=[str(e)]
                )

        return results

    async def run_agent_task(self, agent_name: str, task_id: str) -> AgentResult:
        """Run a specific task on a specific agent."""
        agent = self.registry.get(agent_name)
        if not agent:
            return AgentResult(
                success=False,
                status=AgentStatus.ERROR,
                message=f"Agent '{agent_name}' not found",
                errors=[f"Available agents: {[a.name for a in self.registry.get_all()]}"]
            )

        return await agent.run_task(task_id)

    def get_comprehensive_status(self) -> Dict[str, Any]:
        """Get comprehensive status of all agents and system."""
        agents_by_category = {}
        overall_status = AgentStatus.HEALTHY
        total_warnings = 0
        total_errors = 0

        for agent in self.registry.get_all():
            category = agent.category
            if category not in agents_by_category:
                agents_by_category[category] = []

            agent_summary = agent.get_summary()
            agents_by_category[category].append(agent_summary)

            # Update overall status
            if agent.status == AgentStatus.CRITICAL:
                overall_status = AgentStatus.CRITICAL
            elif agent.status == AgentStatus.ERROR and overall_status not in [AgentStatus.CRITICAL]:
                overall_status = AgentStatus.ERROR
            elif agent.status == AgentStatus.WARNING and overall_status == AgentStatus.HEALTHY:
                overall_status = AgentStatus.WARNING

            # Count issues
            for task in agent.tasks.values():
                if task.last_result:
                    total_warnings += len(task.last_result.warnings)
                    total_errors += len(task.last_result.errors)

        return {
            "overall_status": overall_status.value,
            "orchestrator_running": self._is_running,
            "start_time": self._start_time.isoformat() if self._start_time else None,
            "current_time": datetime.now(timezone.utc).isoformat(),
            "total_agents": len(self.registry.get_all()),
            "total_warnings": total_warnings,
            "total_errors": total_errors,
            "agents_by_category": agents_by_category,
            "categories": list(agents_by_category.keys()),
        }

    def get_agent_by_name(self, name: str) -> Optional[BaseAgent]:
        """Get a specific agent by name."""
        return self.registry.get(name)

    def get_agents_by_category(self, category: str) -> List[BaseAgent]:
        """Get all agents in a category."""
        return self.registry.get_by_category(category)

    async def start_scheduler(self, interval_seconds: int = 60) -> None:
        """Start the background task scheduler."""
        if self._is_running:
            return

        self._is_running = True
        self._start_time = datetime.now(timezone.utc)
        self._scheduler_task = asyncio.create_task(
            self._scheduler_loop(interval_seconds)
        )
        self.logger.info("Orchestrator scheduler started")

    async def stop_scheduler(self) -> None:
        """Stop the background task scheduler."""
        self._is_running = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Orchestrator scheduler stopped")

    async def _scheduler_loop(self, interval_seconds: int) -> None:
        """Background loop to run scheduled tasks."""
        while self._is_running:
            try:
                current_time = datetime.now(timezone.utc)

                for agent in self.registry.get_all():
                    for task_id, task in agent.tasks.items():
                        if not task.enabled or not task.interval_seconds:
                            continue

                        # Check if task is due
                        if task.last_run is None:
                            should_run = True
                        else:
                            elapsed = (current_time - task.last_run).total_seconds()
                            should_run = elapsed >= task.interval_seconds

                        if should_run:
                            try:
                                await agent.run_task(task_id)
                            except Exception as e:
                                self.logger.error(f"Scheduled task failed: {agent.name}/{task_id}: {e}")

                await asyncio.sleep(interval_seconds)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Scheduler loop error: {e}")
                await asyncio.sleep(interval_seconds)

    def to_dict(self) -> Dict[str, Any]:
        """Convert orchestrator state to dictionary."""
        return self.get_comprehensive_status()

# Convenience functions for CLI/API usage
async def quick_status() -> Dict[str, Any]:
    """Quick status check of all systems."""
    orchestrator = AgentOrchestrator.get_instance()
    results = await orchestrator.check_all_status()

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "overall": orchestrator.get_comprehensive_status(),
        "agents": {name: result.to_dict() for name, result in results.items()}
    }

async def quick_diagnose() -> Dict[str, Any]:
    """Quick diagnosis of all issues."""
    orchestrator = AgentOrchestrator.get_instance()
    results = await orchestrator.diagnose_all()

    all_issues = []
    all_suggestions = []

    for name, result in results.items():
        for error in result.errors:
            all_issues.append(f"[{name}] {error}")
        for suggestion in result.suggestions:
            all_suggestions.append(f"[{name}] {suggestion}")

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "issues_count": len(all_issues),
        "issues": all_issues,
        "suggestions": all_suggestions,
        "details": {name: result.to_dict() for name, result in results.items()}
    }

async def quick_fix(auto_fix: bool = False) -> Dict[str, Any]:
    """Quick fix attempt for all issues."""
    orchestrator = AgentOrchestrator.get_instance()
    results = await orchestrator.fix_all_errors(auto_fix=auto_fix)

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "auto_fix": auto_fix,
        "results": {name: result.to_dict() for name, result in results.items()}
    }

async def quick_develop() -> Dict[str, Any]:
    """Get all development suggestions."""
    orchestrator = AgentOrchestrator.get_instance()
    results = await orchestrator.get_all_suggestions()

    all_suggestions = []
    for name, result in results.items():
        for suggestion in result.suggestions:
            all_suggestions.append({"agent": name, "suggestion": suggestion})

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_suggestions": len(all_suggestions),
        "suggestions": all_suggestions,
        "by_agent": {name: result.to_dict() for name, result in results.items()}
    }
