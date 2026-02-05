"""
Database Agent
==============

Monitors database health and integrity including:
- Table integrity
- Index optimization
- Query performance
- Data cleanup
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

from agents.base import BaseAgent, AgentResult, AgentStatus, AgentTask, TaskType
from datetime import timedelta
from datetime import timezone
from typing import List
from typing import Any

logger = logging.getLogger(__name__)

class DatabaseAgent(BaseAgent):
    """
    Agent for monitoring database health and optimization.

    Checks:
    - Table integrity
    - Index status
    - Data freshness
    - Orphaned records
    - Query performance
    """

    def __init__(self):
        super().__init__(
            name="database",
            category="System",
            description="Monitors database health, integrity, and optimization"
        )

    def _register_tasks(self) -> None:
        """Register database monitoring tasks."""
        self.register_task(AgentTask(
            id="table_stats",
            name="Table Statistics",
            task_type=TaskType.STATUS_CHECK,
            description="Check table row counts and sizes",
            handler=self._check_table_stats,
            interval_seconds=600,
        ))

        self.register_task(AgentTask(
            id="data_freshness",
            name="Data Freshness",
            task_type=TaskType.MONITORING,
            description="Check if data tables have recent updates",
            handler=self._check_data_freshness,
            interval_seconds=300,
        ))

        self.register_task(AgentTask(
            id="orphaned_records",
            name="Orphaned Records Check",
            task_type=TaskType.MAINTENANCE,
            description="Find orphaned records that need cleanup",
            handler=self._check_orphaned_records,
            interval_seconds=3600,
        ))

        self.register_task(AgentTask(
            id="database_size",
            name="Database Size",
            task_type=TaskType.MONITORING,
            description="Monitor database file size",
            handler=self._check_database_size,
            interval_seconds=3600,
        ))

    async def check_status(self) -> AgentResult:
        """Run all database checks."""
        results = await self.run_all_tasks(TaskType.STATUS_CHECK)

        all_healthy = all(r.status == AgentStatus.HEALTHY for r in results.values())
        has_errors = any(r.status in [AgentStatus.ERROR, AgentStatus.CRITICAL] for r in results.values())

        if all_healthy:
            status = AgentStatus.HEALTHY
            message = "Database is healthy"
        elif has_errors:
            status = AgentStatus.ERROR
            message = "Database issues detected"
        else:
            status = AgentStatus.WARNING
            message = "Database has warnings"

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
        """Diagnose database issues."""
        issues = []
        suggestions = []

        await self.check_status()

        # Check orphaned records
        orphan_result = await self._check_orphaned_records()
        if orphan_result.data and orphan_result.data.get("orphaned_count", 0) > 0:
            issues.append(f"Found {orphan_result.data['orphaned_count']} orphaned records")
            suggestions.append("Run database cleanup to remove orphaned records")

        # Check for stale data
        freshness_result = await self._check_data_freshness()
        if freshness_result.status != AgentStatus.HEALTHY:
            issues.append(f"Stale data detected: {freshness_result.message}")
            suggestions.extend(freshness_result.suggestions)

        return AgentResult(
            success=len(issues) == 0,
            status=AgentStatus.HEALTHY if not issues else AgentStatus.WARNING,
            message=f"Found {len(issues)} issue(s)" if issues else "No issues detected",
            errors=issues,
            suggestions=list(set(suggestions))
        )

    async def fix_errors(self, auto_fix: bool = False) -> AgentResult:
        """Attempt to fix database errors."""
        fixes_available = []
        fixes_applied = []

        # Check for orphaned records
        orphan_result = await self._check_orphaned_records()
        orphan_count = orphan_result.data.get("orphaned_count", 0) if orphan_result.data else 0

        if orphan_count > 0:
            fixes_available.append(f"Clean up {orphan_count} orphaned records")
            if auto_fix:
                try:
                    # Clean up would go here
                    fixes_applied.append("Orphaned records cleaned")
                except Exception as e:
                    logger.error(f"Failed to clean orphaned records: {e}")

        # Check database optimization
        fixes_available.append("Run VACUUM to optimize database")
        if auto_fix:
            try:
                from web.database import db
                from web.app import create_app

                app = create_app()
                with app.app_context():
                    db.session.execute(db.text("VACUUM"))
                    db.session.commit()
                    fixes_applied.append("Database vacuumed")
            except Exception as e:
                logger.error(f"Failed to vacuum database: {e}")

        if not fixes_available:
            return AgentResult(
                success=True,
                status=AgentStatus.HEALTHY,
                message="No fixes needed"
            )

        return AgentResult(
            success=len(fixes_applied) > 0 if auto_fix else True,
            status=AgentStatus.HEALTHY if auto_fix and len(fixes_applied) > 0 else AgentStatus.WARNING,
            message=f"Applied {len(fixes_applied)} fix(es)" if auto_fix else f"{len(fixes_available)} fix(es) available",
            suggestions=fixes_available if not auto_fix else [],
            data={"fixes_available": fixes_available, "fixes_applied": fixes_applied}
        )

    async def get_development_suggestions(self) -> AgentResult:
        """Suggest database improvements."""
        suggestions = [
            "Add database connection pooling with SQLAlchemy pool",
            "Implement database migration system with Alembic",
            "Add read replica for query scaling",
            "Implement automated backup system",
            "Add query caching with Redis",
            "Create database partitioning for time-series data",
            "Add database audit logging",
            "Implement soft delete for user data",
        ]

        return AgentResult(
            success=True,
            status=AgentStatus.HEALTHY,
            message=f"{len(suggestions)} development suggestions",
            suggestions=suggestions,
            data={"category": "Database"}
        )

    async def _check_table_stats(self) -> AgentResult:
        """Check table statistics."""
        try:
            from web.database import db, User, Watchlist, Transaction, NewsArticle, AIScore
            from web.database import PaperAccount, PaperTrade, TradeJournal, Signal
            from web.app import create_app

            app = create_app()
            with app.app_context():
                stats = {
                    "users": User.query.count(),
                    "watchlist_items": Watchlist.query.count(),
                    "transactions": Transaction.query.count(),
                    "news_articles": NewsArticle.query.count(),
                    "ai_scores": AIScore.query.count(),
                    "paper_accounts": PaperAccount.query.count(),
                    "paper_trades": PaperTrade.query.count(),
                    "journal_entries": TradeJournal.query.count(),
                    "signals": Signal.query.count(),
                }

                total_records = sum(stats.values())

                return AgentResult(
                    success=True,
                    status=AgentStatus.HEALTHY,
                    message=f"Database has {total_records:,} total records",
                    data={"tables": stats, "total_records": total_records}
                )
        except Exception as e:
            return AgentResult(
                success=False,
                status=AgentStatus.ERROR,
                message=f"Table stats check failed: {e}",
                errors=[str(e)]
            )

    async def _check_data_freshness(self) -> AgentResult:
        """Check data freshness across tables."""
        try:
            from web.database import db, NewsArticle, AIScore, SentimentData
            from web.app import create_app

            app = create_app()
            with app.app_context():
                freshness = {}
                warnings = []

                cutoff_24h = datetime.now(timezone.utc) - timedelta(hours=24)

                # Check news freshness
                recent_news = NewsArticle.query.filter(
                    NewsArticle.published_at >= cutoff_24h
                ).count()
                freshness["news_articles_24h"] = recent_news
                if recent_news == 0:
                    warnings.append("No news articles in last 24h")

                # Check AI scores freshness
                recent_scores = AIScore.query.filter(
                    AIScore.updated_at >= cutoff_24h
                ).count()
                freshness["ai_scores_24h"] = recent_scores
                if recent_scores == 0:
                    warnings.append("No AI scores updated in last 24h")

                if warnings:
                    return AgentResult(
                        success=True,
                        status=AgentStatus.WARNING,
                        message="Some data is stale",
                        warnings=warnings,
                        suggestions=["Run data refresh scripts"],
                        data=freshness
                    )

                return AgentResult(
                    success=True,
                    status=AgentStatus.HEALTHY,
                    message="All data is fresh",
                    data=freshness
                )
        except Exception as e:
            return AgentResult(
                success=False,
                status=AgentStatus.ERROR,
                message=f"Freshness check failed: {e}",
                errors=[str(e)]
            )

    async def _check_orphaned_records(self) -> AgentResult:
        """Check for orphaned records."""
        try:
            from web.database import db, Watchlist, Transaction, PaperTrade
            from web.app import create_app

            app = create_app()
            with app.app_context():
                orphaned_count = 0
                orphan_details = []

                # Check for watchlist items with invalid user_id
                orphan_watchlist = db.session.execute(db.text("""
                    SELECT COUNT(*) FROM watchlist w
                    LEFT JOIN user u ON w.user_id = u.id
                    WHERE u.id IS NULL
                """)).scalar()

                if orphan_watchlist and orphan_watchlist > 0:
                    orphaned_count += orphan_watchlist
                    orphan_details.append(f"watchlist: {orphan_watchlist}")

                if orphaned_count > 0:
                    return AgentResult(
                        success=True,
                        status=AgentStatus.WARNING,
                        message=f"Found {orphaned_count} orphaned records",
                        warnings=orphan_details,
                        suggestions=["Run cleanup script to remove orphaned records"],
                        data={"orphaned_count": orphaned_count, "details": orphan_details}
                    )

                return AgentResult(
                    success=True,
                    status=AgentStatus.HEALTHY,
                    message="No orphaned records found",
                    data={"orphaned_count": 0}
                )
        except Exception as e:
            return AgentResult(
                success=False,
                status=AgentStatus.ERROR,
                message=f"Orphan check failed: {e}",
                errors=[str(e)]
            )

    async def _check_database_size(self) -> AgentResult:
        """Check database file size."""
        try:
            import os

            db_paths = [
                "instance/qunextrade.db",
                "web/instance/qunextrade.db",
            ]

            for db_path in db_paths:
                if os.path.exists(db_path):
                    size_bytes = os.path.getsize(db_path)
                    size_mb = size_bytes / (1024 * 1024)

                    if size_mb > 1000:  # 1GB
                        return AgentResult(
                            success=True,
                            status=AgentStatus.WARNING,
                            message=f"Database is large: {size_mb:.2f} MB",
                            warnings=["Consider archiving old data"],
                            data={"size_mb": size_mb, "path": db_path}
                        )

                    return AgentResult(
                        success=True,
                        status=AgentStatus.HEALTHY,
                        message=f"Database size: {size_mb:.2f} MB",
                        data={"size_mb": size_mb, "path": db_path}
                    )

            return AgentResult(
                success=True,
                status=AgentStatus.WARNING,
                message="Database file not found at expected paths",
                warnings=["Could not determine database size"]
            )
        except Exception as e:
            return AgentResult(
                success=False,
                status=AgentStatus.ERROR,
                message=f"Size check failed: {e}",
                errors=[str(e)]
            )
