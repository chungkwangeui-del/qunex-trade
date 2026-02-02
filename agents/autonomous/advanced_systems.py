"""
Advanced Systems for Ultimate Bot
=================================

Includes:
- Daily Reports System
- Rollback System
- Auto Test Generation
- Expert Competition System
- Emergency Alerts
"""

import json
import logging
import subprocess
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
from datetime import timedelta
from typing import List
from typing import Optional
from typing import Any

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# DAILY REPORTS SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class DailyReport:
    """A daily summary report."""
    date: str
    cycles_run: int
    tasks_completed: int
    tasks_failed: int
    files_fixed: int
    commits_made: int
    expert_performance: Dict[str, Dict[str, Any]]
    issues_found: List[str]
    issues_resolved: List[str]
    escalations: List[str]
    recommendations: List[str]
    created_at: datetime = field(default_factory=datetime.now)


class DailyReportSystem:
    """
    Generates daily summary reports of all bot activity.
    """

    def __init__(self):
        self.data_dir = Path("data/daily_reports")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.current_stats = {
            'cycles_run': 0,
            'tasks_completed': 0,
            'tasks_failed': 0,
            'files_fixed': [],
            'commits_made': 0,
            'issues_found': [],
            'issues_resolved': [],
            'escalations': []
        }

    def record_cycle(self):
        """Record a cycle completion."""
        self.current_stats['cycles_run'] += 1

    def record_task_completion(self, success: bool):
        """Record task completion."""
        if success:
            self.current_stats['tasks_completed'] += 1
        else:
            self.current_stats['tasks_failed'] += 1

    def record_file_fixed(self, file_path: str):
        """Record a file that was fixed."""
        if file_path not in self.current_stats['files_fixed']:
            self.current_stats['files_fixed'].append(file_path)

    def record_commit(self):
        """Record a commit."""
        self.current_stats['commits_made'] += 1

    def record_issue(self, issue: str, resolved: bool = False):
        """Record an issue found or resolved."""
        if resolved:
            self.current_stats['issues_resolved'].append(issue)
        else:
            self.current_stats['issues_found'].append(issue)

    def record_escalation(self, description: str):
        """Record an escalation."""
        self.current_stats['escalations'].append(description)

    def generate_report(self, expert_performance: Dict[str, Dict[str, Any]]) -> DailyReport:
        """Generate the daily report."""
        today = datetime.now().strftime('%Y-%m-%d')

        # Generate recommendations based on stats
        recommendations = []

        if self.current_stats['tasks_failed'] > self.current_stats['tasks_completed']:
            recommendations.append("⚠️ High failure rate detected. Consider reviewing error patterns.")

        if len(self.current_stats['escalations']) > 5:
            recommendations.append("📋 Multiple escalations today. Manual review recommended.")

        if self.current_stats['commits_made'] == 0:
            recommendations.append("💡 No commits made. Consider running git commit.")

        # Find underperforming experts
        for expert_id, perf in expert_performance.items():
            if perf.get('tasks_completed', 0) == 0 and perf.get('tasks_failed', 0) > 0:
                recommendations.append(f"🔧 {expert_id} is struggling. May need attention.")

        report = DailyReport(
            date=today,
            cycles_run=self.current_stats['cycles_run'],
            tasks_completed=self.current_stats['tasks_completed'],
            tasks_failed=self.current_stats['tasks_failed'],
            files_fixed=len(self.current_stats['files_fixed']),
            commits_made=self.current_stats['commits_made'],
            expert_performance=expert_performance,
            issues_found=self.current_stats['issues_found'][:20],  # Limit
            issues_resolved=self.current_stats['issues_resolved'][:20],
            escalations=self.current_stats['escalations'],
            recommendations=recommendations
        )

        # Save report
        self._save_report(report)

        # Reset stats for next day
        self._reset_stats()

        return report

    def _save_report(self, report: DailyReport):
        """Save report to disk."""
        report_file = self.data_dir / f"report_{report.date}.json"
        try:
            data = {
                'date': report.date,
                'cycles_run': report.cycles_run,
                'tasks_completed': report.tasks_completed,
                'tasks_failed': report.tasks_failed,
                'files_fixed': report.files_fixed,
                'commits_made': report.commits_made,
                'expert_performance': report.expert_performance,
                'issues_found': report.issues_found,
                'issues_resolved': report.issues_resolved,
                'escalations': report.escalations,
                'recommendations': report.recommendations,
                'created_at': report.created_at.isoformat()
            }
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save report: {e}")

    def _reset_stats(self):
        """Reset daily stats."""
        self.current_stats = {
            'cycles_run': 0,
            'tasks_completed': 0,
            'tasks_failed': 0,
            'files_fixed': [],
            'commits_made': 0,
            'issues_found': [],
            'issues_resolved': [],
            'escalations': []
        }

    def get_report_text(self, report: DailyReport) -> str:
        """Generate text version of report."""
        lines = []
        lines.append("")
        lines.append("╔" + "═"*58 + "╗")
        lines.append("║" + " "*15 + f"📊 DAILY REPORT - {report.date}" + " "*14 + "║")
        lines.append("╚" + "═"*58 + "╝")
        lines.append("")
        lines.append("  SUMMARY")
        lines.append("  " + "─"*50)
        lines.append(f"  Cycles Run:      {report.cycles_run}")
        lines.append(f"  Tasks Completed: {report.tasks_completed}")
        lines.append(f"  Tasks Failed:    {report.tasks_failed}")
        lines.append(f"  Files Fixed:     {report.files_fixed}")
        lines.append(f"  Commits Made:    {report.commits_made}")
        lines.append("")

        if report.expert_performance:
            lines.append("  EXPERT PERFORMANCE")
            lines.append("  " + "─"*50)
            for expert_id, perf in report.expert_performance.items():
                done = perf.get('tasks_completed', 0)
                fail = perf.get('tasks_failed', 0)
                score = perf.get('performance_score', 100)
                lines.append(f"  {expert_id:20} Done:{done:3} Fail:{fail:3} Score:{score:.0f}%")
            lines.append("")

        if report.escalations:
            lines.append("  ⚠️ ESCALATIONS (Needs Your Attention)")
            lines.append("  " + "─"*50)
            for esc in report.escalations[:5]:
                lines.append(f"  • {esc[:60]}")
            lines.append("")

        if report.recommendations:
            lines.append("  💡 RECOMMENDATIONS")
            lines.append("  " + "─"*50)
            for rec in report.recommendations:
                lines.append(f"  {rec}")
            lines.append("")

        lines.append("═"*60)

        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# ROLLBACK SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Checkpoint:
    """A system checkpoint for rollback."""
    id: str
    timestamp: datetime
    commit_hash: str
    description: str
    files_state: Dict[str, str]  # file_path -> content hash


class RollbackSystem:
    """
    Automatic rollback system for when things go wrong.

    Creates checkpoints and can rollback to previous state.
    """

    def __init__(self):
        self.data_dir = Path("data/rollback")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.checkpoints: List[Checkpoint] = []
        self.max_checkpoints = 10

        self._load_checkpoints()

    def _load_checkpoints(self):
        """Load existing checkpoints."""
        checkpoints_file = self.data_dir / "checkpoints.json"
        if checkpoints_file.exists():
            try:
                with open(checkpoints_file, 'r') as f:
                    data = json.load(f)
                    for cp in data:
                        checkpoint = Checkpoint(
                            id=cp['id'],
                            timestamp=datetime.fromisoformat(cp['timestamp']),
                            commit_hash=cp['commit_hash'],
                            description=cp['description'],
                            files_state=cp.get('files_state', {})
                        )
                        self.checkpoints.append(checkpoint)
            except Exception as e:
                logger.warning(f"Could not load checkpoints: {e}")

    def _save_checkpoints(self):
        """Save checkpoints to disk."""
        checkpoints_file = self.data_dir / "checkpoints.json"
        try:
            data = [
                {
                    'id': cp.id,
                    'timestamp': cp.timestamp.isoformat(),
                    'commit_hash': cp.commit_hash,
                    'description': cp.description,
                    'files_state': cp.files_state
                }
                for cp in self.checkpoints[-self.max_checkpoints:]
            ]
            with open(checkpoints_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save checkpoints: {e}")

    def create_checkpoint(self, description: str = "Auto checkpoint") -> Optional[Checkpoint]:
        """Create a checkpoint of current state."""
        try:
            # Get current git commit hash
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                capture_output=True,
                text=True,
                timeout=10
            )
            commit_hash = result.stdout.strip() if result.returncode == 0 else "unknown"

            checkpoint_id = f"CP-{datetime.now().strftime('%Y%m%d%H%M%S')}"

            checkpoint = Checkpoint(
                id=checkpoint_id,
                timestamp=datetime.now(),
                commit_hash=commit_hash,
                description=description,
                files_state={}
            )

            self.checkpoints.append(checkpoint)
            self._save_checkpoints()

            logger.info(f"[CHECKPOINT] Created: {checkpoint_id}")

            return checkpoint

        except Exception as e:
            logger.error(f"Failed to create checkpoint: {e}")
            return None

    def rollback_to(self, checkpoint_id: str) -> bool:
        """Rollback to a specific checkpoint."""
        checkpoint = next(
            (cp for cp in self.checkpoints if cp.id == checkpoint_id),
            None
        )

        if not checkpoint:
            logger.error(f"Checkpoint not found: {checkpoint_id}")
            return False

        try:
            # Rollback using git
            if checkpoint.commit_hash != "unknown":
                result = subprocess.run(
                    ['git', 'reset', '--hard', checkpoint.commit_hash],
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if result.returncode == 0:
                    logger.info(f"[ROLLBACK] Rolled back to {checkpoint_id}")
                    return True
                else:
                    logger.error(f"Git reset failed: {result.stderr}")
                    return False

            return False

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False

    def rollback_last(self) -> bool:
        """Rollback to the last checkpoint."""
        if len(self.checkpoints) < 2:
            logger.warning("Not enough checkpoints to rollback")
            return False

        # Get second to last checkpoint
        checkpoint = self.checkpoints[-2]
        return self.rollback_to(checkpoint.id)

    def get_checkpoints(self) -> List[Dict[str, Any]]:
        """Get list of available checkpoints."""
        return [
            {
                'id': cp.id,
                'timestamp': cp.timestamp.isoformat(),
                'commit_hash': cp.commit_hash[:8] if len(cp.commit_hash) > 8 else cp.commit_hash,
                'description': cp.description
            }
            for cp in self.checkpoints
        ]


# ═══════════════════════════════════════════════════════════════════════════════
# AUTO TEST GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

class AutoTestGenerator:
    """
    Automatically generates tests for code changes.
    """

    def __init__(self):
        self.tests_dir = Path("tests")
        self.tests_dir.mkdir(exist_ok=True)

    def generate_test_for_function(
        self,
        function_name: str,
        file_path: str,
        function_code: str
    ) -> str:
        """Generate a basic test for a function."""
        module_path = file_path.replace('/', '.').replace('\\', '.').replace('.py', '')

        test_code = f'''"""Auto-generated test for {function_name}"""
import pytest
from {module_path} import {function_name}


class Test{function_name.title().replace('_', '')}:
    """Tests for {function_name}"""

    def test_{function_name}_basic(self):
        """Basic test for {function_name}"""
        # TODO: Add actual test logic
        # result = {function_name}()
        # assert result is not None
        pass

    def test_{function_name}_edge_cases(self):
        """Edge case tests for {function_name}"""
        # TODO: Add edge case tests
        pass

    def test_{function_name}_error_handling(self):
        """Error handling tests for {function_name}"""
        # TODO: Add error handling tests
        pass
'''
        return test_code

    def generate_test_file(
        self,
        source_file: str,
        functions: List[str]
    ) -> Optional[str]:
        """Generate a test file for a source file."""
        # Determine test file path
        source_path = Path(source_file)
        test_file = self.tests_dir / f"test_{source_path.stem}.py"

        # Generate test content
        module_path = source_file.replace('/', '.').replace('\\', '.').replace('.py', '')

        imports = f"from {module_path} import {', '.join(functions)}"

        test_content = f'''"""Auto-generated tests for {source_file}"""
import pytest
{imports}


'''

        for func in functions:
            test_content += f'''
class Test{func.title().replace('_', '')}:
    """Tests for {func}"""

    def test_{func}_runs(self):
        """Test that {func} runs without error"""
        # Basic smoke test
        pass

'''

        try:
            with open(test_file, 'w') as f:
                f.write(test_content)

            logger.info(f"[TEST] Generated: {test_file}")
            return str(test_file)

        except Exception as e:
            logger.error(f"Failed to generate test file: {e}")
            return None


# ═══════════════════════════════════════════════════════════════════════════════
# EXPERT COMPETITION SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════

class CompetitionRank(Enum):
    """Ranks for experts based on performance."""
    BRONZE = "🥉 Bronze"
    SILVER = "🥈 Silver"
    GOLD = "🥇 Gold"
    PLATINUM = "💎 Platinum"
    DIAMOND = "💠 Diamond"
    MASTER = "👑 Master"


@dataclass
class ExpertScore:
    """Score tracking for an expert."""
    expert_id: str
    points: int = 0
    rank: CompetitionRank = CompetitionRank.BRONZE
    achievements: List[str] = field(default_factory=list)
    streak: int = 0
    best_streak: int = 0
    daily_points: int = 0


class CompetitionSystem:
    """
    Competition system to motivate experts to perform better.

    Awards points for:
    - Successful task completion
    - Streaks
    - Special achievements
    """

    def __init__(self):
        self.data_dir = Path("data/competition")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.scores: Dict[str, ExpertScore] = {}
        self.leaderboard_history: List[Dict] = []

        # Point values
        self.points = {
            'task_complete': 10,
            'task_fast': 5,  # Bonus for fast completion
            'streak_5': 25,
            'streak_10': 50,
            'streak_25': 100,
            'no_failures_day': 50,
            'most_tasks_day': 75,
            'first_task_day': 15,
        }

        # Rank thresholds
        self.rank_thresholds = {
            CompetitionRank.BRONZE: 0,
            CompetitionRank.SILVER: 100,
            CompetitionRank.GOLD: 300,
            CompetitionRank.PLATINUM: 600,
            CompetitionRank.DIAMOND: 1000,
            CompetitionRank.MASTER: 2000,
        }

        self._load_scores()

    def _load_scores(self):
        """Load saved scores."""
        scores_file = self.data_dir / "scores.json"
        if scores_file.exists():
            try:
                with open(scores_file, 'r') as f:
                    data = json.load(f)
                    for expert_id, score_data in data.items():
                        self.scores[expert_id] = ExpertScore(
                            expert_id=expert_id,
                            points=score_data.get('points', 0),
                            rank=CompetitionRank[score_data.get('rank', 'BRONZE')],
                            achievements=score_data.get('achievements', []),
                            streak=score_data.get('streak', 0),
                            best_streak=score_data.get('best_streak', 0)
                        )
            except Exception as e:
                logger.warning(f"Could not load scores: {e}")

    def _save_scores(self):
        """Save scores to disk."""
        scores_file = self.data_dir / "scores.json"
        try:
            data = {}
            for expert_id, score in self.scores.items():
                data[expert_id] = {
                    'points': score.points,
                    'rank': score.rank.name,
                    'achievements': score.achievements,
                    'streak': score.streak,
                    'best_streak': score.best_streak
                }
            with open(scores_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save scores: {e}")

    def _get_score(self, expert_id: str) -> ExpertScore:
        """Get or create score for expert."""
        if expert_id not in self.scores:
            self.scores[expert_id] = ExpertScore(expert_id=expert_id)
        return self.scores[expert_id]

    def _update_rank(self, score: ExpertScore):
        """Update rank based on points."""
        for rank in reversed(list(CompetitionRank)):
            if score.points >= self.rank_thresholds[rank]:
                if score.rank != rank:
                    score.rank = rank
                    self._award_achievement(score, f"Reached {rank.value}")
                break

    def _award_achievement(self, score: ExpertScore, achievement: str):
        """Award an achievement."""
        if achievement not in score.achievements:
            score.achievements.append(achievement)
            logger.info(f"[ACHIEVEMENT] {score.expert_id}: {achievement}")

    def record_task_success(self, expert_id: str, task_time: float = 0):
        """Record a successful task completion."""
        score = self._get_score(expert_id)

        # Base points
        points = self.points['task_complete']

        # Fast completion bonus
        if task_time > 0 and task_time < 5:
            points += self.points['task_fast']

        score.points += points
        score.streak += 1
        score.daily_points += points

        # Best streak update
        if score.streak > score.best_streak:
            score.best_streak = score.streak

        # Streak achievements
        if score.streak == 5:
            score.points += self.points['streak_5']
            self._award_achievement(score, "5 Task Streak 🔥")
        elif score.streak == 10:
            score.points += self.points['streak_10']
            self._award_achievement(score, "10 Task Streak 🔥🔥")
        elif score.streak == 25:
            score.points += self.points['streak_25']
            self._award_achievement(score, "25 Task Streak 🔥🔥🔥")

        self._update_rank(score)
        self._save_scores()

    def record_task_failure(self, expert_id: str):
        """Record a task failure."""
        score = self._get_score(expert_id)
        score.streak = 0  # Reset streak
        self._save_scores()

    def get_leaderboard(self) -> List[Dict[str, Any]]:
        """Get the current leaderboard."""
        sorted_scores = sorted(
            self.scores.values(),
            key=lambda s: s.points,
            reverse=True
        )

        return [
            {
                'rank': i + 1,
                'expert_id': s.expert_id,
                'points': s.points,
                'level': s.rank.value,
                'streak': s.streak,
                'achievements': len(s.achievements)
            }
            for i, s in enumerate(sorted_scores)
        ]

    def get_leaderboard_text(self) -> str:
        """Get text representation of leaderboard."""
        leaderboard = self.get_leaderboard()

        lines = []
        lines.append("")
        lines.append("  🏆 EXPERT LEADERBOARD")
        lines.append("  " + "─"*50)
        lines.append("  #   Expert              Points  Level        Streak")
        lines.append("  " + "─"*50)

        for entry in leaderboard[:10]:
            lines.append(
                f"  {entry['rank']:<3} {entry['expert_id']:18} "
                f"{entry['points']:>6}  {entry['level']:12} {entry['streak']:>3}🔥"
            )

        lines.append("  " + "─"*50)

        return "\n".join(lines)

    def reset_daily(self):
        """Reset daily stats and award daily achievements."""
        daily_leader = max(
            self.scores.values(),
            key=lambda s: s.daily_points,
            default=None
        )

        if daily_leader and daily_leader.daily_points > 0:
            daily_leader.points += self.points['most_tasks_day']
            self._award_achievement(daily_leader, f"Daily Champion 🏆")

        # Reset daily points
        for score in self.scores.values():
            score.daily_points = 0

        self._save_scores()


# ═══════════════════════════════════════════════════════════════════════════════
# EMERGENCY ALERTS SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════

class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "ℹ️"
    WARNING = "⚠️"
    ERROR = "❌"
    CRITICAL = "🚨"


@dataclass
class Alert:
    """An emergency alert."""
    id: str
    level: AlertLevel
    title: str
    message: str
    source: str  # Which expert/system raised it
    timestamp: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False
    resolved: bool = False


class EmergencyAlertSystem:
    """
    Emergency alert system for critical issues.

    Alerts are displayed prominently and can trigger notifications.
    """

    def __init__(self):
        self.data_dir = Path("data/alerts")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.alerts: List[Alert] = []
        self.alert_counter = 0

        self._load_alerts()

    def _load_alerts(self):
        """Load existing alerts."""
        alerts_file = self.data_dir / "alerts.json"
        if alerts_file.exists():
            try:
                with open(alerts_file, 'r') as f:
                    data = json.load(f)
                    self.alert_counter = data.get('counter', 0)
                    for a in data.get('alerts', []):
                        alert = Alert(
                            id=a['id'],
                            level=AlertLevel[a['level']],
                            title=a['title'],
                            message=a['message'],
                            source=a['source'],
                            timestamp=datetime.fromisoformat(a['timestamp']),
                            acknowledged=a.get('acknowledged', False),
                            resolved=a.get('resolved', False)
                        )
                        self.alerts.append(alert)
            except Exception as e:
                logger.warning(f"Could not load alerts: {e}")

    def _save_alerts(self):
        """Save alerts to disk."""
        alerts_file = self.data_dir / "alerts.json"
        try:
            data = {
                'counter': self.alert_counter,
                'alerts': [
                    {
                        'id': a.id,
                        'level': a.level.name,
                        'title': a.title,
                        'message': a.message,
                        'source': a.source,
                        'timestamp': a.timestamp.isoformat(),
                        'acknowledged': a.acknowledged,
                        'resolved': a.resolved
                    }
                    for a in self.alerts[-100:]  # Keep last 100
                ]
            }
            with open(alerts_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save alerts: {e}")

    def raise_alert(
        self,
        level: AlertLevel,
        title: str,
        message: str,
        source: str = "system"
    ) -> Alert:
        """Raise a new alert."""
        self.alert_counter += 1

        alert = Alert(
            id=f"ALERT-{self.alert_counter:05d}",
            level=level,
            title=title,
            message=message,
            source=source
        )

        self.alerts.append(alert)
        self._save_alerts()

        # Log based on level
        if level == AlertLevel.CRITICAL:
            logger.critical(f"[ALERT] {title}: {message}")
            self._display_critical_alert(alert)
        elif level == AlertLevel.ERROR:
            logger.error(f"[ALERT] {title}: {message}")
        elif level == AlertLevel.WARNING:
            logger.warning(f"[ALERT] {title}: {message}")
        else:
            logger.info(f"[ALERT] {title}: {message}")

        return alert

    def _display_critical_alert(self, alert: Alert):
        """Display critical alert prominently."""
        print()
        print("  " + "🚨"*25)
        print(f"  🚨 CRITICAL ALERT: {alert.title}")
        print("  " + "🚨"*25)
        print(f"  {alert.message}")
        print(f"  Source: {alert.source}")
        print(f"  Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print("  " + "🚨"*25)
        print()

    def acknowledge(self, alert_id: str):
        """Acknowledge an alert."""
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                self._save_alerts()
                break

    def resolve(self, alert_id: str):
        """Resolve an alert."""
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.resolved = True
                self._save_alerts()
                break

    def get_active_alerts(self) -> List[Alert]:
        """Get all unresolved alerts."""
        return [a for a in self.alerts if not a.resolved]

    def get_critical_alerts(self) -> List[Alert]:
        """Get all critical unresolved alerts."""
        return [
            a for a in self.alerts
            if a.level == AlertLevel.CRITICAL and not a.resolved
        ]

    def get_alerts_summary(self) -> Dict[str, int]:
        """Get summary of alerts."""
        active = self.get_active_alerts()
        return {
            'total': len(self.alerts),
            'active': len(active),
            'critical': len([a for a in active if a.level == AlertLevel.CRITICAL]),
            'errors': len([a for a in active if a.level == AlertLevel.ERROR]),
            'warnings': len([a for a in active if a.level == AlertLevel.WARNING]),
            'unacknowledged': len([a for a in active if not a.acknowledged])
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON INSTANCES
# ═══════════════════════════════════════════════════════════════════════════════

_report_system: Optional[DailyReportSystem] = None
_rollback_system: Optional[RollbackSystem] = None
_test_generator: Optional[AutoTestGenerator] = None
_competition_system: Optional[CompetitionSystem] = None
_alert_system: Optional[EmergencyAlertSystem] = None


def get_report_system() -> DailyReportSystem:
    global _report_system
    if _report_system is None:
        _report_system = DailyReportSystem()
    return _report_system


def get_rollback_system() -> RollbackSystem:
    global _rollback_system
    if _rollback_system is None:
        _rollback_system = RollbackSystem()
    return _rollback_system


def get_test_generator() -> AutoTestGenerator:
    global _test_generator
    if _test_generator is None:
        _test_generator = AutoTestGenerator()
    return _test_generator


def get_competition_system() -> CompetitionSystem:
    global _competition_system
    if _competition_system is None:
        _competition_system = CompetitionSystem()
    return _competition_system


def get_alert_system() -> EmergencyAlertSystem:
    global _alert_system
    if _alert_system is None:
        _alert_system = EmergencyAlertSystem()
    return _alert_system

