"""
Analysis Agent
==============

Monitors analysis features including:
- Pattern recognition (Head/Shoulders, Triangles, etc.)
- Sentiment analysis
- Technical analysis (RSI, MACD, Bollinger)
- Advanced Support/Resistance
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

class AnalysisAgent(BaseAgent):
    """
    Agent for monitoring analysis features.

    Checks:
    - Chart pattern recognition
    - Sentiment analysis service
    - Technical indicators
    - Advanced S/R analysis
    """

    def __init__(self):
        super().__init__(
            name="analysis",
            category="Analysis",
            description="Monitors analysis tools: patterns, sentiment, technical indicators"
        )
        self.knowledge = CodebaseKnowledge()
        self.project_root = Path(__file__).parent.parent

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

        # Check sentiment data freshness
        try:
            from web.database import SentimentData
            from web.app import create_app

            app = create_app()
            with app.app_context():
                recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
                stale_count = SentimentData.query.filter(
                    SentimentData.updated_at < recent_cutoff
                ).count() if hasattr(SentimentData, 'updated_at') else 0

                if stale_count > 0:
                    fixes_available.append(f"Update {stale_count} stale sentiment records")
        except Exception as e:
            logger.error(f"Error checking sentiment freshness: {e}")

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
            "Integrate NLP for news sentiment analysis",
            "Add correlation analysis between assets",
            "Implement intermarket analysis dashboard",
            "Add volume profile analysis (POC, VAH, VAL)",
            "Create market structure break detection",
            "Add order flow imbalance indicators",
            "Implement Fibonacci auto-detection",
            "Add Gann analysis tools",
            "Create volatility smile visualization for options",
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
            pattern_file = self.project_root / "web" / "pattern_recognition.py"

            if not pattern_file.exists():
                return AgentResult(
                    success=False,
                    status=AgentStatus.ERROR,
                    message="Pattern recognition file not found",
                    errors=["web/pattern_recognition.py missing"]
                )

            content = pattern_file.read_text(encoding='utf-8')
            line_count = len(content.splitlines())

            # Check for pattern types
            patterns = [
                ("head and shoulders", "Head & Shoulders"),
                ("double top", "Double Top/Bottom"),
                ("triangle", "Triangle patterns"),
                ("wedge", "Wedge patterns"),
                ("flag", "Flag patterns"),
                ("channel", "Channel patterns"),
            ]

            found = []
            for pattern, name in patterns:
                if pattern.lower() in content.lower():
                    found.append(name)

            if line_count > 100 and "def " in content:
                return AgentResult(
                    success=True,
                    status=AgentStatus.HEALTHY,
                    message=f"Pattern recognition available ({line_count} lines, {len(found)} patterns)",
                    data={
                        "pattern_types": found,
                        "line_count": line_count,
                        "file": "web/pattern_recognition.py"
                    }
                )

            return AgentResult(
                success=True,
                status=AgentStatus.WARNING,
                message="Pattern recognition may be incomplete",
                warnings=[f"Only {len(found)} pattern types found"],
                data={"pattern_types": found, "line_count": line_count}
            )

        except Exception as e:
            return AgentResult(
                success=False,
                status=AgentStatus.ERROR,
                message=f"Pattern recognition check failed: {e}",
                errors=[str(e)]
            )

    async def _check_sentiment_service(self) -> AgentResult:
        """Check sentiment analysis service."""
        try:
            sentiment_file = self.project_root / "web" / "sentiment_service.py"

            if not sentiment_file.exists():
                return AgentResult(
                    success=False,
                    status=AgentStatus.ERROR,
                    message="Sentiment service file not found",
                    errors=["web/sentiment_service.py missing"]
                )

            content = sentiment_file.read_text(encoding='utf-8')
            line_count = len(content.splitlines())

            # Check for data sources
            sources = []
            if "reddit" in content.lower():
                sources.append("Reddit")
            if "twitter" in content.lower() or "x.com" in content.lower():
                sources.append("Twitter/X")
            if "stocktwits" in content.lower():
                sources.append("StockTwits")
            if "news" in content.lower():
                sources.append("News")
            if "sentiment" in content.lower():
                sources.append("Sentiment Analysis")

            if line_count > 50 and "def " in content:
                return AgentResult(
                    success=True,
                    status=AgentStatus.HEALTHY,
                    message=f"Sentiment service available ({line_count} lines)",
                    data={"sources": sources, "line_count": line_count}
                )

            return AgentResult(
                success=True,
                status=AgentStatus.WARNING,
                message="Sentiment service may need enhancement",
                warnings=["Service might be incomplete"],
                data={"sources": sources, "line_count": line_count}
            )

        except Exception as e:
            return AgentResult(
                success=False,
                status=AgentStatus.ERROR,
                message=f"Sentiment service check failed: {e}",
                errors=[str(e)]
            )

    async def _check_technical_analysis(self) -> AgentResult:
        """Check technical analysis functionality."""
        try:
            ta_file = self.project_root / "web" / "technical_analysis.py"

            if not ta_file.exists():
                return AgentResult(
                    success=False,
                    status=AgentStatus.ERROR,
                    message="Technical analysis file not found",
                    errors=["web/technical_analysis.py missing"]
                )

            content = ta_file.read_text(encoding='utf-8')
            line_count = len(content.splitlines())

            # Check for common indicators
            indicators = [
                ("rsi", "RSI (Relative Strength Index)"),
                ("macd", "MACD"),
                ("bollinger", "Bollinger Bands"),
                ("sma", "SMA (Simple Moving Average)"),
                ("ema", "EMA (Exponential Moving Average)"),
                ("atr", "ATR (Average True Range)"),
                ("vwap", "VWAP"),
            ]

            found = []
            for indicator, name in indicators:
                if indicator.lower() in content.lower():
                    found.append(name)

            if line_count > 50 and "def " in content:
                return AgentResult(
                    success=True,
                    status=AgentStatus.HEALTHY,
                    message=f"Technical analysis available ({line_count} lines, {len(found)} indicators)",
                    data={"indicators": found, "line_count": line_count}
                )

            return AgentResult(
                success=True,
                status=AgentStatus.WARNING,
                message="Technical analysis may be incomplete",
                warnings=[f"Only {len(found)} indicators found"],
                data={"indicators": found, "line_count": line_count}
            )

        except Exception as e:
            return AgentResult(
                success=False,
                status=AgentStatus.ERROR,
                message=f"Technical analysis check failed: {e}",
                errors=[str(e)]
            )

    async def _check_advanced_sr(self) -> AgentResult:
        """Check advanced S/R analysis."""
        try:
            sr_file = self.project_root / "web" / "advanced_sr_analysis.py"

            if not sr_file.exists():
                return AgentResult(
                    success=False,
                    status=AgentStatus.ERROR,
                    message="Advanced S/R file not found",
                    errors=["web/advanced_sr_analysis.py missing"]
                )

            content = sr_file.read_text(encoding='utf-8')
            line_count = len(content.splitlines())

            # Check for S/R features
            features = []
            if "volume profile" in content.lower():
                features.append("Volume Profile")
            if "pivot" in content.lower():
                features.append("Pivot Points")
            if "fibonacci" in content.lower():
                features.append("Fibonacci Levels")
            if "support" in content.lower() and "resistance" in content.lower():
                features.append("S/R Detection")
            if "def " in content:
                features.append("Analysis Functions")

            if line_count > 50:
                return AgentResult(
                    success=True,
                    status=AgentStatus.HEALTHY,
                    message=f"Advanced S/R analysis available ({line_count} lines)",
                    data={"features": features, "line_count": line_count}
                )

            return AgentResult(
                success=True,
                status=AgentStatus.WARNING,
                message="Advanced S/R may be incomplete",
                warnings=["Module seems small"],
                data={"features": features, "line_count": line_count}
            )

        except Exception as e:
            return AgentResult(
                success=False,
                status=AgentStatus.ERROR,
                message=f"Advanced S/R check failed: {e}",
                errors=[str(e)]
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
                ).count() if hasattr(ChartPattern, 'detected_at') else 0

                return AgentResult(
                    success=True,
                    status=AgentStatus.HEALTHY,
                    message=f"Patterns: {total_patterns} total, {recent_patterns} recent (7d)",
                    data={
                        "total_patterns": total_patterns,
                        "recent_patterns_7d": recent_patterns,
                    }
                )
        except ImportError:
            return AgentResult(
                success=True,
                status=AgentStatus.WARNING,
                message="ChartPattern model not found",
                warnings=["Pattern storage not yet implemented"],
                suggestions=["Add ChartPattern model to database.py"]
            )
        except Exception as e:
            return AgentResult(
                success=False,
                status=AgentStatus.ERROR,
                message=f"Pattern check failed: {e}",
                errors=[str(e)]
            )
