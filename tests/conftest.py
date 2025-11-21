"""
Pytest Configuration and Fixtures

This file contains shared fixtures for all tests, including:
- Mock API clients (Polygon, Alpha Vantage, Finnhub, NewsAPI, Anthropic)
- Test database setup
- Flask test client
"""

import os
import sys
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta, timezone

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web"))


@pytest.fixture
def app():
    """Create Flask test app with in-memory SQLite database"""
    # Import database first
    from web.database import db
    from flask import Flask

    # Set testing environment variables
    os.environ["TESTING"] = "true"
    os.environ["FLASK_ENV"] = "testing"
    os.environ["SECRET_KEY"] = "test-secret-key"

    # Set dummy API keys to prevent initialization errors
    os.environ.setdefault("POLYGON_API_KEY", "test-polygon-key")
    os.environ.setdefault("ALPHA_VANTAGE_API_KEY", "test-alpha-key")
    os.environ.setdefault("FINNHUB_API_KEY", "test-finnhub-key")
    os.environ.setdefault("NEWS_API_KEY", "test-news-key")
    os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")

    # Create a bare-bones Flask app for testing
    flask_app = Flask(__name__)
    flask_app.config["TESTING"] = True
    flask_app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    flask_app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    flask_app.config["WTF_CSRF_ENABLED"] = False
    flask_app.config["SECRET_KEY"] = "test-secret-key"

    # Initialize database
    db.init_app(flask_app)

    # Initialize cache
    from web.extensions import cache
    cache.init_app(flask_app)

    # Initialize Flask-Login for authentication tests
    from flask_login import LoginManager

    login_manager = LoginManager()
    login_manager.init_app(flask_app)

    @login_manager.user_loader
    def load_user(user_id):
        from web.database import User

        return User.query.get(int(user_id))

    # Import and register blueprints from the actual app
    with flask_app.app_context():
        # Import blueprints after app context is set
        try:
            from web.api_watchlist import api_watchlist

            flask_app.register_blueprint(api_watchlist)
        except (ImportError, Exception) as e:
            print(f"Warning: Could not import api_watchlist: {e}")

        try:
            from web.api_polygon import api_polygon

            flask_app.register_blueprint(api_polygon)
        except (ImportError, Exception) as e:
            print(f"Warning: Could not import api_polygon: {e}")

        # Create all tables
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Flask test client"""
    return app.test_client()


@pytest.fixture
def db_session(app):
    """Database session for tests"""
    from web.database import db

    return db.session


@pytest.fixture
def test_user(app, db_session):
    """Create a test user"""
    from web.database import User

    user = User(
        email="test@qunextrade.com",
        username="testuser",
        subscription_tier="premium",
        subscription_status="active",
        subscription_start=datetime.now(timezone.utc),
        subscription_end=datetime.now(timezone.utc) + timedelta(days=365),
        email_verified=True,
    )
    user.set_password("testpassword123")

    db_session.add(user)
    db_session.commit()

    return user


@pytest.fixture
def admin_user(app, db_session):
    """Create an admin user"""
    from web.database import User

    admin = User(
        email="admin@qunextrade.com",
        username="admin",
        subscription_tier="developer",
        subscription_status="active",
        subscription_start=datetime.now(timezone.utc),
        subscription_end=datetime.now(timezone.utc) + timedelta(days=3650),
        email_verified=True,
    )
    admin.set_password("admin")

    db_session.add(admin)
    db_session.commit()

    return admin


@pytest.fixture
def mock_polygon_api():
    """Mock Polygon.io API responses"""
    mock = MagicMock()

    # Mock market movers
    mock.get_market_movers.return_value = {
        "gainers": [
            {"ticker": "AAPL", "price": 150.0, "change_percent": 5.2},
            {"ticker": "MSFT", "price": 300.0, "change_percent": 3.1},
        ],
        "losers": [
            {"ticker": "TSLA", "price": 200.0, "change_percent": -4.5},
        ],
    }

    # Mock stock quote
    mock.get_quote.return_value = {
        "ticker": "AAPL",
        "price": 150.0,
        "change": 7.5,
        "change_percent": 5.0,
        "volume": 50000000,
    }

    # Mock technical indicators
    mock.get_technical_indicators.return_value = {
        "rsi": 65.5,
        "macd": 1.2,
        "price_to_ma50": 1.05,
        "price_to_ma200": 1.15,
    }

    return mock


@pytest.fixture
def mock_alpha_vantage_api():
    """Mock Alpha Vantage API responses"""
    mock = MagicMock()

    # Mock company overview
    mock.get_company_overview.return_value = (
        {
            "Symbol": "AAPL",
            "Name": "Apple Inc",
            "MarketCapitalization": "2500000000000",
            "PERatio": "28.5",
            "PriceToBookRatio": "45.2",
            "EPS": "6.15",
            "QuarterlyEarningsGrowthYOY": "0.12",
            "QuarterlyRevenueGrowthYOY": "0.08",
        },
        None,
    )

    return mock


@pytest.fixture
def mock_finnhub_api():
    """Mock Finnhub API responses"""
    mock = MagicMock()

    # Mock economic calendar
    mock.get_economic_calendar.return_value = {
        "economicCalendar": [
            {
                "event": "GDP Growth Rate",
                "country": "US",
                "time": "2025-01-15 08:30:00",
                "impact": "high",
                "actual": "2.8",
                "estimate": "2.5",
                "prev": "2.4",
            },
            {
                "event": "Unemployment Rate",
                "country": "US",
                "time": "2025-01-16 10:00:00",
                "impact": "high",
                "actual": None,
                "estimate": "3.8",
                "prev": "3.7",
            },
        ]
    }

    return mock


@pytest.fixture
def mock_newsapi():
    """Mock NewsAPI responses"""
    mock = MagicMock()

    mock.get_everything.return_value = {
        "status": "ok",
        "totalResults": 2,
        "articles": [
            {
                "title": "Apple stock surges on strong iPhone sales",
                "description": "Apple Inc. shares rose 5% today...",
                "url": "https://example.com/article1",
                "source": {"name": "Tech News"},
                "publishedAt": "2025-01-12T10:00:00Z",
            },
            {
                "title": "Microsoft announces new AI features",
                "description": "Microsoft unveiled new AI capabilities...",
                "url": "https://example.com/article2",
                "source": {"name": "Business Wire"},
                "publishedAt": "2025-01-12T14:30:00Z",
            },
        ],
    }

    return mock


@pytest.fixture
def mock_anthropic_api():
    """Mock Anthropic Claude API responses"""
    mock = MagicMock()

    # Mock message response
    mock_response = MagicMock()
    mock_response.content = [
        MagicMock(
            text='{"rating": 4.2, "sentiment": "positive", "analysis": "Strong growth potential based on recent earnings."}'
        )
    ]

    mock.messages.create.return_value = mock_response

    return mock


@pytest.fixture
def mock_requests_get(mock_finnhub_api):
    """Mock requests.get for external API calls"""
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_finnhub_api.get_economic_calendar.return_value
        mock_response.raise_for_status.return_value = None

        mock_get.return_value = mock_response
        yield mock_get
