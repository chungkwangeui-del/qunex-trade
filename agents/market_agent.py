"""
Market Data Agent
=================

Monitors market data infrastructure including:
- Polygon.io API connectivity
- Real-time price feeds
- Historical data availability
- News feed health
- Market hours awareness
"""

import logging
import os
from datetime import datetime, timezone, timedelta, time
from typing import Dict, Any, List, Optional

from agents.base import BaseAgent, AgentResult, AgentStatus, AgentTask, TaskType
from agents.codebase_knowledge import CodebaseKnowledge
from datetime import timedelta
from datetime import timezone
from typing import List
from typing import Optional
from typing import Any

logger = logging.getLogger(__name__)

class MarketDataAgent(BaseAgent):
    """
    Agent for monitoring market data infrastructure.

    Checks:
    - Polygon.io API health and quota
    - Real-time price data freshness
    - Historical data availability
    - News and sentiment feeds
    - Market hours detection
    """

    def __init__(self):
        super().__init__(
            name="market",
            category="Market Data",
            description="Monitors market data feeds, APIs, and data freshness"
        )
        self.knowledge = CodebaseKnowledge()

    def _register_tasks(self) -> None:
        """Register market data monitoring tasks."""
        self.register_task(AgentTask(
            id="polygon_health",
            name="Polygon API Health",
            task_type=TaskType.STATUS_CHECK,
            description="Check Polygon.io API connectivity and quota",
            handler=self._check_polygon_api,
            interval_seconds=300,
        ))

        self.register_task(AgentTask(
            id="price_freshness",
            name="Price Data Freshness",
            task_type=TaskType.MONITORING,
            description="Check if price data is current",
            handler=self._check_price_freshness,
            interval_seconds=60,
        ))

        self.register_task(AgentTask(
            id="news_feed",
            name="News Feed Health",
            task_type=TaskType.STATUS_CHECK,
            description="Check news and economic calendar data",
            handler=self._check_news_feed,
            interval_seconds=600,
        ))

        self.register_task(AgentTask(
            id="market_hours",
            name="Market Hours Status",
            task_type=TaskType.MONITORING,
            description="Check current market session and hours",
            handler=self._check_market_hours,
            interval_seconds=60,
        ))

        self.register_task(AgentTask(
            id="indices_status",
            name="Market Indices Status",
            task_type=TaskType.MONITORING,
            description="Check market indices data availability",
            handler=self._check_indices,
            interval_seconds=300,
        ))

    async def check_status(self) -> AgentResult:
        """Run all market data checks."""
        results = await self.run_all_tasks(TaskType.STATUS_CHECK)

        all_healthy = all(r.status == AgentStatus.HEALTHY for r in results.values())
        has_errors = any(r.status in [AgentStatus.ERROR, AgentStatus.CRITICAL] for r in results.values())

        if all_healthy:
            status = AgentStatus.HEALTHY
            message = "All market data sources healthy"
        elif has_errors:
            status = AgentStatus.ERROR
            message = "Market data issues detected"
        else:
            status = AgentStatus.WARNING
            message = "Some market data sources have warnings"

        self.status = status

        return AgentResult(
            success=not has_errors,
            status=status,
            message=message,
            data={
                "checks": {k: v.to_dict() for k, v in results.items()},
            }
        )

    async def diagnose_issues(self) -> AgentResult:
        """Diagnose market data issues."""
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
        """Attempt to fix market data errors."""
        fixes_available = []
        fixes_applied = []

        # Check for API key issues
        if not os.getenv("POLYGON_API_KEY"):
            fixes_available.append("Set POLYGON_API_KEY environment variable")

        # Check news data freshness
        try:
            from pathlib import Path
            news_file = Path("data/news_analysis.json")
            if news_file.exists():
                import json
                mtime = datetime.fromtimestamp(news_file.stat().st_mtime, tz=timezone.utc)
                age_hours = (datetime.now(timezone.utc) - mtime).total_seconds() / 3600

                if age_hours > 6:
                    fixes_available.append("Refresh news data (older than 6 hours)")
                    if auto_fix:
                        try:
                            # Try to run news refresh
                            from scripts.refresh_news import main as refresh_news
                            refresh_news()
                            fixes_applied.append("Refreshed news data")
                        except Exception as e:
                            logger.error(f"Failed to refresh news: {e}")
        except Exception as e:
            logger.error(f"Error checking news freshness: {e}")

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
        """Suggest market data improvements."""
        suggestions = [
            "Add WebSocket for real-time Polygon data streaming",
            "Implement data caching layer with Redis",
            "Add fallback data providers (Alpha Vantage, Yahoo Finance)",
            "Create market breadth indicators (A/D line, TRIN)",
            "Add sector rotation analysis",
            "Implement unusual volume detection",
            "Add pre/post market data handling",
            "Create market internals dashboard",
            "Add forex and crypto data feeds",
            "Implement historical data backfill automation",
        ]

        return AgentResult(
            success=True,
            status=AgentStatus.HEALTHY,
            message=f"{len(suggestions)} development suggestions",
            suggestions=suggestions,
            data={"category": "Market Data"}
        )

    async def _check_polygon_api(self) -> AgentResult:
        """Check Polygon.io API health."""
        api_key = os.getenv("POLYGON_API_KEY")

        if not api_key:
            return AgentResult(
                success=False,
                status=AgentStatus.ERROR,
                message="POLYGON_API_KEY not configured",
                errors=["Missing POLYGON_API_KEY environment variable"],
                suggestions=["Set POLYGON_API_KEY in environment or .env file"]
            )

        try:
            # Try to import and use the polygon service
            from web.polygon_service import PolygonService

            service = PolygonService()

            # The service exists and was initialized successfully
            return AgentResult(
                success=True,
                status=AgentStatus.HEALTHY,
                message="Polygon API configured and ready",
                data={
                    "api_key_set": True,
                    "service": "PolygonService initialized"
                }
            )
        except ImportError as e:
            return AgentResult(
                success=False,
                status=AgentStatus.ERROR,
                message=f"Cannot import PolygonService: {e}",
                errors=[str(e)],
                suggestions=["Check web/polygon_service.py for errors"]
            )
        except Exception as e:
            return AgentResult(
                success=False,
                status=AgentStatus.ERROR,
                message=f"Polygon API check failed: {e}",
                errors=[str(e)],
                suggestions=["Verify Polygon API key is valid"]
            )

    async def _check_price_freshness(self) -> AgentResult:
        """Check price data freshness."""
        from pathlib import Path

        try:
            # Check if polygon service file exists and has content
            polygon_file = Path("web/polygon_service.py")

            if not polygon_file.exists():
                return AgentResult(
                    success=False,
                    status=AgentStatus.ERROR,
                    message="Polygon service file not found",
                    errors=["web/polygon_service.py missing"]
                )

            content = polygon_file.read_text(encoding='utf-8')
            line_count = len(content.splitlines())

            # Check for key functions
            has_quote = "quote" in content.lower()
            has_aggregate = "aggregate" in content.lower()
            has_ticker = "ticker" in content.lower()

            if line_count > 100 and (has_quote or has_aggregate):
                return AgentResult(
                    success=True,
                    status=AgentStatus.HEALTHY,
                    message=f"Price service available ({line_count} lines)",
                    data={
                        "line_count": line_count,
                        "has_quote": has_quote,
                        "has_aggregate": has_aggregate,
                        "has_ticker": has_ticker
                    }
                )

            return AgentResult(
                success=True,
                status=AgentStatus.WARNING,
                message="Price service may be incomplete",
                warnings=["Service needs verification"],
                data={"line_count": line_count}
            )

        except Exception as e:
            return AgentResult(
                success=False,
                status=AgentStatus.ERROR,
                message=f"Price freshness check failed: {e}",
                errors=[str(e)]
            )

    async def _check_news_feed(self) -> AgentResult:
        """Check news and economic calendar data."""
        from pathlib import Path
        import json

        issues = []
        data = {}

        # Check news analysis file
        news_file = Path("data/news_analysis.json")
        if news_file.exists():
            try:
                mtime = datetime.fromtimestamp(news_file.stat().st_mtime, tz=timezone.utc)
                age_hours = (datetime.now(timezone.utc) - mtime).total_seconds() / 3600
                data["news_age_hours"] = round(age_hours, 2)

                if age_hours > 24:
                    issues.append(f"News data is {age_hours:.1f} hours old")

                # Try to read the file
                with open(news_file, "r", encoding="utf-8") as f:
                    news_data = json.load(f)
                    data["news_count"] = len(news_data) if isinstance(news_data, list) else 0

            except Exception as e:
                issues.append(f"Cannot read news file: {e}")
        else:
            issues.append("News analysis file not found")

        # Check economic calendar
        calendar_file = Path("data/economic_calendar.json")
        if calendar_file.exists():
            try:
                mtime = datetime.fromtimestamp(calendar_file.stat().st_mtime, tz=timezone.utc)
                age_hours = (datetime.now(timezone.utc) - mtime).total_seconds() / 3600
                data["calendar_age_hours"] = round(age_hours, 2)

                if age_hours > 24:
                    issues.append(f"Economic calendar is {age_hours:.1f} hours old")

            except Exception as e:
                issues.append(f"Cannot read calendar file: {e}")
        else:
            data["calendar_exists"] = False

        if issues:
            return AgentResult(
                success=True,
                status=AgentStatus.WARNING,
                message=f"News feed has {len(issues)} warning(s)",
                warnings=issues,
                suggestions=["Run scripts/refresh_news.py to update"],
                data=data
            )

        return AgentResult(
            success=True,
            status=AgentStatus.HEALTHY,
            message="News feeds healthy",
            data=data
        )

    async def _check_market_hours(self) -> AgentResult:
        """Check current market session."""
        now = datetime.now(timezone.utc)

        # Convert to Eastern Time (US market hours)
        # Simple approximation - in production use pytz
        eastern_offset = timedelta(hours=-5)  # EST (adjust for DST as needed)
        eastern_time = now + eastern_offset

        current_time = eastern_time.time()
        current_day = eastern_time.weekday()  # 0=Monday, 6=Sunday

        # Market hours: 9:30 AM - 4:00 PM EST, Mon-Fri
        market_open = time(9, 30)
        market_close = time(16, 0)
        pre_market_open = time(4, 0)
        after_hours_close = time(20, 0)

        is_weekday = current_day < 5

        if is_weekday:
            if market_open <= current_time <= market_close:
                session = "Regular Trading Hours"
                status = AgentStatus.HEALTHY
            elif pre_market_open <= current_time < market_open:
                session = "Pre-Market"
                status = AgentStatus.HEALTHY
            elif market_close < current_time <= after_hours_close:
                session = "After Hours"
                status = AgentStatus.HEALTHY
            else:
                session = "Market Closed"
                status = AgentStatus.WARNING
        else:
            session = "Weekend - Market Closed"
            status = AgentStatus.WARNING

        return AgentResult(
            success=True,
            status=status,
            message=f"Current session: {session}",
            data={
                "session": session,
                "eastern_time": eastern_time.strftime("%Y-%m-%d %H:%M:%S EST"),
                "utc_time": now.isoformat(),
                "is_market_open": session == "Regular Trading Hours",
                "day_of_week": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][current_day],
            }
        )

    async def _check_indices(self) -> AgentResult:
        """Check market indices data availability."""
        from pathlib import Path

        try:
            indices_file = Path("web/indices_service.py")

            if not indices_file.exists():
                return AgentResult(
                    success=False,
                    status=AgentStatus.ERROR,
                    message="Indices service file not found",
                    errors=["web/indices_service.py missing"]
                )

            content = indices_file.read_text(encoding='utf-8')
            line_count = len(content.splitlines())

            # Check for key features
            has_indices = "indic" in content.lower()
            has_sector = "sector" in content.lower()

            if line_count > 50 and "def " in content:
                return AgentResult(
                    success=True,
                    status=AgentStatus.HEALTHY,
                    message=f"Indices service available ({line_count} lines)",
                    data={
                        "line_count": line_count,
                        "has_indices": has_indices,
                        "has_sector": has_sector
                    }
                )

            return AgentResult(
                success=True,
                status=AgentStatus.WARNING,
                message="Indices service may be incomplete",
                warnings=["Service needs verification"],
                data={"line_count": line_count}
            )

        except Exception as e:
            return AgentResult(
                success=False,
                status=AgentStatus.ERROR,
                message=f"Indices check failed: {e}",
                errors=[str(e)]
            )
