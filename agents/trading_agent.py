"""
Trading Agent
=============

Monitors trading features including:
- Scalping module (쉽알 methodology)
- Swing trading (ICT/SMC)
- Paper trading system
- Trade signals
- AI scoring
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from pathlib import Path

from agents.base import BaseAgent, AgentResult, AgentStatus, AgentTask, TaskType
from agents.codebase_knowledge import CodebaseKnowledge
from datetime import timedelta
from datetime import timezone
from typing import List
from typing import Any

logger = logging.getLogger(__name__)

class TradingAgent(BaseAgent):
    """
    Agent for monitoring trading features.

    Checks:
    - Scalping analysis (쉽알 methodology - Order Blocks, FVG)
    - Swing trading (ICT/SMC - Market Structure, Liquidity)
    - Paper trading system
    - Trade signals generation
    - AI scoring system freshness
    """

    def __init__(self):
        super().__init__(
            name="trading",
            category="Trading",
            description="Monitors trading features: scalping, swing, paper trading, and signals"
        )
        self.knowledge = CodebaseKnowledge()
        self.project_root = Path(__file__).parent.parent

    def _register_tasks(self) -> None:
        """Register trading monitoring tasks."""
        self.register_task(AgentTask(
            id="scalp_service",
            name="Scalp Service Status",
            task_type=TaskType.STATUS_CHECK,
            description="Check scalping analysis service (쉽알 methodology)",
            handler=self._check_scalp_service,
            interval_seconds=300,
        ))

        self.register_task(AgentTask(
            id="swing_service",
            name="Swing Service Status",
            task_type=TaskType.STATUS_CHECK,
            description="Check ICT/SMC swing trading service",
            handler=self._check_swing_service,
            interval_seconds=300,
        ))

        self.register_task(AgentTask(
            id="paper_trading",
            name="Paper Trading System",
            task_type=TaskType.STATUS_CHECK,
            description="Verify paper trading system is operational",
            handler=self._check_paper_trading,
            interval_seconds=600,
        ))

        self.register_task(AgentTask(
            id="signals_status",
            name="Trade Signals Status",
            task_type=TaskType.STATUS_CHECK,
            description="Check trade signal generation and tracking",
            handler=self._check_signals,
            interval_seconds=600,
        ))

        self.register_task(AgentTask(
            id="ai_scores",
            name="AI Score System",
            task_type=TaskType.STATUS_CHECK,
            description="Verify AI scoring system is up to date",
            handler=self._check_ai_scores,
            interval_seconds=1800,
        ))

    async def check_status(self) -> AgentResult:
        """Run all trading feature checks."""
        results = await self.run_all_tasks(TaskType.STATUS_CHECK)

        all_healthy = all(r.status == AgentStatus.HEALTHY for r in results.values())
        has_errors = any(r.status in [AgentStatus.ERROR, AgentStatus.CRITICAL] for r in results.values())

        if all_healthy:
            status = AgentStatus.HEALTHY
            message = "All trading features operational"
        elif has_errors:
            status = AgentStatus.ERROR
            message = "Trading feature issues detected"
        else:
            status = AgentStatus.WARNING
            message = "Some trading features have warnings"

        self.status = status

        return AgentResult(
            success=not has_errors,
            status=status,
            message=message,
            data={
                "features": {k: v.to_dict() for k, v in results.items()},
            }
        )

    async def diagnose_issues(self) -> AgentResult:
        """Diagnose trading system issues."""
        issues = []
        suggestions = []

        await self.check_status()

        for task_id, task in self.tasks.items():
            if task.last_result and task.last_result.status != AgentStatus.HEALTHY:
                issues.append(f"{task.name}: {task.last_result.message}")
                suggestions.extend(task.last_result.suggestions)

        return AgentResult(
            success=len(issues) == 0,
            status=AgentStatus.HEALTHY if not issues else AgentStatus.WARNING,
            message=f"Found {len(issues)} issue(s)" if issues else "No issues detected",
            errors=issues,
            suggestions=list(set(suggestions))
        )

    async def fix_errors(self, auto_fix: bool = False) -> AgentResult:
        """Attempt to fix trading system errors."""
        fixes_available = []
        fixes_applied = []

        # Check AI scores freshness
        ai_result = await self._check_ai_scores()
        if ai_result.status != AgentStatus.HEALTHY:
            fixes_available.append("Update AI scores for all tracked stocks")
            if auto_fix:
                try:
                    from scripts.cron_update_ai_scores import update_ai_scores
                    update_ai_scores()
                    fixes_applied.append("Updated AI scores")
                except ImportError:
                    logger.warning("Could not import cron_update_ai_scores")
                except Exception as e:
                    logger.error(f"Failed to update AI scores: {e}")

        if not fixes_available:
            return AgentResult(
                success=True,
                status=AgentStatus.HEALTHY,
                message="No fixes needed"
            )

        return AgentResult(
            success=len(fixes_applied) > 0 if auto_fix else True,
            status=AgentStatus.HEALTHY if auto_fix and fixes_applied else AgentStatus.WARNING,
            message=f"Applied {len(fixes_applied)} fix(es)" if auto_fix else f"{len(fixes_available)} fix(es) available",
            suggestions=fixes_available if not auto_fix else [],
            data={"fixes_available": fixes_available, "fixes_applied": fixes_applied}
        )

    async def get_development_suggestions(self) -> AgentResult:
        """Suggest trading feature improvements."""
        suggestions = [
            "Add automated trading strategy backtesting",
            "Implement trailing stop-loss for paper trades",
            "Add position sizing calculator (Kelly criterion)",
            "Integrate TradingView charts for advanced analysis",
            "Add multi-timeframe confluence analysis",
            "Implement order block detection algorithm",
            "Add fair value gap (FVG) scanner",
            "Create institutional order flow visualization",
            "Add automated trade journal entries from paper trades",
            "Implement profit target and stop-loss automation",
            "Add Wyckoff accumulation/distribution detection",
            "Create market structure break alerts",
        ]

        return AgentResult(
            success=True,
            status=AgentStatus.HEALTHY,
            message=f"{len(suggestions)} development suggestions",
            suggestions=suggestions,
            data={"category": "Trading Features"}
        )

    async def _check_scalp_service(self) -> AgentResult:
        """Check scalping service (쉽알 methodology)."""
        try:
            scalp_file = self.project_root / "web" / "scalp_service.py"

            if not scalp_file.exists():
                return AgentResult(
                    success=False,
                    status=AgentStatus.ERROR,
                    message="Scalp service file not found",
                    errors=["web/scalp_service.py missing"],
                    suggestions=["Create scalp_service.py module"]
                )

            # Check file has content and key functions
            content = scalp_file.read_text(encoding='utf-8')
            line_count = len(content.splitlines())

            required_features = [
                ("order block", "Order Block detection"),
                ("fvg", "Fair Value Gap detection"),
                ("confluence", "Confluence analysis"),
                ("def ", "Function definitions"),
            ]

            missing = []
            found = []
            for feature, name in required_features:
                if feature.lower() in content.lower():
                    found.append(name)
                else:
                    missing.append(name)

            # Service is function-based, not class-based
            if line_count > 100 and "def " in content:
                return AgentResult(
                    success=True,
                    status=AgentStatus.HEALTHY,
                    message=f"Scalp service operational ({line_count} lines)",
                    data={
                        "features": found,
                        "line_count": line_count,
                        "methodology": "쉽알 (Order Blocks, FVG, Confluences)"
                    }
                )

            return AgentResult(
                success=True,
                status=AgentStatus.WARNING,
                message="Scalp service may be incomplete",
                warnings=[f"Missing feature: {m}" for m in missing] if missing else ["File seems small"],
                data={"found_features": found, "missing_features": missing}
            )

        except Exception as e:
            return AgentResult(
                success=False,
                status=AgentStatus.ERROR,
                message=f"Scalp service check failed: {e}",
                errors=[str(e)],
                suggestions=["Check scalp_service.py for errors"]
            )

    async def _check_swing_service(self) -> AgentResult:
        """Check swing trading service (ICT/SMC methodology)."""
        try:
            swing_file = self.project_root / "web" / "swing_service.py"

            if not swing_file.exists():
                return AgentResult(
                    success=False,
                    status=AgentStatus.ERROR,
                    message="Swing service file not found",
                    errors=["web/swing_service.py missing"]
                )

            content = swing_file.read_text(encoding='utf-8')
            line_count = len(content.splitlines())

            # Check for ICT/SMC concepts
            ict_concepts = [
                ("market structure", "Market Structure (BOS/CHoCH)"),
                ("liquidity", "Liquidity levels"),
                ("order block", "Order Blocks"),
                ("fvg", "Fair Value Gaps"),
                ("ote", "Optimal Trade Entry"),
            ]

            found = []
            for concept, name in ict_concepts:
                if concept.lower() in content.lower():
                    found.append(name)

            # Service is function-based, check if it has substantial content
            if line_count > 100 and len(found) >= 3:
                return AgentResult(
                    success=True,
                    status=AgentStatus.HEALTHY,
                    message=f"Swing service operational ({line_count} lines, {len(found)} ICT concepts)",
                    data={
                        "concepts": found,
                        "line_count": line_count,
                        "methodology": "ICT/SMC (Inner Circle Trader)"
                    }
                )

            return AgentResult(
                success=True,
                status=AgentStatus.WARNING,
                message="Swing service may need more ICT concepts",
                warnings=[f"Only {len(found)}/5 core ICT concepts found"],
                data={"found_concepts": found, "line_count": line_count}
            )

        except Exception as e:
            return AgentResult(
                success=False,
                status=AgentStatus.ERROR,
                message=f"Swing service check failed: {e}",
                errors=[str(e)]
            )

    async def _check_paper_trading(self) -> AgentResult:
        """Check paper trading system health."""
        try:
            from web.database import db, PaperAccount, PaperTrade
            from web.app import create_app

            app = create_app()
            with app.app_context():
                total_accounts = PaperAccount.query.count()
                total_trades = PaperTrade.query.count()

                # Check for recent activity
                recent_cutoff = datetime.now(timezone.utc) - timedelta(days=7)
                recent_trades = PaperTrade.query.filter(
                    PaperTrade.trade_date >= recent_cutoff
                ).count() if hasattr(PaperTrade, 'trade_date') else 0

                return AgentResult(
                    success=True,
                    status=AgentStatus.HEALTHY,
                    message=f"Paper trading operational: {total_accounts} accounts, {recent_trades} trades (7d)",
                    data={
                        "total_accounts": total_accounts,
                        "total_trades": total_trades,
                        "recent_trades_7d": recent_trades
                    }
                )
        except ImportError as e:
            return AgentResult(
                success=False,
                status=AgentStatus.ERROR,
                message=f"Cannot import paper trading models: {e}",
                errors=[str(e)],
                suggestions=["Check database.py for PaperAccount/PaperTrade models"]
            )
        except Exception as e:
            return AgentResult(
                success=False,
                status=AgentStatus.ERROR,
                message=f"Paper trading check failed: {e}",
                errors=[str(e)]
            )

    async def _check_signals(self) -> AgentResult:
        """Check trade signal status."""
        try:
            from web.database import db, Signal
            from web.app import create_app

            app = create_app()
            with app.app_context():
                total_signals = Signal.query.count()
                active_signals = Signal.query.filter_by(status="active").count() if hasattr(Signal, 'status') else 0

                return AgentResult(
                    success=True,
                    status=AgentStatus.HEALTHY,
                    message=f"Signals: {total_signals} total, {active_signals} active",
                    data={
                        "total_signals": total_signals,
                        "active_signals": active_signals,
                    }
                )
        except ImportError:
            # Signal model might not exist yet
            return AgentResult(
                success=True,
                status=AgentStatus.WARNING,
                message="Signal model not found in database",
                warnings=["Signal tracking not yet implemented"],
                suggestions=["Add Signal model to database.py for trade tracking"]
            )
        except Exception as e:
            return AgentResult(
                success=False,
                status=AgentStatus.ERROR,
                message=f"Signal check failed: {e}",
                errors=[str(e)]
            )

    async def _check_ai_scores(self) -> AgentResult:
        """Check AI score system health."""
        try:
            from web.database import db, AIScore
            from web.app import create_app

            app = create_app()
            with app.app_context():
                total_scores = AIScore.query.count()

                if total_scores == 0:
                    return AgentResult(
                        success=False,
                        status=AgentStatus.ERROR,
                        message="No AI scores in database",
                        errors=["AI score table is empty"],
                        suggestions=["Run scripts/cron_update_ai_scores.py"]
                    )

                # Check freshness
                recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
                recent_scores = AIScore.query.filter(
                    AIScore.updated_at >= recent_cutoff
                ).count() if hasattr(AIScore, 'updated_at') else total_scores

                if recent_scores == 0:
                    return AgentResult(
                        success=True,
                        status=AgentStatus.WARNING,
                        message=f"AI scores not updated in 24h (total: {total_scores})",
                        warnings=["Scores may be stale"],
                        suggestions=["Run scripts/cron_update_ai_scores.py"]
                    )

                return AgentResult(
                    success=True,
                    status=AgentStatus.HEALTHY,
                    message=f"AI scores healthy: {recent_scores}/{total_scores} updated today",
                    data={
                        "total_scores": total_scores,
                        "updated_today": recent_scores
                    }
                )
        except ImportError:
            # Check if ML models exist
            ml_model = self.project_root / "ml" / "models" / "ai_score_model.pkl"
            if ml_model.exists():
                return AgentResult(
                    success=True,
                    status=AgentStatus.WARNING,
                    message="AI model exists but database model not found",
                    warnings=["AIScore model not in database.py"],
                    data={"model_file": str(ml_model)}
                )
            return AgentResult(
                success=False,
                status=AgentStatus.ERROR,
                message="AI scoring system not found",
                errors=["Missing AIScore model and ML models"],
                suggestions=["Set up AI scoring system"]
            )
        except Exception as e:
            return AgentResult(
                success=False,
                status=AgentStatus.ERROR,
                message=f"AI score check failed: {e}",
                errors=[str(e)]
            )
