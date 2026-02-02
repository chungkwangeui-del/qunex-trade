"""
Pytest Configuration and Fixtures for Qunex Trade Tests

Provides shared fixtures for:
- Flask test client
- Database setup/teardown
- Mock services
- Authentication helpers
"""

import pytest
import os
import sys
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web.app import create_app
from web.database import db, User
from web.config import Config

class TestConfig(Config):
    """Test configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test-secret-key"
    CACHE_TYPE = "SimpleCache"

    # Disable rate limiting in tests
    RATELIMIT_ENABLED = False

@pytest.fixture(scope="session")
def app():
    """Create application for testing"""
    app = create_app(TestConfig)

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture(scope="function")
def client(app):
    """Create test client"""
    with app.test_client() as client:
        yield client

@pytest.fixture(scope="function")
def app_context(app):
    """Create app context for database operations"""
    with app.app_context():
        yield app

@pytest.fixture(scope="function")
def db_session(app_context):
    """Create database session with rollback"""
    db.session.begin_nested()
    yield db.session
    db.session.rollback()

@pytest.fixture
def test_user(app_context, db_session):
    """Create a test user"""
    user = User(
        username="testuser",
        email="test@example.com",
        is_verified=True
    )
    user.set_password("testpassword123")
    db.session.add(user)
    db.session.commit()
    yield user
    db.session.delete(user)
    db.session.commit()

@pytest.fixture
def authenticated_client(client, test_user):
    """Create an authenticated test client"""
    with client.session_transaction() as session:
        session["_user_id"] = str(test_user.id)
        session["_fresh"] = True
    yield client

@pytest.fixture
def mock_polygon():
    """Mock Polygon API service"""
    with patch("web.polygon_service.PolygonService") as mock:
        instance = mock.return_value

        # Mock common methods
        instance.get_stock_quote.return_value = {
            "price": 150.00,
            "change": 2.50,
            "change_percent": 1.69,
            "volume": 50000000,
            "open": 148.00,
            "high": 151.00,
            "low": 147.50,
            "prev_close": 147.50
        }

        instance.get_market_indices.return_value = {
            "SPY": {"name": "S&P 500", "price": 500.00, "change_percent": 0.5},
            "QQQ": {"name": "NASDAQ", "price": 400.00, "change_percent": 0.8},
            "DIA": {"name": "Dow Jones", "price": 380.00, "change_percent": 0.3},
            "IWM": {"name": "Russell 2000", "price": 200.00, "change_percent": -0.2}
        }

        instance.get_market_snapshot.return_value = {
            "AAPL": {"price": 150.00, "change": 2.50, "change_percent": 1.69},
            "MSFT": {"price": 350.00, "change": -1.50, "change_percent": -0.43}
        }

        instance.get_ticker_details.return_value = {
            "name": "Apple Inc.",
            "market_cap": 2500000000000,
            "description": "Apple designs, manufactures, and sells smartphones..."
        }

        yield instance

@pytest.fixture
def mock_news():
    """Mock news articles"""
    return [
        {
            "title": "Tech stocks rally on AI optimism",
            "url": "https://example.com/news/1",
            "source": "Reuters",
            "published_at": "2026-01-21T10:00:00Z",
            "sentiment": "bullish",
            "tickers": ["AAPL", "MSFT", "GOOGL"]
        },
        {
            "title": "Fed signals potential rate cuts",
            "url": "https://example.com/news/2",
            "source": "Bloomberg",
            "published_at": "2026-01-21T09:00:00Z",
            "sentiment": "bullish",
            "tickers": ["SPY", "QQQ"]
        }
    ]

# Helper functions for tests
def login_user(client, email="test@example.com", password="testpassword123"):
    """Helper to log in a user"""
    return client.post("/auth/login", data={
        "email": email,
        "password": password
    }, follow_redirects=True)

def create_user(db_session, username, email, password="testpass123", verified=True):
    """Helper to create a user"""
    user = User(username=username, email=email, is_verified=verified)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user
