"""
Statistics & Reports Agent
===========================

Tracks agent performance, generates reports, and provides analytics.
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
from datetime import timedelta
from typing import List
from typing import Optional
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AgentStats:
    """Statistics for a single agent."""
    name: str
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    total_fixes: int = 0
    total_issues_found: int = 0
    average_duration_ms: float = 0.0
    last_run: Optional[str] = None
    last_status: str = 'unknown'


@dataclass
class DailyStats:
    """Statistics for a single day."""
    date: str
    total_runs: int = 0
    successful_runs: int = 0
    issues_found: int = 0
    issues_fixed: int = 0
    errors: int = 0
    warnings: int = 0
    agents_active: int = 0


@dataclass
class Report:
    """Generated report."""
    id: str
    type: str  # 'daily', 'weekly', 'monthly', 'custom'
    title: str
    generated_at: str
    period_start: str
    period_end: str
    summary: Dict[str, Any]
    details: Dict[str, Any]
    recommendations: List[str]


class StatisticsAgent:
    """
    Tracks and analyzes agent performance.

    Features:
    - Track all agent runs
    - Calculate success rates
    - Identify trends
    - Generate reports
    - Provide recommendations
    """

    def __init__(self):
        self.project_root = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        self.data_dir = self.project_root / 'data' / 'agents' / 'stats'
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.agent_stats: Dict[str, AgentStats] = {}
        self.daily_stats: Dict[str, DailyStats] = {}
        self.events: List[Dict] = []

        self._load_data()

    def _load_data(self):
        """Load persisted statistics."""
        try:
            stats_file = self.data_dir / 'agent_stats.json'
            if stats_file.exists():
                with open(stats_file, 'r') as f:
                    data = json.load(f)
                    self.agent_stats = {
                        k: AgentStats(**v) for k, v in data.get('agent_stats', {}).items()
                    }
                    self.daily_stats = {
                        k: DailyStats(**v) for k, v in data.get('daily_stats', {}).items()
                    }
        except Exception as e:
            logger.warning(f"Could not load stats: {e}")

    def _save_data(self):
        """Persist statistics."""
        try:
            stats_file = self.data_dir / 'agent_stats.json'
            with open(stats_file, 'w') as f:
                json.dump({
                    'agent_stats': {k: asdict(v) for k, v in self.agent_stats.items()},
                    'daily_stats': {k: asdict(v) for k, v in self.daily_stats.items()},
                    'last_updated': datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save stats: {e}")

    def record_run(
        self,
        agent_name: str,
        success: bool,
        duration_ms: float,
        issues_found: int = 0,
        issues_fixed: int = 0,
        status: str = 'unknown',
        details: Dict = None
    ):
        """
        Record an agent run.

        Args:
            agent_name: Name of the agent
            success: Whether the run was successful
            duration_ms: Duration in milliseconds
            issues_found: Number of issues found
            issues_fixed: Number of issues fixed
            status: Final status
            details: Additional details
        """
        now = datetime.now()
        today = now.strftime('%Y-%m-%d')

        # Update agent stats
        if agent_name not in self.agent_stats:
            self.agent_stats[agent_name] = AgentStats(name=agent_name)

        stats = self.agent_stats[agent_name]
        stats.total_runs += 1
        if success:
            stats.successful_runs += 1
        else:
            stats.failed_runs += 1
        stats.total_fixes += issues_fixed
        stats.total_issues_found += issues_found

        # Update average duration
        n = stats.total_runs
        stats.average_duration_ms = (
            (stats.average_duration_ms * (n - 1) + duration_ms) / n
        )

        stats.last_run = now.isoformat()
        stats.last_status = status

        # Update daily stats
        if today not in self.daily_stats:
            self.daily_stats[today] = DailyStats(date=today)

        daily = self.daily_stats[today]
        daily.total_runs += 1
        if success:
            daily.successful_runs += 1
        daily.issues_found += issues_found
        daily.issues_fixed += issues_fixed
        if status == 'error':
            daily.errors += 1
        elif status == 'warning':
            daily.warnings += 1

        # Record event
        self.events.append({
            'timestamp': now.isoformat(),
            'agent': agent_name,
            'success': success,
            'duration_ms': duration_ms,
            'issues_found': issues_found,
            'issues_fixed': issues_fixed,
            'status': status,
            'details': details
        })

        # Keep only last 1000 events
        if len(self.events) > 1000:
            self.events = self.events[-1000:]

        self._save_data()

    def get_agent_stats(self, agent_name: str = None) -> Dict[str, Any]:
        """
        Get statistics for an agent or all agents.

        Args:
            agent_name: Specific agent or None for all

        Returns:
            Statistics dictionary
        """
        if agent_name:
            stats = self.agent_stats.get(agent_name)
            if stats:
                return {
                    **asdict(stats),
                    'success_rate': (
                        stats.successful_runs / stats.total_runs * 100
                        if stats.total_runs > 0 else 0
                    ),
                    'fix_rate': (
                        stats.total_fixes / stats.total_issues_found * 100
                        if stats.total_issues_found > 0 else 0
                    )
                }
            return {}

        # All agents
        result = {}
        for name, stats in self.agent_stats.items():
            result[name] = {
                **asdict(stats),
                'success_rate': (
                    stats.successful_runs / stats.total_runs * 100
                    if stats.total_runs > 0 else 0
                )
            }
        return result

    def get_daily_stats(self, days: int = 7) -> List[Dict]:
        """
        Get daily statistics.

        Args:
            days: Number of days to include

        Returns:
            List of daily stats
        """
        result = []
        today = datetime.now().date()

        for i in range(days):
            date = (today - timedelta(days=i)).strftime('%Y-%m-%d')
            if date in self.daily_stats:
                result.append(asdict(self.daily_stats[date]))
            else:
                result.append(DailyStats(date=date).__dict__)

        return list(reversed(result))

    def get_trends(self) -> Dict[str, Any]:
        """
        Analyze trends in agent performance.

        Returns:
            Trend analysis
        """
        if not self.daily_stats:
            return {'message': 'Not enough data for trend analysis'}

        # Get last 7 days vs previous 7 days
        today = datetime.now().date()

        recent_runs = 0
        recent_issues = 0
        recent_fixes = 0

        previous_runs = 0
        previous_issues = 0
        previous_fixes = 0

        for i in range(7):
            date = (today - timedelta(days=i)).strftime('%Y-%m-%d')
            if date in self.daily_stats:
                stats = self.daily_stats[date]
                recent_runs += stats.total_runs
                recent_issues += stats.issues_found
                recent_fixes += stats.issues_fixed

        for i in range(7, 14):
            date = (today - timedelta(days=i)).strftime('%Y-%m-%d')
            if date in self.daily_stats:
                stats = self.daily_stats[date]
                previous_runs += stats.total_runs
                previous_issues += stats.issues_found
                previous_fixes += stats.issues_fixed

        def trend(current, previous):
            if previous == 0:
                return 'new' if current > 0 else 'stable'
            change = (current - previous) / previous * 100
            if change > 10:
                return f'+{change:.1f}%'
            elif change < -10:
                return f'{change:.1f}%'
            return 'stable'

        return {
            'period': 'Last 7 days vs previous 7 days',
            'runs': {
                'current': recent_runs,
                'previous': previous_runs,
                'trend': trend(recent_runs, previous_runs)
            },
            'issues_found': {
                'current': recent_issues,
                'previous': previous_issues,
                'trend': trend(recent_issues, previous_issues)
            },
            'issues_fixed': {
                'current': recent_fixes,
                'previous': previous_fixes,
                'trend': trend(recent_fixes, previous_fixes)
            },
            'fix_rate': {
                'current': f'{recent_fixes/recent_issues*100:.1f}%' if recent_issues > 0 else 'N/A',
                'previous': f'{previous_fixes/previous_issues*100:.1f}%' if previous_issues > 0 else 'N/A'
            }
        }

    def generate_report(self, report_type: str = 'daily') -> Report:
        """
        Generate a report.

        Args:
            report_type: 'daily', 'weekly', 'monthly'

        Returns:
            Report object
        """
        now = datetime.now()
        report_id = f'{report_type.upper()}-{now.strftime("%Y%m%d%H%M%S")}'

        if report_type == 'daily':
            period_start = now.replace(hour=0, minute=0, second=0).isoformat()
            period_end = now.isoformat()
            days = 1
        elif report_type == 'weekly':
            period_start = (now - timedelta(days=7)).isoformat()
            period_end = now.isoformat()
            days = 7
        else:  # monthly
            period_start = (now - timedelta(days=30)).isoformat()
            period_end = now.isoformat()
            days = 30

        # Calculate summary
        daily_data = self.get_daily_stats(days)

        total_runs = sum(d['total_runs'] for d in daily_data)
        successful_runs = sum(d['successful_runs'] for d in daily_data)
        issues_found = sum(d['issues_found'] for d in daily_data)
        issues_fixed = sum(d['issues_fixed'] for d in daily_data)
        errors = sum(d['errors'] for d in daily_data)
        warnings = sum(d['warnings'] for d in daily_data)

        # Top performing agents
        agent_performance = []
        for name, stats in self.agent_stats.items():
            if stats.total_runs > 0:
                agent_performance.append({
                    'name': name,
                    'runs': stats.total_runs,
                    'success_rate': stats.successful_runs / stats.total_runs * 100,
                    'fixes': stats.total_fixes
                })

        agent_performance.sort(key=lambda x: x['success_rate'], reverse=True)

        # Generate recommendations
        recommendations = []

        if total_runs == 0:
            recommendations.append('Start running agents to collect performance data')
        else:
            success_rate = successful_runs / total_runs * 100
            if success_rate < 80:
                recommendations.append(f'Overall success rate is {success_rate:.1f}%. Review failing agents.')

            if issues_found > 0:
                fix_rate = issues_fixed / issues_found * 100
                if fix_rate < 50:
                    recommendations.append(f'Fix rate is only {fix_rate:.1f}%. Consider manual intervention.')

            if errors > 10:
                recommendations.append(f'{errors} errors occurred. Review error logs.')

            # Check for underperforming agents
            for agent in agent_performance:
                if agent['success_rate'] < 70:
                    recommendations.append(f"Agent '{agent['name']}' has low success rate ({agent['success_rate']:.1f}%)")

        if not recommendations:
            recommendations.append('All agents performing well. Keep monitoring.')

        summary = {
            'total_runs': total_runs,
            'successful_runs': successful_runs,
            'success_rate': f'{successful_runs/total_runs*100:.1f}%' if total_runs > 0 else 'N/A',
            'issues_found': issues_found,
            'issues_fixed': issues_fixed,
            'fix_rate': f'{issues_fixed/issues_found*100:.1f}%' if issues_found > 0 else 'N/A',
            'errors': errors,
            'warnings': warnings,
            'active_agents': len([a for a in self.agent_stats.values() if a.total_runs > 0])
        }

        details = {
            'daily_breakdown': daily_data,
            'agent_performance': agent_performance[:10],
            'trends': self.get_trends()
        }

        return Report(
            id=report_id,
            type=report_type,
            title=f'{report_type.title()} Agent Performance Report',
            generated_at=now.isoformat(),
            period_start=period_start,
            period_end=period_end,
            summary=summary,
            details=details,
            recommendations=recommendations
        )

    def get_dashboard_data(self) -> Dict[str, Any]:
        """
        Get data for dashboard display.

        Returns:
            Dashboard data
        """
        today = datetime.now().strftime('%Y-%m-%d')
        today_stats = self.daily_stats.get(today, DailyStats(date=today))

        # Calculate totals
        total_runs = sum(s.total_runs for s in self.agent_stats.values())
        total_fixes = sum(s.total_fixes for s in self.agent_stats.values())
        total_issues = sum(s.total_issues_found for s in self.agent_stats.values())

        # Active agents (run in last 24 hours)
        cutoff = (datetime.now() - timedelta(hours=24)).isoformat()
        active_agents = sum(
            1 for s in self.agent_stats.values()
            if s.last_run and s.last_run > cutoff
        )

        return {
            'overview': {
                'total_runs': total_runs,
                'total_fixes': total_fixes,
                'total_issues': total_issues,
                'fix_rate': f'{total_fixes/total_issues*100:.1f}%' if total_issues > 0 else '0%',
                'active_agents': active_agents,
                'total_agents': len(self.agent_stats)
            },
            'today': {
                'runs': today_stats.total_runs,
                'successful': today_stats.successful_runs,
                'issues_found': today_stats.issues_found,
                'issues_fixed': today_stats.issues_fixed,
                'errors': today_stats.errors,
                'warnings': today_stats.warnings
            },
            'chart_data': self.get_daily_stats(7),
            'agent_status': [
                {
                    'name': name,
                    'status': stats.last_status,
                    'last_run': stats.last_run,
                    'success_rate': (
                        stats.successful_runs / stats.total_runs * 100
                        if stats.total_runs > 0 else 0
                    )
                }
                for name, stats in self.agent_stats.items()
            ],
            'recent_events': self.events[-10:][::-1]  # Last 10, newest first
        }

    def export_report(self, report: Report, format: str = 'json') -> str:
        """
        Export a report.

        Args:
            report: The report to export
            format: 'json' or 'markdown'

        Returns:
            Exported content as string
        """
        if format == 'json':
            return json.dumps(asdict(report), indent=2)

        # Markdown format
        md = """# {report.title}

**Generated:** {report.generated_at}
**Period:** {report.period_start} to {report.period_end}

## Summary

| Metric | Value |
|--------|-------|
"""
        for key, value in report.summary.items():
            md += f"| {key.replace('_', ' ').title()} | {value} |\n"

        md += "\n## Recommendations\n\n"
        for rec in report.recommendations:
            md += f"- {rec}\n"

        md += "\n## Agent Performance\n\n"
        md += "| Agent | Runs | Success Rate | Fixes |\n"
        md += "|-------|------|--------------|-------|\n"

        for agent in report.details.get('agent_performance', []):
            md += f"| {agent['name']} | {agent['runs']} | {agent['success_rate']:.1f}% | {agent['fixes']} |\n"

        return md

    def reset_stats(self, confirm: bool = False):
        """Reset all statistics."""
        if confirm:
            self.agent_stats = {}
            self.daily_stats = {}
            self.events = []
            self._save_data()
            logger.info("Statistics reset")


# Singleton instance
_stats_instance: Optional[StatisticsAgent] = None


def get_statistics() -> StatisticsAgent:
    """Get the statistics singleton."""
    global _stats_instance
    if _stats_instance is None:
        _stats_instance = StatisticsAgent()
    return _stats_instance


