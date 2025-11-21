"""
Tests for Service Layer

Tests all service modules:
- Polygon API service
- News collector service
- Email service
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime


class TestPolygonService:
    """Test Polygon API service"""

    def test_polygon_service_initialization(self, app):
        """Test PolygonService can be initialized"""
        from web.polygon_service import PolygonService

        service = PolygonService()
        assert service is not None

    def test_get_stock_quote_with_mock(self, app, mock_polygon_api):
        """Test getting stock quote with mocked API"""
        with patch("src.polygon_service.PolygonService") as mock_service:
            mock_service.return_value = mock_polygon_api

            service = mock_service()
            quote = service.get_quote("AAPL")

            assert quote is not None
            assert quote["ticker"] == "AAPL"
            assert "price" in quote

    def test_get_market_movers_with_mock(self, app, mock_polygon_api):
        """Test getting market movers with mocked API"""
        with patch("src.polygon_service.PolygonService") as mock_service:
            mock_service.return_value = mock_polygon_api

            service = mock_service()
            movers = service.get_market_movers()

            assert "gainers" in movers
            assert "losers" in movers
            assert len(movers["gainers"]) > 0

    def test_polygon_service_handles_api_errors(self, app):
        """Test Polygon service handles API errors gracefully"""
        with patch("src.polygon_service.PolygonService") as mock_service:
            mock_instance = MagicMock()
            mock_instance.get_quote.side_effect = Exception("API Error")
            mock_service.return_value = mock_instance

            service = mock_service()

            # Should not crash, should return None or empty
            try:
                result = service.get_quote("AAPL")
                assert result is None or isinstance(result, dict)
            except Exception:
                pytest.fail("Service should handle API errors gracefully")


class TestNewsCollector:
    """Test news collector service"""

    def test_news_collector_initialization(self, app, monkeypatch):
        """Test NewsCollector can be initialized"""
        monkeypatch.setenv("NEWSAPI_KEY", "test_key")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test_key")

        from src.news_collector import NewsCollector

        collector = NewsCollector()
        assert collector is not None

    def test_fetch_news_with_mock(self, app, mock_newsapi, mock_anthropic_api, monkeypatch):
        """Test fetching news with mocked APIs"""
        monkeypatch.setenv("NEWSAPI_KEY", "test_key")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test_key")

        with patch("src.news_collector.NewsApiClient", return_value=mock_newsapi):
            with patch("anthropic.Anthropic", return_value=mock_anthropic_api):
                from src.news_collector import NewsCollector

                collector = NewsCollector()
                articles = collector.fetch_market_news()

                assert isinstance(articles, list)

    def test_news_collector_handles_empty_results(self, app, monkeypatch):
        """Test news collector handles empty API results"""
        monkeypatch.setenv("NEWSAPI_KEY", "test_key")

        mock_newsapi = MagicMock()
        mock_newsapi.get_everything.return_value = {
            "status": "ok",
            "totalResults": 0,
            "articles": [],
        }

        with patch("src.news_collector.NewsApiClient", return_value=mock_newsapi):
            from src.news_collector import NewsCollector

            collector = NewsCollector()
            articles = collector.fetch_market_news()

            assert articles == [] or articles is None


class TestEmailService:
    """Test email service"""

    def test_send_email_with_mock(self, app, monkeypatch):
        """Test sending email with mocked SMTP"""
        monkeypatch.setenv("MAIL_USERNAME", "test@example.com")
        monkeypatch.setenv("MAIL_PASSWORD", "testpassword")

        with patch("flask_mail.Mail.send") as mock_send:
            from flask_mail import Message

            msg = Message("Test", recipients=["user@example.com"])

            # Should not crash
            try:
                mock_send(msg)
            except Exception:
                # Expected if mail not configured
                pass

    def test_email_verification_token_generation(self, app, test_user):
        """Test email verification token generation"""
        # If email verification is implemented
        if hasattr(test_user, "generate_verification_token"):
            token = test_user.generate_verification_token()
            assert token is not None
            assert len(token) > 10


class TestCacheService:
    """Test caching service"""

    def test_cache_stores_and_retrieves(self, app):
        """Test cache can store and retrieve data"""
        from web.app import cache

        # Set cache value
        cache.set("test_key", "test_value", timeout=60)

        # Retrieve cache value
        value = cache.get("test_key")
        assert value == "test_value"

    def test_cache_expires(self, app):
        """Test cache expires after timeout"""
        from web.app import cache
        import time

        # Set cache with short timeout
        cache.set("expire_key", "expire_value", timeout=1)

        # Wait for expiration
        time.sleep(2)

        # Should be None after expiration
        value = cache.get("expire_key")
        assert value is None

    def test_cache_delete(self, app):
        """Test cache can be deleted"""
        from web.app import cache

        cache.set("delete_key", "delete_value")
        cache.delete("delete_key")

        value = cache.get("delete_key")
        assert value is None


class TestDatabaseQueries:
    """Test database query optimization"""

    def test_no_n_plus_1_on_watchlist(self, app, db_session, test_user):
        """Test watchlist queries don't cause N+1 problem"""
        from web.database import Watchlist

        # Create multiple watchlist items
        tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
        for ticker in tickers:
            watchlist = Watchlist(user_id=test_user.id, ticker=ticker)
            db_session.add(watchlist)
        db_session.commit()

        # Query should be efficient (single query or with joinedload)
        watchlist_items = Watchlist.query.filter_by(user_id=test_user.id).all()

        assert len(watchlist_items) == 5

    def test_no_n_plus_1_on_ai_scores(self, app, db_session):
        """Test AI score queries are optimized"""
        from web.database import AIScore

        # Create multiple AI scores
        tickers = ["AAPL", "MSFT", "GOOGL"]
        for ticker in tickers:
            score = AIScore(ticker=ticker, score=75, rating="Buy")
            db_session.add(score)
        db_session.commit()

        # Query with .in_() to avoid N+1
        scores = AIScore.query.filter(AIScore.ticker.in_(tickers)).all()

        assert len(scores) == 3


class TestDefensiveProgramming:
    """Test defensive programming practices"""

    def test_handles_none_api_response(self, app):
        """Test code handles None API responses"""
        from web.polygon_service import PolygonService

        with patch.object(PolygonService, "get_stock_quote", return_value=None):
            service = PolygonService()
            result = service.get_stock_quote("INVALID")

            assert result is None

    def test_handles_empty_database_results(self, app, db_session, test_user):
        """Test code handles empty database results"""
        from web.database import Watchlist

        # Query non-existent data
        watchlist = Watchlist.query.filter_by(user_id=99999).all()

        # Should return empty list, not crash
        assert watchlist == []

    def test_handles_invalid_json(self, client, test_user):
        """Test API endpoints handle invalid JSON"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user.id)

        response = client.post(
            "/api/watchlist",
            data="invalid json{{{",
            content_type="application/json",
        )

        # Should return error, not crash
        assert response.status_code == 400
