"""
Tests for Database Models

Tests all database models for:
- Correct password hashing
- Relationship integrity
- Data validation
- Model methods
"""

import pytest
from datetime import datetime, timedelta, timezone


class TestUserModel:
    """Test User model"""

    def test_user_password_hashing(self, app, db_session):
        """Test password is hashed, not stored as plaintext"""
        from web.database import User

        user = User(
            email="hash@test.com",
            username="hashtest",
            subscription_tier="free",
            subscription_status="active",
        )
        user.set_password("mysecretpassword")

        db_session.add(user)
        db_session.commit()

        # Password should be hashed
        assert user.password_hash != "mysecretpassword"
        assert len(user.password_hash) > 20  # Hashed passwords are long

        # Should verify correctly
        assert user.check_password("mysecretpassword") is True
        assert user.check_password("wrongpassword") is False

    def test_user_is_developer_method(self, app, db_session):
        """Test is_developer() method works correctly"""
        from web.database import User

        # Create developer user
        dev_user = User(
            email="dev@test.com",
            username="developer",
            subscription_tier="developer",
            subscription_status="active",
        )
        db_session.add(dev_user)

        # Create regular user
        regular_user = User(
            email="regular@test.com",
            username="regular",
            subscription_tier="premium",
            subscription_status="active",
        )
        db_session.add(regular_user)
        db_session.commit()

        assert dev_user.is_developer() is True
        assert regular_user.is_developer() is False

    def test_user_subscription_expiry_check(self, app, db_session):
        """Test subscription expiry is checked correctly"""
        from web.database import User

        # Create expired subscription user
        expired_user = User(
            email="expired@test.com",
            username="expired",
            subscription_tier="premium",
            subscription_status="active",
            subscription_end=datetime.now(timezone.utc) - timedelta(days=1),
        )
        db_session.add(expired_user)

        # Create active subscription user
        active_user = User(
            email="active@test.com",
            username="active",
            subscription_tier="premium",
            subscription_status="active",
            subscription_end=datetime.now(timezone.utc) + timedelta(days=30),
        )
        db_session.add(active_user)
        db_session.commit()

        # Test has_active_subscription method if it exists
        if hasattr(expired_user, "has_active_subscription"):
            assert expired_user.has_active_subscription() is False
            assert active_user.has_active_subscription() is True

    def test_user_unique_email_constraint(self, app, db_session):
        """Test email uniqueness is enforced"""
        from web.database import User
        from sqlalchemy.exc import IntegrityError

        user1 = User(
            email="duplicate@test.com",
            username="user1",
            subscription_tier="free",
        )
        user1.set_password("password1")
        db_session.add(user1)
        db_session.commit()

        # Try to create duplicate email
        user2 = User(
            email="duplicate@test.com",
            username="user2",
            subscription_tier="free",
        )
        user2.set_password("password2")
        db_session.add(user2)

        with pytest.raises(IntegrityError):
            db_session.commit()


class TestWatchlistModel:
    """Test Watchlist model"""

    def test_watchlist_user_relationship(self, app, db_session, test_user):
        """Test Watchlist has correct relationship with User"""
        from web.database import Watchlist

        watchlist = Watchlist(user_id=test_user.id, ticker="AAPL")
        db_session.add(watchlist)
        db_session.commit()

        # Test relationship
        assert watchlist.user_id == test_user.id
        if hasattr(watchlist, "user"):
            assert watchlist.user.email == test_user.email

    def test_watchlist_ticker_validation(self, app, db_session, test_user):
        """Test ticker is stored correctly"""
        from web.database import Watchlist

        watchlist = Watchlist(user_id=test_user.id, ticker="AAPL")
        db_session.add(watchlist)
        db_session.commit()

        retrieved = Watchlist.query.filter_by(ticker="AAPL").first()
        assert retrieved is not None
        assert retrieved.ticker == "AAPL"


class TestNewsArticleModel:
    """Test NewsArticle model"""

    def test_news_article_creation(self, app, db_session):
        """Test NewsArticle can be created with all fields"""
        from web.database import NewsArticle

        article = NewsArticle(
            title="Test Article",
            description="Test description",
            url="https://example.com/article",
            source="Test Source",
            published_at=datetime.now(timezone.utc),
            ai_rating=4.2,
            ai_analysis="Positive outlook for tech stocks",
            sentiment="positive",
        )
        db_session.add(article)
        db_session.commit()

        retrieved = NewsArticle.query.filter_by(title="Test Article").first()
        assert retrieved is not None
        assert retrieved.ai_rating == 4.2
        assert retrieved.sentiment == "positive"

    def test_news_article_unique_url(self, app, db_session):
        """Test article URLs are unique"""
        from web.database import NewsArticle
        from sqlalchemy.exc import IntegrityError

        article1 = NewsArticle(
            title="Article 1",
            url="https://example.com/same-url",
            source="Source",
            published_at=datetime.now(timezone.utc),
        )
        db_session.add(article1)
        db_session.commit()

        # Try duplicate URL
        article2 = NewsArticle(
            title="Article 2",
            url="https://example.com/same-url",
            source="Source",
            published_at=datetime.now(timezone.utc),
        )
        db_session.add(article2)

        with pytest.raises(IntegrityError):
            db_session.commit()


class TestEconomicEventModel:
    """Test EconomicEvent model"""

    def test_economic_event_creation(self, app, db_session):
        """Test EconomicEvent stores all fields correctly"""
        from web.database import EconomicEvent

        event = EconomicEvent(
            title="GDP Growth Rate",
            date=datetime.now(timezone.utc),
            time="08:30 EST",
            country="US",
            importance="high",
            actual="2.8",
            forecast="2.5",
            previous="2.4",
            source="Finnhub",
        )
        db_session.add(event)
        db_session.commit()

        retrieved = EconomicEvent.query.filter_by(title="GDP Growth Rate").first()
        assert retrieved is not None
        assert retrieved.importance == "high"
        assert retrieved.country == "US"

    def test_economic_event_importance_levels(self, app, db_session):
        """Test different importance levels are stored"""
        from web.database import EconomicEvent

        for importance in ["low", "medium", "high"]:
            event = EconomicEvent(
                title=f"Event {importance}",
                date=datetime.now(timezone.utc),
                time="10:00 EST",
                country="US",
                importance=importance,
                source="Finnhub",
            )
            db_session.add(event)

        db_session.commit()

        assert EconomicEvent.query.filter_by(importance="low").count() == 1
        assert EconomicEvent.query.filter_by(importance="medium").count() == 1
        assert EconomicEvent.query.filter_by(importance="high").count() == 1


class TestAIScoreModel:
    """Test AIScore model"""

    def test_ai_score_creation(self, app, db_session):
        """Test AIScore stores score and rating"""
        from web.database import AIScore

        ai_score = AIScore(
            ticker="AAPL",
            score=85,
            rating="Strong Buy",
            features_json='{"pe_ratio": 28.5, "rsi": 65}',
        )
        db_session.add(ai_score)
        db_session.commit()

        retrieved = AIScore.query.filter_by(ticker="AAPL").first()
        assert retrieved is not None
        assert retrieved.score == 85
        assert retrieved.rating == "Strong Buy"

    def test_ai_score_updated_at_timestamp(self, app, db_session):
        """Test updated_at timestamp is set automatically"""
        from web.database import AIScore

        ai_score = AIScore(ticker="MSFT", score=70, rating="Buy")
        db_session.add(ai_score)
        db_session.commit()

        assert ai_score.updated_at is not None
        assert isinstance(ai_score.updated_at, datetime)


class TestModelDefensiveProgramming:
    """Test models handle edge cases defensively"""

    def test_user_handles_none_password(self, app, db_session):
        """Test User model handles None password gracefully"""
        from web.database import User

        user = User(email="test@test.com", username="test")

        # Should not crash when checking password before it's set
        if user.password_hash is None:
            assert user.check_password("anything") is False

    def test_news_article_handles_missing_fields(self, app, db_session):
        """Test NewsArticle works with minimal required fields"""
        from web.database import NewsArticle

        # Create with only required fields
        article = NewsArticle(
            title="Minimal Article",
            url="https://example.com/minimal",
            source="Test",
            published_at=datetime.now(timezone.utc),
        )
        db_session.add(article)
        db_session.commit()

        retrieved = NewsArticle.query.filter_by(title="Minimal Article").first()
        assert retrieved is not None
        assert retrieved.ai_rating is None  # Optional field
        assert retrieved.ai_analysis is None  # Optional field
