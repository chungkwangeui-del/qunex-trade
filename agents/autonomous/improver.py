"""
Improver Agent (R&D)
====================

Proactively improves code quality and suggests enhancements.
Focuses on:
- Code optimization
- Performance improvements
- Best practices
- Modern patterns
"""

import re
import ast
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from agents.autonomous.task_queue import Task, TaskChange, TaskType, TaskPriority
from agents.codebase_knowledge import CodebaseKnowledge
from datetime import timezone
from typing import List
from typing import Optional
from typing import Any
from typing import Tuple

logger = logging.getLogger(__name__)


class ImproverAgent:
    """
    The Improver Agent proactively enhances the codebase.

    Capabilities:
    - Identify optimization opportunities
    - Suggest architectural improvements
    - Add type hints
    - Improve code organization
    - Update to modern patterns
    """

    def __init__(self):
        self.name = "improver"
        self.project_root = Path(__file__).parent.parent.parent
        self.knowledge = CodebaseKnowledge()

    async def analyze_improvements(self) -> List[Dict[str, Any]]:
        """
        Analyze codebase and identify improvement opportunities.
        """
        improvements = []

        # Scan all Python files
        for py_file in self.project_root.rglob("*.py"):
            if ".git" in str(py_file) or "__pycache__" in str(py_file):
                continue

            file_improvements = await self._analyze_file(py_file)
            improvements.extend(file_improvements)

        # Sort by priority
        improvements.sort(key=lambda x: x.get("priority", 5))

        return improvements

    async def _analyze_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Analyze a single file for improvements"""
        improvements = []
        relative_path = str(file_path.relative_to(self.project_root))

        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.split('\n')
            line_count = len(lines)

            # Check file size
            if line_count > 500:
                improvements.append({
                    "file": relative_path,
                    "type": "refactor",
                    "priority": 3,
                    "title": f"Split large file ({line_count} lines)",
                    "description": f"{relative_path} has {line_count} lines. Consider splitting into modules.",
                    "auto_fixable": False,
                })

            # Parse AST
            try:
                tree = ast.parse(content)
            except SyntaxError:
                return improvements

            # Check for long functions
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    func_lines = (node.end_lineno or 0) - node.lineno
                    if func_lines > 50:
                        improvements.append({
                            "file": relative_path,
                            "type": "refactor",
                            "priority": 3,
                            "title": f"Refactor long function: {node.name}",
                            "description": f"Function {node.name} is {func_lines} lines. Break into smaller functions.",
                            "line": node.lineno,
                            "auto_fixable": False,
                        })

                    # Check for missing type hints
                    if not node.returns and not node.name.startswith('_'):
                        improvements.append({
                            "file": relative_path,
                            "type": "type_hints",
                            "priority": 4,
                            "title": f"Add return type hint: {node.name}",
                            "description": f"Function {node.name} lacks return type annotation.",
                            "line": node.lineno,
                            "auto_fixable": True,
                        })

            # Check for class without docstring
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    has_docstring = (
                        node.body and
                        isinstance(node.body[0], ast.Expr) and
                        isinstance(node.body[0].value, ast.Constant)
                    )
                    if not has_docstring:
                        improvements.append({
                            "file": relative_path,
                            "type": "documentation",
                            "priority": 4,
                            "title": f"Add docstring to class: {node.name}",
                            "description": f"Class {node.name} lacks documentation.",
                            "line": node.lineno,
                            "auto_fixable": True,
                        })

            # Check for print statements (should use logging)
            if 'print(' in content and 'logger' not in content:
                improvements.append({
                    "file": relative_path,
                    "type": "best_practice",
                    "priority": 4,
                    "title": "Replace print with logging",
                    "description": f"{relative_path} uses print() instead of logging.",
                    "auto_fixable": True,
                })

            # Check for TODO comments
            for i, line in enumerate(lines, 1):
                if '# TODO' in line or '# FIXME' in line:
                    todo_text = line.split('#', 1)[1].strip()
                    improvements.append({
                        "file": relative_path,
                        "type": "todo",
                        "priority": 4,
                        "title": f"TODO in {relative_path}",
                        "description": todo_text,
                        "line": i,
                        "auto_fixable": False,
                    })

            # Check for missing error handling in API routes
            if '@' in content and 'route' in content.lower():
                if 'try:' not in content:
                    improvements.append({
                        "file": relative_path,
                        "type": "error_handling",
                        "priority": 2,
                        "title": "Add error handling to routes",
                        "description": f"{relative_path} has routes without try/except blocks.",
                        "auto_fixable": False,
                    })

        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {e}")

        return improvements

    async def process_task(self, task: Task) -> Tuple[bool, str]:
        """Process an improvement task"""
        logger.info(f"Improver processing task: {task.id}")

        improvements_made = []

        for file_path in task.target_files:
            full_path = self.project_root / file_path

            if not full_path.exists():
                continue

            try:
                original = full_path.read_text(encoding='utf-8')
                improved = await self._improve_file(original, task)

                if improved != original:
                    # Validate
                    if file_path.endswith('.py'):
                        try:
                            ast.parse(improved)
                        except SyntaxError:
                            continue

                    change = TaskChange(
                        file_path=str(full_path),
                        change_type="modify",
                        original_content=original,
                        new_content=improved,
                        description="Code improvements",
                    )

                    full_path.write_text(improved, encoding='utf-8')
                    change.applied = True
                    task.changes.append(change)
                    improvements_made.append(file_path)

            except Exception as e:
                logger.error(f"Error improving {file_path}: {e}")

        if improvements_made:
            return True, f"Improved {len(improvements_made)} file(s)"
        return False, "No improvements applied"

    async def _improve_file(self, content: str, task: Task) -> str:
        """Apply improvements to file content"""
        improved = content

        # Add logging import if using print
        if 'print(' in improved and 'import logging' not in improved:
            # Add logging setup
            logging_setup = '''import logging

logger = logging.getLogger(__name__)

'''
            # Find position after imports
            lines = improved.split('\n')
            insert_pos = 0
            for i, line in enumerate(lines):
                if line.startswith('import ') or line.startswith('from '):
                    insert_pos = i + 1

            lines.insert(insert_pos, logging_setup)
            improved = '\n'.join(lines)

            # Replace print with logger
            improved = re.sub(
                r'print\(([^)]+)\)',
                r'logger.info(\1)',
                improved
            )

        # Add type hints to simple functions
        improved = self._add_simple_type_hints(improved)

        return improved

    def _add_simple_type_hints(self, content: str) -> str:
        """Add obvious type hints to functions"""
        # Simple pattern: functions that return None
        pattern = r'(def \w+\([^)]*\)):'

        def add_none_return(match):
            func_def = match.group(1)
            if '-> ' not in func_def:
                # Check if function body has no return or return without value
                return f'{func_def} -> None:'
            return match.group(0)

        # Only apply to functions that clearly return None
        # (this is conservative to avoid breaking code)
        return content

    def can_handle_task(self, task: Task) -> bool:
        """Check if this agent can handle a task"""
        return task.task_type in [TaskType.IMPROVEMENT, TaskType.REFACTOR]

    def get_priority_improvements(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top priority improvements synchronously"""
        import asyncio
        improvements = asyncio.run(self.analyze_improvements())
        return improvements[:limit]


