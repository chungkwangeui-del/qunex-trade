"""
Expert Learning System
======================

Advanced learning system that helps experts learn from experience.

Features:
- Pattern recognition from past fixes
- Error memory to avoid repeating mistakes
- Success strategies learned and reused
- Knowledge sharing between experts
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path
from collections import defaultdict
import hashlib
import re
from datetime import timedelta
from typing import List
from typing import Optional
from typing import Any
from typing import Tuple

logger = logging.getLogger(__name__)


@dataclass
class FixPattern:
    """A learned fix pattern."""
    id: str
    error_pattern: str  # Regex pattern to match error
    fix_pattern: str    # How to fix it
    confidence: float   # 0-1, how confident we are this works
    success_count: int = 0
    failure_count: int = 0
    last_used: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    category: str = "general"
    expert_id: str = ""

    def update_success(self):
        """Record successful use."""
        self.success_count += 1
        self.last_used = datetime.now()
        total = self.success_count + self.failure_count
        self.confidence = self.success_count / total if total > 0 else 0.5

    def update_failure(self):
        """Record failed use."""
        self.failure_count += 1
        self.last_used = datetime.now()
        total = self.success_count + self.failure_count
        self.confidence = self.success_count / total if total > 0 else 0.5


@dataclass
class ErrorMemory:
    """Memory of past errors to avoid."""
    error_hash: str
    error_message: str
    file_path: str
    cause: str  # What caused the error
    solution: str  # How it was fixed
    times_seen: int = 1
    last_seen: datetime = field(default_factory=datetime.now)


@dataclass
class SuccessStrategy:
    """A successful strategy that worked."""
    id: str
    task_type: str  # Type of task
    strategy: str   # Description of strategy
    steps: List[str]  # Steps taken
    result: str     # What was achieved
    effectiveness: float = 1.0  # How effective (0-1)
    times_used: int = 1
    expert_id: str = ""


@dataclass
class Knowledge:
    """A piece of knowledge learned."""
    id: str
    topic: str
    content: str
    source: str  # Which expert learned this
    verified: bool = False
    useful_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)


class ExpertLearningSystem:
    """
    Central learning system for all experts.

    Collects and shares knowledge across all experts.
    """

    def __init__(self):
        self.data_dir = Path("data/learning")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Knowledge stores
        self.fix_patterns: Dict[str, FixPattern] = {}
        self.error_memories: Dict[str, ErrorMemory] = {}
        self.success_strategies: Dict[str, SuccessStrategy] = {}
        self.knowledge_base: Dict[str, Knowledge] = {}

        # Expert-specific learning
        self.expert_experience: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'total_fixes': 0,
            'patterns_learned': 0,
            'knowledge_shared': 0,
            'specializations': []
        })

        # Load existing knowledge
        self._load_all()

    def _load_all(self):
        """Load all stored knowledge."""
        # Load fix patterns
        patterns_file = self.data_dir / "fix_patterns.json"
        if patterns_file.exists():
            try:
                with open(patterns_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for p in data:
                        pattern = FixPattern(
                            id=p['id'],
                            error_pattern=p['error_pattern'],
                            fix_pattern=p['fix_pattern'],
                            confidence=p.get('confidence', 0.5),
                            success_count=p.get('success_count', 0),
                            failure_count=p.get('failure_count', 0),
                            category=p.get('category', 'general'),
                            expert_id=p.get('expert_id', '')
                        )
                        self.fix_patterns[pattern.id] = pattern
            except Exception as e:
                logger.warning(f"Could not load fix patterns: {e}")

        # Load error memories
        errors_file = self.data_dir / "error_memories.json"
        if errors_file.exists():
            try:
                with open(errors_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for e in data:
                        memory = ErrorMemory(
                            error_hash=e['error_hash'],
                            error_message=e['error_message'],
                            file_path=e['file_path'],
                            cause=e['cause'],
                            solution=e['solution'],
                            times_seen=e.get('times_seen', 1)
                        )
                        self.error_memories[memory.error_hash] = memory
            except Exception as e:
                logger.warning(f"Could not load error memories: {e}")

    def _save_all(self):
        """Save all knowledge to disk."""
        # Save fix patterns
        patterns_file = self.data_dir / "fix_patterns.json"
        try:
            patterns_data = []
            for p in self.fix_patterns.values():
                patterns_data.append({
                    'id': p.id,
                    'error_pattern': p.error_pattern,
                    'fix_pattern': p.fix_pattern,
                    'confidence': p.confidence,
                    'success_count': p.success_count,
                    'failure_count': p.failure_count,
                    'category': p.category,
                    'expert_id': p.expert_id
                })
            with open(patterns_file, 'w', encoding='utf-8') as f:
                json.dump(patterns_data, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save fix patterns: {e}")

        # Save error memories
        errors_file = self.data_dir / "error_memories.json"
        try:
            errors_data = []
            for e in self.error_memories.values():
                errors_data.append({
                    'error_hash': e.error_hash,
                    'error_message': e.error_message,
                    'file_path': e.file_path,
                    'cause': e.cause,
                    'solution': e.solution,
                    'times_seen': e.times_seen
                })
            with open(errors_file, 'w', encoding='utf-8') as f:
                json.dump(errors_data, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save error memories: {e}")

    def learn_fix_pattern(
        self,
        expert_id: str,
        error_pattern: str,
        fix_pattern: str,
        category: str = "general"
    ) -> FixPattern:
        """Learn a new fix pattern from an expert."""
        pattern_id = f"FP-{len(self.fix_patterns) + 1:04d}"

        pattern = FixPattern(
            id=pattern_id,
            error_pattern=error_pattern,
            fix_pattern=fix_pattern,
            confidence=0.5,
            category=category,
            expert_id=expert_id
        )

        self.fix_patterns[pattern_id] = pattern
        self.expert_experience[expert_id]['patterns_learned'] += 1

        self._save_all()

        logger.info(f"[LEARN] {expert_id} learned pattern: {error_pattern[:50]}...")

        return pattern

    def remember_error(
        self,
        error_message: str,
        file_path: str,
        cause: str,
        solution: str
    ) -> ErrorMemory:
        """Remember an error and how it was fixed."""
        error_hash = hashlib.md5(f"{error_message}{file_path}".encode()).hexdigest()[:12]

        if error_hash in self.error_memories:
            # Already seen this error
            memory = self.error_memories[error_hash]
            memory.times_seen += 1
            memory.last_seen = datetime.now()
            # Update solution if we have a better one
            if len(solution) > len(memory.solution):
                memory.solution = solution
        else:
            # New error
            memory = ErrorMemory(
                error_hash=error_hash,
                error_message=error_message,
                file_path=file_path,
                cause=cause,
                solution=solution
            )
            self.error_memories[error_hash] = memory

        self._save_all()

        return memory

    def find_solution(self, error_message: str, file_path: str = "") -> Optional[str]:
        """Find a known solution for an error."""
        # First, check exact match in error memories
        error_hash = hashlib.md5(f"{error_message}{file_path}".encode()).hexdigest()[:12]
        if error_hash in self.error_memories:
            return self.error_memories[error_hash].solution

        # Then, check fix patterns
        for pattern in sorted(self.fix_patterns.values(), key=lambda p: -p.confidence):
            try:
                if re.search(pattern.error_pattern, error_message, re.IGNORECASE):
                    return pattern.fix_pattern
            except re.error:
                continue

        return None

    def find_matching_patterns(self, error_message: str) -> List[FixPattern]:
        """Find all patterns that match an error."""
        matches = []

        for pattern in self.fix_patterns.values():
            try:
                if re.search(pattern.error_pattern, error_message, re.IGNORECASE):
                    matches.append(pattern)
            except re.error:
                continue

        return sorted(matches, key=lambda p: -p.confidence)

    def record_pattern_success(self, pattern_id: str):
        """Record that a pattern was used successfully."""
        if pattern_id in self.fix_patterns:
            self.fix_patterns[pattern_id].update_success()
            self._save_all()

    def record_pattern_failure(self, pattern_id: str):
        """Record that a pattern failed."""
        if pattern_id in self.fix_patterns:
            self.fix_patterns[pattern_id].update_failure()
            self._save_all()

    def record_success_strategy(
        self,
        expert_id: str,
        task_type: str,
        strategy: str,
        steps: List[str],
        result: str
    ) -> SuccessStrategy:
        """Record a successful strategy."""
        strategy_id = f"SS-{len(self.success_strategies) + 1:04d}"

        success = SuccessStrategy(
            id=strategy_id,
            task_type=task_type,
            strategy=strategy,
            steps=steps,
            result=result,
            expert_id=expert_id
        )

        self.success_strategies[strategy_id] = success

        return success

    def get_best_strategy(self, task_type: str) -> Optional[SuccessStrategy]:
        """Get the best known strategy for a task type."""
        strategies = [
            s for s in self.success_strategies.values()
            if s.task_type == task_type
        ]

        if strategies:
            return max(strategies, key=lambda s: s.effectiveness * s.times_used)

        return None

    def share_knowledge(
        self,
        expert_id: str,
        topic: str,
        content: str
    ) -> Knowledge:
        """Share knowledge with other experts."""
        knowledge_id = f"KB-{len(self.knowledge_base) + 1:04d}"

        knowledge = Knowledge(
            id=knowledge_id,
            topic=topic,
            content=content,
            source=expert_id
        )

        self.knowledge_base[knowledge_id] = knowledge
        self.expert_experience[expert_id]['knowledge_shared'] += 1

        return knowledge

    def search_knowledge(self, query: str) -> List[Knowledge]:
        """Search the knowledge base."""
        query_lower = query.lower()
        results = []

        for knowledge in self.knowledge_base.values():
            if (query_lower in knowledge.topic.lower() or
                query_lower in knowledge.content.lower()):
                results.append(knowledge)

        return sorted(results, key=lambda k: -k.useful_count)

    def mark_knowledge_useful(self, knowledge_id: str):
        """Mark knowledge as useful."""
        if knowledge_id in self.knowledge_base:
            self.knowledge_base[knowledge_id].useful_count += 1

    def get_expert_stats(self, expert_id: str) -> Dict[str, Any]:
        """Get learning stats for an expert."""
        exp = self.expert_experience[expert_id]

        # Count patterns this expert learned
        patterns = [p for p in self.fix_patterns.values() if p.expert_id == expert_id]
        avg_confidence = sum(p.confidence for p in patterns) / len(patterns) if patterns else 0

        return {
            'total_fixes': exp['total_fixes'],
            'patterns_learned': len(patterns),
            'avg_pattern_confidence': avg_confidence,
            'knowledge_shared': exp['knowledge_shared'],
            'specializations': exp['specializations']
        }

    def get_overall_stats(self) -> Dict[str, Any]:
        """Get overall learning system stats."""
        return {
            'total_patterns': len(self.fix_patterns),
            'total_error_memories': len(self.error_memories),
            'total_strategies': len(self.success_strategies),
            'total_knowledge': len(self.knowledge_base),
            'avg_pattern_confidence': (
                sum(p.confidence for p in self.fix_patterns.values()) / len(self.fix_patterns)
                if self.fix_patterns else 0
            ),
            'most_effective_patterns': [
                {'id': p.id, 'confidence': p.confidence, 'uses': p.success_count + p.failure_count}
                for p in sorted(self.fix_patterns.values(), key=lambda p: -p.confidence)[:5]
            ]
        }

    def add_default_patterns(self):
        """Add default fix patterns based on common Python errors."""
        default_patterns = [
            ("undefined variable '(\\w+)'", "Check if variable is defined or imported", "variable"),
            ("'(\\w+)' is not defined", "Add import or define the variable", "import"),
            ("IndentationError", "Fix indentation to use consistent spaces/tabs", "syntax"),
            ("SyntaxError: invalid syntax", "Check for missing colons, parentheses, or brackets", "syntax"),
            ("ModuleNotFoundError: No module named '(\\w+)'", "Install missing package with pip install", "import"),
            ("TypeError: .* takes .* positional argument", "Check function arguments match definition", "type"),
            ("AttributeError: .* has no attribute '(\\w+)'", "Check object type and available attributes", "attribute"),
            ("KeyError: '(\\w+)'", "Check if key exists in dictionary before accessing", "dict"),
            ("IndexError: list index out of range", "Check list length before accessing index", "list"),
            ("ValueError: .* is not in list", "Verify item exists before using list.index()", "list"),
            ("FileNotFoundError", "Check file path exists before opening", "file"),
            ("PermissionError", "Check file permissions or run with elevated privileges", "file"),
            ("ConnectionError", "Check network connection and server availability", "network"),
            ("TimeoutError", "Increase timeout or check server response time", "network"),
            ("json.JSONDecodeError", "Verify JSON format is valid", "json"),
        ]

        for error_pat, fix_pat, category in default_patterns:
            # Check if similar pattern already exists
            exists = any(
                p.error_pattern == error_pat
                for p in self.fix_patterns.values()
            )

            if not exists:
                self.learn_fix_pattern(
                    expert_id="system",
                    error_pattern=error_pat,
                    fix_pattern=fix_pat,
                    category=category
                )


# Singleton instance
_learning_system: Optional[ExpertLearningSystem] = None


def get_learning_system() -> ExpertLearningSystem:
    """Get the learning system singleton."""
    global _learning_system
    if _learning_system is None:
        _learning_system = ExpertLearningSystem()
        # Add default patterns if empty
        if not _learning_system.fix_patterns:
            _learning_system.add_default_patterns()
    return _learning_system

