"""
🔔 Notifier
Sends notifications via Discord, Slack, and Email.
"""
import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Try to import httpx or requests
try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False
    try:
        import requests
        HAS_REQUESTS = True
    except ImportError:
        HAS_REQUESTS = False


@dataclass
class NotificationConfig:
    """Notification configuration."""
    discord_webhook: str = ""
    slack_webhook: str = ""
    email_smtp_host: str = ""
    email_smtp_port: int = 587
    email_username: str = ""
    email_password: str = ""
    email_from: str = ""
    email_to: list = field(default_factory=list)


@dataclass
class Notification:
    """A notification to send."""
    title: str
    message: str
    severity: str = "info"  # info, warning, error, critical
    timestamp: str = ""
    source: str = "Ultimate Bot"


class Notifier:
    """
    Sends notifications via multiple channels.
    """

    def __init__(self, config: Optional[NotificationConfig] = None):
        self.config = config or self._load_config()
        self.sent_notifications: list[dict] = []

    def _load_config(self) -> NotificationConfig:
        """Load config from environment or config file."""
        config = NotificationConfig()

        # Try environment variables first
        config.discord_webhook = os.environ.get('DISCORD_WEBHOOK', '')
        config.slack_webhook = os.environ.get('SLACK_WEBHOOK', '')
        config.email_smtp_host = os.environ.get('SMTP_HOST', '')
        config.email_smtp_port = int(os.environ.get('SMTP_PORT', '587'))
        config.email_username = os.environ.get('SMTP_USERNAME', '')
        config.email_password = os.environ.get('SMTP_PASSWORD', '')
        config.email_from = os.environ.get('EMAIL_FROM', '')
        config.email_to = os.environ.get('EMAIL_TO', '').split(',') if os.environ.get('EMAIL_TO') else []

        # Try config file
        config_file = Path("config/notifications.json")
        if config_file.exists():
            try:
                data = json.loads(config_file.read_text())
                for key, value in data.items():
                    if hasattr(config, key) and not getattr(config, key):
                        setattr(config, key, value)
            except Exception as e:
                logger.error(f"Error loading notification config: {e}")

        return config

    def _get_severity_emoji(self, severity: str) -> str:
        """Get emoji for severity level."""
        return {
            'info': 'ℹ️',
            'warning': '⚠️',
            'error': '❌',
            'critical': '🚨'
        }.get(severity, 'ℹ️')

    def _get_severity_color(self, severity: str) -> int:
        """Get Discord color for severity level."""
        return {
            'info': 0x3498db,    # Blue
            'warning': 0xf39c12,  # Yellow
            'error': 0xe74c3c,    # Red
            'critical': 0x9b59b6  # Purple
        }.get(severity, 0x3498db)

    async def send_discord(self, notification: Notification) -> bool:
        """Send notification to Discord webhook."""
        if not self.config.discord_webhook:
            logger.debug("Discord webhook not configured")
            return False

        emoji = self._get_severity_emoji(notification.severity)
        color = self._get_severity_color(notification.severity)

        payload = {
            "embeds": [{
                "title": f"{emoji} {notification.title}",
                "description": notification.message,
                "color": color,
                "timestamp": notification.timestamp or datetime.now().isoformat(),
                "footer": {
                    "text": notification.source
                }
            }]
        }

        try:
            if HAS_HTTPX:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        self.config.discord_webhook,
                        json=payload,
                        timeout=10
                    )
                    return response.status_code == 204
            elif HAS_REQUESTS:
                import requests
                response = requests.post(
                    self.config.discord_webhook,
                    json=payload,
                    timeout=10
                )
                return response.status_code == 204
        except Exception as e:
            logger.error(f"Error sending Discord notification: {e}")

        return False

    async def send_slack(self, notification: Notification) -> bool:
        """Send notification to Slack webhook."""
        if not self.config.slack_webhook:
            logger.debug("Slack webhook not configured")
            return False

        emoji = self._get_severity_emoji(notification.severity)

        payload = {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{emoji} {notification.title}"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": notification.message
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Source:* {notification.source} | *Time:* {notification.timestamp or datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        }
                    ]
                }
            ]
        }

        try:
            if HAS_HTTPX:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        self.config.slack_webhook,
                        json=payload,
                        timeout=10
                    )
                    return response.status_code == 200
            elif HAS_REQUESTS:
                import requests
                response = requests.post(
                    self.config.slack_webhook,
                    json=payload,
                    timeout=10
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Error sending Slack notification: {e}")

        return False

    def send_email(self, notification: Notification) -> bool:
        """Send notification via email."""
        if not all([
            self.config.email_smtp_host,
            self.config.email_username,
            self.config.email_from,
            self.config.email_to
        ]):
            logger.debug("Email not configured")
            return False

        emoji = self._get_severity_emoji(notification.severity)

        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"[{notification.severity.upper()}] {notification.title}"
            msg['From'] = self.config.email_from
            msg['To'] = ', '.join(self.config.email_to)

            # Plain text version
            text = """
{emoji} {notification.title}

{notification.message}

---
Source: {notification.source}
Time: {notification.timestamp or datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

            # HTML version
            severity_colors = {
                'info': '#3498db',
                'warning': '#f39c12',
                'error': '#e74c3c',
                'critical': '#9b59b6'
            }
            color = severity_colors.get(notification.severity, '#3498db')

            html = """
<html>
<body style="font-family: Arial, sans-serif;">
    <div style="border-left: 4px solid {color}; padding-left: 15px;">
        <h2>{emoji} {notification.title}</h2>
        <p>{notification.message}</p>
        <hr>
        <small style="color: #666;">
            Source: {notification.source}<br>
            Time: {notification.timestamp or datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </small>
    </div>
</body>
</html>
"""

            msg.attach(MIMEText(text, 'plain'))
            msg.attach(MIMEText(html, 'html'))

            # Send email
            with smtplib.SMTP(self.config.email_smtp_host, self.config.email_smtp_port) as server:
                server.starttls()
                if self.config.email_password:
                    server.login(self.config.email_username, self.config.email_password)
                server.sendmail(
                    self.config.email_from,
                    self.config.email_to,
                    msg.as_string()
                )

            return True

        except Exception as e:
            logger.error(f"Error sending email: {e}")

        return False

    async def send(self, notification: Notification) -> dict:
        """Send notification to all configured channels."""
        results = {
            'discord': False,
            'slack': False,
            'email': False
        }

        notification.timestamp = notification.timestamp or datetime.now().isoformat()

        # Try all channels
        results['discord'] = await self.send_discord(notification)
        results['slack'] = await self.send_slack(notification)
        results['email'] = self.send_email(notification)

        # Record sent notification
        self.sent_notifications.append({
            'title': notification.title,
            'severity': notification.severity,
            'timestamp': notification.timestamp,
            'channels': results
        })

        return results

    async def send_alert(self, title: str, message: str, severity: str = "warning") -> dict:
        """Quick method to send an alert."""
        notification = Notification(
            title=title,
            message=message,
            severity=severity
        )
        return await self.send(notification)

    async def send_critical_alert(self, title: str, message: str) -> dict:
        """Send a critical alert."""
        return await self.send_alert(title, message, severity="critical")

    def get_status(self) -> dict:
        """Get notification system status."""
        return {
            'discord_configured': bool(self.config.discord_webhook),
            'slack_configured': bool(self.config.slack_webhook),
            'email_configured': bool(self.config.email_smtp_host and self.config.email_to),
            'notifications_sent': len(self.sent_notifications)
        }


# Singleton instance
_notifier: Optional[Notifier] = None

def get_notifier() -> Notifier:
    """Get or create notifier instance."""
    global _notifier
    if _notifier is None:
        _notifier = Notifier()
    return _notifier


