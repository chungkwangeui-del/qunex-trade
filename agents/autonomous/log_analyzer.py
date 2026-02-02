"""
Log Analyzer Agent
==================

Monitors application logs for errors, patterns, and anomalies.
Automatically detects and reports issues from runtime errors.
"""

import os
import re
import logging
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
import json
from datetime import timedelta
from typing import List
from typing import Optional
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class LogEntry:
    """Parsed log entry."""
    timestamp: datetime
    level: str  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    message: str
    source: str  # file/module
    line_number: Optional[int] = None
    traceback: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LogPattern:
    """Detected pattern in logs."""
    pattern: str
    count: int
    first_seen: datetime
    last_seen: datetime
    severity: str
    category: str  # 'error', 'security', 'performance', 'api'
    examples: List[str] = field(default_factory=list)


@dataclass
class LogAlert:
    """Alert generated from log analysis."""
    id: str
    timestamp: datetime
    severity: str  # 'info', 'warning', 'error', 'critical'
    title: str
    message: str
    pattern: Optional[str] = None
    count: int = 1
    suggested_action: Optional[str] = None
    auto_fixable: bool = False


class LogAnalyzer:
    """
    Real-time log monitoring and analysis.

    Features:
    - Parse multiple log formats
    - Detect error patterns
    - Track frequency/trends
    - Generate alerts
    - Suggest fixes
    """

    # Common log patterns
    LOG_PATTERNS = {
        'error': [
            r'(?i)error|exception|failed|failure|traceback',
        ],
        'security': [
            r'(?i)unauthorized|forbidden|invalid.?token|auth.?fail',
            r'(?i)sql.?injection|xss|csrf',
            r'(?i)brute.?force|too.?many.?requests|rate.?limit',
        ],
        'performance': [
            r'(?i)timeout|slow.?query|high.?cpu|memory.?leak',
            r'(?i)connection.?pool|deadlock',
        ],
        'api': [
            r'(?i)api.?error|request.?failed|invalid.?response',
            r'(?i)polygon|finnhub|external.?service',
        ],
        'database': [
            r'(?i)database|sqlite|sqlalchemy|migration',
            r'(?i)constraint|integrity|duplicate.?key',
        ]
    }

    # Error patterns with suggested fixes
    ERROR_FIXES = {
        r'ModuleNotFoundError: No module named \'(\w+)\'': {
            'action': 'Install missing module',
            'command': 'pip install {match}',
            'auto_fix': True
        },
        r'ImportError: cannot import name \'(\w+)\'': {
            'action': 'Check import path or circular imports',
            'auto_fix': False
        },
        r'OperationalError.*database is locked': {
            'action': 'Database connection pool exhausted',
            'command': 'Restart application or increase pool size',
            'auto_fix': False
        },
        r'ConnectionError|ConnectionRefusedError': {
            'action': 'External service unavailable',
            'auto_fix': False
        },
        r'MemoryError|Out of memory': {
            'action': 'Memory limit exceeded - consider optimization',
            'auto_fix': False
        },
        r'RateLimitExceeded|429': {
            'action': 'API rate limit hit - implement backoff',
            'auto_fix': False
        }
    }

    def __init__(self):
        self.project_root = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        self.log_paths = self._find_log_files()
        self.patterns: Dict[str, LogPattern] = {}
        self.alerts: List[LogAlert] = []
        self.seen_errors: Set[str] = set()
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.last_positions: Dict[str, int] = {}  # Track file read positions

    def _find_log_files(self) -> List[Path]:
        """Find all log files in the project."""
        log_files = []

        # Common log locations
        log_dirs = [
            self.project_root / 'logs',
            self.project_root / 'log',
            self.project_root / 'data' / 'logs',
            Path('/var/log'),
        ]

        for log_dir in log_dirs:
            if log_dir.exists():
                log_files.extend(log_dir.glob('*.log'))
                log_files.extend(log_dir.glob('*.txt'))

        # Also check for Flask/app logs
        app_log = self.project_root / 'app.log'
        if app_log.exists():
            log_files.append(app_log)

        return log_files

    def parse_log_line(self, line: str, source: str = '') -> Optional[LogEntry]:
        """
        Parse a single log line.

        Supports multiple formats:
        - Standard Python logging: 2024-01-01 12:00:00,000 - module - LEVEL - message
        - Flask/Werkzeug: 127.0.0.1 - - [01/Jan/2024 12:00:00] "GET / HTTP/1.1" 200
        - Simple: [LEVEL] message
        """
        # Python logging format
        match = re.match(
            r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:,\d{3})?)\s*-?\s*(\w+)?\s*-?\s*(DEBUG|INFO|WARNING|ERROR|CRITICAL)\s*-?\s*(.*)',
            line
        )
        if match:
            try:
                ts_str = match.group(1).replace(',', '.')
                timestamp = datetime.strptime(ts_str[:19], '%Y-%m-%d %H:%M:%S')
            except ValueError:
                timestamp = datetime.now()

            return LogEntry(
                timestamp=timestamp,
                level=match.group(3),
                message=match.group(4),
                source=match.group(2) or source
            )

        # Flask/Werkzeug access log format
        match = re.match(
            r'([\d.]+)\s+-\s+-\s+\[([^\]]+)\]\s+"(\w+)\s+([^"]+)"\s+(\d+)',
            line
        )
        if match:
            status_code = int(match.group(5))
            level = 'ERROR' if status_code >= 500 else 'WARNING' if status_code >= 400 else 'INFO'

            return LogEntry(
                timestamp=datetime.now(),
                level=level,
                message=f'{match.group(3)} {match.group(4)} -> {status_code}',
                source='werkzeug',
                extra={'ip': match.group(1), 'status': status_code}
            )

        # Simple format with level in brackets
        match = re.match(r'\[?(DEBUG|INFO|WARNING|ERROR|CRITICAL)\]?\s*:?\s*(.*)', line, re.I)
        if match:
            return LogEntry(
                timestamp=datetime.now(),
                level=match.group(1).upper(),
                message=match.group(2),
                source=source
            )

        # If line looks like an error/traceback
        if re.search(r'(?i)error|exception|traceback|failed', line):
            return LogEntry(
                timestamp=datetime.now(),
                level='ERROR',
                message=line.strip(),
                source=source
            )

        return None

    def analyze_file(self, log_path: Path, since: Optional[datetime] = None) -> List[LogEntry]:
        """
        Analyze a log file.

        Args:
            log_path: Path to the log file
            since: Only analyze entries after this time

        Returns:
            List of LogEntry objects
        """
        entries = []

        if not log_path.exists():
            return entries

        try:
            # Get last read position
            start_pos = self.last_positions.get(str(log_path), 0)

            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(start_pos)
                current_entry = None
                traceback_lines = []

                for line in f:
                    # Check for traceback continuation
                    if line.startswith('  ') or line.startswith('\t'):
                        if current_entry:
                            traceback_lines.append(line.rstrip())
                        continue

                    # Save previous entry
                    if current_entry:
                        if traceback_lines:
                            current_entry.traceback = '\n'.join(traceback_lines)
                            traceback_lines = []
                        entries.append(current_entry)

                    # Parse new line
                    current_entry = self.parse_log_line(line.strip(), log_path.name)

                    # Filter by time if specified
                    if current_entry and since:
                        if current_entry.timestamp < since:
                            current_entry = None

                # Don't forget last entry
                if current_entry:
                    if traceback_lines:
                        current_entry.traceback = '\n'.join(traceback_lines)
                    entries.append(current_entry)

                # Update position
                self.last_positions[str(log_path)] = f.tell()

        except Exception as e:
            logger.error(f"Error reading log file {log_path}: {e}")

        return entries

    def detect_patterns(self, entries: List[LogEntry]) -> List[LogPattern]:
        """
        Detect patterns in log entries.

        Args:
            entries: List of log entries to analyze

        Returns:
            List of detected patterns
        """
        pattern_counts: Dict[str, Dict] = defaultdict(lambda: {
            'count': 0,
            'first_seen': None,
            'last_seen': None,
            'examples': []
        })

        for entry in entries:
            # Skip non-error entries for pattern detection
            if entry.level not in ('WARNING', 'ERROR', 'CRITICAL'):
                continue

            # Normalize message for pattern matching
            normalized = self._normalize_message(entry.message)

            # Categorize
            category = self._categorize_entry(entry)

            # Update pattern stats
            pattern_key = f"{category}:{normalized}"
            pattern_data = pattern_counts[pattern_key]
            pattern_data['count'] += 1
            pattern_data['category'] = category
            pattern_data['severity'] = entry.level

            if pattern_data['first_seen'] is None:
                pattern_data['first_seen'] = entry.timestamp
            pattern_data['last_seen'] = entry.timestamp

            if len(pattern_data['examples']) < 3:
                pattern_data['examples'].append(entry.message)

        # Convert to LogPattern objects
        patterns = []
        for pattern_key, data in pattern_counts.items():
            if data['count'] >= 2:  # Only patterns that repeat
                patterns.append(LogPattern(
                    pattern=pattern_key.split(':', 1)[1],
                    count=data['count'],
                    first_seen=data['first_seen'],
                    last_seen=data['last_seen'],
                    severity=data['severity'],
                    category=data['category'],
                    examples=data['examples']
                ))

        return sorted(patterns, key=lambda p: p.count, reverse=True)

    def _normalize_message(self, message: str) -> str:
        """Normalize a log message for pattern matching."""
        # Remove variable parts
        normalized = re.sub(r'\d+', '<NUM>', message)
        normalized = re.sub(r'0x[0-9a-fA-F]+', '<HEX>', normalized)
        normalized = re.sub(r'[a-fA-F0-9]{8,}', '<HASH>', normalized)
        normalized = re.sub(r'/[^\s]+', '<PATH>', normalized)
        normalized = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '<EMAIL>', normalized)

        # Truncate
        return normalized[:100] if len(normalized) > 100 else normalized

    def _categorize_entry(self, entry: LogEntry) -> str:
        """Categorize a log entry."""
        message = entry.message.lower()

        for category, patterns in self.LOG_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, message, re.I):
                    return category

        return 'general'

    def generate_alerts(self, entries: List[LogEntry], patterns: List[LogPattern]) -> List[LogAlert]:
        """
        Generate alerts from log analysis.

        Args:
            entries: Log entries
            patterns: Detected patterns

        Returns:
            List of alerts
        """
        alerts = []
        alert_counter = 0

        # Alert for critical errors
        critical_count = sum(1 for e in entries if e.level == 'CRITICAL')
        if critical_count > 0:
            alert_counter += 1
            alerts.append(LogAlert(
                id=f'ALERT-{alert_counter:04d}',
                timestamp=datetime.now(),
                severity='critical',
                title=f'{critical_count} Critical Errors Detected',
                message='Critical errors require immediate attention',
                count=critical_count,
                suggested_action='Review critical errors and fix immediately'
            ))

        # Alert for high-frequency patterns
        for pattern in patterns:
            if pattern.count >= 10:
                alert_counter += 1
                alerts.append(LogAlert(
                    id=f'ALERT-{alert_counter:04d}',
                    timestamp=datetime.now(),
                    severity='warning' if pattern.severity == 'WARNING' else 'error',
                    title=f'Recurring {pattern.category.title()} Issue',
                    message=f'Pattern "{pattern.pattern[:50]}..." occurred {pattern.count} times',
                    pattern=pattern.pattern,
                    count=pattern.count,
                    suggested_action=self._get_fix_suggestion(pattern.examples[0] if pattern.examples else '')
                ))

        # Alert for specific error patterns
        for entry in entries:
            if entry.level in ('ERROR', 'CRITICAL'):
                for pattern, fix_info in self.ERROR_FIXES.items():
                    match = re.search(pattern, entry.message)
                    if match:
                        # Avoid duplicate alerts
                        error_key = f"{pattern}:{match.group(0)}"
                        if error_key not in self.seen_errors:
                            self.seen_errors.add(error_key)
                            alert_counter += 1

                            action = fix_info['action']
                            if 'command' in fix_info and match.groups():
                                action += f"\nCommand: {fix_info['command'].format(match=match.group(1))}"

                            alerts.append(LogAlert(
                                id=f'ALERT-{alert_counter:04d}',
                                timestamp=datetime.now(),
                                severity='error',
                                title=f'{entry.level}: {match.group(0)[:50]}',
                                message=entry.message[:200],
                                suggested_action=action,
                                auto_fixable=fix_info.get('auto_fix', False)
                            ))

        return alerts

    def _get_fix_suggestion(self, message: str) -> Optional[str]:
        """Get fix suggestion for a message."""
        for pattern, fix_info in self.ERROR_FIXES.items():
            if re.search(pattern, message):
                return fix_info['action']
        return None

    async def analyze_all(self, since_hours: int = 24) -> Dict[str, Any]:
        """
        Analyze all log files.

        Args:
            since_hours: Only analyze logs from the last N hours

        Returns:
            Analysis results
        """
        since = datetime.now() - timedelta(hours=since_hours)
        all_entries = []

        # Analyze each log file
        for log_path in self.log_paths:
            entries = self.analyze_file(log_path, since)
            all_entries.extend(entries)

        # Detect patterns
        patterns = self.detect_patterns(all_entries)

        # Generate alerts
        alerts = self.generate_alerts(all_entries, patterns)

        # Store for later
        self.patterns = {p.pattern: p for p in patterns}
        self.alerts = alerts

        # Summary stats
        level_counts = defaultdict(int)
        category_counts = defaultdict(int)

        for entry in all_entries:
            level_counts[entry.level] += 1
            category_counts[self._categorize_entry(entry)] += 1

        return {
            'total_entries': len(all_entries),
            'time_range': {
                'start': since.isoformat(),
                'end': datetime.now().isoformat(),
                'hours': since_hours
            },
            'by_level': dict(level_counts),
            'by_category': dict(category_counts),
            'patterns': [
                {
                    'pattern': p.pattern,
                    'count': p.count,
                    'category': p.category,
                    'severity': p.severity
                }
                for p in patterns[:10]  # Top 10 patterns
            ],
            'alerts': [
                {
                    'id': a.id,
                    'severity': a.severity,
                    'title': a.title,
                    'message': a.message,
                    'count': a.count,
                    'auto_fixable': a.auto_fixable
                }
                for a in alerts
            ],
            'log_files': [str(p) for p in self.log_paths],
            'health_score': self._calculate_health_score(all_entries, alerts)
        }

    def _calculate_health_score(self, entries: List[LogEntry], alerts: List[LogAlert]) -> int:
        """Calculate log health score (0-100)."""
        if not entries:
            return 100

        score = 100

        # Deduct for errors
        error_count = sum(1 for e in entries if e.level in ('ERROR', 'CRITICAL'))
        error_ratio = error_count / len(entries)
        score -= min(40, int(error_ratio * 200))

        # Deduct for critical alerts
        critical_alerts = sum(1 for a in alerts if a.severity == 'critical')
        score -= min(30, critical_alerts * 10)

        # Deduct for high-frequency patterns
        high_freq_patterns = sum(1 for p in self.patterns.values() if p.count > 20)
        score -= min(20, high_freq_patterns * 5)

        return max(0, score)

    def get_recent_errors(self, limit: int = 20) -> List[Dict]:
        """Get recent errors from logs."""
        errors = []

        for log_path in self.log_paths:
            entries = self.analyze_file(log_path)
            for entry in entries:
                if entry.level in ('ERROR', 'CRITICAL'):
                    errors.append({
                        'timestamp': entry.timestamp.isoformat(),
                        'level': entry.level,
                        'message': entry.message,
                        'source': entry.source,
                        'traceback': entry.traceback
                    })

        return sorted(errors, key=lambda x: x['timestamp'], reverse=True)[:limit]

    def watch_logs(self, callback):
        """
        Watch logs for new entries (blocking).

        Args:
            callback: Function to call with new LogEntry objects
        """
        import time

        while True:
            for log_path in self.log_paths:
                entries = self.analyze_file(log_path)
                for entry in entries:
                    if entry.level in ('WARNING', 'ERROR', 'CRITICAL'):
                        callback(entry)

            time.sleep(5)


# Singleton instance
_analyzer_instance: Optional[LogAnalyzer] = None


def get_log_analyzer() -> LogAnalyzer:
    """Get the log analyzer singleton."""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = LogAnalyzer()
    return _analyzer_instance


