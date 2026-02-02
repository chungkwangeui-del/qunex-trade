"""
Task Queue System
=================

Manages work items for the autonomous agents.
Tasks are prioritized and processed in order.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
from pathlib import Path
import threading
from datetime import timezone
from typing import List
from typing import Optional
from typing import Any

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """Task priority levels"""
    CRITICAL = 1    # Security issues, crashes
    HIGH = 2        # Bugs, broken features
    MEDIUM = 3      # Improvements, optimizations
    LOW = 4         # Nice-to-have, cosmetic
    BACKLOG = 5     # Future considerations


class TaskStatus(Enum):
    """Task status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    TESTING = "testing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ROLLED_BACK = "rolled_back"


class TaskType(Enum):
    """Types of tasks"""
    BUG_FIX = "bug_fix"
    SECURITY_FIX = "security_fix"
    FEATURE = "feature"
    IMPROVEMENT = "improvement"
    REFACTOR = "refactor"
    TEST = "test"
    DOCUMENTATION = "documentation"
    MAINTENANCE = "maintenance"


@dataclass
class TaskChange:
    """A code change within a task"""
    file_path: str
    change_type: str  # create, modify, delete
    original_content: Optional[str] = None
    new_content: Optional[str] = None
    description: str = ""
    applied: bool = False


@dataclass
class Task:
    """A work item for agents to process"""
    id: str
    title: str
    description: str
    task_type: TaskType
    priority: TaskPriority
    status: TaskStatus = TaskStatus.PENDING

    # Assignment
    assigned_agent: Optional[str] = None
    created_by: str = "system"

    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Work details
    target_files: List[str] = field(default_factory=list)
    changes: List[TaskChange] = field(default_factory=list)

    # Results
    success: bool = False
    error_message: Optional[str] = None
    review_notes: List[str] = field(default_factory=list)
    test_results: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    tags: List[str] = field(default_factory=list)
    related_tasks: List[str] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['task_type'] = self.task_type.value
        data['priority'] = self.priority.value
        data['status'] = self.status.value
        data['created_at'] = self.created_at.isoformat() if self.created_at else None
        data['started_at'] = self.started_at.isoformat() if self.started_at else None
        data['completed_at'] = self.completed_at.isoformat() if self.completed_at else None
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Create from dictionary"""
        data['task_type'] = TaskType(data['task_type'])
        data['priority'] = TaskPriority(data['priority'])
        data['status'] = TaskStatus(data['status'])
        if data.get('created_at'):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if data.get('started_at'):
            data['started_at'] = datetime.fromisoformat(data['started_at'])
        if data.get('completed_at'):
            data['completed_at'] = datetime.fromisoformat(data['completed_at'])
        data['changes'] = [TaskChange(**c) for c in data.get('changes', [])]
        return cls(**data)


class TaskQueue:
    """
    Priority queue for managing agent tasks.

    Features:
    - Priority-based ordering
    - Persistence to disk
    - Thread-safe operations
    - Task history tracking
    """

    _instance = None
    _lock = threading.Lock()

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path("data/agent_tasks.json")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        self.tasks: Dict[str, Task] = {}
        self.history: List[str] = []  # Completed task IDs

        self._load()

    @classmethod
    def get_instance(cls) -> 'TaskQueue':
        """Get singleton instance"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def add_task(self, task: Task) -> str:
        """Add a new task to the queue"""
        with self._lock:
            self.tasks[task.id] = task
            self._save()
            logger.info(f"Task added: {task.id} - {task.title}")
        return task.id

    def create_task(
        self,
        title: str,
        description: str,
        task_type: TaskType,
        priority: TaskPriority = TaskPriority.MEDIUM,
        target_files: List[str] = None,
        tags: List[str] = None,
        created_by: str = "system"
    ) -> Task:
        """Create and add a new task"""
        task = Task(
            id=str(uuid.uuid4())[:8],
            title=title,
            description=description,
            task_type=task_type,
            priority=priority,
            target_files=target_files or [],
            tags=tags or [],
            created_by=created_by,
        )
        self.add_task(task)
        return task

    def get_next_task(self, agent_name: Optional[str] = None) -> Optional[Task]:
        """Get the highest priority pending task"""
        with self._lock:
            pending = [
                t for t in self.tasks.values()
                if t.status == TaskStatus.PENDING
            ]

            if not pending:
                return None

            # Sort by priority (lower number = higher priority)
            pending.sort(key=lambda t: (t.priority.value, t.created_at))

            task = pending[0]
            task.status = TaskStatus.IN_PROGRESS
            task.assigned_agent = agent_name
            task.started_at = datetime.now(timezone.utc)

            self._save()
            return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a specific task"""
        return self.tasks.get(task_id)

    def update_task(self, task: Task) -> None:
        """Update a task"""
        with self._lock:
            self.tasks[task.id] = task
            self._save()

    def complete_task(self, task_id: str, success: bool = True, error_message: str = None) -> None:
        """Mark a task as completed"""
        with self._lock:
            task = self.tasks.get(task_id)
            if task:
                task.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
                task.success = success
                task.error_message = error_message
                task.completed_at = datetime.now(timezone.utc)
                self.history.append(task_id)
                self._save()

    def retry_task(self, task_id: str) -> bool:
        """Retry a failed task"""
        with self._lock:
            task = self.tasks.get(task_id)
            if task and task.retry_count < task.max_retries:
                task.status = TaskStatus.PENDING
                task.retry_count += 1
                task.error_message = None
                self._save()
                return True
            return False

    def rollback_task(self, task_id: str) -> bool:
        """Rollback changes from a task"""
        task = self.tasks.get(task_id)
        if not task:
            return False

        # Rollback each change in reverse order
        for change in reversed(task.changes):
            if change.applied and change.original_content is not None:
                try:
                    file_path = Path(change.file_path)
                    if change.change_type == "delete":
                        file_path.write_text(change.original_content, encoding='utf-8')
                    elif change.change_type == "create":
                        file_path.unlink(missing_ok=True)
                    elif change.change_type == "modify":
                        file_path.write_text(change.original_content, encoding='utf-8')
                    change.applied = False
                except Exception as e:
                    logger.error(f"Rollback failed for {change.file_path}: {e}")
                    return False

        task.status = TaskStatus.ROLLED_BACK
        self._save()
        return True

    def get_pending_tasks(self) -> List[Task]:
        """Get all pending tasks sorted by priority"""
        pending = [t for t in self.tasks.values() if t.status == TaskStatus.PENDING]
        pending.sort(key=lambda t: (t.priority.value, t.created_at))
        return pending

    def get_in_progress_tasks(self) -> List[Task]:
        """Get all in-progress tasks"""
        return [t for t in self.tasks.values() if t.status == TaskStatus.IN_PROGRESS]

    def get_completed_tasks(self, limit: int = 50) -> List[Task]:
        """Get recent completed tasks"""
        completed = [
            t for t in self.tasks.values()
            if t.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]
        ]
        completed.sort(key=lambda t: t.completed_at or t.created_at, reverse=True)
        return completed[:limit]

    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        by_status = {}
        by_priority = {}
        by_type = {}

        for task in self.tasks.values():
            status = task.status.value
            by_status[status] = by_status.get(status, 0) + 1

            priority = task.priority.name
            by_priority[priority] = by_priority.get(priority, 0) + 1

            task_type = task.task_type.value
            by_type[task_type] = by_type.get(task_type, 0) + 1

        return {
            "total_tasks": len(self.tasks),
            "pending": by_status.get("pending", 0),
            "in_progress": by_status.get("in_progress", 0),
            "completed": by_status.get("completed", 0),
            "failed": by_status.get("failed", 0),
            "by_status": by_status,
            "by_priority": by_priority,
            "by_type": by_type,
        }

    def clear_completed(self, older_than_days: int = 7) -> int:
        """Clear old completed tasks"""
        cutoff = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        from datetime import timedelta
        cutoff = cutoff - timedelta(days=older_than_days)

        removed = 0
        with self._lock:
            to_remove = []
            for task_id, task in self.tasks.items():
                if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                    if task.completed_at and task.completed_at < cutoff:
                        to_remove.append(task_id)

            for task_id in to_remove:
                del self.tasks[task_id]
                removed += 1

            if removed > 0:
                self._save()

        return removed

    def _save(self) -> None:
        """Save queue to disk"""
        try:
            data = {
                "tasks": {k: v.to_dict() for k, v in self.tasks.items()},
                "history": self.history[-100:],  # Keep last 100
            }
            self.storage_path.write_text(
                json.dumps(data, indent=2, default=str),
                encoding='utf-8'
            )
        except Exception as e:
            logger.error(f"Failed to save task queue: {e}")

    def _load(self) -> None:
        """Load queue from disk"""
        try:
            if self.storage_path.exists():
                data = json.loads(self.storage_path.read_text(encoding='utf-8'))
                self.tasks = {
                    k: Task.from_dict(v)
                    for k, v in data.get("tasks", {}).items()
                }
                self.history = data.get("history", [])
        except Exception as e:
            logger.error(f"Failed to load task queue: {e}")
            self.tasks = {}
            self.history = []


