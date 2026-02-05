"""
Escalation System
=================

When agents can't automatically fix issues, this system provides:
- Clear explanation of what the problem is
- Why it can't be auto-fixed
- Step-by-step manual fix instructions
- Commands to run (if applicable)
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from enum import Enum
from pathlib import Path
from datetime import timezone
import os
from typing import List
from typing import Optional
from typing import Any

logger = logging.getLogger(__name__)


class EscalationReason(Enum):
    """Why an issue requires human intervention."""
    REQUIRES_CREDENTIALS = "requires_credentials"  # API keys, passwords
    REQUIRES_PAYMENT = "requires_payment"  # Subscription, billing
    REQUIRES_DECISION = "requires_decision"  # Architecture choice
    REQUIRES_EXTERNAL = "requires_external"  # External service setup
    COMPLEX_REFACTOR = "complex_refactor"  # Too risky to auto-fix
    SECURITY_SENSITIVE = "security_sensitive"  # Security-critical changes
    DATABASE_MIGRATION = "database_migration"  # Schema changes
    CONFIG_CHANGE = "config_change"  # Environment/deployment config
    PERMISSION_NEEDED = "permission_needed"  # File/system permissions
    UNCLEAR_INTENT = "unclear_intent"  # Need clarification


class EscalationPriority(Enum):
    """How urgent is this escalation."""
    CRITICAL = 1  # System broken, needs immediate fix
    HIGH = 2      # Major feature broken
    MEDIUM = 3    # Functionality impaired
    LOW = 4       # Nice to fix, not urgent
    INFO = 5      # FYI only


@dataclass
class ManualStep:
    """A single step in the manual fix process."""
    step_number: int
    description: str
    command: Optional[str] = None  # Shell command if applicable
    code_snippet: Optional[str] = None  # Code to add/modify
    file_to_edit: Optional[str] = None  # Which file to edit
    notes: Optional[str] = None  # Additional info


@dataclass
class Escalation:
    """A problem that requires human intervention."""
    id: str
    title: str
    description: str
    reason: EscalationReason
    priority: EscalationPriority

    # What caused this
    source_agent: str
    source_task: Optional[str] = None
    affected_files: List[str] = field(default_factory=list)

    # How to fix it
    why_not_auto: str = ""  # Why agents can't fix this
    manual_steps: List[ManualStep] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved: bool = False
    resolved_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "reason": self.reason.value,
            "priority": self.priority.value,
            "source_agent": self.source_agent,
            "affected_files": self.affected_files,
            "why_not_auto": self.why_not_auto,
            "manual_steps": [
                {
                    "step": s.step_number,
                    "description": s.description,
                    "command": s.command,
                    "code": s.code_snippet,
                    "file": s.file_to_edit,
                    "notes": s.notes,
                }
                for s in self.manual_steps
            ],
            "created_at": self.created_at.isoformat(),
            "resolved": self.resolved,
        }


class EscalationManager:
    """Manages escalations - problems requiring human intervention."""

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.escalations: Dict[str, Escalation] = {}
        self._counter = 0

        # Persistence file
        self._data_dir = Path(__file__).parent.parent.parent / "data" / "agents"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._persistence_file = self._data_dir / "escalations.json"

        # Load existing escalations from disk
        self._load_from_disk()

        # Pre-defined fix instructions for common issues
        self.fix_templates = self._load_fix_templates()

    def _generate_id(self) -> str:
        self._counter += 1
        return f"ESC-{self._counter:04d}"

    def _load_from_disk(self) -> None:
        """Load escalations from persistent storage."""
        if not self._persistence_file.exists():
            return

        try:
            import json
            data = json.loads(self._persistence_file.read_text(encoding='utf-8'))

            self._counter = data.get("counter", 0)

            for esc_data in data.get("escalations", []):
                try:
                    # Reconstruct manual steps
                    steps = []
                    for step_data in esc_data.get("manual_steps", []):
                        steps.append(ManualStep(
                            step_number=step_data.get("step", 1),
                            description=step_data.get("description", ""),
                            command=step_data.get("command"),
                            code_snippet=step_data.get("code"),
                            file_to_edit=step_data.get("file"),
                            notes=step_data.get("notes"),
                        ))

                    escalation = Escalation(
                        id=esc_data["id"],
                        title=esc_data["title"],
                        description=esc_data["description"],
                        reason=EscalationReason(esc_data["reason"]),
                        priority=EscalationPriority(esc_data["priority"]),
                        source_agent=esc_data["source_agent"],
                        affected_files=esc_data.get("affected_files", []),
                        why_not_auto=esc_data.get("why_not_auto", ""),
                        manual_steps=steps,
                        created_at=datetime.fromisoformat(esc_data["created_at"]),
                        resolved=esc_data.get("resolved", False),
                    )

                    if esc_data.get("resolved_at"):
                        escalation.resolved_at = datetime.fromisoformat(esc_data["resolved_at"])

                    self.escalations[escalation.id] = escalation

                except Exception as e:
                    logger.error(f"Error loading escalation: {e}")

            logger.info(f"Loaded {len(self.escalations)} escalations from disk")

        except Exception as e:
            logger.error(f"Error loading escalations: {e}")

    def _save_to_disk(self) -> None:
        """Save escalations to persistent storage."""
        try:
            import json

            data = {
                "counter": self._counter,
                "escalations": [esc.to_dict() for esc in self.escalations.values()],
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }

            self._persistence_file.write_text(
                json.dumps(data, indent=2, default=str),
                encoding='utf-8'
            )

        except Exception as e:
            logger.error(f"Error saving escalations: {e}")

    def create_escalation(
        self,
        title: str,
        description: str,
        reason: EscalationReason,
        priority: EscalationPriority,
        source_agent: str,
        affected_files: List[str] = None,
        why_not_auto: str = "",
        manual_steps: List[ManualStep] = None,
    ) -> Escalation:
        """Create a new escalation."""
        escalation = Escalation(
            id=self._generate_id(),
            title=title,
            description=description,
            reason=reason,
            priority=priority,
            source_agent=source_agent,
            affected_files=affected_files or [],
            why_not_auto=why_not_auto,
            manual_steps=manual_steps or [],
        )

        # If no manual steps provided, try to get from templates
        if not escalation.manual_steps:
            template_steps = self._get_template_steps(escalation)
            if template_steps:
                escalation.manual_steps = template_steps

        self.escalations[escalation.id] = escalation
        logger.info(f"Created escalation {escalation.id}: {title}")

        # Save to disk
        self._save_to_disk()

        return escalation

    def resolve_escalation(self, escalation_id: str) -> bool:
        """Mark an escalation as resolved."""
        if escalation_id in self.escalations:
            self.escalations[escalation_id].resolved = True
            self.escalations[escalation_id].resolved_at = datetime.now(timezone.utc)

            # Save to disk
            self._save_to_disk()

            return True
        return False

    def clear_resolved(self) -> int:
        """Remove all resolved escalations. Returns count removed."""
        resolved_ids = [eid for eid, esc in self.escalations.items() if esc.resolved]
        for eid in resolved_ids:
            del self.escalations[eid]

        if resolved_ids:
            self._save_to_disk()

        return len(resolved_ids)

    def get_pending_escalations(self) -> List[Escalation]:
        """Get all unresolved escalations, sorted by priority."""
        pending = [e for e in self.escalations.values() if not e.resolved]
        return sorted(pending, key=lambda x: x.priority.value)

    def get_escalations_by_reason(self, reason: EscalationReason) -> List[Escalation]:
        """Get escalations of a specific type."""
        return [e for e in self.escalations.values()
                if e.reason == reason and not e.resolved]

    def _load_fix_templates(self) -> Dict[str, List[ManualStep]]:
        """Pre-defined fix instructions for common issues."""
        return {
            # API Key Issues
            "missing_polygon_api_key": [
                ManualStep(1, "Get a free API key from Polygon.io",
                          notes="Visit https://polygon.io and create an account"),
                ManualStep(2, "Copy your API key from the dashboard"),
                ManualStep(3, "Add to your .env file",
                          code_snippet='POLYGON_API_KEY=your_key_here',
                          file_to_edit='.env'),
                ManualStep(4, "Restart the application",
                          command='python run.py'),
            ],

            "missing_alpha_vantage_key": [
                ManualStep(1, "Get a free API key from Alpha Vantage",
                          notes="Visit https://www.alphavantage.co/support/#api-key"),
                ManualStep(2, "Add to your .env file",
                          code_snippet='ALPHA_VANTAGE_API_KEY=your_key_here',
                          file_to_edit='.env'),
            ],

            # Database Issues
            "database_connection_failed": [
                ManualStep(1, "Check if database file exists",
                          command='dir instance\\*.db'),
                ManualStep(2, "If missing, initialize the database",
                          command='python -c "from web.app import create_app; from web.extensions import db; app = create_app(); app.app_context().push(); db.create_all()"'),
                ManualStep(3, "Check DATABASE_URL in .env",
                          code_snippet='DATABASE_URL=sqlite:///instance/app.db',
                          file_to_edit='.env'),
            ],

            "database_migration_needed": [
                ManualStep(1, "Backup your current database",
                          command='copy instance\\app.db instance\\app.db.backup'),
                ManualStep(2, "Review the model changes in web/models/"),
                ManualStep(3, "Generate a migration",
                          command='flask db migrate -m "description"'),
                ManualStep(4, "Review the migration file in migrations/versions/"),
                ManualStep(5, "Apply the migration",
                          command='flask db upgrade'),
            ],

            # Security Issues
            "weak_secret_key": [
                ManualStep(1, "Generate a strong secret key",
                          command='python -c "import secrets; print(secrets.token_hex(32))"'),
                ManualStep(2, "Update SECRET_KEY in .env",
                          code_snippet='SECRET_KEY=your_generated_key_here',
                          file_to_edit='.env',
                          notes="NEVER commit this to git!"),
            ],

            "csrf_protection_disabled": [
                ManualStep(1, "Ensure Flask-WTF is installed",
                          command='pip install flask-wtf'),
                ManualStep(2, "Initialize CSRF protection in web/extensions.py",
                          code_snippet='from flask_wtf.csrf import CSRFProtect\ncsrf = CSRFProtect()',
                          file_to_edit='web/extensions.py'),
                ManualStep(3, "Initialize in create_app",
                          code_snippet='csrf.init_app(app)',
                          file_to_edit='web/app.py'),
            ],

            # Dependency Issues
            "missing_dependency": [
                ManualStep(1, "Install the missing package",
                          command='pip install {package_name}'),
                ManualStep(2, "Add to requirements.txt",
                          command='pip freeze | findstr {package_name} >> requirements.txt'),
            ],

            # Configuration Issues
            "debug_mode_in_production": [
                ManualStep(1, "Set DEBUG=False in production",
                          code_snippet='DEBUG=False\nFLASK_ENV=production',
                          file_to_edit='.env'),
                ManualStep(2, "Use environment variable",
                          code_snippet='DEBUG = os.getenv("DEBUG", "False").lower() == "true"',
                          file_to_edit='config.py'),
            ],

            # File Permission Issues
            "log_file_permission": [
                ManualStep(1, "Create logs directory if missing",
                          command='mkdir logs'),
                ManualStep(2, "Check directory permissions"),
            ],

            # External Service Issues
            "external_service_down": [
                ManualStep(1, "Check the service status page",
                          notes="Visit the service's status page"),
                ManualStep(2, "Try again later or use a backup service"),
                ManualStep(3, "Consider implementing offline fallback"),
            ],
        }

    def _get_template_steps(self, escalation: Escalation) -> List[ManualStep]:
        """Get template steps based on escalation type."""
        description_lower = escalation.description.lower()

        # Match known patterns
        if "polygon" in description_lower and "api" in description_lower:
            return self.fix_templates.get("missing_polygon_api_key", [])
        elif "alpha vantage" in description_lower:
            return self.fix_templates.get("missing_alpha_vantage_key", [])
        elif "database" in description_lower and "connection" in description_lower:
            return self.fix_templates.get("database_connection_failed", [])
        elif "migration" in description_lower:
            return self.fix_templates.get("database_migration_needed", [])
        elif "secret" in description_lower and "key" in description_lower:
            return self.fix_templates.get("weak_secret_key", [])
        elif "csrf" in description_lower:
            return self.fix_templates.get("csrf_protection_disabled", [])
        elif "debug" in description_lower and "production" in description_lower:
            return self.fix_templates.get("debug_mode_in_production", [])

        return []

    def get_stats(self) -> Dict[str, Any]:
        """Get escalation statistics."""
        all_escalations = list(self.escalations.values())
        pending = [e for e in all_escalations if not e.resolved]
        resolved = [e for e in all_escalations if e.resolved]

        return {
            "total": len(all_escalations),
            "pending": len(pending),
            "resolved": len(resolved),
            "by_priority": {
                "critical": len([e for e in pending if e.priority == EscalationPriority.CRITICAL]),
                "high": len([e for e in pending if e.priority == EscalationPriority.HIGH]),
                "medium": len([e for e in pending if e.priority == EscalationPriority.MEDIUM]),
                "low": len([e for e in pending if e.priority == EscalationPriority.LOW]),
            },
            "by_reason": {
                reason.value: len([e for e in pending if e.reason == reason])
                for reason in EscalationReason
            },
        }


# ============ Common Escalation Creators ============

def escalate_missing_api_key(api_name: str, source_agent: str) -> Escalation:
    """Create escalation for missing API key."""
    manager = EscalationManager.get_instance()

    api_instructions = {
        "polygon": {
            "url": "https://polygon.io",
            "env_var": "POLYGON_API_KEY",
            "steps": manager.fix_templates.get("missing_polygon_api_key", []),
        },
        "alpha_vantage": {
            "url": "https://www.alphavantage.co",
            "env_var": "ALPHA_VANTAGE_API_KEY",
            "steps": manager.fix_templates.get("missing_alpha_vantage_key", []),
        },
    }

    api_info = api_instructions.get(api_name.lower().replace(" ", "_"), {})

    return manager.create_escalation(
        title=f"Missing {api_name} API Key",
        description=f"The {api_name} API key is not configured. Market data features require this key.",
        reason=EscalationReason.REQUIRES_CREDENTIALS,
        priority=EscalationPriority.HIGH,
        source_agent=source_agent,
        affected_files=[".env"],
        why_not_auto="API keys contain sensitive credentials that only you can provide. "
                     f"Visit {api_info.get('url', 'the provider')} to get your key.",
        manual_steps=api_info.get("steps", []),
    )


def escalate_database_issue(issue_type: str, details: str, source_agent: str) -> Escalation:
    """Create escalation for database issues."""
    manager = EscalationManager.get_instance()

    if "migration" in issue_type.lower():
        template = "database_migration_needed"
        priority = EscalationPriority.HIGH
    else:
        template = "database_connection_failed"
        priority = EscalationPriority.CRITICAL

    return manager.create_escalation(
        title=f"Database Issue: {issue_type}",
        description=details,
        reason=EscalationReason.DATABASE_MIGRATION,
        priority=priority,
        source_agent=source_agent,
        affected_files=["instance/app.db", "migrations/"],
        why_not_auto="Database changes can cause data loss. Manual review ensures your data is safe.",
        manual_steps=manager.fix_templates.get(template, []),
    )


def escalate_security_issue(issue: str, file_path: str, source_agent: str) -> Escalation:
    """Create escalation for security issues."""
    manager = EscalationManager.get_instance()

    if "secret" in issue.lower():
        template = "weak_secret_key"
    elif "csrf" in issue.lower():
        template = "csrf_protection_disabled"
    elif "debug" in issue.lower():
        template = "debug_mode_in_production"
    else:
        template = None

    return manager.create_escalation(
        title=f"Security Issue: {issue}",
        description=f"A security vulnerability was detected in {file_path}",
        reason=EscalationReason.SECURITY_SENSITIVE,
        priority=EscalationPriority.CRITICAL,
        source_agent=source_agent,
        affected_files=[file_path],
        why_not_auto="Security changes require careful review to avoid breaking authentication or exposing data.",
        manual_steps=manager.fix_templates.get(template, []) if template else [],
    )


def escalate_complex_refactor(
    description: str,
    files: List[str],
    source_agent: str,
    suggested_approach: str = "",
) -> Escalation:
    """Create escalation for complex refactoring needs."""
    manager = EscalationManager.get_instance()

    steps = [
        ManualStep(1, "Review the affected files",
                  notes=f"Files: {', '.join(files[:5])}"),
        ManualStep(2, "Create a backup or git commit before changes"),
        ManualStep(3, "Plan the refactoring approach",
                  notes=suggested_approach if suggested_approach else "Consider the impact on dependent code"),
        ManualStep(4, "Implement changes incrementally"),
        ManualStep(5, "Test thoroughly after each change"),
    ]

    return manager.create_escalation(
        title="Complex Refactoring Needed",
        description=description,
        reason=EscalationReason.COMPLEX_REFACTOR,
        priority=EscalationPriority.MEDIUM,
        source_agent=source_agent,
        affected_files=files,
        why_not_auto="This refactoring affects multiple files and could break existing functionality. "
                     "It requires understanding the business logic and careful planning.",
        manual_steps=steps,
    )


def escalate_architecture_decision(
    question: str,
    options: List[str],
    source_agent: str,
) -> Escalation:
    """Create escalation when an architecture decision is needed."""
    manager = EscalationManager.get_instance()

    steps = [
        ManualStep(1, f"Consider the options: {', '.join(options)}"),
        ManualStep(2, "Evaluate trade-offs for your specific use case"),
        ManualStep(3, "Make a decision and document it"),
        ManualStep(4, "Implement the chosen approach"),
    ]

    return manager.create_escalation(
        title="Architecture Decision Required",
        description=question,
        reason=EscalationReason.REQUIRES_DECISION,
        priority=EscalationPriority.MEDIUM,
        source_agent=source_agent,
        why_not_auto="This requires understanding your specific requirements and preferences. "
                     "The agents cannot make business or architectural decisions for you.",
        manual_steps=steps,
    )

