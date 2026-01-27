"""
Trading Agent
=============

Monitors trading features including:
- Scalping module
- Swing trading module
- Paper trading system
- Trade signals
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

from agents.base import BaseAgent, AgentResult, AgentStatus, AgentTask, TaskType

logger = logging.getLogger(__name__)


class TradingAgent(BaseAgent):
    """
    Agent for monitoring trading features.
    
    Checks:
    - Scalping analysis functionality
    - Swing trading (ICT/SMC) module
    - Paper trading system
    - Trade signals generation
    - Position tracking
    """
    
    def __init__(self):
        super().__init__(
            name="trading",
            category="Trading",
            description="Monitors trading features: scalping, swing, paper trading, and signals"
        )
    
    def _register_tasks(self) -> None:
        """Register trading monitoring tasks."""
        self.register_task(AgentTask(
            id="scalp_service",
            name="Scalp Service Status",
            task_type=TaskType.STATUS_CHECK,
            description="Check scalping analysis service health",
            handler=self._check_scalp_service,
            interval_seconds=300,
        ))
        
        self.register_task(AgentTask(
            id="swing_service",
            name="Swing Service Status",
            task_type=TaskType.STATUS_CHECK,
            description="Check ICT/SMC swing trading service health",
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
        
        # Run status checks
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
            suggestions=list(set(suggestions))  # Remove duplicates
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
            "Add position sizing calculator based on Kelly criterion",
            "Integrate TradingView charts for advanced analysis",
            "Add multi-timeframe confluence analysis",
            "Implement order block detection algorithm",
            "Add fair value gap (FVG) scanner",
            "Create institutional order flow visualization",
            "Add automated trade journal entries from paper trades",
            "Implement profit target and stop-loss automation",
        ]
        
        return AgentResult(
            success=True,
            status=AgentStatus.HEALTHY,
            message=f"{len(suggestions)} development suggestions",
            suggestions=suggestions,
            data={"category": "Trading Features"}
        )
    
    async def _check_scalp_service(self) -> AgentResult:
        """Check scalping service health."""
        try:
            from web.scalp_service import ScalpService
            
            service = ScalpService()
            
            # Try to analyze a sample stock
            result = service.analyze("SPY")
            
            if result:
                return AgentResult(
                    success=True,
                    status=AgentStatus.HEALTHY,
                    message="Scalp service operational",
                    data={"sample_analysis": bool(result)}
                )
            else:
                return AgentResult(
                    success=True,
                    status=AgentStatus.WARNING,
                    message="Scalp service responded but no data returned",
                    warnings=["Analysis returned empty - might be outside market hours"]
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
        """Check swing trading service health."""
        try:
            from web.swing_service import SwingService
            
            service = SwingService()
            
            # Try to get swing analysis
            result = service.analyze("AAPL")
            
            if result:
                return AgentResult(
                    success=True,
                    status=AgentStatus.HEALTHY,
                    message="Swing service operational",
                    data={"sample_analysis": bool(result)}
                )
            else:
                return AgentResult(
                    success=True,
                    status=AgentStatus.WARNING,
                    message="Swing service responded but no data returned",
                    warnings=["Analysis returned empty"]
                )
        except Exception as e:
            return AgentResult(
                success=False,
                status=AgentStatus.ERROR,
                message=f"Swing service check failed: {e}",
                errors=[str(e)],
                suggestions=["Check swing_service.py for errors"]
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
                ).count()
                
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
                active_signals = Signal.query.filter_by(status="active").count()
                pending_signals = Signal.query.filter_by(status="pending").count()
                
                # Success rate
                closed_signals = Signal.query.filter(Signal.status.in_(["success", "failed"])).all()
                if closed_signals:
                    success_rate = sum(1 for s in closed_signals if s.status == "success") / len(closed_signals) * 100
                else:
                    success_rate = None
                
                return AgentResult(
                    success=True,
                    status=AgentStatus.HEALTHY,
                    message=f"Signals: {active_signals} active, {pending_signals} pending",
                    data={
                        "total_signals": total_signals,
                        "active_signals": active_signals,
                        "pending_signals": pending_signals,
                        "success_rate": success_rate
                    }
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
                
                # Check freshness
                recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
                recent_scores = AIScore.query.filter(
                    AIScore.updated_at >= recent_cutoff
                ).count()
                
                if total_scores == 0:
                    return AgentResult(
                        success=False,
                        status=AgentStatus.ERROR,
                        message="No AI scores in database",
                        errors=["AI score table is empty"],
                        suggestions=["Run cron_update_ai_scores.py"]
                    )
                
                if recent_scores == 0:
                    return AgentResult(
                        success=True,
                        status=AgentStatus.WARNING,
                        message=f"AI scores not updated in 24h (total: {total_scores})",
                        warnings=["Scores may be stale"],
                        suggestions=["Run cron_update_ai_scores.py to refresh"]
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
        except Exception as e:
            return AgentResult(
                success=False,
                status=AgentStatus.ERROR,
                message=f"AI score check failed: {e}",
                errors=[str(e)]
            )

