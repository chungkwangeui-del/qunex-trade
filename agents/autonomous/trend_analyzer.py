"""
📈 Trend Analyzer
Tracks code quality trends over time and generates insights.
"""
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class DailyMetrics:
    """Metrics for a single day."""
    date: str
    total_issues: int = 0
    critical_issues: int = 0
    files_analyzed: int = 0
    quality_score: float = 0.0
    tests_passed: int = 0
    tests_failed: int = 0
    commits: int = 0
    lines_changed: int = 0
    auto_fixes: int = 0


@dataclass
class TrendData:
    """Historical trend data."""
    metrics: list = field(default_factory=list)
    last_updated: str = ""


class TrendAnalyzer:
    """
    Analyzes code quality trends over time.
    Tracks metrics and generates insights.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path("data/trends")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.data_file = self.data_dir / "trend_data.json"
        self.trend_data = self._load_data()

    def _load_data(self) -> TrendData:
        """Load trend data from file."""
        if self.data_file.exists():
            try:
                data = json.loads(self.data_file.read_text())
                return TrendData(
                    metrics=[DailyMetrics(**m) for m in data.get('metrics', [])],
                    last_updated=data.get('last_updated', '')
                )
            except Exception as e:
                logger.error(f"Error loading trend data: {e}")
        return TrendData()

    def _save_data(self):
        """Save trend data to file."""
        try:
            data = {
                'metrics': [asdict(m) for m in self.trend_data.metrics],
                'last_updated': datetime.now().isoformat()
            }
            self.data_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Error saving trend data: {e}")

    def record_metrics(self, metrics: DailyMetrics):
        """Record metrics for today."""
        today = datetime.now().strftime('%Y-%m-%d')
        metrics.date = today

        # Update or add today's metrics
        existing = next((m for m in self.trend_data.metrics if m.date == today), None)
        if existing:
            # Update existing
            idx = self.trend_data.metrics.index(existing)
            self.trend_data.metrics[idx] = metrics
        else:
            self.trend_data.metrics.append(metrics)

        # Keep only last 90 days
        cutoff = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        self.trend_data.metrics = [m for m in self.trend_data.metrics if m.date >= cutoff]

        self._save_data()

    def get_trend(self, days: int = 7) -> dict:
        """Get trend analysis for specified period."""
        if not self.trend_data.metrics:
            return {'status': 'no_data', 'message': 'No trend data available'}

        recent = self.trend_data.metrics[-days:] if len(self.trend_data.metrics) >= days else self.trend_data.metrics

        if len(recent) < 2:
            return {'status': 'insufficient_data', 'message': 'Need at least 2 days of data'}

        # Calculate trends
        first_half = recent[:len(recent)//2]
        second_half = recent[len(recent)//2:]

        avg_quality_first = sum(m.quality_score for m in first_half) / len(first_half)
        avg_quality_second = sum(m.quality_score for m in second_half) / len(second_half)

        avg_issues_first = sum(m.total_issues for m in first_half) / len(first_half)
        avg_issues_second = sum(m.total_issues for m in second_half) / len(second_half)

        quality_trend = avg_quality_second - avg_quality_first
        issue_trend = avg_issues_second - avg_issues_first

        # Determine overall direction
        if quality_trend > 5:
            direction = "improving"
            icon = "📈"
        elif quality_trend < -5:
            direction = "declining"
            icon = "📉"
        else:
            direction = "stable"
            icon = "➡️"

        return {
            'status': 'ok',
            'direction': direction,
            'icon': icon,
            'quality_change': round(quality_trend, 1),
            'issue_change': round(issue_trend, 1),
            'current_quality': round(avg_quality_second, 1),
            'current_issues': round(avg_issues_second, 0),
            'data_points': len(recent),
            'period_days': days
        }

    def get_insights(self) -> list:
        """Generate insights from trend data."""
        insights = []

        if len(self.trend_data.metrics) < 3:
            return [{'type': 'info', 'message': 'Collecting data... insights will appear after a few days'}]

        recent = self.trend_data.metrics[-7:]

        # Quality trend
        quality_scores = [m.quality_score for m in recent]
        if quality_scores[-1] > quality_scores[0] + 5:
            insights.append({
                'type': 'positive',
                'icon': '🎉',
                'message': f'Code quality improved by {quality_scores[-1] - quality_scores[0]:.1f} points this week!'
            })
        elif quality_scores[-1] < quality_scores[0] - 5:
            insights.append({
                'type': 'warning',
                'icon': '⚠️',
                'message': f'Code quality dropped by {quality_scores[0] - quality_scores[-1]:.1f} points. Review recent changes.'
            })

        # Critical issues trend
        critical = [m.critical_issues for m in recent]
        if critical[-1] == 0 and any(c > 0 for c in critical[:-1]):
            insights.append({
                'type': 'positive',
                'icon': '🛡️',
                'message': 'All critical issues resolved!'
            })
        elif critical[-1] > critical[0]:
            insights.append({
                'type': 'alert',
                'icon': '🚨',
                'message': f'Critical issues increased from {critical[0]} to {critical[-1]}. Immediate attention needed.'
            })

        # Test health
        test_pass = [m.tests_passed for m in recent if m.tests_passed > 0]
        test_fail = [m.tests_failed for m in recent if m.tests_failed >= 0]

        if test_fail and test_fail[-1] > 0:
            insights.append({
                'type': 'warning',
                'icon': '🧪',
                'message': f'{test_fail[-1]} tests currently failing. Fix before merging.'
            })
        elif test_pass and test_pass[-1] > 0:
            insights.append({
                'type': 'positive',
                'icon': '✅',
                'message': f'All {test_pass[-1]} tests passing!'
            })

        # Auto-fix effectiveness
        fixes = sum(m.auto_fixes for m in recent)
        if fixes > 0:
            insights.append({
                'type': 'info',
                'icon': '🤖',
                'message': f'Auto-fixed {fixes} issues this week'
            })

        return insights

    def generate_report(self, output_path: Optional[Path] = None) -> str:
        """Generate trend report."""
        output = output_path or Path("reports/trend_analysis.md")
        output.parent.mkdir(parents=True, exist_ok=True)

        trend = self.get_trend(7)
        insights = self.get_insights()

        report = """# 📈 Code Quality Trend Report

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Current Status

| Metric | Value |
|--------|-------|
| Direction | {trend.get('icon', '?')} {trend.get('direction', 'unknown').title()} |
| Quality Score | {trend.get('current_quality', 'N/A')}/100 |
| Quality Change | {'+' if trend.get('quality_change', 0) > 0 else ''}{trend.get('quality_change', 0)} |
| Current Issues | {trend.get('current_issues', 'N/A')} |

## Insights

"""
        for insight in insights:
            report += f"- {insight.get('icon', '•')} {insight['message']}\n"

        # Add historical data
        if self.trend_data.metrics:
            report += "\n## Historical Data (Last 7 Days)\n\n"
            report += "| Date | Quality | Issues | Critical | Tests |\n"
            report += "|------|---------|--------|----------|-------|\n"

            for m in self.trend_data.metrics[-7:]:
                test_status = f"✅{m.tests_passed}" if m.tests_failed == 0 else f"❌{m.tests_failed}"
                report += f"| {m.date} | {m.quality_score:.0f} | {m.total_issues} | {m.critical_issues} | {test_status} |\n"

        report += "\n---\n*Report generated by Trend Analyzer*\n"

        output.write_text(report, encoding='utf-8')
        return str(output)

    def get_chart_data(self) -> dict:
        """Get data formatted for charts."""
        return {
            'labels': [m.date for m in self.trend_data.metrics],
            'quality': [m.quality_score for m in self.trend_data.metrics],
            'issues': [m.total_issues for m in self.trend_data.metrics],
            'critical': [m.critical_issues for m in self.trend_data.metrics]
        }


# Singleton instance
_analyzer: Optional[TrendAnalyzer] = None

def get_trend_analyzer() -> TrendAnalyzer:
    """Get or create trend analyzer instance."""
    global _analyzer
    if _analyzer is None:
        _analyzer = TrendAnalyzer()
    return _analyzer


