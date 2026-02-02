"""
Expert Communication System
===========================

Enables expert bots to communicate with each other for collaboration.

Example conversations:
- Fixer → Security: "I fixed the SQL injection, please verify"
- Developer → Tester: "New feature added, please run tests"
- Analyzer → Fixer: "Found complexity issue in auth.py, please optimize"
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import json
from typing import List
from typing import Optional
from typing import Any

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Types of messages between experts."""
    REQUEST = "request"       # Asking another expert to do something
    RESPONSE = "response"     # Responding to a request
    NOTIFY = "notify"         # Just informing
    VERIFY = "verify"         # Asking to verify work
    APPROVAL = "approval"     # Approving work
    REJECTION = "rejection"   # Rejecting work with feedback
    ESCALATE = "escalate"     # Escalating to Ultimate Bot


class MessagePriority(Enum):
    """Message priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class ExpertMessage:
    """A message between experts."""
    id: str
    from_expert: str
    to_expert: str
    message_type: MessageType
    subject: str
    content: str
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: datetime = field(default_factory=datetime.now)
    context: Dict[str, Any] = field(default_factory=dict)
    read: bool = False
    response_to: Optional[str] = None  # ID of message this responds to


@dataclass
class Conversation:
    """A conversation thread between experts."""
    id: str
    participants: List[str]
    subject: str
    messages: List[ExpertMessage] = field(default_factory=list)
    status: str = "open"  # open, resolved, escalated
    created_at: datetime = field(default_factory=datetime.now)


class ExpertCommunicationHub:
    """
    Central hub for expert communication.

    All experts communicate through this hub.
    The Ultimate Bot monitors all communications.
    """

    def __init__(self):
        self.messages: List[ExpertMessage] = []
        self.conversations: Dict[str, Conversation] = {}
        self.message_counter = 0
        self.conversation_counter = 0
        self.data_dir = Path("data/expert_comm")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Communication templates
        self.templates = {
            "verify_fix": "I've fixed {issue} in {file}. Please verify the fix is correct.",
            "request_review": "Please review my changes to {file}. Changes: {changes}",
            "report_issue": "Found {severity} issue in {file}: {description}",
            "test_request": "New code added to {file}. Please run tests.",
            "security_check": "Please perform security audit on {file}",
            "approval": "Approved. {feedback}",
            "rejection": "Rejected. Reason: {reason}. Suggested fix: {suggestion}",
        }

        self._load_history()

    def _load_history(self):
        """Load communication history."""
        history_file = self.data_dir / "history.json"
        if history_file.exists():
            try:
                with open(history_file, 'r') as f:
                    data = json.load(f)
                    self.message_counter = data.get('message_counter', 0)
                    self.conversation_counter = data.get('conversation_counter', 0)
            except Exception:
                pass

    def _save_history(self):
        """Save communication history."""
        history_file = self.data_dir / "history.json"
        try:
            data = {
                'message_counter': self.message_counter,
                'conversation_counter': self.conversation_counter,
                'last_save': datetime.now().isoformat()
            }
            with open(history_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save history: {e}")

    def send_message(
        self,
        from_expert: str,
        to_expert: str,
        message_type: MessageType,
        subject: str,
        content: str,
        priority: MessagePriority = MessagePriority.NORMAL,
        context: Dict[str, Any] = None
    ) -> ExpertMessage:
        """Send a message from one expert to another."""
        self.message_counter += 1

        message = ExpertMessage(
            id=f"MSG-{self.message_counter:05d}",
            from_expert=from_expert,
            to_expert=to_expert,
            message_type=message_type,
            subject=subject,
            content=content,
            priority=priority,
            context=context or {}
        )

        self.messages.append(message)
        self._save_history()

        logger.info(f"[COMM] {from_expert} → {to_expert}: {subject}")

        return message

    def request_verification(
        self,
        from_expert: str,
        to_expert: str,
        file_path: str,
        issue: str,
        fix_description: str
    ) -> ExpertMessage:
        """Request another expert to verify a fix."""
        content = self.templates["verify_fix"].format(
            issue=issue,
            file=file_path
        )
        content += f"\n\nFix details:\n{fix_description}"

        return self.send_message(
            from_expert=from_expert,
            to_expert=to_expert,
            message_type=MessageType.VERIFY,
            subject=f"Verify fix: {issue[:30]}",
            content=content,
            priority=MessagePriority.HIGH,
            context={
                'file_path': file_path,
                'issue': issue,
                'fix': fix_description
            }
        )

    def request_review(
        self,
        from_expert: str,
        to_expert: str,
        file_path: str,
        changes: str
    ) -> ExpertMessage:
        """Request a code review."""
        content = self.templates["request_review"].format(
            file=file_path,
            changes=changes
        )

        return self.send_message(
            from_expert=from_expert,
            to_expert=to_expert,
            message_type=MessageType.REQUEST,
            subject=f"Review request: {file_path}",
            content=content,
            context={'file_path': file_path, 'changes': changes}
        )

    def report_issue(
        self,
        from_expert: str,
        to_expert: str,
        file_path: str,
        severity: str,
        description: str
    ) -> ExpertMessage:
        """Report an issue to another expert."""
        content = self.templates["report_issue"].format(
            severity=severity,
            file=file_path,
            description=description
        )

        priority = {
            'critical': MessagePriority.URGENT,
            'high': MessagePriority.HIGH,
            'medium': MessagePriority.NORMAL,
            'low': MessagePriority.LOW
        }.get(severity.lower(), MessagePriority.NORMAL)

        return self.send_message(
            from_expert=from_expert,
            to_expert=to_expert,
            message_type=MessageType.NOTIFY,
            subject=f"[{severity.upper()}] Issue in {file_path}",
            content=content,
            priority=priority,
            context={'file_path': file_path, 'severity': severity}
        )

    def approve(
        self,
        from_expert: str,
        original_message: ExpertMessage,
        feedback: str = "Looks good!"
    ) -> ExpertMessage:
        """Approve work done by another expert."""
        content = self.templates["approval"].format(feedback=feedback)

        return self.send_message(
            from_expert=from_expert,
            to_expert=original_message.from_expert,
            message_type=MessageType.APPROVAL,
            subject=f"Approved: {original_message.subject}",
            content=content,
            context={'original_message_id': original_message.id}
        )

    def reject(
        self,
        from_expert: str,
        original_message: ExpertMessage,
        reason: str,
        suggestion: str = ""
    ) -> ExpertMessage:
        """Reject work with feedback."""
        content = self.templates["rejection"].format(
            reason=reason,
            suggestion=suggestion or "Please review and try again."
        )

        return self.send_message(
            from_expert=from_expert,
            to_expert=original_message.from_expert,
            message_type=MessageType.REJECTION,
            subject=f"Rejected: {original_message.subject}",
            content=content,
            priority=MessagePriority.HIGH,
            context={
                'original_message_id': original_message.id,
                'reason': reason
            }
        )

    def escalate_to_ultimate(
        self,
        from_expert: str,
        subject: str,
        description: str,
        context: Dict[str, Any] = None
    ) -> ExpertMessage:
        """Escalate an issue to the Ultimate Bot."""
        return self.send_message(
            from_expert=from_expert,
            to_expert="ultimate_bot",
            message_type=MessageType.ESCALATE,
            subject=f"[ESCALATION] {subject}",
            content=description,
            priority=MessagePriority.URGENT,
            context=context or {}
        )

    def get_inbox(self, expert_id: str, unread_only: bool = False) -> List[ExpertMessage]:
        """Get messages for an expert."""
        messages = [m for m in self.messages if m.to_expert == expert_id]
        if unread_only:
            messages = [m for m in messages if not m.read]
        return sorted(messages, key=lambda m: m.timestamp, reverse=True)

    def get_sent(self, expert_id: str) -> List[ExpertMessage]:
        """Get messages sent by an expert."""
        return sorted(
            [m for m in self.messages if m.from_expert == expert_id],
            key=lambda m: m.timestamp,
            reverse=True
        )

    def mark_read(self, message_id: str):
        """Mark a message as read."""
        for msg in self.messages:
            if msg.id == message_id:
                msg.read = True
                break

    def get_escalations(self) -> List[ExpertMessage]:
        """Get all escalations to Ultimate Bot."""
        return [
            m for m in self.messages
            if m.message_type == MessageType.ESCALATE
        ]

    def get_pending_verifications(self, expert_id: str) -> List[ExpertMessage]:
        """Get pending verification requests for an expert."""
        return [
            m for m in self.messages
            if m.to_expert == expert_id
            and m.message_type == MessageType.VERIFY
            and not m.read
        ]

    def get_communication_summary(self) -> Dict[str, Any]:
        """Get summary of all communications."""
        return {
            'total_messages': len(self.messages),
            'unread_count': len([m for m in self.messages if not m.read]),
            'escalations': len([m for m in self.messages if m.message_type == MessageType.ESCALATE]),
            'pending_verifications': len([m for m in self.messages if m.message_type == MessageType.VERIFY and not m.read]),
            'by_type': {
                t.value: len([m for m in self.messages if m.message_type == t])
                for t in MessageType
            }
        }


# Singleton instance
_comm_hub: Optional[ExpertCommunicationHub] = None


def get_comm_hub() -> ExpertCommunicationHub:
    """Get the communication hub singleton."""
    global _comm_hub
    if _comm_hub is None:
        _comm_hub = ExpertCommunicationHub()
    return _comm_hub

