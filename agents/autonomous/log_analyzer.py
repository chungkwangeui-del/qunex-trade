"""
📋 Log Analyzer
Analyzes application logs to detect patterns, errors, and anomalies.
"""
import re
import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class LogEntry:
    """Parsed log entry."""
    timestamp: str
    level: str
    message: str
    source: str = ""
    line_number: int = 0


@dataclass
class LogAnalysisResult:
    """Result of log analysis."""
    total_entries: int = 0
    error_count: int = 0
    warning_count: int = 0
    error_patterns: list = field(default_factory=list)
    anomalies: list = field(default_factory=list)
    top_errors: list = field(default_factory=list)
    recommendations: list = field(default_factory=list)


class LogAnalyzer:
    """
    Analyzes log files for patterns, errors, and anomalies.
    """

    def __init__(self, log_dir: Optional[Path] = None):
        self.log_dir = log_dir or Path("logs")
        self.results: list[LogAnalysisResult] = []

        # Log patterns to detect
        self.patterns = {
            'error': re.compile(r'\b(ERROR|CRITICAL|FATAL|Exception|Traceback)\b', re.IGNORECASE),
            'warning': re.compile(r'\b(WARNING|WARN)\b', re.IGNORECASE),
            'info': re.compile(r'\b(INFO)\b', re.IGNORECASE),
            'debug': re.compile(r'\b(DEBUG)\b', re.IGNORECASE),
        }

        # Common error patterns
        self.error_patterns = [
            (r'ConnectionError|ConnectionRefused|timeout', 'Connection Issues'),
            (r'MemoryError|OutOfMemory|memory', 'Memory Issues'),
            (r'PermissionError|Access denied|forbidden', 'Permission Issues'),
            (r'FileNotFoundError|No such file', 'File Not Found'),
            (r'ImportError|ModuleNotFoundError', 'Import Errors'),
            (r'KeyError|IndexError|AttributeError', 'Data Access Errors'),
            (r'ValueError|TypeError|InvalidArgument', 'Type/Value Errors'),
            (r'DatabaseError|IntegrityError|OperationalError', 'Database Errors'),
            (r'AuthenticationError|Unauthorized|401', 'Authentication Issues'),
            (r'RateLimitError|429|Too many requests', 'Rate Limiting'),
        ]

    def analyze_file(self, file_path: Path) -> LogAnalysisResult:
        """Analyze a single log file."""
        result = LogAnalysisResult()
        error_messages = []
        warning_messages = []
        timestamps = []

        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            lines = content.split('\n')
            result.total_entries = len(lines)

            for i, line in enumerate(lines):
                if not line.strip():
                    continue

                # Detect log level
                if self.patterns['error'].search(line):
                    result.error_count += 1
                    error_messages.append(line[:200])  # Truncate long lines
                elif self.patterns['warning'].search(line):
                    result.warning_count += 1
                    warning_messages.append(line[:200])

                # Extract timestamp if present
                ts_match = re.search(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}', line)
                if ts_match:
                    timestamps.append(ts_match.group())

            # Categorize errors
            error_categories = defaultdict(int)
            for error in error_messages:
                categorized = False
                for pattern, category in self.error_patterns:
                    if re.search(pattern, error, re.IGNORECASE):
                        error_categories[category] += 1
                        categorized = True
                        break
                if not categorized:
                    error_categories['Other'] += 1

            result.error_patterns = [
                {'category': cat, 'count': count}
                for cat, count in sorted(error_categories.items(), key=lambda x: -x[1])
            ]

            # Find top repeated errors
            error_counter = Counter(error_messages)
            result.top_errors = [
                {'message': msg[:100], 'count': count}
                for msg, count in error_counter.most_common(5)
            ]

            # Detect anomalies
            result.anomalies = self._detect_anomalies(timestamps, error_messages)

            # Generate recommendations
            result.recommendations = self._generate_recommendations(result)

        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {e}")

        return result

    def _detect_anomalies(self, timestamps: list, errors: list) -> list:
        """Detect anomalies in logs."""
        anomalies = []

        # Check for error bursts
        if len(errors) > 10:
            anomalies.append({
                'type': 'error_burst',
                'severity': 'high',
                'message': f'High error rate detected: {len(errors)} errors'
            })

        # Check for repeated errors
        error_counter = Counter(errors)
        for error, count in error_counter.items():
            if count > 5:
                anomalies.append({
                    'type': 'repeated_error',
                    'severity': 'medium',
                    'message': f'Error repeated {count} times: {error[:50]}...'
                })
                break  # Only report first repeated error

        return anomalies

    def _generate_recommendations(self, result: LogAnalysisResult) -> list:
        """Generate recommendations based on analysis."""
        recommendations = []

        if result.error_count > 100:
            recommendations.append({
                'priority': 'high',
                'message': 'High error volume - investigate root cause immediately'
            })

        for pattern in result.error_patterns:
            if pattern['category'] == 'Connection Issues' and pattern['count'] > 5:
                recommendations.append({
                    'priority': 'high',
                    'message': 'Multiple connection errors - check network/service availability'
                })
            elif pattern['category'] == 'Memory Issues':
                recommendations.append({
                    'priority': 'critical',
                    'message': 'Memory issues detected - review memory usage and leaks'
                })
            elif pattern['category'] == 'Database Errors':
                recommendations.append({
                    'priority': 'high',
                    'message': 'Database errors found - check DB connection and queries'
                })
            elif pattern['category'] == 'Rate Limiting':
                recommendations.append({
                    'priority': 'medium',
                    'message': 'Rate limiting detected - implement backoff strategy'
                })

        return recommendations

    def analyze_all(self) -> dict:
        """Analyze all log files in directory."""
        if not self.log_dir.exists():
            return {'status': 'no_logs', 'message': 'Log directory not found'}

        log_files = list(self.log_dir.glob("*.log")) + list(self.log_dir.glob("*.txt"))

        if not log_files:
            return {'status': 'no_logs', 'message': 'No log files found'}

        total_errors = 0
        total_warnings = 0
        all_patterns = defaultdict(int)
        all_recommendations = []

        for log_file in log_files[:10]:  # Limit to 10 files
            result = self.analyze_file(log_file)
            self.results.append(result)
            total_errors += result.error_count
            total_warnings += result.warning_count

            for pattern in result.error_patterns:
                all_patterns[pattern['category']] += pattern['count']

            all_recommendations.extend(result.recommendations)

        return {
            'status': 'ok',
            'files_analyzed': len(log_files),
            'total_errors': total_errors,
            'total_warnings': total_warnings,
            'error_patterns': dict(all_patterns),
            'recommendations': all_recommendations[:10]  # Top 10
        }

    def generate_report(self, output_path: Optional[Path] = None) -> str:
        """Generate log analysis report."""
        output = output_path or Path("reports/log_analysis.md")
        output.parent.mkdir(parents=True, exist_ok=True)

        analysis = self.analyze_all()

        report = """# 📋 Log Analysis Report

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary

| Metric | Value |
|--------|-------|
| Files Analyzed | {analysis.get('files_analyzed', 0)} |
| Total Errors | {analysis.get('total_errors', 0)} |
| Total Warnings | {analysis.get('total_warnings', 0)} |

## Error Categories

"""
        patterns = analysis.get('error_patterns', {})
        for category, count in sorted(patterns.items(), key=lambda x: -x[1]):
            report += f"- **{category}**: {count} occurrences\n"

        report += "\n## Recommendations\n\n"
        for rec in analysis.get('recommendations', []):
            priority_icon = "🔴" if rec['priority'] == 'critical' else "🟠" if rec['priority'] == 'high' else "🟡"
            report += f"- {priority_icon} {rec['message']}\n"

        if not analysis.get('recommendations'):
            report += "- ✅ No critical issues found in logs\n"

        report += "\n---\n*Report generated by Log Analyzer*\n"

        output.write_text(report, encoding='utf-8')
        return str(output)


# Singleton instance
_analyzer: Optional[LogAnalyzer] = None

def get_log_analyzer(log_dir: Optional[Path] = None) -> LogAnalyzer:
    """Get or create log analyzer instance."""
    global _analyzer
    if _analyzer is None:
        _analyzer = LogAnalyzer(log_dir)
    return _analyzer
