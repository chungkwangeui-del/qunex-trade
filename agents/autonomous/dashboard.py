"""
📊 Web Dashboard
Real-time monitoring dashboard for Ultimate Bot.
"""
import json
import asyncio
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Try to import Flask
try:
    from flask import Flask, render_template_string, jsonify, request
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False


@dataclass
class DashboardData:
    """Data for dashboard display."""
    status: str = "unknown"
    cycle_count: int = 0
    uptime_hours: float = 0
    total_fixes: int = 0
    total_issues: int = 0
    health_score: float = 0
    active_bots: int = 0
    total_bots: int = 8
    recent_activity: list = None
    trends: dict = None
    alerts: list = None

    def __post_init__(self):
        if self.recent_activity is None:
            self.recent_activity = []
        if self.trends is None:
            self.trends = {}
        if self.alerts is None:
            self.alerts = []


DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🤖 Ultimate Bot Dashboard</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');

        :root {
            --bg-primary: #0a0a0f;
            --bg-secondary: #12121a;
            --bg-card: #1a1a24;
            --accent-cyan: #00f5ff;
            --accent-purple: #a855f7;
            --accent-green: #10b981;
            --accent-red: #ef4444;
            --accent-yellow: #f59e0b;
            --text-primary: #f0f0f0;
            --text-secondary: #888;
            --border-color: #2a2a3a;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Space Grotesk', sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            background-image:
                radial-gradient(circle at 20% 80%, rgba(168, 85, 247, 0.1) 0%, transparent 50%),
                radial-gradient(circle at 80% 20%, rgba(0, 245, 255, 0.1) 0%, transparent 50%);
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--border-color);
        }

        .logo {
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        .logo-icon {
            font-size: 2.5rem;
        }

        .logo h1 {
            font-size: 1.8rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .status-badge {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 1rem;
            border-radius: 2rem;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.9rem;
        }

        .status-badge.healthy {
            background: rgba(16, 185, 129, 0.2);
            border: 1px solid var(--accent-green);
            color: var(--accent-green);
        }

        .status-badge.warning {
            background: rgba(245, 158, 11, 0.2);
            border: 1px solid var(--accent-yellow);
            color: var(--accent-yellow);
        }

        .status-badge.error {
            background: rgba(239, 68, 68, 0.2);
            border: 1px solid var(--accent-red);
            color: var(--accent-red);
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }

        .status-dot.healthy { background: var(--accent-green); }
        .status-dot.warning { background: var(--accent-yellow); }
        .status-dot.error { background: var(--accent-red); }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }

        .card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 1rem;
            padding: 1.5rem;
            transition: transform 0.3s, box-shadow 0.3s;
        }

        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 40px rgba(0, 245, 255, 0.1);
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }

        .card-title {
            font-size: 0.9rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .card-icon {
            font-size: 1.5rem;
        }

        .card-value {
            font-size: 2.5rem;
            font-weight: 700;
            font-family: 'JetBrains Mono', monospace;
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .card-subtext {
            font-size: 0.85rem;
            color: var(--text-secondary);
            margin-top: 0.5rem;
        }

        .section-title {
            font-size: 1.2rem;
            font-weight: 600;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .bots-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 1rem;
        }

        .bot-card {
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 0.75rem;
            padding: 1rem;
            text-align: center;
            transition: all 0.3s;
        }

        .bot-card:hover {
            border-color: var(--accent-cyan);
        }

        .bot-card.active {
            border-color: var(--accent-green);
            box-shadow: 0 0 20px rgba(16, 185, 129, 0.2);
        }

        .bot-icon {
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }

        .bot-name {
            font-weight: 600;
            margin-bottom: 0.25rem;
        }

        .bot-status {
            font-size: 0.75rem;
            color: var(--text-secondary);
        }

        .activity-list {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 1rem;
            padding: 1.5rem;
        }

        .activity-item {
            display: flex;
            align-items: center;
            gap: 1rem;
            padding: 0.75rem 0;
            border-bottom: 1px solid var(--border-color);
        }

        .activity-item:last-child {
            border-bottom: none;
        }

        .activity-icon {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1rem;
        }

        .activity-icon.fix { background: rgba(16, 185, 129, 0.2); }
        .activity-icon.alert { background: rgba(239, 68, 68, 0.2); }
        .activity-icon.scan { background: rgba(0, 245, 255, 0.2); }

        .activity-content {
            flex: 1;
        }

        .activity-text {
            font-size: 0.9rem;
        }

        .activity-time {
            font-size: 0.75rem;
            color: var(--text-secondary);
            font-family: 'JetBrains Mono', monospace;
        }

        .alerts-section {
            margin-top: 2rem;
        }

        .alert {
            display: flex;
            align-items: center;
            gap: 1rem;
            padding: 1rem;
            border-radius: 0.5rem;
            margin-bottom: 0.5rem;
        }

        .alert.critical {
            background: rgba(239, 68, 68, 0.15);
            border-left: 4px solid var(--accent-red);
        }

        .alert.warning {
            background: rgba(245, 158, 11, 0.15);
            border-left: 4px solid var(--accent-yellow);
        }

        .refresh-btn {
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple));
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 0.5rem;
            color: var(--bg-primary);
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }

        .refresh-btn:hover {
            transform: scale(1.05);
            box-shadow: 0 5px 20px rgba(0, 245, 255, 0.3);
        }

        footer {
            text-align: center;
            padding: 2rem;
            color: var(--text-secondary);
            font-size: 0.85rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo">
                <span class="logo-icon">🤖👑</span>
                <h1>ULTIMATE BOT</h1>
            </div>
            <div class="status-badge {{ 'healthy' if data.status == 'running' else 'warning' if data.status == 'idle' else 'error' }}">
                <span class="status-dot {{ 'healthy' if data.status == 'running' else 'warning' if data.status == 'idle' else 'error' }}"></span>
                {{ data.status.upper() }}
            </div>
        </header>

        <div class="grid">
            <div class="card">
                <div class="card-header">
                    <span class="card-title">Cycle Count</span>
                    <span class="card-icon">🔄</span>
                </div>
                <div class="card-value">{{ data.cycle_count }}</div>
                <div class="card-subtext">Total cycles completed</div>
            </div>

            <div class="card">
                <div class="card-header">
                    <span class="card-title">Uptime</span>
                    <span class="card-icon">⏱️</span>
                </div>
                <div class="card-value">{{ "%.1f"|format(data.uptime_hours) }}h</div>
                <div class="card-subtext">Hours running</div>
            </div>

            <div class="card">
                <div class="card-header">
                    <span class="card-title">Auto Fixes</span>
                    <span class="card-icon">🔧</span>
                </div>
                <div class="card-value">{{ data.total_fixes }}</div>
                <div class="card-subtext">Issues fixed automatically</div>
            </div>

            <div class="card">
                <div class="card-header">
                    <span class="card-title">Health Score</span>
                    <span class="card-icon">💚</span>
                </div>
                <div class="card-value">{{ "%.0f"|format(data.health_score) }}%</div>
                <div class="card-subtext">Codebase health</div>
            </div>
        </div>

        <section>
            <h2 class="section-title">🤖 Expert Bots</h2>
            <div class="bots-grid">
                <div class="bot-card active">
                    <div class="bot-icon">🛠️</div>
                    <div class="bot-name">Fixer</div>
                    <div class="bot-status">Active</div>
                </div>
                <div class="bot-card">
                    <div class="bot-icon">👨‍💻</div>
                    <div class="bot-name">Developer</div>
                    <div class="bot-status">Standby</div>
                </div>
                <div class="bot-card active">
                    <div class="bot-icon">🔬</div>
                    <div class="bot-name">Analyzer</div>
                    <div class="bot-status">Active</div>
                </div>
                <div class="bot-card active">
                    <div class="bot-icon">🔒</div>
                    <div class="bot-name">Security</div>
                    <div class="bot-status">Active</div>
                </div>
                <div class="bot-card">
                    <div class="bot-icon">🔄</div>
                    <div class="bot-name">Git</div>
                    <div class="bot-status">Standby</div>
                </div>
                <div class="bot-card">
                    <div class="bot-icon">📊</div>
                    <div class="bot-name">Deploy</div>
                    <div class="bot-status">Standby</div>
                </div>
                <div class="bot-card">
                    <div class="bot-icon">🧪</div>
                    <div class="bot-name">Tester</div>
                    <div class="bot-status">Standby</div>
                </div>
                <div class="bot-card">
                    <div class="bot-icon">⚡</div>
                    <div class="bot-name">Healer</div>
                    <div class="bot-status">Standby</div>
                </div>
            </div>
        </section>

        <section class="alerts-section">
            <h2 class="section-title">📋 Recent Activity</h2>
            <div class="activity-list">
                {% for activity in data.recent_activity[:10] %}
                <div class="activity-item">
                    <div class="activity-icon {{ activity.type }}">
                        {% if activity.type == 'fix' %}✅{% elif activity.type == 'alert' %}⚠️{% else %}🔍{% endif %}
                    </div>
                    <div class="activity-content">
                        <div class="activity-text">{{ activity.message }}</div>
                        <div class="activity-time">{{ activity.time }}</div>
                    </div>
                </div>
                {% else %}
                <div class="activity-item">
                    <div class="activity-content">
                        <div class="activity-text">No recent activity</div>
                    </div>
                </div>
                {% endfor %}
            </div>
        </section>

        {% if data.alerts %}
        <section class="alerts-section">
            <h2 class="section-title">🚨 Active Alerts</h2>
            {% for alert in data.alerts %}
            <div class="alert {{ alert.severity }}">
                <span>{% if alert.severity == 'critical' %}🔴{% else %}🟠{% endif %}</span>
                <span>{{ alert.message }}</span>
            </div>
            {% endfor %}
        </section>
        {% endif %}

        <footer>
            <button class="refresh-btn" onclick="location.reload()">🔄 Refresh</button>
            <p style="margin-top: 1rem;">Ultimate Bot Dashboard • Auto-refreshes every 30 seconds</p>
        </footer>
    </div>

    <script>
        // Auto-refresh every 30 seconds
        setTimeout(() => location.reload(), 30000);
    </script>
</body>
</html>
"""


class Dashboard:
    """
    Web dashboard for monitoring Ultimate Bot.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 5050):
        self.host = host
        self.port = port
        self.data = DashboardData()
        self.app = None
        self._running = False

        if HAS_FLASK:
            self._setup_flask()

    def _setup_flask(self):
        """Setup Flask application."""
        self.app = Flask(__name__)

        @self.app.route('/')
        def index():
            return render_template_string(DASHBOARD_HTML, data=self.data)

        @self.app.route('/api/status')
        def api_status():
            return jsonify(asdict(self.data))

        @self.app.route('/api/update', methods=['POST'])
        def api_update():
            try:
                update_data = request.json
                for key, value in update_data.items():
                    if hasattr(self.data, key):
                        setattr(self.data, key, value)
                return jsonify({'status': 'ok'})
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 400

    def update(self, **kwargs):
        """Update dashboard data."""
        for key, value in kwargs.items():
            if hasattr(self.data, key):
                setattr(self.data, key, value)

    def add_activity(self, activity_type: str, message: str):
        """Add activity to recent activity list."""
        activity = {
            'type': activity_type,
            'message': message,
            'time': datetime.now().strftime('%H:%M:%S')
        }
        self.data.recent_activity.insert(0, activity)
        self.data.recent_activity = self.data.recent_activity[:50]  # Keep last 50

    def add_alert(self, message: str, severity: str = "warning"):
        """Add an alert."""
        self.data.alerts.append({
            'message': message,
            'severity': severity,
            'time': datetime.now().isoformat()
        })

    def clear_alerts(self):
        """Clear all alerts."""
        self.data.alerts = []

    def run(self, threaded: bool = True):
        """Start the dashboard server."""
        if not HAS_FLASK:
            logger.warning("Flask not installed. Dashboard unavailable.")
            print("  Dashboard requires Flask: pip install flask")
            return False

        try:
            print(f"  Dashboard starting at http://{self.host}:{self.port}")
            self._running = True

            if threaded:
                import threading
                thread = threading.Thread(
                    target=self.app.run,
                    kwargs={
                        'host': self.host,
                        'port': self.port,
                        'debug': False,
                        'use_reloader': False
                    },
                    daemon=True
                )
                thread.start()
            else:
                self.app.run(
                    host=self.host,
                    port=self.port,
                    debug=False
                )

            return True

        except Exception as e:
            logger.error(f"Dashboard error: {e}")
            print(f"  Dashboard failed to start: {e}")
            return False

    def stop(self):
        """Stop the dashboard server."""
        self._running = False

    @property
    def is_running(self) -> bool:
        """Check if dashboard is running."""
        return self._running

    def generate_static_report(self, output_path: Optional[Path] = None) -> str:
        """Generate a static HTML report."""
        output = output_path or Path("reports/dashboard_snapshot.html")
        output.parent.mkdir(parents=True, exist_ok=True)

        if HAS_FLASK:
            # Use Jinja2 to render
            from jinja2 import Template
            template = Template(DASHBOARD_HTML)
            html = template.render(data=self.data)
        else:
            # Simple string replacement
            html = DASHBOARD_HTML.replace('{{ data.status }}', self.data.status)
            html = html.replace('{{ data.cycle_count }}', str(self.data.cycle_count))

        output.write_text(html, encoding='utf-8')
        return str(output)


# Singleton instance
_dashboard: Optional[Dashboard] = None

def get_dashboard(host: str = "127.0.0.1", port: int = 5050) -> Dashboard:
    """Get or create dashboard instance."""
    global _dashboard
    if _dashboard is None:
        _dashboard = Dashboard(host, port)
    return _dashboard


