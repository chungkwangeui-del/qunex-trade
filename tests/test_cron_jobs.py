"""
Tests for Cron Job Scripts

Tests all background cron jobs with mocked API responses:
- refresh_news (NewsAPI + Anthropic)
- refresh_calendar (Finnhub)
- update_ai_scores (Alpha Vantage + Polygon)
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone
import json


class TestRefreshNewsCron:
    """Test scripts/refresh_data_cron.py::refresh_news_data()"""

    def test_refresh_news_success(
        self, app, db_session, mock_newsapi, mock_anthropic_api, monkeypatch
    ):
        """Test news refresh saves articles to DB with AI analysis"""
        from web.database import NewsArticle
        from newsapi import NewsApiClient

        # Set environment variables
        monkeypatch.setenv("NEWSAPI_KEY", "test_key")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test_key")

        # Mock NewsAPI client
        with patch("src.news_collector.NewsApiClient", return_value=mock_newsapi):
            with patch("anthropic.Anthropic", return_value=mock_anthropic_api):
                # Import after patching
                from scripts.refresh_data_cron import refresh_news_data

                # Run refresh
                result = refresh_news_data()

                assert result is True

                # Verify articles were saved
                articles = NewsArticle.query.all()
                assert len(articles) == 2

                # Verify first article
                article1 = NewsArticle.query.filter_by(
                    title="Apple stock surges on strong iPhone sales"
                ).first()
                assert article1 is not None
                assert article1.ai_rating == 4.2
                assert article1.sentiment == "positive"
                assert "Strong growth" in article1.ai_analysis

    def test_refresh_news_missing_api_key(self, app, monkeypatch):
        """Test news refresh fails gracefully without API keys"""
        monkeypatch.delenv("NEWSAPI_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        from scripts.refresh_data_cron import refresh_news_data

        result = refresh_news_data()
        assert result is False

    def test_refresh_news_cleans_old_articles(self, app, db_session, monkeypatch):
        """Test old articles (>30 days) are deleted"""
        from web.database import NewsArticle

        # Create old article
        old_article = NewsArticle(
            title="Old News",
            url="https://example.com/old",
            source="Test",
            published_at=datetime.now(timezone.utc) - timedelta(days=35),
            ai_rating=3.0,
        )
        db_session.add(old_article)
        db_session.commit()

        assert NewsArticle.query.count() == 1

        # Mock API calls
        monkeypatch.setenv("NEWSAPI_KEY", "test_key")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test_key")

        mock_newsapi = MagicMock()
        mock_newsapi.get_everything.return_value = {
            "status": "ok",
            "totalResults": 0,
            "articles": [],
        }

        with patch("src.news_collector.NewsApiClient", return_value=mock_newsapi):
            with patch("anthropic.Anthropic"):
                from scripts.refresh_data_cron import refresh_news_data

                refresh_news_data()

        # Old article should be deleted
        assert NewsArticle.query.count() == 0


class TestRefreshCalendarCron:
    """Test scripts/refresh_data_cron.py::refresh_calendar_data()"""

    def test_refresh_calendar_success(self, app, db_session, mock_requests_get, monkeypatch):
        """Test calendar refresh saves events to DB"""
        from web.database import EconomicEvent

        monkeypatch.setenv("FINNHUB_API_KEY", "test_key")

        from scripts.refresh_data_cron import refresh_calendar_data

        result = refresh_calendar_data()

        assert result is True

        # Verify events were saved
        events = EconomicEvent.query.all()
        assert len(events) == 2

        # Verify first event
        gdp_event = EconomicEvent.query.filter_by(title="GDP Growth Rate").first()
        assert gdp_event is not None
        assert gdp_event.country == "US"
        assert gdp_event.importance == "high"
        assert gdp_event.actual == "2.8"
        assert gdp_event.forecast == "2.5"

    def test_refresh_calendar_missing_api_key(self, app, monkeypatch):
        """Test calendar refresh fails gracefully without API key"""
        monkeypatch.delenv("FINNHUB_API_KEY", raising=False)

        from scripts.refresh_data_cron import refresh_calendar_data

        result = refresh_calendar_data()
        assert result is False

    def test_refresh_calendar_updates_existing(
        self, app, db_session, mock_requests_get, monkeypatch
    ):
        """Test existing events are updated, not duplicated"""
        from web.database import EconomicEvent

        # Create existing event
        existing = EconomicEvent(
            title="GDP Growth Rate",
            date=datetime.strptime("2025-01-15 08:30:00", "%Y-%m-%d %H:%M:%S"),
            time="08:30 EST",
            country="US",
            importance="medium",  # Will be updated to "high"
            source="Finnhub",
        )
        db_session.add(existing)
        db_session.commit()

        monkeypatch.setenv("FINNHUB_API_KEY", "test_key")

        from scripts.refresh_data_cron import refresh_calendar_data

        refresh_calendar_data()

        # Should still be 2 events (1 existing updated, 1 new)
        events = EconomicEvent.query.all()
        assert len(events) == 2

        # Verify existing event was updated
        gdp_event = EconomicEvent.query.filter_by(title="GDP Growth Rate").first()
        assert gdp_event.importance == "high"  # Updated


class TestUpdateAIScoresCron:
    """Test cron_update_ai_scores.py::update_ai_scores()"""

    def test_update_ai_scores_success(
        self, app, db_session, mock_alpha_vantage_api, mock_polygon_api, monkeypatch
    ):
        """Test AI score calculation and storage"""
        from web.database import AIScore, Watchlist

        # Create watchlist entry
        watchlist = Watchlist(user_id=1, ticker="AAPL")
        db_session.add(watchlist)
        db_session.commit()

        # Set environment variables
        monkeypatch.setenv("ALPHA_VANTAGE_API_KEY", "test_key")
        monkeypatch.setenv("POLYGON_API_KEY", "test_key")
        monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

        # Mock API services
        with patch("cron_update_ai_scores.FundamentalData", return_value=mock_alpha_vantage_api):
            with patch("cron_update_ai_scores.PolygonService", return_value=mock_polygon_api):
                # Import and run
                import cron_update_ai_scores

                # Note: This would require refactoring cron_update_ai_scores.py
                # to accept app context, or we mock the entire function
                # For now, test the feature calculation function directly
                features = cron_update_ai_scores.calculate_enhanced_features(
                    "AAPL", mock_polygon_api, mock_alpha_vantage_api, db_session
                )

                assert features is not None
                assert "rsi" in features
                assert "pe_ratio" in features
                assert features["pe_ratio"] == 28.5

                # Test score calculation
                score = cron_update_ai_scores.calculate_ai_score(features)
                assert 0 <= score <= 100
                assert isinstance(score, int)

                # Test rating determination
                rating = cron_update_ai_scores.determine_rating(score)
                assert rating in ["Strong Buy", "Buy", "Hold", "Sell", "Strong Sell"]

    def test_ai_score_defensive_defaults(self, app, db_session, monkeypatch):
        """Test AI score uses defensive defaults when API fails"""
        monkeypatch.setenv("ALPHA_VANTAGE_API_KEY", "test_key")

        # Mock failed API call
        mock_av = MagicMock()
        mock_av.get_company_overview.return_value = (None, None)  # API failure

        import cron_update_ai_scores

        features = cron_update_ai_scores.calculate_enhanced_features(
            "INVALID", None, mock_av, db_session
        )

        # Should return default features
        assert features is not None
        assert features["pe_ratio"] == 20.0  # Default
        assert features["rsi"] == 50  # Default


class TestCronJobAtomicity:
    """Test all cron jobs handle errors with proper rollback"""

    def test_news_refresh_rollback_on_error(self, app, db_session, monkeypatch):
        """Test news refresh rolls back DB on error"""
        from web.database import NewsArticle

        monkeypatch.setenv("NEWSAPI_KEY", "test_key")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test_key")

        # Mock NewsAPI to raise exception
        mock_newsapi = MagicMock()
        mock_newsapi.get_everything.side_effect = Exception("API Error")

        with patch("src.news_collector.NewsApiClient", return_value=mock_newsapi):
            from scripts.refresh_data_cron import refresh_news_data

            result = refresh_news_data()

            # Should return False and not crash
            assert result is False

            # No partial data should be saved
            assert NewsArticle.query.count() == 0
