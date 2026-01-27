"""
Market Data Agent
=================

Monitors market data feeds and APIs including:
- Real-time price feeds
- Market indices data
- News feeds
- Economic calendar
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

from agents.base import BaseAgent, AgentResult, AgentStatus, AgentTask, TaskType

logger = logging.getLogger(__name__)


class MarketDataAgent(BaseAgent):
    """
    Agent for monitoring market data feeds and APIs.
    
    Checks:
    - Polygon API connectivity and rate limits
    - Real-time price data freshness
    - Market indices availability
    - News feed health
    - Economic calendar updates
    """
    
    def __init__(self):
        super().__init__(
            name="market_data",
            category="Market",
            description="Monitors market data feeds, API connectivity, and data freshness"
        )
    
    def _register_tasks(self) -> None:
        """Register market data monitoring tasks."""
        self.register_task(AgentTask(
            id="polygon_status",
            name="Polygon API Status",
            task_type=TaskType.STATUS_CHECK,
            description="Check Polygon API connectivity and rate limits",
            handler=self._check_polygon_status,
            interval_seconds=120,
        ))
        
        self.register_task(AgentTask(
            id="price_data_freshness",
            name="Price Data Freshness",
            task_type=TaskType.STATUS_CHECK,
            description="Verify price data is being updated",
            handler=self._check_price_data_freshness,
            interval_seconds=300,
        ))
        
        self.register_task(AgentTask(
            id="news_feed_status",
            name="News Feed Status",
            task_type=TaskType.STATUS_CHECK,
            description="Check news article updates and AI analysis",
            handler=self._check_news_feed,
            interval_seconds=600,
        ))
        
        self.register_task(AgentTask(
            id="economic_calendar",
            name="Economic Calendar Status",
            task_type=TaskType.STATUS_CHECK,
            description="Verify economic calendar events are up to date",
            handler=self._check_economic_calendar,
            interval_seconds=3600,
        ))
    
    async def check_status(self) -> AgentResult:
        """Run all market data checks."""
        results = await self.run_all_tasks(TaskType.STATUS_CHECK)
        
        all_healthy = all(r.status == AgentStatus.HEALTHY for r in results.values())
        has_errors = any(r.status in [AgentStatus.ERROR, AgentStatus.CRITICAL] for r in results.values())
        
        if all_healthy:
            status = AgentStatus.HEALTHY
            message = "All market data feeds operational"
        elif has_errors:
            status = AgentStatus.ERROR
            message = "Market data feed issues detected"
        else:
            status = AgentStatus.WARNING
            message = "Some market data feeds have warnings"
        
        self.status = status
        
        return AgentResult(
            success=not has_errors,
            status=status,
            message=message,
            data={
                "feeds": {k: v.to_dict() for k, v in results.items()},
            }
        )
    
    async def diagnose_issues(self) -> AgentResult:
        """Diagnose market data issues."""
        issues = []
        suggestions = []
        
        # Check Polygon API
        polygon_result = await self._check_polygon_status()
        if polygon_result.status != AgentStatus.HEALTHY:
            issues.append(f"Polygon API: {polygon_result.message}")
            suggestions.append("Check POLYGON_API_KEY environment variable")
            suggestions.append("Verify Polygon API subscription tier")
        
        # Check news freshness
        news_result = await self._check_news_feed()
        if news_result.status != AgentStatus.HEALTHY:
            issues.append(f"News Feed: {news_result.message}")
            suggestions.append("Run refresh_news.py cron job")
        
        return AgentResult(
            success=len(issues) == 0,
            status=AgentStatus.HEALTHY if not issues else AgentStatus.WARNING,
            message=f"Found {len(issues)} issue(s)" if issues else "No issues detected",
            errors=issues,
            suggestions=suggestions
        )
    
    async def fix_errors(self, auto_fix: bool = False) -> AgentResult:
        """Attempt to fix market data errors."""
        fixes_available = []
        fixes_applied = []
        
        # Check for stale news data
        news_result = await self._check_news_feed()
        if news_result.status != AgentStatus.HEALTHY:
            fixes_available.append("Refresh news data from APIs")
            if auto_fix:
                try:
                    # Trigger news refresh
                    from scripts.refresh_news import refresh_news
                    refresh_news()
                    fixes_applied.append("Refreshed news data")
                except Exception as e:
                    logger.error(f"Failed to refresh news: {e}")
        
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
            "Add WebSocket support for real-time price streaming",
            "Implement data caching layer with Redis",
            "Add market breadth indicators (A/D line, new highs/lows)",
            "Integrate alternative data sources (social sentiment, dark pool)",
            "Add options flow data from OPRA",
            "Implement historical data backfill system",
            "Add intraday market replay feature",
            "Create market scanner with custom filters",
        ]
        
        return AgentResult(
            success=True,
            status=AgentStatus.HEALTHY,
            message=f"{len(suggestions)} development suggestions",
            suggestions=suggestions,
            data={"category": "Market Data"}
        )
    
    async def _check_polygon_status(self) -> AgentResult:
        """Check Polygon API connectivity."""
        try:
            from web.polygon_service import PolygonService
            
            polygon = PolygonService()
            
            # Try to fetch market indices
            indices = polygon.get_market_indices()
            
            if indices and len(indices) > 0:
                return AgentResult(
                    success=True,
                    status=AgentStatus.HEALTHY,
                    message=f"Polygon API healthy, {len(indices)} indices available",
                    data={"indices_count": len(indices)}
                )
            else:
                return AgentResult(
                    success=False,
                    status=AgentStatus.WARNING,
                    message="Polygon API responding but no data returned",
                    warnings=["API returned empty data - might be outside market hours"]
                )
        except Exception as e:
            return AgentResult(
                success=False,
                status=AgentStatus.ERROR,
                message=f"Polygon API check failed: {e}",
                errors=[str(e)],
                suggestions=["Check POLYGON_API_KEY", "Verify API subscription"]
            )
    
    async def _check_price_data_freshness(self) -> AgentResult:
        """Check if price data is being updated."""
        try:
            from web.polygon_service import PolygonService
            
            polygon = PolygonService()
            
            # Check a major stock
            quote = polygon.get_stock_quote("SPY")
            
            if quote and quote.get("price"):
                return AgentResult(
                    success=True,
                    status=AgentStatus.HEALTHY,
                    message="Price data available",
                    data={"sample_quote": quote}
                )
            else:
                return AgentResult(
                    success=False,
                    status=AgentStatus.WARNING,
                    message="Unable to fetch price data",
                    warnings=["Price data may be stale or unavailable"]
                )
        except Exception as e:
            return AgentResult(
                success=False,
                status=AgentStatus.ERROR,
                message=f"Price data check failed: {e}",
                errors=[str(e)]
            )
    
    async def _check_news_feed(self) -> AgentResult:
        """Check news feed health."""
        try:
            from web.database import db, NewsArticle
            from web.app import create_app
            from datetime import timedelta
            
            app = create_app()
            with app.app_context():
                # Check recent news count
                recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
                recent_news = NewsArticle.query.filter(
                    NewsArticle.published_at >= recent_cutoff
                ).count()
                
                total_news = NewsArticle.query.count()
                
                if recent_news > 0:
                    return AgentResult(
                        success=True,
                        status=AgentStatus.HEALTHY,
                        message=f"News feed healthy: {recent_news} articles in last 24h",
                        data={"recent_articles": recent_news, "total_articles": total_news}
                    )
                elif total_news > 0:
                    return AgentResult(
                        success=True,
                        status=AgentStatus.WARNING,
                        message="No recent news articles - feed may be stale",
                        warnings=[f"No articles in last 24h (total: {total_news})"],
                        suggestions=["Run refresh_news.py to update news"]
                    )
                else:
                    return AgentResult(
                        success=False,
                        status=AgentStatus.ERROR,
                        message="No news articles in database",
                        errors=["News database is empty"],
                        suggestions=["Run initial news population script"]
                    )
        except Exception as e:
            return AgentResult(
                success=False,
                status=AgentStatus.ERROR,
                message=f"News feed check failed: {e}",
                errors=[str(e)]
            )
    
    async def _check_economic_calendar(self) -> AgentResult:
        """Check economic calendar status."""
        try:
            from web.database import db, EconomicEvent
            from web.app import create_app
            from datetime import timedelta
            
            app = create_app()
            with app.app_context():
                today = datetime.now(timezone.utc).date()
                
                # Check upcoming events
                upcoming = EconomicEvent.query.filter(
                    EconomicEvent.date >= today
                ).count()
                
                if upcoming > 0:
                    return AgentResult(
                        success=True,
                        status=AgentStatus.HEALTHY,
                        message=f"Economic calendar has {upcoming} upcoming events",
                        data={"upcoming_events": upcoming}
                    )
                else:
                    return AgentResult(
                        success=True,
                        status=AgentStatus.WARNING,
                        message="No upcoming economic events found",
                        warnings=["Calendar may need refresh"],
                        suggestions=["Update economic calendar data"]
                    )
        except Exception as e:
            return AgentResult(
                success=False,
                status=AgentStatus.ERROR,
                message=f"Economic calendar check failed: {e}",
                errors=[str(e)]
            )

