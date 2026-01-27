"""
Agent Notifications System
==========================

Send real-time notifications when agents detect issues.
Supports: WebSocket, Email, Slack, Discord
"""

import logging
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from enum import Enum
import asyncio

logger = logging.getLogger(__name__)


class NotificationChannel(Enum):
    """Available notification channels"""
    WEBSOCKET = "websocket"
    EMAIL = "email"
    SLACK = "slack"
    DISCORD = "discord"
    LOG = "log"


class NotificationPriority(Enum):
    """Priority levels for notifications"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AgentNotification:
    """A notification from an agent"""
    
    def __init__(
        self,
        agent_name: str,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        data: Optional[Dict[str, Any]] = None,
        channels: Optional[List[NotificationChannel]] = None
    ):
        self.agent_name = agent_name
        self.title = title
        self.message = message
        self.priority = priority
        self.data = data or {}
        self.channels = channels or [NotificationChannel.LOG]
        self.timestamp = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent": self.agent_name,
            "title": self.title,
            "message": self.message,
            "priority": self.priority.value,
            "data": self.data,
            "channels": [c.value for c in self.channels],
            "timestamp": self.timestamp.isoformat(),
        }


class NotificationManager:
    """
    Manages sending notifications across different channels.
    
    Usage:
        manager = NotificationManager()
        manager.add_handler(NotificationChannel.SLACK, slack_handler)
        await manager.notify(notification)
    """
    
    _instance = None
    
    def __init__(self):
        self._handlers: Dict[NotificationChannel, callable] = {}
        self._queue: List[AgentNotification] = []
        self._subscribers: List[callable] = []
        
        # Default log handler
        self.add_handler(NotificationChannel.LOG, self._log_handler)
    
    @classmethod
    def get_instance(cls) -> 'NotificationManager':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def add_handler(self, channel: NotificationChannel, handler: callable) -> None:
        """Add a notification handler for a channel."""
        self._handlers[channel] = handler
        logger.info(f"Added notification handler for {channel.value}")
    
    def subscribe(self, callback: callable) -> None:
        """Subscribe to all notifications."""
        self._subscribers.append(callback)
    
    async def notify(self, notification: AgentNotification) -> None:
        """Send a notification through all specified channels."""
        self._queue.append(notification)
        
        # Notify all subscribers
        for subscriber in self._subscribers:
            try:
                if asyncio.iscoroutinefunction(subscriber):
                    await subscriber(notification)
                else:
                    subscriber(notification)
            except Exception as e:
                logger.error(f"Subscriber error: {e}")
        
        # Send through each channel
        for channel in notification.channels:
            handler = self._handlers.get(channel)
            if handler:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(notification)
                    else:
                        handler(notification)
                except Exception as e:
                    logger.error(f"Handler error for {channel.value}: {e}")
    
    def _log_handler(self, notification: AgentNotification) -> None:
        """Default handler - log to console."""
        level = {
            NotificationPriority.LOW: logging.DEBUG,
            NotificationPriority.MEDIUM: logging.INFO,
            NotificationPriority.HIGH: logging.WARNING,
            NotificationPriority.CRITICAL: logging.ERROR,
        }.get(notification.priority, logging.INFO)
        
        logger.log(level, f"[{notification.agent_name}] {notification.title}: {notification.message}")
    
    def get_recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent notifications."""
        return [n.to_dict() for n in self._queue[-limit:]]


# Example handlers for different channels

async def slack_handler(notification: AgentNotification) -> None:
    """Send notification to Slack."""
    import os
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        return
    
    color = {
        NotificationPriority.LOW: "#36a64f",
        NotificationPriority.MEDIUM: "#439FE0",
        NotificationPriority.HIGH: "#FFA500",
        NotificationPriority.CRITICAL: "#FF0000",
    }.get(notification.priority, "#439FE0")
    
    payload = {
        "attachments": [{
            "color": color,
            "title": f"[{notification.agent_name.upper()}] {notification.title}",
            "text": notification.message,
            "footer": "Qunex Trade Agents",
            "ts": notification.timestamp.timestamp()
        }]
    }
    
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            await session.post(webhook_url, json=payload)
    except Exception as e:
        logger.error(f"Slack notification failed: {e}")


async def discord_handler(notification: AgentNotification) -> None:
    """Send notification to Discord."""
    import os
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        return
    
    color = {
        NotificationPriority.LOW: 0x36a64f,
        NotificationPriority.MEDIUM: 0x439FE0,
        NotificationPriority.HIGH: 0xFFA500,
        NotificationPriority.CRITICAL: 0xFF0000,
    }.get(notification.priority, 0x439FE0)
    
    payload = {
        "embeds": [{
            "title": f"[{notification.agent_name.upper()}] {notification.title}",
            "description": notification.message,
            "color": color,
            "footer": {"text": "Qunex Trade Agents"},
            "timestamp": notification.timestamp.isoformat()
        }]
    }
    
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            await session.post(webhook_url, json=payload)
    except Exception as e:
        logger.error(f"Discord notification failed: {e}")


async def email_handler(notification: AgentNotification) -> None:
    """Send notification via email."""
    # Only send for high priority
    if notification.priority not in [NotificationPriority.HIGH, NotificationPriority.CRITICAL]:
        return
    
    try:
        from flask_mail import Message
        from web.extensions import mail
        from web.app import create_app
        
        app = create_app()
        with app.app_context():
            msg = Message(
                subject=f"[ALERT] {notification.title}",
                recipients=["admin@example.com"],  # Configure this
                body=f"""
Agent Alert
===========

Agent: {notification.agent_name}
Priority: {notification.priority.value.upper()}
Time: {notification.timestamp.isoformat()}

Message:
{notification.message}

Data:
{json.dumps(notification.data, indent=2)}
                """
            )
            mail.send(msg)
    except Exception as e:
        logger.error(f"Email notification failed: {e}")


def setup_notifications():
    """Initialize notification handlers."""
    manager = NotificationManager.get_instance()
    
    # Add available handlers based on config
    import os
    
    if os.getenv("SLACK_WEBHOOK_URL"):
        manager.add_handler(NotificationChannel.SLACK, slack_handler)
    
    if os.getenv("DISCORD_WEBHOOK_URL"):
        manager.add_handler(NotificationChannel.DISCORD, discord_handler)
    
    # Email always available via Flask-Mail
    manager.add_handler(NotificationChannel.EMAIL, email_handler)
    
    return manager

