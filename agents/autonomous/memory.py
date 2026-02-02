"""
Agent Memory System
===================

Long-term memory for agents that persists across sessions.
Agents can learn from past actions, remember successful fixes,
and avoid repeating mistakes.
"""

import json
import hashlib
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import dataclass, field, asdict
from collections import defaultdict
from datetime import timedelta
from datetime import timezone
from typing import List
from typing import Optional
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    """A single memory entry."""
    id: str
    category: str  # fix, error, success, learning, pattern
    key: str  # Unique identifier for this type of memory
    value: Any
    context: Dict[str, Any]
    created_at: datetime
    accessed_at: datetime
    access_count: int = 0
    importance: float = 1.0  # 0-1, higher = more important
    expires_at: Optional[datetime] = None


@dataclass
class FixMemory:
    """Memory of a successful fix."""
    issue_pattern: str  # Regex or pattern that identifies the issue
    fix_pattern: str  # How to fix it
    file_types: List[str]
    success_count: int = 0
    failure_count: int = 0
    last_used: Optional[datetime] = None


@dataclass
class ErrorMemory:
    """Memory of an error encountered."""
    error_type: str
    error_message: str
    context: str  # Where it happened
    solution: Optional[str] = None
    occurrence_count: int = 1


class AgentMemory:
    """
    Persistent memory system for agents.

    Capabilities:
    - Remember successful fixes and reuse them
    - Track error patterns and solutions
    - Learn from agent actions
    - Store important discoveries
    - Forget unimportant memories over time
    """

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.data_dir = Path(__file__).parent.parent.parent / "data" / "agent_memory"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Memory stores
        self.memories: Dict[str, MemoryEntry] = {}
        self.fixes: Dict[str, FixMemory] = {}
        self.errors: Dict[str, ErrorMemory] = {}
        self.patterns: Dict[str, Dict[str, Any]] = {}  # Learned patterns

        # Statistics
        self.stats = {
            "total_memories": 0,
            "fixes_learned": 0,
            "fixes_applied": 0,
            "errors_encountered": 0,
            "errors_solved": 0,
        }

        # Load from disk
        self._load()

    def remember(
        self,
        category: str,
        key: str,
        value: Any,
        context: Optional[Dict[str, Any]] = None,
        importance: float = 1.0,
        expires_in_days: Optional[int] = None,
    ) -> str:
        """Store a memory."""
        memory_id = self._generate_id(category, key)

        now = datetime.now(timezone.utc)
        expires_at = None
        if expires_in_days:
            expires_at = now + timedelta(days=expires_in_days)

        if memory_id in self.memories:
            # Update existing memory
            self.memories[memory_id].value = value
            self.memories[memory_id].accessed_at = now
            self.memories[memory_id].access_count += 1
        else:
            # Create new memory
            self.memories[memory_id] = MemoryEntry(
                id=memory_id,
                category=category,
                key=key,
                value=value,
                context=context or {},
                created_at=now,
                accessed_at=now,
                importance=importance,
                expires_at=expires_at,
            )
            self.stats["total_memories"] += 1

        self._save()
        return memory_id

    def recall(self, category: str, key: str) -> Optional[Any]:
        """Retrieve a memory."""
        memory_id = self._generate_id(category, key)

        if memory_id in self.memories:
            memory = self.memories[memory_id]

            # Check if expired
            if memory.expires_at and memory.expires_at < datetime.now(timezone.utc):
                del self.memories[memory_id]
                self._save()
                return None

            # Update access
            memory.accessed_at = datetime.now(timezone.utc)
            memory.access_count += 1

            return memory.value

        return None

    def search(self, query: str, category: Optional[str] = None, limit: int = 10) -> List[MemoryEntry]:
        """Search memories."""
        results = []
        query_lower = query.lower()

        for memory in self.memories.values():
            if category and memory.category != category:
                continue

            # Check if expired
            if memory.expires_at and memory.expires_at < datetime.now(timezone.utc):
                continue

            # Simple text matching
            key_match = query_lower in memory.key.lower()
            value_match = query_lower in str(memory.value).lower()
            context_match = query_lower in str(memory.context).lower()

            if key_match or value_match or context_match:
                results.append(memory)

        # Sort by importance and access count
        results.sort(key=lambda m: (m.importance, m.access_count), reverse=True)

        return results[:limit]

    def learn_fix(
        self,
        issue_pattern: str,
        fix_pattern: str,
        file_types: List[str],
        success: bool = True,
    ) -> None:
        """Learn a fix pattern."""
        fix_id = hashlib.md5(f"{issue_pattern}:{fix_pattern}".encode()).hexdigest()[:12]

        if fix_id in self.fixes:
            fix = self.fixes[fix_id]
            if success:
                fix.success_count += 1
            else:
                fix.failure_count += 1
            fix.last_used = datetime.now(timezone.utc)
        else:
            self.fixes[fix_id] = FixMemory(
                issue_pattern=issue_pattern,
                fix_pattern=fix_pattern,
                file_types=file_types,
                success_count=1 if success else 0,
                failure_count=0 if success else 1,
                last_used=datetime.now(timezone.utc),
            )
            self.stats["fixes_learned"] += 1

        self._save()

    def get_fix_for_issue(self, issue_text: str, file_type: str) -> Optional[FixMemory]:
        """Find a known fix for an issue."""
        import re

        best_match = None
        best_score = 0

        for fix in self.fixes.values():
            if file_type not in fix.file_types and "*" not in fix.file_types:
                continue

            try:
                if re.search(fix.issue_pattern, issue_text, re.IGNORECASE):
                    # Calculate confidence score
                    score = fix.success_count / (fix.success_count + fix.failure_count + 1)
                    if score > best_score:
                        best_score = score
                        best_match = fix
            except re.error:
                # Pattern match by simple string
                if fix.issue_pattern.lower() in issue_text.lower():
                    score = fix.success_count / (fix.success_count + fix.failure_count + 1)
                    if score > best_score:
                        best_score = score
                        best_match = fix

        if best_match:
            self.stats["fixes_applied"] += 1

        return best_match

    def record_error(
        self,
        error_type: str,
        error_message: str,
        context: str,
        solution: Optional[str] = None,
    ) -> str:
        """Record an error for future reference."""
        error_id = hashlib.md5(f"{error_type}:{error_message[:100]}".encode()).hexdigest()[:12]

        if error_id in self.errors:
            self.errors[error_id].occurrence_count += 1
            if solution:
                self.errors[error_id].solution = solution
                self.stats["errors_solved"] += 1
        else:
            self.errors[error_id] = ErrorMemory(
                error_type=error_type,
                error_message=error_message,
                context=context,
                solution=solution,
            )
            self.stats["errors_encountered"] += 1

        self._save()
        return error_id

    def get_error_solution(self, error_type: str, error_message: str) -> Optional[str]:
        """Get a known solution for an error."""
        for error in self.errors.values():
            if error.error_type == error_type and error.solution:
                # Check similarity
                if error.error_message[:50].lower() in error_message.lower():
                    return error.solution

        return None

    def learn_pattern(self, pattern_name: str, pattern_data: Dict[str, Any]) -> None:
        """Learn a new code pattern."""
        self.patterns[pattern_name] = {
            **pattern_data,
            "learned_at": datetime.now(timezone.utc).isoformat(),
            "uses": 0,
        }
        self._save()

    def get_pattern(self, pattern_name: str) -> Optional[Dict[str, Any]]:
        """Get a learned pattern."""
        if pattern_name in self.patterns:
            self.patterns[pattern_name]["uses"] += 1
            return self.patterns[pattern_name]
        return None

    def forget_old(self, days: int = 30) -> int:
        """Remove old, unimportant memories."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        forgotten = 0

        for memory_id in list(self.memories.keys()):
            memory = self.memories[memory_id]

            # Don't forget important memories
            if memory.importance > 0.8:
                continue

            # Don't forget frequently accessed memories
            if memory.access_count > 10:
                continue

            if memory.accessed_at < cutoff:
                del self.memories[memory_id]
                forgotten += 1

        if forgotten > 0:
            self._save()

        return forgotten

    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        return {
            **self.stats,
            "active_memories": len(self.memories),
            "known_fixes": len(self.fixes),
            "known_errors": len(self.errors),
            "patterns_learned": len(self.patterns),
        }

    def _generate_id(self, category: str, key: str) -> str:
        """Generate a unique memory ID."""
        return hashlib.md5(f"{category}:{key}".encode()).hexdigest()[:16]

    def _load(self) -> None:
        """Load memories from disk."""
        memories_file = self.data_dir / "memories.json"
        fixes_file = self.data_dir / "fixes.json"
        errors_file = self.data_dir / "errors.json"
        patterns_file = self.data_dir / "patterns.json"
        stats_file = self.data_dir / "stats.json"

        try:
            if memories_file.exists():
                data = json.loads(memories_file.read_text(encoding='utf-8'))
                for m in data:
                    self.memories[m["id"]] = MemoryEntry(
                        id=m["id"],
                        category=m["category"],
                        key=m["key"],
                        value=m["value"],
                        context=m.get("context", {}),
                        created_at=datetime.fromisoformat(m["created_at"]),
                        accessed_at=datetime.fromisoformat(m["accessed_at"]),
                        access_count=m.get("access_count", 0),
                        importance=m.get("importance", 1.0),
                        expires_at=datetime.fromisoformat(m["expires_at"]) if m.get("expires_at") else None,
                    )

            if fixes_file.exists():
                data = json.loads(fixes_file.read_text(encoding='utf-8'))
                for fix_id, f in data.items():
                    self.fixes[fix_id] = FixMemory(
                        issue_pattern=f["issue_pattern"],
                        fix_pattern=f["fix_pattern"],
                        file_types=f["file_types"],
                        success_count=f.get("success_count", 0),
                        failure_count=f.get("failure_count", 0),
                        last_used=datetime.fromisoformat(f["last_used"]) if f.get("last_used") else None,
                    )

            if errors_file.exists():
                data = json.loads(errors_file.read_text(encoding='utf-8'))
                for error_id, e in data.items():
                    self.errors[error_id] = ErrorMemory(
                        error_type=e["error_type"],
                        error_message=e["error_message"],
                        context=e["context"],
                        solution=e.get("solution"),
                        occurrence_count=e.get("occurrence_count", 1),
                    )

            if patterns_file.exists():
                self.patterns = json.loads(patterns_file.read_text(encoding='utf-8'))

            if stats_file.exists():
                self.stats = json.loads(stats_file.read_text(encoding='utf-8'))

        except Exception as e:
            logger.error(f"Error loading agent memory: {e}")

    def _save(self) -> None:
        """Save memories to disk."""
        try:
            # Save memories
            memories_data = []
            for m in self.memories.values():
                memories_data.append({
                    "id": m.id,
                    "category": m.category,
                    "key": m.key,
                    "value": m.value,
                    "context": m.context,
                    "created_at": m.created_at.isoformat(),
                    "accessed_at": m.accessed_at.isoformat(),
                    "access_count": m.access_count,
                    "importance": m.importance,
                    "expires_at": m.expires_at.isoformat() if m.expires_at else None,
                })

            (self.data_dir / "memories.json").write_text(
                json.dumps(memories_data, indent=2),
                encoding='utf-8'
            )

            # Save fixes
            fixes_data = {}
            for fix_id, f in self.fixes.items():
                fixes_data[fix_id] = {
                    "issue_pattern": f.issue_pattern,
                    "fix_pattern": f.fix_pattern,
                    "file_types": f.file_types,
                    "success_count": f.success_count,
                    "failure_count": f.failure_count,
                    "last_used": f.last_used.isoformat() if f.last_used else None,
                }

            (self.data_dir / "fixes.json").write_text(
                json.dumps(fixes_data, indent=2),
                encoding='utf-8'
            )

            # Save errors
            errors_data = {}
            for error_id, e in self.errors.items():
                errors_data[error_id] = {
                    "error_type": e.error_type,
                    "error_message": e.error_message,
                    "context": e.context,
                    "solution": e.solution,
                    "occurrence_count": e.occurrence_count,
                }

            (self.data_dir / "errors.json").write_text(
                json.dumps(errors_data, indent=2),
                encoding='utf-8'
            )

            # Save patterns
            (self.data_dir / "patterns.json").write_text(
                json.dumps(self.patterns, indent=2, default=str),
                encoding='utf-8'
            )

            # Save stats
            (self.data_dir / "stats.json").write_text(
                json.dumps(self.stats, indent=2),
                encoding='utf-8'
            )

        except Exception as e:
            logger.error(f"Error saving agent memory: {e}")


# Convenience function
def get_memory() -> AgentMemory:
    """Get the global agent memory instance."""
    return AgentMemory.get_instance()

