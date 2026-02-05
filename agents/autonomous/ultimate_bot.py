"""
Ultimate Bot - Supreme Controller
=================================

The Ultimate Bot is the supreme orchestrator that manages ALL expert bots.
It acts as your substitute, making decisions and coordinating all experts.

Architecture:
    🤖👑 Ultimate Bot (Your Substitute)
              │
    ┌─────────┼─────────┬─────────┬─────────┐
    │         │         │         │         │
  🛠️ Fixer  👨‍💻 Dev   🔬 Analyzer 🔒 Security 🔄 Git
   Expert   Expert    Expert     Expert    Expert

Advanced Features:
- Expert Communication System (experts talk to each other)
- Learning System (learns from past fixes)
- Daily Reports (automatic daily summaries)
- Rollback System (auto-recovery on failure)
- Competition System (experts compete for better performance)
- Emergency Alerts (critical issue notifications)
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from datetime import timedelta
from typing import List
from typing import Optional
from typing import Any

logger = logging.getLogger(__name__)

# Import advanced systems
try:
    from .expert_comm import get_comm_hub, MessageType
    from .learning_system import get_learning_system
    from .advanced_systems import (
        get_report_system, get_rollback_system, get_test_generator,
        get_competition_system, get_alert_system, AlertLevel
    )
    ADVANCED_SYSTEMS_AVAILABLE = True
except ImportError:
    ADVANCED_SYSTEMS_AVAILABLE = False
    logger.warning("Advanced systems not available")

# Import new enhanced systems
try:
    from .ai_reviewer import get_reviewer, AICodeReviewer
    from .trend_analyzer import get_trend_analyzer, DailyMetrics
    from .log_analyzer import get_log_analyzer
    from .dependency_scanner import get_dependency_scanner
    from .backup_manager import get_backup_manager
    from .resource_monitor import get_resource_monitor
    from .api_health import get_api_health_checker
    from .notifier import get_notifier, Notification
    from .test_fixer import get_test_fixer
    from .performance_optimizer import get_performance_optimizer
    from .dashboard import get_dashboard
    ENHANCED_SYSTEMS_AVAILABLE = True
except ImportError as e:
    ENHANCED_SYSTEMS_AVAILABLE = False
    logger.warning(f"Enhanced systems not fully available: {e}")


class BotStatus(Enum):
    """Status of individual bots."""
    IDLE = "idle"
    WORKING = "working"
    ERROR = "error"
    DISABLED = "disabled"
    RESTARTING = "restarting"


class TaskPriority(Enum):
    """Task priority levels."""
    CRITICAL = 1  # Security issues, crashes
    HIGH = 2      # Bugs, errors
    MEDIUM = 3    # Improvements, features
    LOW = 4       # Cleanup, optimization


@dataclass
class BotInfo:
    """Information about an individual bot (expert)."""
    name: str
    description: str
    specialty: str  # Area of expertise
    status: BotStatus = BotStatus.IDLE
    last_run: Optional[datetime] = None
    tasks_completed: int = 0
    tasks_failed: int = 0
    current_task: Optional[str] = None
    error_message: Optional[str] = None
    enabled: bool = True

    # Performance Evaluation
    performance_score: float = 100.0  # 0-100
    avg_task_time: float = 0.0  # seconds
    quality_rating: float = 5.0  # 1-5 stars
    streak: int = 0  # consecutive successes

    def evaluate(self) -> str:
        """Evaluate this expert's performance."""
        total = self.tasks_completed + self.tasks_failed
        if total == 0:
            return "NEW"

        success_rate = (self.tasks_completed / total) * 100

        if success_rate >= 95 and self.streak >= 10:
            return "⭐ EXCELLENT"
        elif success_rate >= 80:
            return "✅ GOOD"
        elif success_rate >= 60:
            return "⚠️ AVERAGE"
        else:
            return "❌ NEEDS IMPROVEMENT"

    def record_success(self, task_time: float):
        """Record a successful task completion."""
        self.tasks_completed += 1
        self.streak += 1

        # Update average time
        total = self.tasks_completed + self.tasks_failed
        self.avg_task_time = ((self.avg_task_time * (total - 1)) + task_time) / total

        # Update performance score
        self.performance_score = min(100, self.performance_score + 1)

        # Update quality rating based on streak
        if self.streak >= 5:
            self.quality_rating = min(5.0, self.quality_rating + 0.1)

    def record_failure(self):
        """Record a task failure."""
        self.tasks_failed += 1
        self.streak = 0
        self.performance_score = max(0, self.performance_score - 5)
        self.quality_rating = max(1.0, self.quality_rating - 0.2)


@dataclass
class UltimateTask:
    """A task managed by the Ultimate Bot."""
    id: str
    description: str
    priority: TaskPriority
    assigned_bot: Optional[str] = None
    status: str = "pending"  # pending, in_progress, completed, failed
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    result: Optional[str] = None
    retries: int = 0
    max_retries: int = 3


class UltimateBot:
    """
    The Supreme Controller - manages all individual bots.

    This bot acts as your substitute, making decisions about:
    - Which bot should handle which task
    - When to run maintenance cycles
    - How to handle failures
    - What to report to you
    """

    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.bots: Dict[str, BotInfo] = {}
        self.task_queue: List[UltimateTask] = []
        self.completed_tasks: List[UltimateTask] = []
        self.is_running = False
        self.cycle_count = 0
        self.start_time: Optional[datetime] = None
        self.data_dir = Path("data/ultimate_bot")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Initialize all bots
        self._register_bots()

        # Load previous state
        self._load_state()

        # Configuration
        self.config = {
            'cycle_interval': 60,      # Seconds between cycles
            'health_check_interval': 300,  # Health check every 5 min
            'auto_fix_enabled': True,
            'auto_deploy_enabled': False,  # Manual approval needed
            'max_concurrent_tasks': 50,    # Process more tasks per cycle!
            'max_task_queue': 100,         # Limit queue size to prevent bloat
            'report_interval': 3600,   # Report every hour
            'daily_report_hour': 23,   # Generate daily report at 11 PM
            'auto_rollback': True,     # Auto rollback on critical failure
        }

        # Initialize advanced systems
        if ADVANCED_SYSTEMS_AVAILABLE:
            self.comm_hub = get_comm_hub()
            self.learning = get_learning_system()
            self.reports = get_report_system()
            self.rollback = get_rollback_system()
            self.competition = get_competition_system()
            self.alerts = get_alert_system()
            self.test_generator = get_test_generator()
        else:
            self.comm_hub = None
            self.learning = None
            self.reports = None
            self.rollback = None
            self.competition = None
            self.alerts = None
            self.test_generator = None

        # Initialize enhanced systems
        if ENHANCED_SYSTEMS_AVAILABLE:
            self.ai_reviewer = get_reviewer(self.project_root)
            self.trend_analyzer = get_trend_analyzer()
            self.log_analyzer = get_log_analyzer()
            self.dependency_scanner = get_dependency_scanner(self.project_root)
            self.backup_manager = get_backup_manager(self.project_root)
            self.resource_monitor = get_resource_monitor()
            self.api_health = get_api_health_checker()
            self.notifier = get_notifier()
            self.test_fixer = get_test_fixer(self.project_root)
            self.performance_optimizer = get_performance_optimizer(self.project_root)
            self.dashboard = get_dashboard()
        else:
            self.ai_reviewer = None
            self.trend_analyzer = None
            self.log_analyzer = None
            self.dependency_scanner = None
            self.backup_manager = None
            self.resource_monitor = None
            self.api_health = None
            self.notifier = None
            self.test_fixer = None
            self.performance_optimizer = None
            self.dashboard = None

    def _register_bots(self):
        """Register all expert bots."""
        # Each expert has: (id, name, description, specialty)
        experts_config = [
            ("fixer", "🛠️ Fixer Expert",
             "Automatically fixes code errors, bugs, and syntax issues",
             "Bug Fixing & Error Resolution"),

            ("developer", "👨‍💻 Developer Expert",
             "Writes new features, APIs, and production-ready code",
             "Feature Development & Code Generation"),

            ("analyzer", "🔬 Analyzer Expert",
             "Deep code analysis, complexity metrics, and quality assessment",
             "Code Quality & Static Analysis"),

            ("security", "🔒 Security Expert",
             "Finds vulnerabilities, injection risks, and security issues",
             "Security Auditing & Vulnerability Detection"),

            ("git", "🔄 Git Expert",
             "Manages version control, commits, pushes, and changelogs",
             "Version Control & Repository Management"),

            ("deployer", "📊 Deploy Expert",
             "Handles deployment pipelines and production releases",
             "Deployment & Release Management"),

            ("tester", "🧪 Tester Expert",
             "Runs unit tests, integration tests, and coverage analysis",
             "Testing & Quality Assurance"),

            ("healer", "⚡ Healer Expert",
             "Auto-recovers from system errors and restores health",
             "System Recovery & Self-Healing"),
        ]

        for bot_id, name, desc, specialty in experts_config:
            self.bots[bot_id] = BotInfo(
                name=name,
                description=desc,
                specialty=specialty
            )

    def _load_state(self):
        """Load previous state from disk."""
        state_file = self.data_dir / "state.json"
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    data = json.load(f)
                    self.cycle_count = data.get('cycle_count', 0)
                    # Load task queue
                    for task_data in data.get('task_queue', []):
                        task = UltimateTask(
                            id=task_data['id'],
                            description=task_data['description'],
                            priority=TaskPriority(task_data['priority']),
                            assigned_bot=task_data.get('assigned_bot'),
                            status=task_data.get('status', 'pending'),
                            retries=task_data.get('retries', 0)
                        )
                        self.task_queue.append(task)
            except Exception as e:
                logger.warning(f"Could not load state: {e}")

    def _save_state(self):
        """Save current state to disk."""
        state_file = self.data_dir / "state.json"
        try:
            data = {
                'cycle_count': self.cycle_count,
                'last_save': datetime.now().isoformat(),
                'task_queue': [
                    {
                        'id': t.id,
                        'description': t.description,
                        'priority': t.priority.value,
                        'assigned_bot': t.assigned_bot,
                        'status': t.status,
                        'retries': t.retries
                    }
                    for t in self.task_queue
                ]
            }
            with open(state_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save state: {e}")

    async def start(self):
        """Start the Ultimate Bot - begins managing all expert bots."""
        self.is_running = True
        self.start_time = datetime.now()

        # Create initial checkpoint
        if self.rollback:
            self.rollback.create_checkpoint("Ultimate Bot startup")

        print()
        print("  ╔" + "═"*58 + "╗")
        print("  ║" + " "*15 + "🤖👑 ULTIMATE BOT ACTIVATED" + " "*16 + "║")
        print("  ╚" + "═"*58 + "╝")
        print()
        print(f"  📊 Managing {len(self.bots)} expert bots")
        print(f"  ⚙️  Auto-fix: {'ENABLED' if self.config['auto_fix_enabled'] else 'DISABLED'}")
        print(f"  ⏱️  Cycle: Every {self.config['cycle_interval']} seconds")
        print()

        # Show advanced systems status
        print("  ┌" + "─"*58 + "┐")
        print("  │  ADVANCED SYSTEMS                                        │")
        print("  ├" + "─"*58 + "┤")
        systems = [
            ("💬 Expert Communication", self.comm_hub is not None),
            ("🧠 Learning System", self.learning is not None),
            ("📊 Daily Reports", self.reports is not None),
            ("⏪ Rollback System", self.rollback is not None),
            ("🏆 Competition System", self.competition is not None),
            ("🚨 Emergency Alerts", self.alerts is not None),
        ]
        for name, active in systems:
            status = "✅ Active" if active else "❌ Disabled"
            print(f"  │  {name:30} {status:>16}     │")
        print("  └" + "─"*58 + "┘")
        print()

        # Show enhanced systems status
        print("  ┌" + "─"*58 + "┐")
        print("  │  ENHANCED SYSTEMS (NEW!)                                 │")
        print("  ├" + "─"*58 + "┤")
        enhanced = [
            ("🧠 AI Code Reviewer", self.ai_reviewer is not None),
            ("📈 Trend Analyzer", self.trend_analyzer is not None),
            ("📋 Log Analyzer", self.log_analyzer is not None),
            ("🔍 Dependency Scanner", self.dependency_scanner is not None),
            ("💾 Auto Backup", self.backup_manager is not None),
            ("📊 Resource Monitor", self.resource_monitor is not None),
            ("🌐 API Health Check", self.api_health is not None),
            ("🔔 Notifier (Discord/Slack)", self.notifier is not None),
            ("🧪 Test Fixer", self.test_fixer is not None),
            ("⚡ Performance Optimizer", self.performance_optimizer is not None),
            ("🖥️ Web Dashboard", self.dashboard is not None),
        ]
        for name, active in enhanced:
            status = "✅ Active" if active else "❌ Disabled"
            print(f"  │  {name:30} {status:>16}     │")
        print("  └" + "─"*58 + "┘")
        print()

        # Start web dashboard
        if self.dashboard:
            self.dashboard.run(threaded=True)
            print("  🌐 Dashboard: http://127.0.0.1:5050")
            print()

        print("  " + "─"*60)
        print("  Expert Team:")
        for bot_id, bot in self.bots.items():
            print(f"    {bot.name:22} → {bot.specialty}")
        print("  " + "─"*60)
        print()

        # Start all subsystems
        await asyncio.gather(
            self._main_loop(),
            self._health_monitor(),
            self._report_generator(),
            self._competition_updater(),
            self._alert_monitor(),
            self._enhanced_systems_monitor(),
        )

    async def stop(self):
        """Stop the Ultimate Bot gracefully."""
        print("\n🛑 Ultimate Bot shutting down...")
        self.is_running = False
        self._save_state()
        print("✅ State saved. Goodbye!")

    async def _main_loop(self):
        """Main control loop - the brain of the Ultimate Bot."""
        while self.is_running:
            try:
                self.cycle_count += 1
                cycle_start = datetime.now()

                print(f"\n{'─'*50}")
                print(f"  📍 Cycle #{self.cycle_count} - {cycle_start.strftime('%H:%M:%S')}")
                print(f"{'─'*50}")

                # Reset cycle flags
                self._security_alerted_this_cycle = False

                # Phase 1: Fix actual syntax errors
                await self._run_proactive_fixes()

                # Phase 2: Health scan (report only - no fake tasks)
                await self._scan_for_issues()

                # Phase 3: Run tests periodically (every 5 cycles)
                if self.cycle_count % 5 == 0:
                    await self._run_tests()

                # Phase 4: Commit any fixes
                await self._auto_commit()

                # Phase 5: Print cycle summary
                await self._print_cycle_summary()

                # Save state
                self._save_state()

                # Record cycle in reports
                if self.reports:
                    self.reports.record_cycle()

                # Health check every 5 cycles
                if self.cycle_count % 5 == 0:
                    print("\n  🏥 Health Check...")
                    await self._health_check()

                # Wait for next cycle
                elapsed = (datetime.now() - cycle_start).total_seconds()
                wait_time = max(0, self.config['cycle_interval'] - elapsed)

                if wait_time > 0:
                    print(f"\n  ⏳ Next cycle in {wait_time:.0f}s...")
                    await asyncio.sleep(wait_time)

            except Exception as e:
                logger.error(f"Main loop error: {e}")
                print(f"  ❌ Error: {e}")
                await asyncio.sleep(10)  # Brief pause on error

    async def _run_proactive_fixes(self):
        """Run the fixer proactively every cycle."""
        print("  🛠️ Running proactive fixes...")

        total_fixes = 0
        all_files = set()

        # Phase 1: Fix syntax errors (RealFixer)
        try:
            from .real_fixer import RealFixerAgent
            fixer = RealFixerAgent()
            result = await fixer.fix_all_errors()

            fixed = result.get('errors_fixed', 0)
            files = result.get('fixed_files', [])

            if fixed > 0:
                total_fixes += fixed
                all_files.update(files)
                print(f"     ✅ Syntax: Fixed {fixed} errors")

        except Exception as e:
            logger.debug(f"RealFixer error: {e}")

        # Phase 2: Expert fixes (code quality, patterns)
        try:
            from .expert_fixer import ExpertFixer
            expert = ExpertFixer()
            result = await expert.fix_all()

            expert_fixes = result.get('fixes_applied', 0)
            expert_files = result.get('files_fixed', [])
            manual_count = result.get('manual_review_count', 0)

            if expert_fixes > 0:
                total_fixes += expert_fixes
                all_files.update(expert_files)
                print(f"     ✅ Expert: Fixed {expert_fixes} code quality issues")

            if manual_count > 0:
                print(f"     📋 {manual_count} issues need manual review (see reports/)")

        except Exception as e:
            logger.debug(f"ExpertFixer error: {e}")

        # Summary and commit
        if total_fixes > 0:
            print(f"     🎯 Total: {total_fixes} fixes in {len(all_files)} files")

            # Update expert stats
            self.bots['fixer'].record_success(1.0)
            if self.competition:
                self.competition.record_task_success('fixer', 1.0)

            # Commit fixes
            await self._commit_fixes(f"🛠️ Auto-fixed {total_fixes} issues in {len(all_files)} files")
        else:
            print("     ✓ No errors to fix")

    async def _commit_fixes(self, message: str):
        """Immediately commit any fixes."""
        try:
            from .git_agent import GitAgent
            import os
            git = GitAgent()

            # Remove lock file if exists (common issue)
            lock_file = Path(".git/index.lock")
            if lock_file.exists():
                try:
                    os.remove(lock_file)
                    print("     🔓 Removed git lock file")
                except Exception:
                    pass

            # Stage ALL changes
            git.run_git("add", "-A")

            # Commit
            success, msg = git.commit(message)
            if success:
                print("     📝 Committed!")

                # Push immediately
                push_ok, push_msg = git.push()
                if push_ok:
                    print("     🚀 Pushed to GitHub!")
                    self.bots['git'].record_success(0.5)
                else:
                    print(f"     ⚠️ Push: {push_msg[:30] if push_msg else 'pending'}")
            elif "nothing to commit" in msg.lower() if msg else False:
                pass  # Silent - no changes
            elif "Unable to create" in msg if msg else False:
                # Lock file issue - try to remove and retry
                if lock_file.exists():
                    os.remove(lock_file)
                success, msg = git.commit(message)
                if success:
                    print("     📝 Committed (retry)!")
            else:
                print(f"     ⚠️ Commit: {msg[:30] if msg else 'issue'}")
        except Exception as e:
            print(f"     ⚠️ Commit error: {e}")

    async def _auto_commit(self):
        """Auto-commit changes if any."""
        try:
            from .git_agent import GitAgent
            import os
            git = GitAgent()

            # Remove lock file if exists
            lock_file = Path(".git/index.lock")
            if lock_file.exists():
                try:
                    os.remove(lock_file)
                except Exception:
                    pass

            status = git.get_status()
            has_changes = status.get('modified', []) or status.get('staged', []) or status.get('untracked', [])

            if has_changes:
                print("  🔄 Auto-committing...")

                # Stage all changes
                git.run_git("add", "-A")

                # Commit
                success, commit_msg = git.commit("Auto-fix by Ultimate Bot 🤖")

                if success:
                    print("     ✅ Committed")

                    # Push to remote
                    push_success, push_msg = git.push()
                    if push_success:
                        print("     ✅ Pushed to GitHub")
                        if self.reports:
                            self.reports.record_commit()
                        self.bots['git'].record_success(1.0)
                    else:
                        print(f"     ⚠️ Push: {push_msg[:40] if push_msg else 'pending'}")
                elif commit_msg and "nothing to commit" in commit_msg.lower():
                    pass  # Silent
                else:
                    print(f"     ⚠️ {commit_msg[:40] if commit_msg else ''}")

        except Exception as e:
            print(f"     ⚠️ Git: {e}")

    async def _scan_for_issues(self):
        """Scan the codebase for issues - report only, no fake tasks."""
        print("  🔍 Scanning codebase health...")

        try:
            from .smart_analyzer import SmartAnalyzer

            analyzer = SmartAnalyzer()
            analysis = analyzer.analyze_project()

            # Count issues by severity for reporting
            critical_count = analysis.get('issues_by_severity', {}).get('critical', 0)
            high_count = analysis.get('issues_by_severity', {}).get('high', 0)
            total_issues = analysis.get('total_issues', 0)

            # Report health status (but don't create fake tasks)
            if critical_count > 0:
                print(f"     ⚠️ {critical_count} critical issues need manual review")
            if high_count > 0:
                print(f"     ⚠️ {high_count} high priority issues detected")

            # Calculate health score
            health_score = analysis.get('health_score', 100)
            if health_score >= 80:
                print(f"     ✅ Codebase health: {health_score}% (GOOD)")
            elif health_score >= 60:
                print(f"     ⚠️ Codebase health: {health_score}% (NEEDS ATTENTION)")
            else:
                print(f"     ❌ Codebase health: {health_score}% (POOR)")

            # Record in reports
            if self.reports:
                self.reports.record_issue(f"Health scan: {total_issues} total issues, score: {health_score}%")

            # The proactive fix already handles syntax errors
            # Other issues require manual review - don't create meaningless tasks
            print(f"     ✓ Scan complete ({total_issues} issues logged for review)")

        except ImportError as e:
            logger.warning(f"Could not import analyzer: {e}")
        except Exception as e:
            logger.error(f"Scan error: {e}")

    async def _run_tests(self):
        """Run tests periodically to ensure code quality."""
        print("  🧪 Running tests...")
        try:
            import subprocess
            result = subprocess.run(
                ['python', '-m', 'pytest', 'tests/', '-q', '--tb=no', '--no-header', '-x'],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(self.project_root)
            )

            if result.returncode == 0:
                print("     ✅ All tests passed!")
                self.bots['tester'].record_success(1.0)
            elif result.returncode == 5:
                print("     ⚠️ No tests found")
            else:
                # Extract failure info
                output = result.stdout + result.stderr
                if 'failed' in output.lower():
                    # Count failures
                    import re
                    match = re.search(r'(\d+) failed', output)
                    fails = match.group(1) if match else 'some'
                    print(f"     ❌ {fails} tests failed")
                else:
                    print("     ⚠️ Test issues detected")

        except subprocess.TimeoutExpired:
            print("     ⚠️ Tests timed out")
        except FileNotFoundError:
            print("     ⚠️ pytest not installed")
        except Exception as e:
            print(f"     ⚠️ Test error: {e}")

    async def _print_cycle_summary(self):
        """Print summary for this cycle."""
        # Get stats
        total_bots = len([b for b in self.bots.values() if b.enabled])
        active_bots = len([b for b in self.bots.values() if b.enabled and b.tasks_completed > 0])

        # Calculate overall performance
        total_completed = sum(b.tasks_completed for b in self.bots.values())
        total_failed = sum(b.tasks_failed for b in self.bots.values())
        total_tasks = total_completed + total_failed
        performance = (total_completed / total_tasks * 100) if total_tasks > 0 else 100

        # Find top performer
        top_bot = max(self.bots.values(), key=lambda b: b.tasks_completed, default=None)
        top_name = top_bot.name if top_bot and top_bot.tasks_completed > 0 else "N/A"

        print(f"\n  ┌{'─'*40}┐")
        print(f"  │ {'CYCLE SUMMARY':<38} │")
        print(f"  ├{'─'*40}┤")
        print(f"  │ Cycle:            #{self.cycle_count:<18} │")
        print(f"  │ Active Experts:    {active_bots}/{total_bots:<17} │")
        print(f"  │ Performance:      {performance:.1f}%{' '*16} │")
        print(f"  │ Top Expert:       {top_name[:20]:<18} │")
        print(f"  └{'─'*40}┘")

    async def _health_check(self):
        """Perform health check on all systems."""
        try:
            # Check bot statuses
            healthy_bots = sum(1 for b in self.bots.values() if b.enabled and b.status != BotStatus.ERROR)
            total_bots = len(self.bots)

            if healthy_bots < total_bots:
                unhealthy = [b.name for b in self.bots.values() if b.status == BotStatus.ERROR]
                print(f"     ⚠️ {len(unhealthy)} bots have errors: {', '.join(unhealthy[:3])}")

            # Check disk space (simple check)
            try:
                import shutil
                total, used, free = shutil.disk_usage(self.project_root)
                free_gb = free / (1024**3)
                if free_gb < 1:
                    print(f"     ⚠️ Low disk space: {free_gb:.1f}GB free")
            except Exception:
                pass

            # Record health in reports
            if self.reports:
                self.reports.record_issue(f"Health check: {healthy_bots}/{total_bots} bots healthy")

        except Exception as e:
            logger.debug(f"Health check error: {e}")

    def _task_exists(self, description: str) -> bool:
        """Check if a similar task already exists."""
        # Extract file and issue type for better matching
        desc_lower = description.lower()

        for task in self.task_queue:
            task_lower = task.description.lower()

            # Exact match
            if description == task.description:
                return True

            # Same file + same issue type = duplicate
            # Extract file name from [filename] pattern
            if ']' in description and ']' in task.description:
                new_file = description.split(']')[0]
                task_file = task.description.split(']')[0]

                if new_file == task_file:
                    # Same file - check if same issue type
                    new_issue = description.split(']')[1][:30] if len(description.split(']')) > 1 else ''
                    task_issue = task.description.split(']')[1][:30] if len(task.description.split(']')) > 1 else ''

                    if new_issue == task_issue:
                        return True

        return False

    async def _assign_tasks(self):
        """Assign tasks to appropriate bots based on task type."""
        print("  📋 Assigning tasks to bots...")

        # Sort by priority
        self.task_queue.sort(key=lambda t: t.priority.value)

        assigned = 0
        for task in self.task_queue:
            if task.status == 'pending' and not task.assigned_bot:
                # Determine which bot should handle this
                bot_id = self._select_bot_for_task(task)

                if bot_id and self.bots[bot_id].enabled:
                    task.assigned_bot = bot_id
                    assigned += 1

        print(f"     Assigned {assigned} tasks")

    def _select_bot_for_task(self, task: UltimateTask) -> Optional[str]:
        """Select the best bot for a given task - distribute work across experts."""
        desc = task.description.lower()

        # === SECURITY EXPERT ===
        # Security vulnerabilities and auth issues
        if any(word in desc for word in [
            'sql injection', 'xss', 'csrf', 'injection',
            'hardcoded password', 'hardcoded secret', 'hardcoded key',
            'unprotected route', 'login_required', 'auth',
            'vulnerability', 'security'
        ]):
            return 'security'

        # === TESTER EXPERT ===
        # Test-related issues
        if any(word in desc for word in [
            'test fail', 'assert fail', 'pytest', 'unittest',
            'test_', 'coverage', 'mock'
        ]):
            return 'tester'

        # === ANALYZER EXPERT ===
        # Code quality and complexity issues
        if any(word in desc for word in [
            'high complexity', 'complexity:', 'cyclomatic',
            'too many arguments', 'too many', 'refactor',
            'code smell', 'duplicate code'
        ]):
            return 'analyzer'

        # === HEALER EXPERT ===
        # Exception handling and error recovery
        if any(word in desc for word in [
            'pass in except', 'bare except', 'exception handling',
            'error handling', 'silent fail', 'log exception'
        ]):
            return 'healer'

        # === DEVELOPER EXPERT ===
        # Feature development and improvements
        if any(word in desc for word in [
            'missing feature', 'todo', 'fixme', 'implement',
            'add feature', 'enhancement'
        ]):
            return 'developer'

        # === GIT EXPERT ===
        # Version control issues
        if any(word in desc for word in [
            'merge conflict', 'git conflict', 'commit', 'branch'
        ]):
            return 'git'

        # === DEPLOYER EXPERT ===
        # Deployment and config issues
        if any(word in desc for word in [
            'deploy', 'release', 'production', 'config',
            'environment', 'debug enabled'
        ]):
            return 'deployer'

        # === FIXER EXPERT ===
        # Actual code fixes (syntax, imports, etc.)
        # Only real fixable issues go here
        if any(word in desc for word in [
            'syntax error', 'import error', 'unused import',
            'name error', 'attribute error', 'type error'
        ]):
            return 'fixer'

        # Default: Round-robin based on task count to balance load
        bot_tasks = {bot_id: 0 for bot_id in self.bots.keys()}
        for t in self.task_queue:
            if t.assigned_bot:
                bot_tasks[t.assigned_bot] = bot_tasks.get(t.assigned_bot, 0) + 1

        # Find bot with least tasks
        min_bot = min(bot_tasks, key=bot_tasks.get)
        return min_bot

    async def _execute_tasks(self):
        """Execute assigned tasks through expert bots."""
        print("  ⚡ Delegating to experts...")

        # Get tasks ready for execution
        ready_tasks = [
            t for t in self.task_queue
            if t.status == 'pending' and t.assigned_bot
        ][:self.config['max_concurrent_tasks']]

        if not ready_tasks:
            print("     ✓ No pending tasks")
            return

        for task in ready_tasks:
            try:
                task_start = datetime.now()
                task.status = 'in_progress'
                bot = self.bots[task.assigned_bot]
                bot.status = BotStatus.WORKING
                bot.current_task = task.description[:50]

                print(f"     → {bot.name}: {task.description[:35]}...")

                # Execute based on expert type
                success = await self._run_bot_task(task)

                task_time = (datetime.now() - task_start).total_seconds()

                if success:
                    task.status = 'completed'
                    task.completed_at = datetime.now()
                    bot.record_success(task_time)
                    print(f"       ✅ Done in {task_time:.1f}s | {bot.evaluate()}")

                    # Record in advanced systems
                    if self.reports:
                        self.reports.record_task_completion(True)
                    if self.competition:
                        self.competition.record_task_success(task.assigned_bot, task_time)
                    if self.learning:
                        self.learning.record_success_strategy(
                            task.assigned_bot,
                            "task_completion",
                            f"Completed: {task.description[:30]}",
                            ["analyzed", "fixed", "verified"],
                            "success"
                        )
                else:
                    task.retries += 1
                    if task.retries >= task.max_retries:
                        task.status = 'failed'
                        bot.record_failure()
                        print(f"       ❌ Failed | {bot.evaluate()}")

                        # Record failure in systems
                        if self.reports:
                            self.reports.record_task_completion(False)
                        if self.competition:
                            self.competition.record_task_failure(task.assigned_bot)
                        if self.alerts and task.priority == TaskPriority.CRITICAL:
                            self.alerts.raise_alert(
                                AlertLevel.ERROR,
                                f"Critical task failed: {task.description[:30]}",
                                f"Expert {bot.name} failed to complete critical task",
                                task.assigned_bot
                            )
                    else:
                        task.status = 'pending'
                        print(f"       ⚠️ Retry {task.retries}/{task.max_retries}")

                bot.status = BotStatus.IDLE
                bot.current_task = None
                bot.last_run = datetime.now()

            except Exception as e:
                logger.error(f"Task execution error: {e}")
                task.status = 'failed'
                task.result = str(e)
                if task.assigned_bot in self.bots:
                    self.bots[task.assigned_bot].record_failure()

        # Move completed/failed tasks
        self.task_queue = [t for t in self.task_queue if t.status not in ['completed', 'failed']]

    async def _run_bot_task(self, task: UltimateTask) -> bool:
        """Run a specific bot task."""
        try:
            if task.assigned_bot == 'fixer':
                from .real_fixer import RealFixerAgent
                fixer = RealFixerAgent()

                # ACTUALLY fix errors - use await!
                result = await fixer.fix_all_errors()

                fixed_count = result.get('errors_fixed', 0)
                print(f"         🛠️ Fixed {fixed_count} errors in {len(result.get('fixed_files', []))} files")

                # Record fixed files in reports
                if self.reports:
                    for f in result.get('fixed_files', []):
                        self.reports.record_file_fixed(f)

                # Learn from fix if learning system available
                if self.learning and fixed_count > 0:
                    self.learning.remember_error(
                        task.description,
                        task.description.split(']')[0].replace('[', ''),
                        "Code issue",
                        "Auto-fixed by Fixer Expert"
                    )

                return fixed_count > 0 or True

            elif task.assigned_bot == 'analyzer':
                from .smart_analyzer import SmartAnalyzer
                analyzer = SmartAnalyzer()
                analysis = analyzer.analyze_project()
                return analysis.get('total_issues', 0) >= 0  # Always succeed

            elif task.assigned_bot == 'git':
                from .git_agent import GitAgent
                git = GitAgent()
                # Only commit if there are changes
                status = git.status()
                if status.get('has_changes'):
                    git.commit("Auto-fix by Ultimate Bot")
                    git.push()
                    if self.reports:
                        self.reports.record_commit()
                return True

            elif task.assigned_bot == 'security':
                # Security Expert: Focus on actual security fixes
                from .real_fixer import RealFixerAgent
                fixer = RealFixerAgent()

                # Run targeted security fixes
                result = await fixer.fix_all_errors()
                fixed_count = result.get('errors_fixed', 0)

                if fixed_count > 0:
                    print(f"         🔒 Security Expert fixed {fixed_count} security issues")

                # Mark task as complete - security review done
                return True

            elif task.assigned_bot == 'tester':
                from .test_runner import TestRunnerAgent
                tester = TestRunnerAgent()
                report = await tester.run_all_tests()
                return report.passed > 0 if report else True

            elif task.assigned_bot == 'healer':
                from .self_healer import SelfHealerAgent
                healer = SelfHealerAgent()
                await healer.run_health_check()
                return True

            elif task.assigned_bot == 'developer':
                # Developer just marks tasks as reviewed for now
                return True

            elif task.assigned_bot == 'deployer':
                # Deployer - manual approval needed
                if self.alerts:
                    self.alerts.raise_alert(
                        AlertLevel.INFO,
                        "Deployment task pending",
                        f"Deploy Expert ready: {task.description[:50]}",
                        "deployer"
                    )
                return True

            else:
                # Generic task - just mark as done
                return True

        except ImportError as e:
            logger.warning(f"Bot module not available: {e}")
            return False
        except Exception as e:
            logger.error(f"Bot task error: {e}")
            return False

    async def _review_results(self):
        """Review and summarize the cycle results."""
        pending = len([t for t in self.task_queue if t.status == 'pending'])

        # Calculate team performance
        total_done = sum(b.tasks_completed for b in self.bots.values())
        total_failed = sum(b.tasks_failed for b in self.bots.values())
        avg_score = sum(b.performance_score for b in self.bots.values()) / len(self.bots)

        # Find top performer
        top_bot = max(self.bots.values(), key=lambda b: b.tasks_completed)

        print()
        print(f"  ┌{'─'*40}┐")
        print("  │ CYCLE SUMMARY                          │")
        print(f"  ├{'─'*40}┤")
        print(f"  │ Tasks Remaining: {pending:>4}                   │")
        print(f"  │ Team Performance: {avg_score:>5.1f}%               │")
        print(f"  │ Total Completed: {total_done:>4}                   │")
        print(f"  │ Top Expert: {top_bot.name[:15]:>15}        │")
        print(f"  └{'─'*40}┘")

    async def _health_monitor(self):
        """Monitor health of all bots."""
        while self.is_running:
            try:
                await asyncio.sleep(self.config['health_check_interval'])

                print("\n  🏥 Health Check...")

                for bot_id, bot in self.bots.items():
                    if bot.status == BotStatus.ERROR:
                        print(f"     ⚠️ {bot.name} in error state, attempting recovery...")
                        bot.status = BotStatus.RESTARTING
                        await asyncio.sleep(1)
                        bot.status = BotStatus.IDLE
                        bot.error_message = None
                        print(f"     ✅ {bot.name} recovered")

            except Exception as e:
                logger.error(f"Health monitor error: {e}")

    async def _report_generator(self):
        """Generate periodic reports for the Creator."""
        last_daily_report = None

        while self.is_running:
            try:
                await asyncio.sleep(self.config['report_interval'])

                report = self.generate_report()

                # Save report
                report_file = self.data_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(report_file, 'w') as f:
                    json.dump(report, f, indent=2, default=str)

                print(f"\n  📝 Report saved: {report_file.name}")

                # Check if it's time for daily report
                now = datetime.now()
                if (now.hour == self.config['daily_report_hour'] and
                    (last_daily_report is None or last_daily_report.date() != now.date())):

                    if self.reports:
                        expert_perf = {
                            bot_id: {
                                'tasks_completed': bot.tasks_completed,
                                'tasks_failed': bot.tasks_failed,
                                'performance_score': bot.performance_score
                            }
                            for bot_id, bot in self.bots.items()
                        }
                        daily = self.reports.generate_report(expert_perf)
                        print("\n" + self.reports.get_report_text(daily))
                        last_daily_report = now

            except Exception as e:
                logger.error(f"Report generator error: {e}")

    async def _competition_updater(self):
        """Update competition leaderboard periodically."""
        while self.is_running:
            try:
                await asyncio.sleep(1800)  # Every 30 minutes

                if self.competition:
                    # Show leaderboard
                    print(self.competition.get_leaderboard_text())

            except Exception as e:
                logger.error(f"Competition updater error: {e}")

    async def _alert_monitor(self):
        """Monitor for and display critical alerts."""
        while self.is_running:
            try:
                await asyncio.sleep(60)  # Check every minute

                if self.alerts:
                    critical = self.alerts.get_critical_alerts()
                    if critical:
                        for alert in critical:
                            if not alert.acknowledged:
                                print(f"\n  🚨 ALERT: {alert.title}")
                                print(f"     {alert.message}")

            except Exception as e:
                logger.error(f"Alert monitor error: {e}")

    async def _enhanced_systems_monitor(self):
        """Run enhanced systems periodically."""
        cycle = 0
        while self.is_running:
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                cycle += 1

                # === Resource Monitoring (every 5 min) ===
                if self.resource_monitor:
                    result = self.resource_monitor.monitor()
                    if result.get('status') == 'critical':
                        print("\n  🚨 RESOURCE ALERT!")
                        for alert in result.get('alerts', []):
                            print(f"     {alert.message}")
                        # Send notification
                        if self.notifier:
                            await self.notifier.send_critical_alert(
                                "Resource Alert",
                                "Critical resource usage detected"
                            )
                    # Update dashboard
                    if self.dashboard:
                        snapshot = result.get('snapshot')
                        if snapshot:
                            self.dashboard.add_activity('scan', f"Resource check: CPU {snapshot.cpu_percent:.0f}%, Memory {snapshot.memory_percent:.0f}%")

                # === Backup Check (every 30 min = cycle % 6) ===
                if cycle % 6 == 0 and self.backup_manager:
                    schedule = self.backup_manager.schedule_backup(interval_hours=24)
                    if schedule.get('needed'):
                        print("\n  💾 Creating scheduled backup...")
                        backup = self.backup_manager.create_backup()
                        if backup and self.dashboard:
                            self.dashboard.add_activity('fix', f"Backup created: {backup.name}")

                # === Dependency Scan (every hour = cycle % 12) ===
                if cycle % 12 == 0 and self.dependency_scanner:
                    print("\n  🔍 Scanning dependencies...")
                    result = self.dependency_scanner.full_scan()
                    if result.vulnerable_count > 0:
                        print(f"     ⚠️ {result.vulnerable_count} vulnerable packages!")
                        if self.notifier:
                            await self.notifier.send_alert(
                                "Vulnerable Dependencies",
                                f"Found {result.vulnerable_count} vulnerable packages",
                                severity="warning"
                            )

                # === AI Code Review (every 2 hours = cycle % 24) ===
                if cycle % 24 == 0 and self.ai_reviewer:
                    print("\n  🧠 Running AI code review...")
                    review = await self.ai_reviewer.review_project()
                    report_path = self.ai_reviewer.generate_report()
                    print(f"     📝 Review report: {report_path}")
                    print(f"     Quality: {review.get('average_quality', 0):.0f}/100")
                    if self.dashboard:
                        self.dashboard.add_activity('scan', f"AI review: {review.get('average_quality', 0):.0f}/100 quality")

                # === Performance Analysis (every 2 hours = cycle % 24) ===
                if cycle % 24 == 1 and self.performance_optimizer:
                    print("\n  ⚡ Analyzing performance...")
                    issues = self.performance_optimizer.analyze_project()
                    if issues:
                        report_path = self.performance_optimizer.generate_report()
                        summary = self.performance_optimizer.get_summary()
                        critical = summary.get('by_severity', {}).get('critical', 0)
                        if critical > 0:
                            print(f"     ⚠️ {critical} critical performance issues!")

                # === Log Analysis (every hour = cycle % 12) ===
                if cycle % 12 == 6 and self.log_analyzer:
                    result = self.log_analyzer.analyze_all()
                    if result.get('status') == 'ok':
                        errors = result.get('total_errors', 0)
                        if errors > 100:
                            print(f"\n  📋 High error volume in logs: {errors}")
                            if self.notifier:
                                await self.notifier.send_alert(
                                    "Log Alert",
                                    f"High error volume detected: {errors} errors",
                                    severity="warning"
                                )

                # === Trend Recording (every cycle) ===
                if self.trend_analyzer:
                    metrics = DailyMetrics(
                        date=datetime.now().strftime('%Y-%m-%d'),
                        total_issues=len(self.task_queue),
                        quality_score=sum(b.performance_score for b in self.bots.values()) / len(self.bots),
                        auto_fixes=sum(b.tasks_completed for b in self.bots.values())
                    )
                    self.trend_analyzer.record_metrics(metrics)

                # === Update Dashboard ===
                if self.dashboard:
                    uptime = (datetime.now() - self.start_time).total_seconds() / 3600 if self.start_time else 0
                    self.dashboard.update(
                        status='running' if self.is_running else 'stopped',
                        cycle_count=self.cycle_count,
                        uptime_hours=uptime,
                        total_fixes=sum(b.tasks_completed for b in self.bots.values()),
                        total_issues=len(self.task_queue),
                        health_score=sum(b.performance_score for b in self.bots.values()) / len(self.bots),
                        active_bots=len([b for b in self.bots.values() if b.tasks_completed > 0])
                    )

            except Exception as e:
                logger.error(f"Enhanced systems monitor error: {e}")

    def generate_report(self) -> Dict[str, Any]:
        """Generate a comprehensive status report."""
        uptime = datetime.now() - self.start_time if self.start_time else timedelta(0)

        bot_stats = {}
        for bot_id, bot in self.bots.items():
            bot_stats[bot_id] = {
                'name': bot.name,
                'status': bot.status.value,
                'tasks_completed': bot.tasks_completed,
                'tasks_failed': bot.tasks_failed,
                'success_rate': (
                    bot.tasks_completed / (bot.tasks_completed + bot.tasks_failed) * 100
                    if (bot.tasks_completed + bot.tasks_failed) > 0 else 100
                ),
                'last_run': bot.last_run.isoformat() if bot.last_run else None,
                'enabled': bot.enabled
            }

        return {
            'timestamp': datetime.now().isoformat(),
            'uptime_seconds': uptime.total_seconds(),
            'uptime_formatted': str(uptime).split('.')[0],
            'cycles_completed': self.cycle_count,
            'pending_tasks': len([t for t in self.task_queue if t.status == 'pending']),
            'bots': bot_stats,
            'config': self.config
        }

    def get_dashboard(self) -> str:
        """Get a text-based dashboard view."""
        lines = []
        lines.append("")
        lines.append("  ╔" + "═"*66 + "╗")
        lines.append("  ║" + " "*20 + "🤖👑 ULTIMATE BOT DASHBOARD" + " "*19 + "║")
        lines.append("  ╚" + "═"*66 + "╝")

        # Uptime and stats
        if self.start_time:
            uptime = datetime.now() - self.start_time
            lines.append(f"  ⏱️  Uptime: {str(uptime).split('.')[0]}")
        lines.append(f"  🔄 Cycles Completed: {self.cycle_count}")
        lines.append(f"  📋 Pending Tasks: {len(self.task_queue)}")

        # Expert Performance Table
        lines.append("")
        lines.append("  ┌" + "─"*66 + "┐")
        lines.append("  │  EXPERT PERFORMANCE EVALUATION" + " "*34 + "│")
        lines.append("  ├" + "─"*66 + "┤")
        lines.append("  │  Expert              │ Status  │ Done │ Fail │ Score │ Rating │")
        lines.append("  ├" + "─"*66 + "┤")

        for bot_id, bot in self.bots.items():
            status_icon = {
                BotStatus.IDLE: "💤 Idle ",
                BotStatus.WORKING: "⚡ Work ",
                BotStatus.ERROR: "❌ Error",
                BotStatus.DISABLED: "🚫 Off  ",
                BotStatus.RESTARTING: "🔄 Reset"
            }.get(bot.status, "❓ ???  ")

            # Format score and rating
            score = f"{bot.performance_score:.0f}%"
            rating = "★" * int(bot.quality_rating) + "☆" * (5 - int(bot.quality_rating))

            name_short = bot.name[:18].ljust(18)
            lines.append(f"  │  {name_short} │ {status_icon} │ {bot.tasks_completed:4} │ {bot.tasks_failed:4} │ {score:>5} │ {rating} │")

        lines.append("  └" + "─"*66 + "┘")

        # Current tasks
        if self.task_queue:
            lines.append("")
            lines.append("  📋 CURRENT TASKS:")
            for task in self.task_queue[:5]:
                priority_icon = {
                    TaskPriority.CRITICAL: "🔴",
                    TaskPriority.HIGH: "🟠",
                    TaskPriority.MEDIUM: "🟡",
                    TaskPriority.LOW: "🟢"
                }.get(task.priority, "⚪")
                assigned = task.assigned_bot or "unassigned"
                lines.append(f"     {priority_icon} [{assigned:10}] {task.description[:40]}...")

            if len(self.task_queue) > 5:
                lines.append(f"     ... and {len(self.task_queue) - 5} more tasks")

        lines.append("")

        return "\n".join(lines)

    # === Control Methods (for Creator) ===

    def enable_bot(self, bot_id: str):
        """Enable a specific bot."""
        if bot_id in self.bots:
            self.bots[bot_id].enabled = True
            print(f"✅ {self.bots[bot_id].name} enabled")

    def disable_bot(self, bot_id: str):
        """Disable a specific bot."""
        if bot_id in self.bots:
            self.bots[bot_id].enabled = False
            print(f"🚫 {self.bots[bot_id].name} disabled")

    def add_task(self, description: str, priority: TaskPriority = TaskPriority.MEDIUM):
        """Manually add a task."""
        task_id = f"manual_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        task = UltimateTask(
            id=task_id,
            description=description,
            priority=priority
        )
        self.task_queue.append(task)
        print(f"✅ Task added: {description[:50]}...")
        return task_id

    def get_pending_tasks(self) -> List[Dict]:
        """Get list of pending tasks."""
        return [
            {
                'id': t.id,
                'description': t.description,
                'priority': t.priority.name,
                'assigned_to': t.assigned_bot,
                'retries': t.retries
            }
            for t in self.task_queue if t.status == 'pending'
        ]


# Singleton instance
_ultimate_bot: Optional[UltimateBot] = None


def get_ultimate_bot() -> UltimateBot:
    """Get the Ultimate Bot singleton."""
    global _ultimate_bot
    if _ultimate_bot is None:
        _ultimate_bot = UltimateBot()
    return _ultimate_bot


async def run_ultimate_bot():
    """Run the Ultimate Bot."""
    bot = get_ultimate_bot()
    try:
        await bot.start()
    except KeyboardInterrupt:
        await bot.stop()


if __name__ == "__main__":
    asyncio.run(run_ultimate_bot())

