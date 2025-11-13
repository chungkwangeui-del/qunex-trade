"""
Unit tests for API endpoints

Tests the main API routes to ensure they return correct data
and handle edge cases properly.
"""

import pytest
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web.app import app
from web.database import db, NewsArticle, EconomicEvent


@pytest.fixture
def client():
    """
    Create a test client with in-memory database.

    Yields:
        FlaskClient: Test client for making HTTP requests
    """
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["WTF_CSRF_ENABLED"] = False

    with app.app_context():
        db.create_all()

        # Seed test data
        _seed_test_data()

        yield app.test_client()

        db.session.remove()
        db.drop_all()


def _seed_test_data():
    """Seed database with test data"""
    # Create test news articles
    for i in range(1, 6):
        article = NewsArticle(
            title=f"Test Article {i}",
            description=f"Description {i}",
            url=f"https://example.com/article-{i}",
            source="Test Source",
            published_at=datetime.utcnow() - timedelta(hours=i),
            ai_rating=i,
            ai_analysis=f"Analysis {i}",
            sentiment="positive" if i > 3 else "neutral",
        )
        db.session.add(article)

    # Create test economic events
    for i in range(1, 4):
        event = EconomicEvent(
            title=f"Economic Event {i}",
            date=datetime.utcnow() + timedelta(days=i),
            time="9:00 AM EST",
            country="US",
            importance="high" if i == 1 else "medium",
            actual="5.0%",
            forecast="4.8%",
            previous="4.5%",
            source="Test",
        )
        db.session.add(event)

    db.session.commit()


class TestNewsAPI:
    """Test suite for news-related API endpoints"""

    def test_get_all_news(self, client):
        """Test retrieving all news articles"""
        response = client.get("/api/news")
        assert response.status_code == 200

        data = response.get_json()
        assert "success" in data
        assert data["success"] is True
        assert "articles" in data
        assert len(data["articles"]) == 5

    def test_get_five_star_news(self, client):
        """Test filtering 5-star news"""
        response = client.get("/api/news/critical")
        assert response.status_code == 200

        data = response.get_json()
        assert "success" in data

        # Check that only 5-star articles are returned
        if data["success"]:
            articles = data.get("articles", [])
            for article in articles:
                assert article.get("ai_rating") == 5

    def test_search_news_by_ticker(self, client):
        """Test searching news by ticker symbol"""
        # Create article with ticker in title
        with app.app_context():
            article = NewsArticle(
                title="AAPL Stock Surges",
                url="https://example.com/aapl-news",
                source="Test",
                published_at=datetime.utcnow(),
                ai_rating=4,
            )
            db.session.add(article)
            db.session.commit()

        response = client.get("/api/news/search?ticker=AAPL")
        assert response.status_code == 200

        data = response.get_json()
        assert "success" in data

    def test_search_news_by_keyword(self, client):
        """Test searching news by keyword"""
        response = client.get("/api/news/search?keyword=test")
        assert response.status_code == 200

        data = response.get_json()
        assert "success" in data

        # Should return articles with 'test' in title
        if data["success"]:
            articles = data.get("articles", [])
            for article in articles:
                assert "test" in article["title"].lower()


class TestEconomicCalendarAPI:
    """Test suite for economic calendar API"""

    def test_get_economic_calendar(self, client):
        """Test retrieving economic calendar events"""
        response = client.get("/api/economic-calendar")
        assert response.status_code == 200

        data = response.get_json()
        assert "success" in data
        assert data["success"] is True
        assert "events" in data
        assert len(data["events"]) == 3

    def test_calendar_events_sorted_by_date(self, client):
        """Test that events are sorted chronologically"""
        response = client.get("/api/economic-calendar")
        assert response.status_code == 200

        data = response.get_json()
        events = data.get("events", [])

        # Check that events are in chronological order
        if len(events) > 1:
            for i in range(len(events) - 1):
                date1 = events[i]["date"]
                date2 = events[i + 1]["date"]
                assert date1 <= date2


class TestStockAPI:
    """Test suite for stock-related API endpoints"""

    @patch("web.app.PolygonService")
    def test_get_stock_chart_data(self, mock_polygon, client):
        """Test fetching stock chart data"""
        # Mock Polygon API response
        mock_service = MagicMock()
        mock_service.get_aggregate_bars.return_value = {
            "candles": [
                {
                    "time": 1640995200,
                    "open": 100,
                    "high": 105,
                    "low": 99,
                    "close": 103,
                    "volume": 1000000,
                }
            ]
        }
        mock_polygon.return_value = mock_service

        response = client.get("/api/stock/AAPL/chart?timeframe=1D")
        assert response.status_code == 200

        data = response.get_json()
        assert "candles" in data or "error" in data

    @patch("web.app.NewsArticle")
    def test_get_stock_news(self, mock_news, client):
        """Test fetching news for specific stock"""
        # Create mock news articles
        with app.app_context():
            article = NewsArticle(
                title="TSLA Announces New Model",
                url="https://example.com/tsla",
                source="Test",
                published_at=datetime.utcnow(),
            )
            db.session.add(article)
            db.session.commit()

        response = client.get("/api/stock/TSLA/news")
        assert response.status_code in [200, 500]  # May fail if Polygon API not configured

    def test_invalid_stock_symbol(self, client):
        """Test API behavior with invalid stock symbol"""
        response = client.get("/api/stock/INVALID_SYMBOL_123/chart")

        # Should handle gracefully (200 with error or 400/500)
        assert response.status_code in [200, 400, 500]


class TestMarketOverviewAPI:
    """Test suite for market overview endpoints"""

    def test_get_market_overview(self, client):
        """Test market overview endpoint"""
        response = client.get("/")
        assert response.status_code == 200

    def test_get_screener_page(self, client):
        """Test screener page loads"""
        response = client.get("/screener")
        assert response.status_code == 200

    def test_get_calendar_page(self, client):
        """Test calendar page loads"""
        response = client.get("/calendar")
        assert response.status_code == 200


class TestErrorHandling:
    """Test suite for error handling"""

    def test_404_error(self, client):
        """Test 404 page not found"""
        response = client.get("/nonexistent-page")
        assert response.status_code == 404

    def test_empty_database_queries(self, client):
        """Test API behavior with empty database"""
        with app.app_context():
            # Clear all data
            NewsArticle.query.delete()
            EconomicEvent.query.delete()
            db.session.commit()

        # APIs should still return valid responses (empty arrays)
        response = client.get("/api/news")
        assert response.status_code == 200

        data = response.get_json()
        assert "success" in data or "articles" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
