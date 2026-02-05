"""
📊 Resource Monitor
Monitors system resources like CPU, memory, and disk usage.
"""
import os
import time
import json
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Try to import psutil, fall back to basic monitoring if not available
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


@dataclass
class ResourceSnapshot:
    """Snapshot of system resources."""
    timestamp: str
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_used_gb: float = 0.0
    memory_total_gb: float = 0.0
    disk_percent: float = 0.0
    disk_used_gb: float = 0.0
    disk_total_gb: float = 0.0
    process_count: int = 0


@dataclass
class ResourceAlert:
    """Resource alert."""
    type: str  # cpu, memory, disk
    severity: str  # warning, critical
    message: str
    value: float
    threshold: float


class ResourceMonitor:
    """
    Monitors system resources and generates alerts.
    """

    # Thresholds
    THRESHOLDS = {
        'cpu': {'warning': 70, 'critical': 90},
        'memory': {'warning': 80, 'critical': 95},
        'disk': {'warning': 80, 'critical': 95}
    }

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path("data/monitoring")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.data_dir / "resource_history.json"
        self.history: list[dict] = self._load_history()
        self.alerts: list[ResourceAlert] = []

    def _load_history(self) -> list:
        """Load resource history."""
        if self.history_file.exists():
            try:
                return json.loads(self.history_file.read_text())
            except Exception:
                pass
        return []

    def _save_history(self):
        """Save resource history."""
        try:
            # Keep only last 1000 entries
            self.history = self.history[-1000:]
            self.history_file.write_text(json.dumps(self.history, indent=2))
        except Exception as e:
            logger.error(f"Error saving resource history: {e}")

    def get_snapshot(self) -> ResourceSnapshot:
        """Get current resource snapshot."""
        snapshot = ResourceSnapshot(
            timestamp=datetime.now().isoformat()
        )

        if HAS_PSUTIL:
            try:
                # CPU
                snapshot.cpu_percent = psutil.cpu_percent(interval=0.1)

                # Memory
                mem = psutil.virtual_memory()
                snapshot.memory_percent = mem.percent
                snapshot.memory_used_gb = mem.used / (1024**3)
                snapshot.memory_total_gb = mem.total / (1024**3)

                # Disk
                disk = psutil.disk_usage('/')
                snapshot.disk_percent = disk.percent
                snapshot.disk_used_gb = disk.used / (1024**3)
                snapshot.disk_total_gb = disk.total / (1024**3)

                # Process count
                snapshot.process_count = len(psutil.pids())

            except Exception as e:
                logger.error(f"Error getting resource info: {e}")
        else:
            # Basic fallback without psutil
            try:
                # Try to get disk usage with os
                import shutil
                total, used, free = shutil.disk_usage('/')
                snapshot.disk_total_gb = total / (1024**3)
                snapshot.disk_used_gb = used / (1024**3)
                snapshot.disk_percent = (used / total) * 100
            except Exception:
                pass

        return snapshot

    def check_alerts(self, snapshot: ResourceSnapshot) -> list:
        """Check for resource alerts."""
        alerts = []

        # CPU alert
        if snapshot.cpu_percent >= self.THRESHOLDS['cpu']['critical']:
            alerts.append(ResourceAlert(
                type='cpu',
                severity='critical',
                message=f'CPU usage critical: {snapshot.cpu_percent:.1f}%',
                value=snapshot.cpu_percent,
                threshold=self.THRESHOLDS['cpu']['critical']
            ))
        elif snapshot.cpu_percent >= self.THRESHOLDS['cpu']['warning']:
            alerts.append(ResourceAlert(
                type='cpu',
                severity='warning',
                message=f'CPU usage high: {snapshot.cpu_percent:.1f}%',
                value=snapshot.cpu_percent,
                threshold=self.THRESHOLDS['cpu']['warning']
            ))

        # Memory alert
        if snapshot.memory_percent >= self.THRESHOLDS['memory']['critical']:
            alerts.append(ResourceAlert(
                type='memory',
                severity='critical',
                message=f'Memory usage critical: {snapshot.memory_percent:.1f}%',
                value=snapshot.memory_percent,
                threshold=self.THRESHOLDS['memory']['critical']
            ))
        elif snapshot.memory_percent >= self.THRESHOLDS['memory']['warning']:
            alerts.append(ResourceAlert(
                type='memory',
                severity='warning',
                message=f'Memory usage high: {snapshot.memory_percent:.1f}%',
                value=snapshot.memory_percent,
                threshold=self.THRESHOLDS['memory']['warning']
            ))

        # Disk alert
        if snapshot.disk_percent >= self.THRESHOLDS['disk']['critical']:
            alerts.append(ResourceAlert(
                type='disk',
                severity='critical',
                message=f'Disk usage critical: {snapshot.disk_percent:.1f}%',
                value=snapshot.disk_percent,
                threshold=self.THRESHOLDS['disk']['critical']
            ))
        elif snapshot.disk_percent >= self.THRESHOLDS['disk']['warning']:
            alerts.append(ResourceAlert(
                type='disk',
                severity='warning',
                message=f'Disk usage high: {snapshot.disk_percent:.1f}%',
                value=snapshot.disk_percent,
                threshold=self.THRESHOLDS['disk']['warning']
            ))

        self.alerts = alerts
        return alerts

    def monitor(self) -> dict:
        """Perform monitoring check."""
        snapshot = self.get_snapshot()
        alerts = self.check_alerts(snapshot)

        # Record in history
        self.history.append({
            'timestamp': snapshot.timestamp,
            'cpu': snapshot.cpu_percent,
            'memory': snapshot.memory_percent,
            'disk': snapshot.disk_percent
        })
        self._save_history()

        return {
            'snapshot': snapshot,
            'alerts': alerts,
            'status': 'critical' if any(a.severity == 'critical' for a in alerts) else
                      'warning' if alerts else 'healthy'
        }

    def get_trends(self, hours: int = 24) -> dict:
        """Get resource trends for specified hours."""
        if not self.history:
            return {'status': 'no_data'}

        # Filter to recent entries
        cutoff = datetime.now().timestamp() - (hours * 3600)
        recent = []

        for entry in self.history:
            try:
                ts = datetime.fromisoformat(entry['timestamp']).timestamp()
                if ts >= cutoff:
                    recent.append(entry)
            except Exception:
                pass

        if not recent:
            return {'status': 'no_recent_data'}

        # Calculate averages
        avg_cpu = sum(e.get('cpu', 0) for e in recent) / len(recent)
        avg_memory = sum(e.get('memory', 0) for e in recent) / len(recent)
        avg_disk = sum(e.get('disk', 0) for e in recent) / len(recent)

        # Find peaks
        max_cpu = max(e.get('cpu', 0) for e in recent)
        max_memory = max(e.get('memory', 0) for e in recent)

        return {
            'status': 'ok',
            'period_hours': hours,
            'data_points': len(recent),
            'averages': {
                'cpu': round(avg_cpu, 1),
                'memory': round(avg_memory, 1),
                'disk': round(avg_disk, 1)
            },
            'peaks': {
                'cpu': round(max_cpu, 1),
                'memory': round(max_memory, 1)
            }
        }

    def generate_report(self, output_path: Optional[Path] = None) -> str:
        """Generate resource monitoring report."""
        output = output_path or Path("reports/resource_monitor.md")
        output.parent.mkdir(parents=True, exist_ok=True)

        snapshot = self.get_snapshot()
        trends = self.get_trends(24)
        alerts = self.check_alerts(snapshot)

        # Status emoji
        if any(a.severity == 'critical' for a in alerts):
            status_emoji = "🔴"
            status_text = "CRITICAL"
        elif alerts:
            status_emoji = "🟠"
            status_text = "WARNING"
        else:
            status_emoji = "🟢"
            status_text = "HEALTHY"

        report = """# 📊 Resource Monitor Report

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## System Status: {status_emoji} {status_text}

## Current Usage

| Resource | Usage | Status |
|----------|-------|--------|
| CPU | {snapshot.cpu_percent:.1f}% | {'🔴' if snapshot.cpu_percent > 90 else '🟠' if snapshot.cpu_percent > 70 else '🟢'} |
| Memory | {snapshot.memory_percent:.1f}% ({snapshot.memory_used_gb:.1f}/{snapshot.memory_total_gb:.1f} GB) | {'🔴' if snapshot.memory_percent > 95 else '🟠' if snapshot.memory_percent > 80 else '🟢'} |
| Disk | {snapshot.disk_percent:.1f}% ({snapshot.disk_used_gb:.1f}/{snapshot.disk_total_gb:.1f} GB) | {'🔴' if snapshot.disk_percent > 95 else '🟠' if snapshot.disk_percent > 80 else '🟢'} |

"""
        # Alerts section
        if alerts:
            report += "## ⚠️ Active Alerts\n\n"
            for alert in alerts:
                icon = "🔴" if alert.severity == 'critical' else "🟠"
                report += f"- {icon} {alert.message}\n"
        else:
            report += "## ✅ No Active Alerts\n\n"

        # Trends section
        if trends.get('status') == 'ok':
            avgs = trends['averages']
            peaks = trends['peaks']

            report += """## 24-Hour Trends

| Metric | Average | Peak |
|--------|---------|------|
| CPU | {avgs['cpu']:.1f}% | {peaks['cpu']:.1f}% |
| Memory | {avgs['memory']:.1f}% | {peaks['memory']:.1f}% |
| Disk | {avgs['disk']:.1f}% | - |

Data points: {trends['data_points']}
"""

        report += "\n---\n*Report generated by Resource Monitor*\n"

        output.write_text(report, encoding='utf-8')
        return str(output)


# Singleton instance
_monitor: Optional[ResourceMonitor] = None

def get_resource_monitor() -> ResourceMonitor:
    """Get or create resource monitor instance."""
    global _monitor
    if _monitor is None:
        _monitor = ResourceMonitor()
    return _monitor


