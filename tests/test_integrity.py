#!/usr/bin/env python3
"""
Integration Integrity Test - Phase 5 Deployment Verification

Tests all critical initialization paths and dependencies to ensure
the application can start successfully in production.

This test simulates the Render.com deployment environment.
"""

import os
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestAppInitialization:
    """Test Flask app initialization without requiring actual database."""

    def test_all_imports_succeed(self):
        """Test that all critical modules can be imported."""
        try:
            # Core modules
            import web.database
            import web.app
            import web.logging_config
            import web.polygon_service
            import web.auth
            import web.admin_views

            # Source modules
            import src.news_collector
            import src.news_analyzer

            # ML modules
            import ml.ai_score_system

            # Scripts
            import scripts.refresh_data_cron
            import scripts.cron_run_backtests

            assert True, "All imports succeeded"
        except ImportError as e:
            pytest.fail(f"Import failed: {e}")

    def test_database_models_defined(self):
        """Test that all database models are properly defined."""
        from web.database import (
            User,
            Watchlist,
            NewsArticle,
            EconomicEvent,
            AIScore,
            Transaction,
            BacktestJob,
        )

        # Verify models have required attributes
        assert hasattr(User, "id")
        assert hasattr(Watchlist, "ticker")
        assert hasattr(NewsArticle, "title")
        assert hasattr(EconomicEvent, "title")  # Fixed: uses 'title' not 'event_name'
        assert hasattr(AIScore, "score")
        assert hasattr(Transaction, "shares")
        assert hasattr(BacktestJob, "status")

        # Verify to_dict methods exist
        assert hasattr(BacktestJob, "to_dict")
        assert hasattr(AIScore, "to_dict")

    @patch.dict(
        os.environ,
        {
            "DATABASE_URL": "postgresql://test:test@localhost/test",
            "SECRET_KEY": "test-secret",
            "POLYGON_API_KEY": "test-key",
            "REDIS_URL": "memory://",
        },
    )
    def test_app_factory_creation(self):
        """Test Flask app can be created with mocked environment."""
        try:
            # Mock SQLAlchemy to avoid actual database connection
            with patch("web.database.db") as mock_db:
                mock_db.create_all = Mock()
                mock_db.session = Mock()

                # Import app - this will trigger initialization
                from web import app as app_module

                # Verify app exists and has expected attributes
                assert hasattr(app_module, "app")
                assert app_module.app is not None

        except Exception as e:
            pytest.fail(f"App creation failed: {e}")

    def test_required_dependencies_available(self):
        """Test that all required packages are installed."""
        required_packages = [
            "flask",
            "flask_login",
            "flask_sqlalchemy",
            "flask_socketio",
            "eventlet",
            "bleach",
            "structlog",
            "shap",
            "xgboost",
            "redis",
            "requests",
            "anthropic",
        ]

        missing = []
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                missing.append(package)

        assert not missing, f"Missing required packages: {missing}"

    def test_logging_config_works(self):
        """Test structured logging configuration."""
        from web.logging_config import configure_structured_logging, get_logger

        # Configure logging
        configure_structured_logging()

        # Get logger
        logger = get_logger(__name__)
        assert logger is not None

        # Test logging (should not raise)
        logger.info("Test log message", test_key="test_value")

    def test_polygon_service_initialization(self):
        """Test PolygonService can be initialized."""
        with patch.dict(os.environ, {"POLYGON_API_KEY": "test-key"}):
            from web.polygon_service import PolygonService

            service = PolygonService()
            assert service.api_key == "test-key"
            assert hasattr(service, "get_aggregates")
            assert hasattr(service, "get_ticker_details")


class TestEnvironmentVariables:
    """Test environment variable handling."""

    def test_all_required_env_vars_documented(self):
        """Test that .env.example contains all required variables."""
        env_example_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env.example")

        assert os.path.exists(env_example_path), ".env.example file not found"

        with open(env_example_path, "r", encoding="utf-8") as f:
            content = f.read()

        required_vars = [
            "DATABASE_URL",
            "REDIS_URL",
            "POLYGON_API_KEY",
            "NEWSAPI_KEY",
            "ANTHROPIC_API_KEY",
            "ALPHA_VANTAGE_API_KEY",
            "FINNHUB_API_KEY",
            "MAIL_USERNAME",
            "MAIL_PASSWORD",
        ]

        missing = []
        for var in required_vars:
            if var not in content:
                missing.append(var)

        assert not missing, f"Missing from .env.example: {missing}"


class TestCronScripts:
    """Test cron job scripts can initialize."""

    @patch.dict(
        os.environ,
        {
            "DATABASE_URL": "postgresql://test:test@localhost/test",
            "NEWSAPI_KEY": "test-key",
            "ANTHROPIC_API_KEY": "test-key",
        },
    )
    def test_refresh_data_cron_imports(self):
        """Test refresh_data_cron can be imported."""
        try:
            import scripts.refresh_data_cron as cron_module

            # Verify functions exist
            assert hasattr(cron_module, "refresh_news_data")
            assert hasattr(cron_module, "refresh_calendar_data")
        except Exception as e:
            pytest.fail(f"Failed to import refresh_data_cron: {e}")

    @patch.dict(
        os.environ,
        {
            "DATABASE_URL": "postgresql://test:test@localhost/test",
            "ALPHA_VANTAGE_API_KEY": "test-key",
            "POLYGON_API_KEY": "test-key",
        },
    )
    def test_ai_score_cron_imports(self):
        """Test cron_update_ai_scores can be imported."""
        try:
            import cron_update_ai_scores as cron_module

            # Verify functions exist
            assert hasattr(cron_module, "update_ai_scores")
            assert hasattr(cron_module, "calculate_enhanced_features")
        except Exception as e:
            pytest.fail(f"Failed to import cron_update_ai_scores: {e}")

    @patch.dict(
        os.environ,
        {
            "DATABASE_URL": "postgresql://test:test@localhost/test",
            "POLYGON_API_KEY": "test-key",
        },
    )
    def test_backtest_cron_imports(self):
        """Test cron_run_backtests can be imported."""
        try:
            import scripts.cron_run_backtests as cron_module

            # Verify functions exist
            assert hasattr(cron_module, "run_backtests")
        except Exception as e:
            pytest.fail(f"Failed to import cron_run_backtests: {e}")


class TestFreeAPIStrategy:
    """Test that free API strategy is properly implemented."""

    def test_ai_score_uses_alpha_vantage(self):
        """Test AI Score system uses Alpha Vantage, not Polygon Financials."""
        with open("cron_update_ai_scores.py", "r", encoding="utf-8") as f:
            content = f.read()

        # Verify Alpha Vantage is used
        assert (
            "alpha_vantage.get_company_overview" in content or "FundamentalData" in content
        ), "AI Score should use Alpha Vantage for fundamentals"

        # Verify Polygon Financials is NOT used for fundamentals
        assert (
            "polygon.get_financials" not in content and "polygon.get_fundamental" not in content
        ), "AI Score should NOT use paid Polygon Financials API"

    def test_calendar_uses_finnhub(self):
        """Test Calendar uses Finnhub, not Polygon."""
        script_path = "scripts/refresh_data_cron.py"
        with open(script_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Verify Finnhub is used
        assert (
            "finnhub.io" in content or "FINNHUB_API_KEY" in content
        ), "Calendar should use Finnhub API"

        # Verify Polygon is NOT used for calendar
        calendar_section = content[content.find("def refresh_calendar_data") :]
        assert (
            "polygon" not in calendar_section.lower() or "polygon.io" not in calendar_section
        ), "Calendar should NOT use Polygon for economic events"

    def test_rate_limiting_in_ai_score(self):
        """Test that AI Score has rate limiting for Alpha Vantage."""
        with open("cron_update_ai_scores.py", "r", encoding="utf-8") as f:
            content = f.read()

        # Verify rate limiting exists
        assert "time.sleep" in content, "AI Score should have rate limiting (time.sleep)"

        # Verify limiting to 20 stocks per run (5 calls/min limit)
        assert (
            "limit(20)" in content or "limit=20" in content or ":20]" in content
        ), "AI Score should process max 20 stocks per run"


class TestBlueprints:
    """Test Blueprint registration."""

    @patch.dict(
        os.environ,
        {
            "DATABASE_URL": "postgresql://test:test@localhost/test",
            "SECRET_KEY": "test-secret",
        },
    )
    def test_auth_blueprint_exists(self):
        """Test auth blueprint is properly defined."""
        try:
            from web.auth import auth  # Fixed: blueprint is named 'auth' not 'auth_bp'

            assert auth is not None
            assert hasattr(auth, "name")
            assert auth.name == "auth"
        except Exception as e:
            pytest.fail(f"Auth blueprint test failed: {e}")


if __name__ == "__main__":
    # Run tests
    print("=" * 80)
    print("RUNNING INTEGRITY TESTS")
    print("=" * 80)

    exit_code = pytest.main([__file__, "-v", "--tb=short"])

    if exit_code == 0:
        print("\n" + "=" * 80)
        print("✅ ALL INTEGRITY TESTS PASSED")
        print("=" * 80)
        print("\nThe application is ready for deployment!")
    else:
        print("\n" + "=" * 80)
        print("❌ INTEGRITY TESTS FAILED")
        print("=" * 80)
        print("\nFix the issues above before deploying!")

    sys.exit(exit_code)
