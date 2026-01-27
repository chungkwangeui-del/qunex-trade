"""
Base Agent Framework
====================

Provides the foundation for all automated agents with common functionality
for status checking, error handling, development tasks, and reporting.
"""

import logging
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import traceback
import json

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Status of an agent's health check or task"""
    HEALTHY = "healthy"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    UNKNOWN = "unknown"
    RUNNING = "running"
    STOPPED = "stopped"


class TaskType(Enum):
    """Types of agent tasks"""
    STATUS_CHECK = "status_check"
    ERROR_FIX = "error_fix"
    DEVELOPMENT = "development"
    MAINTENANCE = "maintenance"
    MONITORING = "monitoring"


@dataclass
class AgentResult:
    """Result of an agent task execution"""
    success: bool
    status: AgentStatus
    message: str
    data: Optional[Dict[str, Any]] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    execution_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "status": self.status.value,
            "message": self.message,
            "data": self.data,
            "errors": self.errors,
            "warnings": self.warnings,
            "suggestions": self.suggestions,
            "execution_time_ms": self.execution_time_ms,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class AgentTask:
    """A task to be executed by an agent"""
    id: str
    name: str
    task_type: TaskType
    description: str
    handler: Callable
    interval_seconds: Optional[int] = None  # For scheduled tasks
    enabled: bool = True
    last_run: Optional[datetime] = None
    last_result: Optional[AgentResult] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "task_type": self.task_type.value,
            "description": self.description,
            "interval_seconds": self.interval_seconds,
            "enabled": self.enabled,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "last_result": self.last_result.to_dict() if self.last_result else None,
        }


class BaseAgent(ABC):
    """
    Base class for all automated agents.
    
    Provides common functionality for:
    - Status checking and health monitoring
    - Error detection and automatic fixing
    - Task scheduling and execution
    - Logging and reporting
    """
    
    def __init__(self, name: str, category: str, description: str):
        self.name = name
        self.category = category
        self.description = description
        self.status = AgentStatus.UNKNOWN
        self.tasks: Dict[str, AgentTask] = {}
        self.history: List[AgentResult] = []
        self.max_history = 100
        self._is_running = False
        self._start_time: Optional[datetime] = None
        self.logger = logging.getLogger(f"agents.{name}")
        
        # Initialize tasks
        self._register_tasks()
    
    @abstractmethod
    def _register_tasks(self) -> None:
        """Register all tasks for this agent. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    async def check_status(self) -> AgentResult:
        """
        Check the current status of the system/feature this agent monitors.
        Returns detailed status information.
        """
        pass
    
    @abstractmethod
    async def diagnose_issues(self) -> AgentResult:
        """
        Run diagnostics to find any issues or potential problems.
        Returns a list of detected issues with severity levels.
        """
        pass
    
    @abstractmethod
    async def fix_errors(self, auto_fix: bool = False) -> AgentResult:
        """
        Attempt to fix detected errors.
        If auto_fix=False, returns suggested fixes without applying them.
        If auto_fix=True, attempts to automatically apply fixes.
        """
        pass
    
    @abstractmethod
    async def get_development_suggestions(self) -> AgentResult:
        """
        Analyze the current state and suggest development improvements.
        Returns a list of suggested features, optimizations, or refactoring.
        """
        pass
    
    def register_task(self, task: AgentTask) -> None:
        """Register a task with this agent."""
        self.tasks[task.id] = task
        self.logger.info(f"Registered task: {task.name} ({task.id})")
    
    async def run_task(self, task_id: str) -> AgentResult:
        """Execute a specific task by ID."""
        if task_id not in self.tasks:
            return AgentResult(
                success=False,
                status=AgentStatus.ERROR,
                message=f"Task '{task_id}' not found",
                errors=[f"Available tasks: {list(self.tasks.keys())}"]
            )
        
        task = self.tasks[task_id]
        if not task.enabled:
            return AgentResult(
                success=False,
                status=AgentStatus.WARNING,
                message=f"Task '{task.name}' is disabled"
            )
        
        start_time = datetime.now(timezone.utc)
        try:
            self.logger.info(f"Starting task: {task.name}")
            
            # Execute the handler
            if asyncio.iscoroutinefunction(task.handler):
                result = await task.handler()
            else:
                result = task.handler()
            
            # Calculate execution time
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            result.execution_time_ms = execution_time
            
            # Update task metadata
            task.last_run = datetime.now(timezone.utc)
            task.last_result = result
            
            # Store in history
            self._add_to_history(result)
            
            self.logger.info(f"Task completed: {task.name} ({result.status.value})")
            return result
            
        except Exception as e:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            error_result = AgentResult(
                success=False,
                status=AgentStatus.ERROR,
                message=f"Task '{task.name}' failed with exception",
                errors=[str(e), traceback.format_exc()],
                execution_time_ms=execution_time
            )
            task.last_run = datetime.now(timezone.utc)
            task.last_result = error_result
            self._add_to_history(error_result)
            self.logger.error(f"Task failed: {task.name} - {e}")
            return error_result
    
    async def run_all_tasks(self, task_type: Optional[TaskType] = None) -> Dict[str, AgentResult]:
        """Run all enabled tasks, optionally filtered by type."""
        results = {}
        for task_id, task in self.tasks.items():
            if task.enabled and (task_type is None or task.task_type == task_type):
                results[task_id] = await self.run_task(task_id)
        return results
    
    def _add_to_history(self, result: AgentResult) -> None:
        """Add a result to history, maintaining max size."""
        self.history.append(result)
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the agent's current state."""
        task_summary = {}
        for task_id, task in self.tasks.items():
            task_summary[task_id] = {
                "name": task.name,
                "type": task.task_type.value,
                "enabled": task.enabled,
                "last_run": task.last_run.isoformat() if task.last_run else None,
                "last_status": task.last_result.status.value if task.last_result else None,
            }
        
        return {
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "status": self.status.value,
            "is_running": self._is_running,
            "start_time": self._start_time.isoformat() if self._start_time else None,
            "tasks": task_summary,
            "history_count": len(self.history),
        }
    
    def start(self) -> None:
        """Mark agent as running."""
        self._is_running = True
        self._start_time = datetime.now(timezone.utc)
        self.status = AgentStatus.RUNNING
        self.logger.info(f"Agent started: {self.name}")
    
    def stop(self) -> None:
        """Mark agent as stopped."""
        self._is_running = False
        self.status = AgentStatus.STOPPED
        self.logger.info(f"Agent stopped: {self.name}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert agent to dictionary for JSON serialization."""
        return {
            **self.get_summary(),
            "recent_history": [r.to_dict() for r in self.history[-10:]],
        }


class AgentRegistry:
    """Registry for managing multiple agents."""
    
    _instance = None
    _agents: Dict[str, BaseAgent] = {}
    
    @classmethod
    def get_instance(cls) -> 'AgentRegistry':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def register(self, agent: BaseAgent) -> None:
        """Register an agent."""
        self._agents[agent.name] = agent
        logger.info(f"Registered agent: {agent.name} ({agent.category})")
    
    def get(self, name: str) -> Optional[BaseAgent]:
        """Get an agent by name."""
        return self._agents.get(name)
    
    def get_by_category(self, category: str) -> List[BaseAgent]:
        """Get all agents in a category."""
        return [a for a in self._agents.values() if a.category == category]
    
    def get_all(self) -> List[BaseAgent]:
        """Get all registered agents."""
        return list(self._agents.values())
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all agents."""
        by_category = {}
        for agent in self._agents.values():
            if agent.category not in by_category:
                by_category[agent.category] = []
            by_category[agent.category].append(agent.get_summary())
        
        return {
            "total_agents": len(self._agents),
            "categories": list(by_category.keys()),
            "agents_by_category": by_category,
        }

