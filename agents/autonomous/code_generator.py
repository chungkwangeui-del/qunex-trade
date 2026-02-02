"""
Code Generator Agent
====================

Generates complete, working code from descriptions.
Can create new features, pages, APIs, and more.
"""

import re
import ast
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from datetime import timezone
import json
from typing import List
from typing import Optional
from typing import Any
from typing import Tuple

logger = logging.getLogger(__name__)


@dataclass
class GeneratedCode:
    """Represents generated code."""
    file_path: str
    content: str
    language: str
    description: str
    imports_added: List[str]
    dependencies: List[str]


class CodeGeneratorAgent:
    """
    Generates complete, production-ready code.

    Capabilities:
    - Generate Flask routes/APIs
    - Create database models
    - Build HTML templates
    - Generate JavaScript modules
    - Create test files
    - Full feature scaffolding
    """

    def __init__(self):
        self.name = "code_generator"
        self.project_root = Path(__file__).parent.parent.parent

        # Templates for various code types
        self.templates = self._load_templates()

        # Track generated code
        self.generated_files: List[GeneratedCode] = []

    def _load_templates(self) -> Dict[str, str]:
        """Load code generation templates."""
        return {
            "flask_blueprint": '''"""
{description}
"""

from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
import logging

from web.database import db

logger = logging.getLogger(__name__)

bp = Blueprint("{name}", __name__, url_prefix="/{url_prefix}")


@bp.route("/")
@login_required
def index():
    """Main page for {name}."""
    return render_template("{name}/index.html")


@bp.route("/api/list", methods=["GET"])
@login_required
def api_list():
    """Get all items."""
    try:
        # TODO: Implement list logic
        items = []
        return jsonify({{"success": True, "data": items}})
    except Exception as e:
        logger.error(f"Error listing {name}: {{e}}")
        return jsonify({{"success": False, "error": str(e)}}), 500


@bp.route("/api/create", methods=["POST"])
@login_required
def api_create():
    """Create a new item."""
    try:
        data = request.get_json() or {{}}
        # TODO: Implement create logic
        return jsonify({{"success": True, "message": "Created successfully"}})
    except Exception as e:
        logger.error(f"Error creating {name}: {{e}}")
        return jsonify({{"success": False, "error": str(e)}}), 500


@bp.route("/api/<int:item_id>", methods=["GET"])
@login_required
def api_get(item_id: int):
    """Get a single item."""
    try:
        # TODO: Implement get logic
        item = None
        if not item:
            return jsonify({{"success": False, "error": "Not found"}}), 404
        return jsonify({{"success": True, "data": item}})
    except Exception as e:
        logger.error(f"Error getting {name}: {{e}}")
        return jsonify({{"success": False, "error": str(e)}}), 500


@bp.route("/api/<int:item_id>", methods=["PUT"])
@login_required
def api_update(item_id: int):
    """Update an item."""
    try:
        data = request.get_json() or {{}}
        # TODO: Implement update logic
        return jsonify({{"success": True, "message": "Updated successfully"}})
    except Exception as e:
        logger.error(f"Error updating {name}: {{e}}")
        return jsonify({{"success": False, "error": str(e)}}), 500


@bp.route("/api/<int:item_id>", methods=["DELETE"])
@login_required
def api_delete(item_id: int):
    """Delete an item."""
    try:
        # TODO: Implement delete logic
        return jsonify({{"success": True, "message": "Deleted successfully"}})
    except Exception as e:
        logger.error(f"Error deleting {name}: {{e}}")
        return jsonify({{"success": False, "error": str(e)}}), 500
''',

            "database_model": '''"""
{description}
"""

from datetime import datetime
from web.database import db


class {class_name}(db.Model):
    """
    {description}
    """
    __tablename__ = "{table_name}"

    id = db.Column(db.Integer, primary_key=True)
    {columns}

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

    def __repr__(self):
        return f"<{class_name} {{self.id}}>"

    def to_dict(self):
        """Convert to dictionary."""
        return {{
            "id": self.id,
            {to_dict_fields}
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }}

    @classmethod
    def get_by_id(cls, item_id: int):
        """Get item by ID."""
        return cls.query.get(item_id)

    @classmethod
    def get_by_user(cls, user_id: int):
        """Get items by user."""
        return cls.query.filter_by(user_id=user_id).all()

    def save(self):
        """Save to database."""
        db.session.add(self)
        db.session.commit()
        return self

    def delete(self):
        """Delete from database."""
        db.session.delete(self)
        db.session.commit()
''',

            "html_page": '''{{%- extends "authenticated_base.html" -%}}

{{%- block title -%}}{title} - QunexTrade{{%- endblock -%}}

{{%- block styles -%}}
<style>
    .{name}-container {{
        padding: 2rem;
        max-width: 1400px;
        margin: 0 auto;
    }}

    .{name}-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 2rem;
    }}

    .{name}-title {{
        font-size: 1.75rem;
        font-weight: 600;
        color: var(--text-primary);
    }}

    .{name}-card {{
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }}

    .{name}-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
        gap: 1.5rem;
    }}

    .{name}-empty {{
        text-align: center;
        padding: 3rem;
        color: var(--text-secondary);
    }}

    .{name}-actions {{
        display: flex;
        gap: 0.5rem;
    }}

    .btn-primary {{
        background: var(--primary-color);
        color: white;
        border: none;
        padding: 0.75rem 1.5rem;
        border-radius: 8px;
        cursor: pointer;
        font-weight: 500;
    }}

    .btn-primary:hover {{
        opacity: 0.9;
    }}
</style>
{{%- endblock -%}}

{{%- block content -%}}
<div class="{name}-container">
    <div class="{name}-header">
        <h1 class="{name}-title">{title}</h1>
        <div class="{name}-actions">
            <button class="btn-primary" onclick="create{class_name}()">
                + Add New
            </button>
        </div>
    </div>

    <div class="{name}-grid" id="{name}Grid">
        <div class="{name}-empty" id="{name}Empty">
            <p>No items yet. Click "Add New" to get started.</p>
        </div>
    </div>
</div>

<!-- Modal for creating/editing -->
<div id="{name}Modal" class="modal" style="display: none;">
    <div class="modal-content">
        <h2 id="{name}ModalTitle">Add New</h2>
        <form id="{name}Form">
            {form_fields}
            <div class="modal-actions">
                <button type="button" onclick="close{class_name}Modal()">Cancel</button>
                <button type="submit" class="btn-primary">Save</button>
            </div>
        </form>
    </div>
</div>
{{%- endblock -%}}

{{%- block scripts -%}}
<script>
    // State
    let {name}Items = [];
    let editing{class_name}Id = null;

    // Load items on page load
    document.addEventListener("DOMContentLoaded", load{class_name}s);

    async function load{class_name}s() {{
        try {{
            const response = await fetch("/{url_prefix}/api/list");
            const data = await response.json();

            if (data.success) {{
                {name}Items = data.data;
                render{class_name}s();
            }}
        }} catch (error) {{
            console.error("Error loading {name}s:", error);
        }}
    }}

    function render{class_name}s() {{
        const grid = document.getElementById("{name}Grid");
        const empty = document.getElementById("{name}Empty");

        if ({name}Items.length === 0) {{
            empty.style.display = "block";
            return;
        }}

        empty.style.display = "none";
        grid.innerHTML = {name}Items.map(item => `
            <div class="{name}-card" data-id="${{item.id}}">
                <h3>${{item.name || "Untitled"}}</h3>
                <p>${{item.description || ""}}</p>
                <div class="{name}-actions">
                    <button onclick="edit{class_name}(${{item.id}})">Edit</button>
                    <button onclick="delete{class_name}(${{item.id}})">Delete</button>
                </div>
            </div>
        `).join("");
    }}

    function create{class_name}() {{
        editing{class_name}Id = null;
        document.getElementById("{name}ModalTitle").textContent = "Add New";
        document.getElementById("{name}Form").reset();
        document.getElementById("{name}Modal").style.display = "flex";
    }}

    function edit{class_name}(id) {{
        const item = {name}Items.find(i => i.id === id);
        if (!item) return;

        editing{class_name}Id = id;
        document.getElementById("{name}ModalTitle").textContent = "Edit";
        // TODO: Populate form with item data
        document.getElementById("{name}Modal").style.display = "flex";
    }}

    function close{class_name}Modal() {{
        document.getElementById("{name}Modal").style.display = "none";
    }}

    document.getElementById("{name}Form").addEventListener("submit", async (e) => {{
        e.preventDefault();

        const formData = new FormData(e.target);
        const data = Object.fromEntries(formData.entries());

        try {{
            const url = editing{class_name}Id
                ? `/{url_prefix}/api/${{editing{class_name}Id}}`
                : "/{url_prefix}/api/create";

            const method = editing{class_name}Id ? "PUT" : "POST";

            const response = await fetch(url, {{
                method,
                headers: {{ "Content-Type": "application/json" }},
                body: JSON.stringify(data),
            }});

            const result = await response.json();

            if (result.success) {{
                close{class_name}Modal();
                load{class_name}s();
            }} else {{
                alert(result.error || "An error occurred");
            }}
        }} catch (error) {{
            console.error("Error saving:", error);
            alert("An error occurred");
        }}
    }});

    async function delete{class_name}(id) {{
        if (!confirm("Are you sure you want to delete this?")) return;

        try {{
            const response = await fetch(`/{url_prefix}/api/${{id}}`, {{
                method: "DELETE",
            }});

            const result = await response.json();

            if (result.success) {{
                load{class_name}s();
            }} else {{
                alert(result.error || "An error occurred");
            }}
        }} catch (error) {{
            console.error("Error deleting:", error);
            alert("An error occurred");
        }}
    }}
</script>
{{%- endblock -%}}
''',

            "service_class": '''"""
{description}
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class {class_name}Service:
    """
    Service for {name} operations.

    Handles business logic separately from API/routes.
    """

    def __init__(self):
        self.cache = {{}}
        self.cache_ttl = 300  # 5 minutes

    def get_all(self, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get all items, optionally filtered by user."""
        try:
            from web.database import {model_name}

            query = {model_name}.query

            if user_id:
                query = query.filter_by(user_id=user_id)

            items = query.order_by({model_name}.created_at.desc()).all()

            return [item.to_dict() for item in items]

        except Exception as e:
            logger.error(f"Error getting {name}s: {{e}}")
            return []

    def get_by_id(self, item_id: int) -> Optional[Dict[str, Any]]:
        """Get a single item by ID."""
        try:
            from web.database import {model_name}

            item = {model_name}.get_by_id(item_id)

            if item:
                return item.to_dict()

            return None

        except Exception as e:
            logger.error(f"Error getting {name} {{item_id}}: {{e}}")
            return None

    def create(self, data: Dict[str, Any], user_id: Optional[int] = None) -> Dict[str, Any]:
        """Create a new item."""
        try:
            from web.database import {model_name}, db

            item = {model_name}(
                {create_fields}
                user_id=user_id,
            )

            db.session.add(item)
            db.session.commit()

            return {{"success": True, "data": item.to_dict()}}

        except Exception as e:
            logger.error(f"Error creating {name}: {{e}}")
            return {{"success": False, "error": str(e)}}

    def update(self, item_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing item."""
        try:
            from web.database import {model_name}, db

            item = {model_name}.get_by_id(item_id)

            if not item:
                return {{"success": False, "error": "Not found"}}

            {update_fields}

            db.session.commit()

            return {{"success": True, "data": item.to_dict()}}

        except Exception as e:
            logger.error(f"Error updating {name} {{item_id}}: {{e}}")
            return {{"success": False, "error": str(e)}}

    def delete(self, item_id: int) -> Dict[str, Any]:
        """Delete an item."""
        try:
            from web.database import {model_name}, db

            item = {model_name}.get_by_id(item_id)

            if not item:
                return {{"success": False, "error": "Not found"}}

            db.session.delete(item)
            db.session.commit()

            return {{"success": True}}

        except Exception as e:
            logger.error(f"Error deleting {name} {{item_id}}: {{e}}")
            return {{"success": False, "error": str(e)}}

    def search(self, query: str, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Search items."""
        try:
            from web.database import {model_name}

            items = {model_name}.query.filter(
                {model_name}.name.ilike(f"%{{query}}%")
            )

            if user_id:
                items = items.filter_by(user_id=user_id)

            return [item.to_dict() for item in items.all()]

        except Exception as e:
            logger.error(f"Error searching {name}s: {{e}}")
            return []
''',

            "test_file": '''"""
Tests for {name}
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


class Test{class_name}:
    """Tests for {class_name}."""

    def setup_method(self):
        """Set up test fixtures."""
        self.sample_data = {{
            "name": "Test Item",
            "description": "Test description",
        }}

    def test_create_success(self, client, auth_user):
        """Test successful creation."""
        response = client.post(
            "/{url_prefix}/api/create",
            json=self.sample_data,
            headers={{"Authorization": f"Bearer {{auth_user.token}}"}}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    def test_list_success(self, client, auth_user):
        """Test listing items."""
        response = client.get(
            "/{url_prefix}/api/list",
            headers={{"Authorization": f"Bearer {{auth_user.token}}"}}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert isinstance(data["data"], list)

    def test_get_success(self, client, auth_user, sample_{name}):
        """Test getting a single item."""
        response = client.get(
            f"/{url_prefix}/api/{{sample_{name}.id}}",
            headers={{"Authorization": f"Bearer {{auth_user.token}}"}}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    def test_get_not_found(self, client, auth_user):
        """Test getting non-existent item."""
        response = client.get(
            "/{url_prefix}/api/99999",
            headers={{"Authorization": f"Bearer {{auth_user.token}}"}}
        )

        assert response.status_code == 404

    def test_update_success(self, client, auth_user, sample_{name}):
        """Test updating an item."""
        updated_data = {{"name": "Updated Name"}}

        response = client.put(
            f"/{url_prefix}/api/{{sample_{name}.id}}",
            json=updated_data,
            headers={{"Authorization": f"Bearer {{auth_user.token}}"}}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    def test_delete_success(self, client, auth_user, sample_{name}):
        """Test deleting an item."""
        response = client.delete(
            f"/{url_prefix}/api/{{sample_{name}.id}}",
            headers={{"Authorization": f"Bearer {{auth_user.token}}"}}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    def test_unauthorized_access(self, client):
        """Test accessing without authentication."""
        response = client.get("/{url_prefix}/api/list")

        assert response.status_code in [401, 302]  # Unauthorized or redirect
''',
        }

    def generate_feature(
        self,
        name: str,
        description: str,
        fields: List[Dict[str, str]],
    ) -> List[GeneratedCode]:
        """
        Generate a complete feature with all necessary files.

        Returns list of generated files.
        """
        generated = []

        # Normalize name
        name_lower = name.lower().replace(" ", "_")
        name_title = "".join(word.title() for word in name.split("_"))
        class_name = name_title
        url_prefix = name_lower.replace("_", "-")

        # Generate model columns
        columns = []
        to_dict_fields = []
        form_fields = []
        create_fields = []
        update_fields = []

        for field in fields:
            field_name = field["name"]
            field_type = field.get("type", "string")
            required = field.get("required", False)

            # Database column
            db_type = self._get_db_type(field_type)
            nullable = "nullable=False" if required else ""
            columns.append(f'{field_name} = db.Column(db.{db_type}{", " + nullable if nullable else ""})')

            # to_dict field
            to_dict_fields.append(f'"{field_name}": self.{field_name},')

            # Form field
            input_type = self._get_input_type(field_type)
            form_fields.append(f'''
                <div class="form-group">
                    <label for="{field_name}">{field_name.replace("_", " ").title()}</label>
                    <input type="{input_type}" name="{field_name}" id="{field_name}" {"required" if required else ""}>
                </div>''')

            # Create/update fields
            create_fields.append(f'{field_name}=data.get("{field_name}"),')
            update_fields.append(f'if "{field_name}" in data:\n                item.{field_name} = data["{field_name}"]')

        # 1. Generate Blueprint/Routes
        blueprint_content = self.templates["flask_blueprint"].format(
            name=name_lower,
            description=description,
            url_prefix=url_prefix,
        )

        generated.append(GeneratedCode(
            file_path=f"web/api_{name_lower}.py",
            content=blueprint_content,
            language="python",
            description=f"API routes for {name}",
            imports_added=["flask", "flask_login"],
            dependencies=[],
        ))

        # 2. Generate Database Model
        model_content = self.templates["database_model"].format(
            class_name=class_name,
            table_name=name_lower,
            description=description,
            columns="\n    ".join(columns),
            to_dict_fields="\n            ".join(to_dict_fields),
        )

        generated.append(GeneratedCode(
            file_path=f"web/models/{name_lower}.py",
            content=model_content,
            language="python",
            description=f"Database model for {name}",
            imports_added=["sqlalchemy"],
            dependencies=[],
        ))

        # 3. Generate HTML Template
        html_content = self.templates["html_page"].format(
            name=name_lower,
            title=name.replace("_", " ").title(),
            class_name=class_name,
            url_prefix=url_prefix,
            form_fields="".join(form_fields),
        )

        generated.append(GeneratedCode(
            file_path=f"web/templates/{name_lower}.html",
            content=html_content,
            language="html",
            description=f"HTML template for {name}",
            imports_added=[],
            dependencies=[],
        ))

        # 4. Generate Service Class
        service_content = self.templates["service_class"].format(
            name=name_lower,
            class_name=class_name,
            description=description,
            model_name=class_name,
            create_fields="\n                ".join(create_fields),
            update_fields="\n            ".join(update_fields),
        )

        generated.append(GeneratedCode(
            file_path=f"web/{name_lower}_service.py",
            content=service_content,
            language="python",
            description=f"Service class for {name}",
            imports_added=[],
            dependencies=[],
        ))

        # 5. Generate Tests
        test_content = self.templates["test_file"].format(
            name=name_lower,
            class_name=class_name,
            url_prefix=url_prefix,
        )

        generated.append(GeneratedCode(
            file_path=f"tests/test_{name_lower}.py",
            content=test_content,
            language="python",
            description=f"Tests for {name}",
            imports_added=["pytest"],
            dependencies=["pytest"],
        ))

        self.generated_files.extend(generated)

        return generated

    def generate_api_endpoint(
        self,
        path: str,
        method: str,
        description: str,
        request_fields: List[Dict[str, str]] = None,
        response_fields: List[Dict[str, str]] = None,
    ) -> GeneratedCode:
        """Generate a single API endpoint."""

        function_name = path.replace("/", "_").replace("-", "_").strip("_")

        # Build request handling
        request_code = ""
        if method in ["POST", "PUT", "PATCH"] and request_fields:
            request_code = "data = request.get_json() or {}\n"
            for field in request_fields:
                request_code += f"        {field['name']} = data.get(\"{field['name']}\")\n"
        elif method == "GET" and request_fields:
            for field in request_fields:
                request_code += f"        {field['name']} = request.args.get(\"{field['name']}\")\n"

        # Build response
        response_fields_code = ""
        if response_fields:
            response_fields_code = ", ".join([f'"{f["name"]}": None' for f in response_fields])

        code = f'''
@bp.route("/api/{path}", methods=["{method}"])
@login_required
def api_{function_name}():
    """
    {description}

    Method: {method}
    Path: /api/{path}
    """
    try:
        {request_code}
        # TODO: Implement endpoint logic
        result = {{{response_fields_code}}}

        return jsonify({{"success": True, "data": result}})

    except Exception as e:
        logger.error(f"API error: {{e}}")
        return jsonify({{"success": False, "error": str(e)}}), 500
'''

        return GeneratedCode(
            file_path=f"web/api_endpoints/{function_name}.py",
            content=code,
            language="python",
            description=description,
            imports_added=["flask", "flask_login"],
            dependencies=[],
        )

    def apply_generated_code(self) -> Dict[str, Any]:
        """Apply all generated code to the project."""
        results = {
            "files_created": 0,
            "files_updated": 0,
            "errors": [],
        }

        for generated in self.generated_files:
            file_path = self.project_root / generated.file_path

            try:
                # Create directory if needed
                file_path.parent.mkdir(parents=True, exist_ok=True)

                # Check if file exists
                if file_path.exists():
                    # Append or update
                    existing = file_path.read_text(encoding='utf-8')

                    # For Python files, check if we're adding to an existing module
                    if generated.language == "python" and "def " in existing:
                        # Append new content
                        file_path.write_text(existing + "\n\n" + generated.content, encoding='utf-8')
                        results["files_updated"] += 1
                    else:
                        # Overwrite
                        file_path.write_text(generated.content, encoding='utf-8')
                        results["files_updated"] += 1
                else:
                    file_path.write_text(generated.content, encoding='utf-8')
                    results["files_created"] += 1

            except Exception as e:
                results["errors"].append(f"{generated.file_path}: {str(e)}")

        # Clear generated files
        self.generated_files.clear()

        return results

    def _get_db_type(self, field_type: str) -> str:
        """Convert field type to SQLAlchemy type."""
        mapping = {
            "string": "String(255)",
            "text": "Text",
            "integer": "Integer",
            "float": "Float",
            "boolean": "Boolean",
            "datetime": "DateTime",
            "date": "Date",
            "json": "JSON",
            "decimal": "Numeric(10, 2)",
        }
        return mapping.get(field_type.lower(), "String(255)")

    def _get_input_type(self, field_type: str) -> str:
        """Convert field type to HTML input type."""
        mapping = {
            "string": "text",
            "text": "textarea",
            "integer": "number",
            "float": "number",
            "boolean": "checkbox",
            "datetime": "datetime-local",
            "date": "date",
            "email": "email",
            "url": "url",
            "password": "password",
        }
        return mapping.get(field_type.lower(), "text")

