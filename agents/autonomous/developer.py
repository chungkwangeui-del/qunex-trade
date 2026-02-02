"""
Developer Agent (The Engineer)
==============================

Responsible for writing and modifying code.
Can create new files, modify existing ones, and implement features.
"""

import re
import ast
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from agents.autonomous.task_queue import Task, TaskChange, TaskStatus, TaskType
from agents.codebase_knowledge import CodebaseKnowledge
from datetime import timezone
import json
from typing import List
from typing import Optional
from typing import Any
from typing import Tuple

logger = logging.getLogger(__name__)

class DeveloperAgent:
    """
    The Developer Agent writes and modifies code.

    Capabilities:
    - Read and understand existing code
    - Write new functions/classes
    - Modify existing code safely
    - Add imports and dependencies
    - Create new files
    - Follow project conventions
    """

    def __init__(self):
        self.name = "developer"
        self.knowledge = CodebaseKnowledge()
        self.project_root = Path(__file__).parent.parent.parent

        # Templates for common code patterns
        self.templates = self._load_templates()

    def _load_templates(self) -> Dict[str, str]:
        """Load code templates for common patterns"""
        return {
            "flask_route": '''
@{blueprint}.route("/{path}", methods=["{methods}"])
@login_required
def {function_name}():
    """{docstring}"""
    try:
        {body}
        return jsonify({{"success": True, "data": result}})
    except Exception as e:
        logger.error(f"{function_name} error: {{e}}")
        return jsonify({{"success": False, "error": str(e)}}), 500
''',
            "api_endpoint": '''
@{blueprint}.route("/api/{path}", methods=["{methods}"])
@login_required
def api_{function_name}():
    """{docstring}"""
    try:
        data = request.get_json() or {{}}
        {body}
        return jsonify({{"success": True, "data": result}})
    except Exception as e:
        return jsonify({{"success": False, "error": str(e)}}), 500
''',
            "model_class": '''
class {class_name}(db.Model):
    """{docstring}"""
    __tablename__ = "{table_name}"

    id = db.Column(db.Integer, primary_key=True)
    {columns}
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {{
            "id": self.id,
            {to_dict_fields}
        }}
''',
            "service_function": '''
def {function_name}({params}) -> {return_type}:
    """
    {docstring}

    Args:
        {args_doc}

    Returns:
        {return_doc}
    """
    try:
        {body}
    except Exception as e:
        logger.error(f"{function_name} error: {{e}}")
        raise
''',
            "test_function": '''
def test_{function_name}():
    """{docstring}"""
    # Arrange
    {arrange}

    # Act
    {act}

    # Assert
    {assertions}
''',
        }

    async def process_task(self, task: Task) -> Tuple[bool, str]:
        """
        Process a development task.
        Returns (success, message)
        """
        logger.info(f"Developer processing task: {task.id} - {task.title}")

        try:
            if task.task_type == TaskType.BUG_FIX:
                return await self._fix_bug(task)
            elif task.task_type == TaskType.FEATURE:
                return await self._implement_feature(task)
            elif task.task_type == TaskType.IMPROVEMENT:
                return await self._improve_code(task)
            elif task.task_type == TaskType.TEST:
                return await self._add_tests(task)
            elif task.task_type == TaskType.REFACTOR:
                return await self._refactor_code(task)
            else:
                return await self._generic_task(task)

        except Exception as e:
            logger.error(f"Developer task failed: {e}")
            return False, str(e)

    async def _fix_bug(self, task: Task) -> Tuple[bool, str]:
        """Fix a bug in the code"""
        if not task.target_files:
            return False, "No target files specified"

        for file_path in task.target_files:
            full_path = self.project_root / file_path

            if not full_path.exists():
                continue

            original_content = full_path.read_text(encoding='utf-8')

            # Analyze the issue from task description
            fix_applied = False
            new_content = original_content

            # Common bug fixes
            description_lower = task.description.lower()

            # Fix: Missing import
            if "import" in description_lower and "missing" in description_lower:
                new_content = self._add_missing_import(new_content, task.description)
                fix_applied = True

            # Fix: Bare except clause
            if "bare except" in description_lower or "except Exception:" in description_lower:
                new_content = self._fix_bare_except(new_content)
                fix_applied = True

            # Fix: Missing CSRF token
            if "csrf" in description_lower:
                new_content = self._add_csrf_token(new_content)
                fix_applied = True

            # Fix: Syntax error (try to auto-fix common issues)
            if "syntax" in description_lower:
                new_content = self._fix_syntax_issues(new_content)
                fix_applied = True

            if fix_applied and new_content != original_content:
                # Validate the fix
                if file_path.endswith(".py"):
                    try:
                        ast.parse(new_content)
                    except SyntaxError as e:
                        return False, f"Fix introduced syntax error: {e}"

                # Apply the change
                change = TaskChange(
                    file_path=str(full_path),
                    change_type="modify",
                    original_content=original_content,
                    new_content=new_content,
                    description=f"Bug fix: {task.title}",
                )

                full_path.write_text(new_content, encoding='utf-8')
                change.applied = True
                task.changes.append(change)

                return True, f"Fixed bug in {file_path}"

        return False, "Could not apply fix automatically"

    async def _implement_feature(self, task: Task) -> Tuple[bool, str]:
        """Implement a new feature"""
        # This is a placeholder - actual implementation would be more sophisticated
        description = task.description.lower()

        # Detect what kind of feature is being requested
        if "api" in description or "endpoint" in description:
            return await self._create_api_endpoint(task)
        elif "route" in description or "page" in description:
            return await self._create_route(task)
        elif "model" in description or "database" in description:
            return await self._create_model(task)

        return False, "Feature type not recognized"

    async def _improve_code(self, task: Task) -> Tuple[bool, str]:
        """Improve existing code"""
        if not task.target_files:
            return False, "No target files specified"

        improvements_made = []

        for file_path in task.target_files:
            full_path = self.project_root / file_path

            if not full_path.exists():
                continue

            original_content = full_path.read_text(encoding='utf-8')
            new_content = original_content

            # Apply improvements
            new_content = self._add_docstrings(new_content)
            new_content = self._improve_error_handling(new_content)
            new_content = self._add_type_hints(new_content)

            if new_content != original_content:
                # Validate
                if file_path.endswith(".py"):
                    try:
                        ast.parse(new_content)
                    except SyntaxError:
                        continue

                change = TaskChange(
                    file_path=str(full_path),
                    change_type="modify",
                    original_content=original_content,
                    new_content=new_content,
                    description=f"Code improvements: {file_path}",
                )

                full_path.write_text(new_content, encoding='utf-8')
                change.applied = True
                task.changes.append(change)
                improvements_made.append(file_path)

        if improvements_made:
            return True, f"Improved {len(improvements_made)} file(s)"
        return False, "No improvements could be made"

    async def _add_tests(self, task: Task) -> Tuple[bool, str]:
        """Add tests for code"""
        tests_dir = self.project_root / "tests"
        tests_dir.mkdir(exist_ok=True)

        for file_path in task.target_files:
            module_name = Path(file_path).stem
            test_file = tests_dir / f"test_{module_name}.py"

            if test_file.exists():
                continue

            # Generate basic test file
            test_content = f'''"""
Tests for {module_name}
"""

import pytest
from unittest.mock import Mock, patch

class Test{module_name.title().replace("_", "")}:
    """Tests for {module_name} module"""

    def setup_method(self):
        """Set up test fixtures"""
        pass

    def test_placeholder(self):
        """Placeholder test - implement actual tests"""
        # TODO: Add actual tests for {module_name}
        assert True
'''

            change = TaskChange(
                file_path=str(test_file),
                change_type="create",
                original_content=None,
                new_content=test_content,
                description=f"Created test file for {module_name}",
            )

            test_file.write_text(test_content, encoding='utf-8')
            change.applied = True
            task.changes.append(change)

        if task.changes:
            return True, f"Created {len(task.changes)} test file(s)"
        return False, "No tests created"

    async def _refactor_code(self, task: Task) -> Tuple[bool, str]:
        """Refactor code for better structure"""
        # Similar to improve but focused on structure
        return await self._improve_code(task)

    async def _generic_task(self, task: Task) -> Tuple[bool, str]:
        """Handle generic tasks"""
        return False, "Task type requires manual implementation"

    async def _create_api_endpoint(self, task: Task) -> Tuple[bool, str]:
        """Create a new API endpoint"""
        # This would need more context about what endpoint to create
        return False, "API endpoint creation requires more specification"

    async def _create_route(self, task: Task) -> Tuple[bool, str]:
        """Create a new route/page"""
        return False, "Route creation requires more specification"

    async def _create_model(self, task: Task) -> Tuple[bool, str]:
        """Create a new database model"""
        return False, "Model creation requires more specification"

    # ============ Code Modification Helpers ============

    def _add_missing_import(self, content: str, description: str) -> str:
        """Add a missing import statement"""
        # Try to extract what import is needed from description
        import_match = re.search(r"import[ing]?\s+['\"]?(\w+)['\"]?", description, re.I)
        if not import_match:
            return content

        module_name = import_match.group(1)

        # Check if already imported
        if f"import {module_name}" in content or f"from {module_name}" in content:
            return content

        # Find position to add import (after existing imports)
        lines = content.split('\n')
        import_end = 0

        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                import_end = i + 1
            elif line.strip() and not line.startswith('#') and not line.startswith('"""'):
                if import_end == 0:
                    import_end = i
                break

        # Add the import
        lines.insert(import_end, f"import {module_name}")

        return '\n'.join(lines)

    def _fix_bare_except(self, content: str) -> str:
        """Fix bare except clauses"""
        # Replace 'except Exception:' with 'except Exception:'
        content = re.sub(r'\bexcept\s*:', 'except Exception:', content)
        return content

    def _add_csrf_token(self, content: str) -> str:
        """Add CSRF token to forms in HTML"""
        if '{{ csrf_token() }}' in content or '{{ form.hidden_tag() }}' in content:
            return content

        # Find forms and add CSRF token
        def add_token(match):
            form_tag = match.group(0)
            # Add right after <form ...>
            return form_tag + '\n    {{ csrf_token() }}'

        content = re.sub(
            r'<form[^>]*method=["\']post["\'][^>]*>',
            add_token,
            content,
            flags=re.IGNORECASE
        )

        return content

    def _fix_syntax_issues(self, content: str) -> str:
        """Try to fix common syntax issues"""
        # Fix unclosed parentheses at end of lines
        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            # Count parentheses
            open_count = line.count('(') - line.count(')')
            if open_count > 0 and not line.rstrip().endswith(','):
                # Might be missing closing paren
                pass  # Don't auto-fix as it could break valid code

            fixed_lines.append(line)

        return '\n'.join(fixed_lines)

    def _add_docstrings(self, content: str) -> str:
        """Add docstrings to functions and classes without them"""
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return content

        lines = content.split('\n')
        insertions = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Check if has docstring
                if not (node.body and isinstance(node.body[0], ast.Expr)
                        and isinstance(node.body[0].value, ast.Constant)
                        and isinstance(node.body[0].value.value, str)):
                    # Needs docstring
                    indent = "    " * (1 + sum(1 for n in ast.walk(tree)
                                              if isinstance(n, ast.ClassDef)
                                              and node in ast.walk(n)))
                    docstring = f'{indent}"""TODO: Add docstring for {node.name}"""'
                    insertions.append((node.body[0].lineno - 1, docstring))

        # Insert docstrings (reverse order to preserve line numbers)
        for line_no, docstring in sorted(insertions, reverse=True):
            lines.insert(line_no, docstring)

        return '\n'.join(lines)

    def _improve_error_handling(self, content: str) -> str:
        """Improve error handling in code"""
        # Already handled by _fix_bare_except
        return self._fix_bare_except(content)

    def _add_type_hints(self, content: str) -> str:
        """Add basic type hints to functions"""
        # This is complex - skip for now
        return content

    def can_handle_task(self, task: Task) -> bool:
        """Check if this agent can handle a task"""
        handleable_types = [
            TaskType.BUG_FIX,
            TaskType.FEATURE,
            TaskType.IMPROVEMENT,
            TaskType.TEST,
            TaskType.REFACTOR,
        ]
        return task.task_type in handleable_types

    # ============ Advanced Code Generation ============

    def generate_service_function(
        self,
        name: str,
        description: str,
        params: List[Dict[str, str]],
        return_type: str = "Dict[str, Any]",
        has_db_access: bool = False,
    ) -> str:
        """Generate a complete service function."""
        # Build parameter string
        param_str = ", ".join([
            f"{p['name']}: {p.get('type', 'Any')}" + (f" = {p['default']}" if 'default' in p else "")
            for p in params
        ])

        # Build docstring args
        args_doc = "\n        ".join([
            f"{p['name']}: {p.get('description', 'Parameter')}"
            for p in params
        ])

        code = f'''def {name}({param_str}) -> {return_type}:
    """
    {description}

    Args:
        {args_doc}

    Returns:
        {return_type}: Result of the operation
    """
    try:
'''

        if has_db_access:
            code += '        # Database operation\n'
            code += '        result = {}\n'
            code += '        # TODO: Implement database logic\n'
        else:
            code += '        result = {}\n'
            code += '        # TODO: Implement business logic\n'

        code += f'''        return result

    except Exception as e:
        logger.error(f"{name} error: {{e}}")
        raise
'''
        return code

    def generate_api_route(
        self,
        path: str,
        method: str = "GET",
        description: str = "API endpoint",
        requires_auth: bool = True,
        request_params: List[Dict[str, str]] = None,
    ) -> str:
        """Generate a Flask API route."""
        function_name = path.replace("/", "_").replace("-", "_").strip("_")

        code = f'''@bp.route("/api/{path}", methods=["{method}"])
'''
        if requires_auth:
            code += '@login_required\n'

        code += f'''def api_{function_name}():
    """
    {description}

    Method: {method}
    Path: /api/{path}
    Auth Required: {requires_auth}
    """
    try:
'''

        if method in ["POST", "PUT", "PATCH"]:
            code += '        data = request.get_json() or {}\n'
            if request_params:
                for param in request_params:
                    code += f'        {param["name"]} = data.get("{param["name"]}")\n'
        elif method == "GET" and request_params:
            for param in request_params:
                code += f'        {param["name"]} = request.args.get("{param["name"]}")\n'

        code += '''
        # TODO: Implement endpoint logic
        result = {}

        return jsonify({"success": True, "data": result})

    except Exception as e:
        logger.error(f"API error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
'''
        return code

    def generate_model_class(
        self,
        name: str,
        table_name: str,
        columns: List[Dict[str, str]],
        description: str = "",
    ) -> str:
        """Generate a SQLAlchemy model class."""
        # Build column definitions
        column_code = []
        to_dict_fields = []

        for col in columns:
            col_name = col["name"]
            col_type = col.get("type", "String")
            nullable = col.get("nullable", True)

            type_mapping = {
                "string": "db.String(255)",
                "text": "db.Text",
                "integer": "db.Integer",
                "float": "db.Float",
                "boolean": "db.Boolean",
                "datetime": "db.DateTime",
                "date": "db.Date",
                "json": "db.JSON",
            }

            db_type = type_mapping.get(col_type.lower(), f"db.{col_type}")

            col_def = f'{col_name} = db.Column({db_type}'
            if not nullable:
                col_def += ', nullable=False'
            if col.get("unique"):
                col_def += ', unique=True'
            if col.get("default"):
                col_def += f', default={col["default"]}'
            col_def += ')'

            column_code.append(f'    {col_def}')
            to_dict_fields.append(f'            "{col_name}": self.{col_name},')

        code = f'''class {name}(db.Model):
    """
    {description or f'{name} model'}
    """
    __tablename__ = "{table_name}"

    id = db.Column(db.Integer, primary_key=True)
{chr(10).join(column_code)}
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {{
            "id": self.id,
{chr(10).join(to_dict_fields)}
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }}

    def __repr__(self):
        return f"<{name} {{self.id}}>"
'''
        return code

    def generate_test_class(
        self,
        module_name: str,
        functions_to_test: List[str],
    ) -> str:
        """Generate a test class for a module."""
        class_name = "".join(word.title() for word in module_name.split("_"))

        test_methods = []
        for func_name in functions_to_test:
            test_methods.append(f'''
    def test_{func_name}_success(self):
        """Test {func_name} with valid input."""
        # Arrange
        # TODO: Set up test data

        # Act
        # TODO: Call {func_name}
        result = None

        # Assert
        assert result is not None

    def test_{func_name}_error_handling(self):
        """Test {func_name} error handling."""
        # Arrange
        # TODO: Set up invalid test data

        # Act & Assert
        # TODO: Test error handling
        pass''')

        code = f'''"""
Tests for {module_name}
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

class Test{class_name}:
    """Tests for {module_name} module."""

    def setup_method(self):
        """Set up test fixtures."""
        # TODO: Add test fixtures
        pass

    def teardown_method(self):
        """Clean up after tests."""
        pass
{''.join(test_methods)}
'''
        return code

    def enhance_function_with_logging(self, function_code: str) -> str:
        """Add comprehensive logging to a function."""
        lines = function_code.split('\n')
        enhanced = []
        func_name = None
        in_function = False
        indent_level = 0

        for i, line in enumerate(lines):
            if line.strip().startswith('def ') or line.strip().startswith('async def '):
                func_match = re.search(r'(?:async\s+)?def\s+(\w+)', line)
                if func_match:
                    func_name = func_match.group(1)
                    in_function = True
                    enhanced.append(line)
                    # Find indent level
                    indent_level = len(line) - len(line.lstrip()) + 4
                    indent = ' ' * indent_level
                    # Add entry log after docstring
                    continue

            if in_function and line.strip().startswith('"""') and i > 0 and lines[i-1].strip().startswith('def'):
                # Skip single-line docstring
                enhanced.append(line)
                continue

            if in_function and func_name and ('try:' in line or (line.strip() and not line.strip().startswith('#') and not line.strip().startswith('"""'))):
                # Add entry log before first real code
                indent = ' ' * indent_level
                enhanced.append(f'{indent}logger.debug(f"Entering {func_name}")')
                in_function = False

            enhanced.append(line)

        return '\n'.join(enhanced)

    def get_capabilities(self) -> List[Dict[str, str]]:
        """Return list of developer capabilities."""
        return [
            {"capability": "generate_service_function", "description": "Create service layer functions"},
            {"capability": "generate_api_route", "description": "Create Flask API endpoints"},
            {"capability": "generate_model_class", "description": "Create SQLAlchemy models"},
            {"capability": "generate_test_class", "description": "Create pytest test classes"},
            {"capability": "fix_bugs", "description": "Fix common code bugs"},
            {"capability": "add_docstrings", "description": "Add documentation to code"},
            {"capability": "improve_error_handling", "description": "Add try/except blocks"},
        ]
