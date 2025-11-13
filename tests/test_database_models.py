"""
Unit tests for database models

Tests the NewsArticle and EconomicEvent models to ensure
proper creation, retrieval, and serialization.
"""

import pytest
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web.app import app
from web.database import db, NewsArticle, EconomicEvent, User


@pytest.fixture
def client():
    """
    Create a test client with in-memory SQLite database.

    Yields:
        FlaskClient: Test client for making requests
    """
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["WTF_CSRF_ENABLED"] = False

    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


class TestNewsArticleModel:
    """Test suite for NewsArticle model"""

    def test_create_news_article(self, client):
        """Test creating a news article"""
        with app.app_context():
            article = NewsArticle(
                title="Test Article",
                description="Test description",
                url="https://example.com/test",
                source="Test Source",
                published_at=datetime.utcnow(),
                ai_rating=5,
                ai_analysis="Positive outlook for tech stocks",
                sentiment="positive",
            )
            db.session.add(article)
            db.session.commit()

            # Retrieve and verify
            saved_article = NewsArticle.query.filter_by(title="Test Article").first()
            assert saved_article is not None
            assert saved_article.title == "Test Article"
            assert saved_article.ai_rating == 5
            assert saved_article.sentiment == "positive"

    def test_news_article_unique_url(self, client):
        """Test that URL is unique constraint"""
        with app.app_context():
            # Create first article
            article1 = NewsArticle(
                title="Article 1",
                url="https://example.com/same-url",
                source="Source 1",
                published_at=datetime.utcnow(),
            )
            db.session.add(article1)
            db.session.commit()

            # Try to create second article with same URL
            article2 = NewsArticle(
                title="Article 2",
                url="https://example.com/same-url",
                source="Source 2",
                published_at=datetime.utcnow(),
            )
            db.session.add(article2)

            # Should raise IntegrityError
            with pytest.raises(Exception):
                db.session.commit()

    def test_news_article_to_dict(self, client):
        """Test NewsArticle to_dict() serialization"""
        with app.app_context():
            article = NewsArticle(
                title="Serialization Test",
                description="Test description",
                url="https://example.com/serial",
                source="Test Source",
                published_at=datetime(2025, 1, 1, 12, 0, 0),
                ai_rating=4,
                ai_analysis="Good analysis",
                sentiment="neutral",
            )
            db.session.add(article)
            db.session.commit()

            # Convert to dict
            article_dict = article.to_dict()

            assert article_dict["title"] == "Serialization Test"
            assert article_dict["ai_rating"] == 4
            assert article_dict["sentiment"] == "neutral"
            assert "published" in article_dict
            assert "id" in article_dict

    def test_news_article_query_by_rating(self, client):
        """Test filtering news articles by AI rating"""
        with app.app_context():
            # Create articles with different ratings
            for i in range(1, 6):
                article = NewsArticle(
                    title=f"Article {i}",
                    url=f"https://example.com/article-{i}",
                    source="Test",
                    published_at=datetime.utcnow(),
                    ai_rating=i,
                )
                db.session.add(article)
            db.session.commit()

            # Query 5-star articles
            five_star = NewsArticle.query.filter(NewsArticle.ai_rating == 5).all()
            assert len(five_star) == 1
            assert five_star[0].title == "Article 5"

            # Query articles with rating >= 4
            high_rated = NewsArticle.query.filter(NewsArticle.ai_rating >= 4).all()
            assert len(high_rated) == 2


class TestEconomicEventModel:
    """Test suite for EconomicEvent model"""

    def test_create_economic_event(self, client):
        """Test creating an economic event"""
        with app.app_context():
            event = EconomicEvent(
                title="Fed Interest Rate Decision",
                date=datetime(2025, 12, 15, 14, 0, 0),
                time="2:00 PM EST",
                country="US",
                importance="high",
                actual="5.25%",
                forecast="5.00%",
                previous="4.75%",
                source="Finnhub",
            )
            db.session.add(event)
            db.session.commit()

            # Retrieve and verify
            saved_event = EconomicEvent.query.filter_by(title="Fed Interest Rate Decision").first()
            assert saved_event is not None
            assert saved_event.importance == "high"
            assert saved_event.country == "US"

    def test_economic_event_unique_constraint(self, client):
        """Test unique constraint on title + date"""
        with app.app_context():
            event_date = datetime(2025, 12, 15, 14, 0, 0)

            # Create first event
            event1 = EconomicEvent(
                title="CPI Report", date=event_date, country="US", importance="high"
            )
            db.session.add(event1)
            db.session.commit()

            # Try to create duplicate
            event2 = EconomicEvent(
                title="CPI Report", date=event_date, country="US", importance="high"
            )
            db.session.add(event2)

            # Should raise IntegrityError
            with pytest.raises(Exception):
                db.session.commit()

    def test_economic_event_to_dict(self, client):
        """Test EconomicEvent to_dict() serialization"""
        with app.app_context():
            event = EconomicEvent(
                title="GDP Report",
                date=datetime(2025, 6, 30, 8, 30, 0),
                time="8:30 AM EST",
                country="US",
                importance="medium",
                actual="2.1%",
                forecast="2.0%",
                previous="1.9%",
            )
            db.session.add(event)
            db.session.commit()

            # Convert to dict
            event_dict = event.to_dict()

            assert event_dict["title"] == "GDP Report"
            assert event_dict["importance"] == "medium"
            assert event_dict["actual"] == "2.1%"
            assert "date" in event_dict
            assert "id" in event_dict

    def test_economic_event_query_by_importance(self, client):
        """Test filtering events by importance"""
        with app.app_context():
            # Create events with different importance
            importances = ["low", "medium", "high"]
            for i, imp in enumerate(importances):
                event = EconomicEvent(
                    title=f"Event {i}",
                    date=datetime.utcnow() + timedelta(days=i),
                    importance=imp,
                    country="US",
                )
                db.session.add(event)
            db.session.commit()

            # Query high importance events
            high_importance = EconomicEvent.query.filter(EconomicEvent.importance == "high").all()
            assert len(high_importance) == 1

    def test_economic_event_date_range_query(self, client):
        """Test querying events within date range"""
        with app.app_context():
            today = datetime.utcnow()

            # Create events at different dates
            for days_ahead in [1, 7, 30, 90]:
                event = EconomicEvent(
                    title=f"Event in {days_ahead} days",
                    date=today + timedelta(days=days_ahead),
                    country="US",
                    importance="medium",
                )
                db.session.add(event)
            db.session.commit()

            # Query events in next 60 days
            end_date = today + timedelta(days=60)
            upcoming_events = EconomicEvent.query.filter(
                EconomicEvent.date >= today, EconomicEvent.date <= end_date
            ).all()

            assert len(upcoming_events) == 3  # 1, 7, 30 days


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
