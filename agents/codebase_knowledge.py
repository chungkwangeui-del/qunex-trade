"""
Codebase Knowledge Base
=======================

Comprehensive knowledge about the Qunex Trade platform structure.
This module provides agents with deep understanding of the codebase.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from pathlib import Path
import os
import ast
import logging
from typing import List
from typing import Optional
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ServiceInfo:
    """Information about a service module"""
    name: str
    path: str
    description: str
    functions: List[str] = field(default_factory=list)
    classes: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    api_blueprint: Optional[str] = None


@dataclass
class RouteInfo:
    """Information about a route"""
    path: str
    method: str
    function: str
    requires_login: bool
    blueprint: str


@dataclass
class ModelInfo:
    """Information about a database model"""
    name: str
    table_name: str
    columns: List[str] = field(default_factory=list)
    relationships: List[str] = field(default_factory=list)


class CodebaseKnowledge:
    """
    Deep knowledge about the Qunex Trade platform.

    Provides:
    - Project structure understanding
    - Service/module documentation
    - Database schema knowledge
    - API endpoint mapping
    - Configuration details
    """

    PROJECT_ROOT = Path(__file__).parent.parent

    # =====================================================================
    # PROJECT STRUCTURE
    # =====================================================================

    PROJECT_STRUCTURE = {
        "web/": "Main Flask web application",
        "web/main/": "Main blueprint(w)ith page routes",
        "web/templates/": "Jinja2 HTML templates",
        "web/static/": "Static assets (CSS, JS, images)",
        "agents/": "Automated agent system",
        "scripts/": "Cron jobs and utility scripts",
        "ml/": "Machine learning models and AI scoring",
        "tests/": "Test suite",
        "data/": "Data files (news, calendar)",
    }

    # =====================================================================
    # SERVICES - What they do and how to use them
    # =====================================================================

    SERVICES = {
        "polygon_service": ServiceInfo(
            name="PolygonService",
            path="web/polygon_service.py",
            description="Market data from Polygon.io API - stocks, indices, quotes",
            functions=["get_stock_quote", "get_market_indices", "get_ticker_details", "get_aggregates"],
            classes=["PolygonService"],
            dependencies=["POLYGON_API_KEY env variable"],
            api_blueprint="api_polygon",
        ),
        "scalp_service": ServiceInfo(
            name="ScalpService",
            path="web/scalp_service.py",
            description="Day trading signals using 쉽알 methodology - Order Blocks, FVG, Volume",
            functions=["analyze_scalp", "detect_order_blocks", "find_fvg", "calculate_confluences"],
            classes=[],  # Function-based module
            dependencies=["polygon_service for price data"],
            api_blueprint="api_scalp",
        ),
        "swing_service": ServiceInfo(
            name="SwingService",
            path="web/swing_service.py",
            description="ICT/SMC swing trading - Market Structure, Liquidity, OTE zones",
            functions=["analyze_swing", "detect_market_structure", "find_liquidity_levels", "calculate_ote"],
            classes=[],
            dependencies=["polygon_service for price data"],
            api_blueprint="api_swing",
        ),
        "sentiment_service": ServiceInfo(
            name="SentimentService",
            path="web/sentiment_service.py",
            description="Social media sentiment analysis - Reddit, Twitter, StockTwits",
            functions=["get_sentiment", "analyze_mentions", "calculate_score"],
            classes=["SentimentService"],
            dependencies=["External sentiment APIs"],
            api_blueprint="api_sentiment",
        ),
        "finnhub_service": ServiceInfo(
            name="FinnhubService",
            path="web/finnhub_service.py",
            description="Finnhub API for earnings, news, company info",
            functions=["get_earnings", "get_company_news", "get_recommendations"],
            classes=["FinnhubService"],
            dependencies=["FINNHUB_API_KEY env variable"],
            api_blueprint=None,
        ),
        "indices_service": ServiceInfo(
            name="IndicesService",
            path="web/indices_service.py",
            description="Market indices data and sector performance",
            functions=["get_indices", "get_sector_performance"],
            classes=[],
            dependencies=["polygon_service"],
            api_blueprint=None,
        ),
    }

    # =====================================================================
    # ANALYSIS MODULES
    # =====================================================================

    ANALYSIS_MODULES = {
        "pattern_recognition": ServiceInfo(
            name="PatternRecognition",
            path="web/pattern_recognition.py",
            description="Chart pattern detection - Head/Shoulders, Triangles, Wedges, Flags",
            functions=["detect_patterns", "find_swing_points", "analyze_pattern"],
            classes=[],
            dependencies=["Price data (bars)"],
            api_blueprint="api_patterns",
        ),
        "technical_analysis": ServiceInfo(
            name="TechnicalAnalysis",
            path="web/technical_analysis.py",
            description="Technical indicators - RSI, MACD, Bollinger Bands, SMA/EMA",
            functions=["calculate_rsi", "calculate_macd", "calculate_bollinger"],
            classes=[],
            dependencies=["Price data, numpy/pandas"],
            api_blueprint=None,
        ),
        "advanced_sr_analysis": ServiceInfo(
            name="AdvancedSRAnalysis",
            path="web/advanced_sr_analysis.py",
            description="Advanced Support/Resistance - Volume Profile, Order Flow",
            functions=["find_support_resistance", "calculate_volume_profile"],
            classes=["AdvancedSRAnalysis"],
            dependencies=["polygon_service"],
            api_blueprint="api_advanced_sr",
        ),
    }

    # =====================================================================
    # DATABASE MODELS
    # =====================================================================

    DATABASE_MODELS = {
        "User": ModelInfo(
            name="User",
            table_name="user",
            columns=["id", "email", "username", "password_hash", "google_id", "subscription_tier", "email_verified"],
            relationships=["watchlist", "transactions", "paper_account", "trade_journal"],
        ),
        "Watchlist": ModelInfo(
            name="Watchlist",
            table_name="watchlist",
            columns=["id", "user_id", "ticker", "company_name", "notes", "alert_price_above", "alert_price_below"],
            relationships=["user"],
        ),
        "Transaction": ModelInfo(
            name="Transaction",
            table_name="transactions",
            columns=["id", "user_id", "ticker", "shares", "price", "transaction_type", "transaction_date"],
            relationships=["user"],
        ),
        "PaperAccount": ModelInfo(
            name="PaperAccount",
            table_name="paper_accounts",
            columns=["id", "user_id", "balance", "initial_balance"],
            relationships=["user"],
        ),
        "PaperTrade": ModelInfo(
            name="PaperTrade",
            table_name="paper_trades",
            columns=["id", "user_id", "ticker", "shares", "price", "trade_type", "is_closed", "realized_pnl"],
            relationships=["user"],
        ),
        "AIScore": ModelInfo(
            name="AIScore",
            table_name="ai_scores",
            columns=["id", "ticker", "score", "rating", "short_term_score", "long_term_score", "features_json"],
            relationships=[],
        ),
        "Signal": ModelInfo(
            name="Signal",
            table_name="signals",
            columns=["id", "ticker", "signal_type", "status", "entry_price", "target_price", "stop_loss"],
            relationships=[],
        ),
        "NewsArticle": ModelInfo(
            name="NewsArticle",
            table_name="news_articles",
            columns=["id", "title", "description", "url", "source", "published_at", "ai_rating", "sentiment"],
            relationships=[],
        ),
        "TradeJournal": ModelInfo(
            name="TradeJournal",
            table_name="trade_journal",
            columns=["id", "user_id", "ticker", "trade_type", "entry_price", "exit_price", "pnl", "outcome"],
            relationships=["user"],
        ),
    }

    # =====================================================================
    # API BLUEPRINTS
    # =====================================================================

    API_BLUEPRINTS = {
        "api_polygon": {"prefix": "/api/polygon", "file": "web/api_polygon.py"},
        "api_watchlist": {"prefix": "/api/watchlist", "file": "web/api_watchlist.py"},
        "api_portfolio": {"prefix": "/api/portfolio", "file": "web/api_portfolio.py"},
        "api_scalp": {"prefix": "/api/scalp", "file": "web/api_scalp.py"},
        "api_swing": {"prefix": "/api/swing", "file": "web/api_swing.py"},
        "api_paper": {"prefix": "/api/paper", "file": "web/api_paper.py"},
        "api_journal": {"prefix": "/api/journal", "file": "web/api_journal.py"},
        "api_chat": {"prefix": "/api/chat", "file": "web/api_chat.py"},
        "api_sentiment": {"prefix": "/api/sentiment", "file": "web/api_sentiment.py"},
        "api_patterns": {"prefix": "/api/patterns", "file": "web/api_patterns.py"},
        "api_options": {"prefix": "/api/options", "file": "web/api_options.py"},
        "api_flow": {"prefix": "/api/flow", "file": "web/api_flow.py"},
        "api_agents": {"prefix": "/api/agents", "file": "web/api_agents.py"},
    }

    # =====================================================================
    # PAGES/ROUTES
    # =====================================================================

    PAGES = {
        "/": {"template": "index.html", "requires_login": False, "description": "Landing page"},
        "/dashboard": {"template": "dashboard.html", "requires_login": True, "description": "User dashboard"},
        "/market": {"template": "market.html", "requires_login": True, "description": "Market overview"},
        "/stocks": {"template": "stocks.html", "requires_login": True, "description": "Stock search"},
        "/stocks/<ticker>": {"template": "stock_chart.html", "requires_login": True, "description": "Stock detail"},
        "/watchlist": {"template": "watchlist.html", "requires_login": True, "description": "User watchlist"},
        "/portfolio": {"template": "portfolio.html", "requires_login": True, "description": "Portfolio management"},
        "/scalping": {"template": "scalping.html", "requires_login": True, "description": "Day trading signals"},
        "/swing": {"template": "swing.html", "requires_login": True, "description": "Swing trading ICT/SMC"},
        "/paper-trading": {"template": "paper_trading.html", "requires_login": True, "description": "Paper trading"},
        "/journal": {"template": "trade_journal.html", "requires_login": True, "description": "Trade journal"},
        "/patterns": {"template": "patterns.html", "requires_login": True, "description": "Chart patterns"},
        "/sentiment": {"template": "sentiment.html", "requires_login": True, "description": "Sentiment analysis"},
        "/options": {"template": "options.html", "requires_login": True, "description": "Options flow"},
        "/chat": {"template": "chat.html", "requires_login": True, "description": "AI chat assistant"},
        "/agents": {"template": "agents.html", "requires_login": True, "description": "Agent dashboard (admin)"},
    }

    # =====================================================================
    # ENVIRONMENT VARIABLES
    # =====================================================================

    ENV_VARIABLES = {
        "SECRET_KEY": {"required": True, "description": "Flask secret key for sessions"},
        "DATABASE_URL": {"required": False, "description": "Database connection string"},
        "POLYGON_API_KEY": {"required": True, "description": "Polygon.io API key for market data"},
        "FINNHUB_API_KEY": {"required": False, "description": "Finnhub API key"},
        "GEMINI_API_KEY": {"required": False, "description": "Google Gemini AI API key"},
        "GOOGLE_CLIENT_ID": {"required": False, "description": "Google OAuth client ID"},
        "GOOGLE_CLIENT_SECRET": {"required": False, "description": "Google OAuth client secret"},
        "MAIL_SERVER": {"required": False, "description": "SMTP server for emails"},
        "SLACK_WEBHOOK_URL": {"required": False, "description": "Slack webhook for notifications"},
    }

    # =====================================================================
    # CRON JOBS
    # =====================================================================

    CRON_JOBS = {
        "cron_update_ai_scores": {
            "file": "scripts/cron_update_ai_scores.py",
            "description": "Update AI scores for all tracked stocks",
            "recommended_schedule": "Every 6 hours",
        },
        "cron_check_alerts": {
            "file": "scripts/cron_check_alerts.py",
            "description": "Check price alerts and notify users",
            "recommended_schedule": "Every 5 minutes during market hours",
        },
        "cron_refresh_insider": {
            "file": "scripts/cron_refresh_insider.py",
            "description": "Refresh insider trading data",
            "recommended_schedule": "Daily",
        },
        "cron_retrain_model": {
            "file": "scripts/cron_retrain_model.py",
            "description": "Retrain ML models with new data",
            "recommended_schedule": "Weekly",
        },
        "refresh_news": {
            "file": "scripts/refresh_news.py",
            "description": "Fetch and analyze new market news",
            "recommended_schedule": "Every hour",
        },
        "cron_run_agents": {
            "file": "scripts/cron_run_agents.py",
            "description": "Run automated agent health checks",
            "recommended_schedule": "Every 15 minutes",
        },
    }

    @classmethod
    def get_project_root(cls) -> Path:
        """Get the project root path."""
        return cls.PROJECT_ROOT

    @classmethod
    def get_service_info(cls, service_name: str) -> Optional[ServiceInfo]:
        """Get information about a service."""
        return cls.SERVICES.get(service_name) or cls.ANALYSIS_MODULES.get(service_name)

    @classmethod
    def get_all_services(cls) -> Dict[str, ServiceInfo]:
        """Get all services."""
        return {**cls.SERVICES, **cls.ANALYSIS_MODULES}

    @classmethod
    def get_model_info(cls, model_name: str) -> Optional[ModelInfo]:
        """Get information about a database model."""
        return cls.DATABASE_MODELS.get(model_name)

    @classmethod
    def file_exists(cls, relative_path: str) -> bool:
        """Check if a file exists in the project."""
        return (cls.PROJECT_ROOT / relative_path).exists()

    @classmethod
    def get_missing_env_vars(cls) -> List[str]:
        """Get list of required but missing environment variables."""
        missing = []
        for var, info in cls.ENV_VARIABLES.items():
            if info["required"] and not os.getenv(var):
                missing.append(var)
        return missing

    @classmethod
    def scan_python_file(cls, filepath: str) -> Dict[str, Any]:
        """Scan a Python file and extract classes, functions, imports."""
        full_path = cls.PROJECT_ROOT / filepath
        if not full_path.exists():
            return {"error": f"File not found: {filepath}"}

        try:
            classes = []
            functions = []
            imports = []
            line_count = 0

            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                line_count = len(content.splitlines())

            tree = ast.parse(content)
            # Free the content string as soon as we have the tree
            del content

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    classes.append(node.name)
                elif isinstance(node, ast.FunctionDef):
                    if not node.name.startswith('_'):
                        functions.append(node.name)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)

            return {
                "filepath": filepath,
                "classes": classes,
                "functions": functions,
                "imports": list(set(imports)),
                "line_count": line_count,
            }
        except Exception as e:
            logger.debug(f"Error scanning {filepath}: {e}")
            return {"error": str(e)}

    @classmethod
    def get_file_issues(cls) -> List[Dict[str, Any]]:
        """Scan for common issues in the codebase."""
        issues = []

        # Check for expected files
        expected_files = [
            "web/app.py",
            "web/database.py",
            "web/config.py",
            "web/polygon_service.py",
            "requirements.txt",
        ]

        for filepath in expected_files:
            if not cls.file_exists(filepath):
                issues.append({
                    "type": "missing_file",
                    "severity": "error",
                    "file": filepath,
                    "message": f"Required file missing: {filepath}"
                })

        # Check for large files that might need refactoring
        web_dir = cls.PROJECT_ROOT / "web"
        if web_dir.exists():
            for py_file in web_dir.glob("*.py"):
                try:
                    line_count = len(py_file.read_text(encoding='utf-8').splitlines())
                    if line_count > 500:
                        issues.append({
                            "type": "large_file",
                            "severity": "warning",
                            "file": str(py_file.relative_to(cls.PROJECT_ROOT)),
                            "message": f"File has {line_count} lines - consider splitting",
                            "lines": line_count
                        })
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.debug(f"Error checking file length for {py_file}: {e}")

        return issues

    @classmethod
    def get_development_priorities(cls) -> List[Dict[str, Any]]:
        """Get prioritized development suggestions based on codebase analysis."""
        priorities = []

        # Check what's missing or could be improved
        if not cls.file_exists("web/admin_views.py"):
            priorities.append({
                "priority": "medium",
                "category": "Admin",
                "suggestion": "Create admin_views.py for Flask-Admin interface",
                "reason": "Admin dashboard shows import error"
            })

        # Check for missing tests
        tests_dir = cls.PROJECT_ROOT / "tests"
        if tests_dir.exists():
            test_files = list(tests_dir.glob("test_*.py"))
            web_files = list((cls.PROJECT_ROOT / "web").glob("*.py"))

            if len(test_files) < len(web_files) / 2:
                priorities.append({
                    "priority": "high",
                    "category": "Testing",
                    "suggestion": f"Add more tests - only {len(test_files)} test files for {len(web_files)} modules",
                    "reason": "Low test coverage"
                })

        # Check for missing environment variables
        missing_env = cls.get_missing_env_vars()
        if missing_env:
            priorities.append({
                "priority": "high",
                "category": "Configuration",
                "suggestion": f"Set required environment variables: {', '.join(missing_env)}",
                "reason": "Missing required configuration"
            })

        return priorities


# Singleton instance for easy access
_knowledge = None

def get_knowledge() -> CodebaseKnowledge:
    """Get the codebase knowledge singleton."""
    global _knowledge
    if _knowledge is None:
        _knowledge = CodebaseKnowledge()
    return _knowledge


