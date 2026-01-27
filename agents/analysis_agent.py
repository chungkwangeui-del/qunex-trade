"""
Analysis Agent
==============

Monitors analysis features including:
- Pattern recognition
- Sentiment analysis
- Options analysis
- Technical analysis
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

from agents.base import BaseAgent, AgentResult, AgentStatus, AgentTask, TaskType

logger = logging.getLogger(__name__)


class AnalysisAgent(BaseAgent):
    """
    Agent for monitoring analysis features.
    
    Checks:
    - Chart pattern recognition
    - Sentiment analysis service
    - Options flow analysis
    - Technical indicators
    - Advanced S/R analysis
    """
    
    def __init__(self):
        super().__init__(
            name="analysis",
            category="Analysis",
            description="Monitors analysis tools: patterns, sentiment, options, technical"
        )
    
    def _register_tasks(self) -> None:
        """Register analysis monitoring tasks."""
        self.register_task(AgentTask(
            id="pattern_recognition",
            name="Pattern Recognition Service",
            task_type=TaskType.STATUS_CHECK,
            description="Check chart pattern recognition functionality",
            handler=self._check_pattern_service,
            interval_seconds=600,
        ))
        
        self.register_task(AgentTask(
            id="sentiment_analysis",
            name="Sentiment Analysis Service",
            task_type=TaskType.STATUS_CHECK,
            description="Check sentiment analysis service health",
            handler=self._check_sentiment_service,
            interval_seconds=600,
        ))
        
        self.register_task(AgentTask(
            id="technical_analysis",
            name="Technical Analysis Service",
            task_type=TaskType.STATUS_CHECK,
            description="Verify technical indicators calculation",
            handler=self._check_technical_analysis,
            interval_seconds=300,
        ))
        
        self.register_task(AgentTask(
            id="advanced_sr",
            name="Advanced S/R Analysis",
            task_type=TaskType.STATUS_CHECK,
            description="Check advanced support/resistance analysis",
            handler=self._check_advanced_sr,
            interval_seconds=600,
        ))
        
        self.register_task(AgentTask(
            id="detected_patterns",
            name="Detected Patterns Status",
            task_type=TaskType.MONITORING,
            description="Monitor detected chart patterns in database",
            handler=self._check_detected_patterns,
            interval_seconds=1800,
        ))
    
    async def check_status(self) -> AgentResult:
        """Run all analysis feature checks."""
        results = await self.run_all_tasks(TaskType.STATUS_CHECK)
        
        all_healthy = all(r.status == AgentStatus.HEALTHY for r in results.values())
        has_errors = any(r.status in [AgentStatus.ERROR, AgentStatus.CRITICAL] for r in results.values())
        
        if all_healthy:
            status = AgentStatus.HEALTHY
            message = "All analysis features operational"
        elif has_errors:
            status = AgentStatus.ERROR
            message = "Analysis feature issues detected"
        else:
            status = AgentStatus.WARNING
            message = "Some analysis features have warnings"
        
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
        """Diagnose analysis system issues."""
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
        """Attempt to fix analysis errors."""
        fixes_available = []
        fixes_applied = []
        
        # Check sentiment data freshness
        try:
            from web.database import db, SentimentData
            from web.app import create_app
            
            app = create_app()
            with app.app_context():
                recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
                stale_count = SentimentData.query.filter(
                    SentimentData.updated_at < recent_cutoff
                ).count()
                
                if stale_count > 0:
                    fixes_available.append(f"Update {stale_count} stale sentiment records")
        except Exception:
            pass
        
        if not fixes_available:
            return AgentResult(
                success=True,
                status=AgentStatus.HEALTHY,
                message="No fixes needed"
            )
        
        return AgentResult(
            success=True,
            status=AgentStatus.WARNING,
            message=f"{len(fixes_available)} fix(es) available",
            suggestions=fixes_available,
            data={"fixes_available": fixes_available}
        )
    
    async def get_development_suggestions(self) -> AgentResult:
        """Suggest analysis feature improvements."""
        suggestions = [
            "Add machine learning-based pattern prediction",
            "Implement Wyckoff accumulation/distribution detection",
            "Add Elliott Wave analysis automation",
            "Integrate natural language processing for news sentiment",
            "Add correlation analysis between assets",
            "Implement intermarket analysis dashboard",
            "Add volume profile analysis (POC, VAH, VAL)",
            "Create market structure break detection",
            "Add order flow imbalance indicators",
            "Implement Fibonacci auto-detection",
        ]
        
        return AgentResult(
            success=True,
            status=AgentStatus.HEALTHY,
            message=f"{len(suggestions)} development suggestions",
            suggestions=suggestions,
            data={"category": "Analysis Features"}
        )
    
    async def _check_pattern_service(self) -> AgentResult:
        """Check pattern recognition service."""
        try:
            from web.pattern_recognition import PatternRecognition
            
            pr = PatternRecognition()
            
            return AgentResult(
                success=True,
                status=AgentStatus.HEALTHY,
                message="Pattern recognition service available",
                data={"service": "PatternRecognition"}
            )
        except Exception as e:
            return AgentResult(
                success=False,
                status=AgentStatus.ERROR,
                message=f"Pattern recognition check failed: {e}",
                errors=[str(e)],
                suggestions=["Check pattern_recognition.py for errors"]
            )
    
    async def _check_sentiment_service(self) -> AgentResult:
        """Check sentiment analysis service."""
        try:
            from web.sentiment_service import SentimentService
            
            service = SentimentService()
            
            return AgentResult(
                success=True,
                status=AgentStatus.HEALTHY,
                message="Sentiment service available",
                data={"service": "SentimentService"}
            )
        except Exception as e:
            return AgentResult(
                success=False,
                status=AgentStatus.ERROR,
                message=f"Sentiment service check failed: {e}",
                errors=[str(e)],
                suggestions=["Check sentiment_service.py for errors"]
            )
    
    async def _check_technical_analysis(self) -> AgentResult:
        """Check technical analysis functionality."""
        try:
            from web.technical_analysis import TechnicalAnalysis
            
            ta = TechnicalAnalysis()
            
            return AgentResult(
                success=True,
                status=AgentStatus.HEALTHY,
                message="Technical analysis service available",
                data={"service": "TechnicalAnalysis"}
            )
        except Exception as e:
            return AgentResult(
                success=False,
                status=AgentStatus.ERROR,
                message=f"Technical analysis check failed: {e}",
                errors=[str(e)],
                suggestions=["Check technical_analysis.py for errors"]
            )
    
    async def _check_advanced_sr(self) -> AgentResult:
        """Check advanced S/R analysis."""
        try:
            from web.advanced_sr_analysis import AdvancedSRAnalysis
            
            sr = AdvancedSRAnalysis()
            
            return AgentResult(
                success=True,
                status=AgentStatus.HEALTHY,
                message="Advanced S/R analysis service available",
                data={"service": "AdvancedSRAnalysis"}
            )
        except Exception as e:
            return AgentResult(
                success=False,
                status=AgentStatus.ERROR,
                message=f"Advanced S/R check failed: {e}",
                errors=[str(e)],
                suggestions=["Check advanced_sr_analysis.py for errors"]
            )
    
    async def _check_detected_patterns(self) -> AgentResult:
        """Check detected patterns in database."""
        try:
            from web.database import db, ChartPattern
            from web.app import create_app
            
            app = create_app()
            with app.app_context():
                total_patterns = ChartPattern.query.count()
                
                recent_cutoff = datetime.now(timezone.utc) - timedelta(days=7)
                recent_patterns = ChartPattern.query.filter(
                    ChartPattern.detected_at >= recent_cutoff
                ).count()
                
                # Pattern by status
                forming = ChartPattern.query.filter_by(status="forming").count()
                complete = ChartPattern.query.filter_by(status="complete").count()
                triggered = ChartPattern.query.filter_by(status="triggered").count()
                
                return AgentResult(
                    success=True,
                    status=AgentStatus.HEALTHY,
                    message=f"Patterns: {total_patterns} total, {recent_patterns} recent",
                    data={
                        "total_patterns": total_patterns,
                        "recent_patterns_7d": recent_patterns,
                        "forming": forming,
                        "complete": complete,
                        "triggered": triggered
                    }
                )
        except Exception as e:
            return AgentResult(
                success=False,
                status=AgentStatus.ERROR,
                message=f"Pattern check failed: {e}",
                errors=[str(e)]
            )

