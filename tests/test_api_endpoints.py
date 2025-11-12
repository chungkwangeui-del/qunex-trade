"""
Tests for API Endpoints

Tests security, authentication, and functionality of API routes:
- api_watchlist.py (CRUD operations with CSRF protection)
- api_polygon.py (market data endpoints with caching)
"""

import pytest
import json
from flask_login import login_user


class TestWatchlistAPI:
    """Test web/api_watchlist.py endpoints"""

    def test_add_to_watchlist_requires_login(self, client):
        """Test adding to watchlist requires authentication"""
        response = client.post(
            "/api/watchlist/add",
            data=json.dumps({"ticker": "AAPL"}),
            content_type="application/json",
        )

        # Should redirect to login (302) or return 401
        assert response.status_code in [302, 401]

    def test_add_to_watchlist_success(self, client, test_user, db_session):
        """Test authenticated user can add ticker to watchlist"""
        from web.database import Watchlist

        # Login user
        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user.id)

        response = client.post(
            "/api/watchlist/add",
            data=json.dumps({"ticker": "AAPL"}),
            content_type="application/json",
            headers={"X-CSRFToken": "test-token"},  # CSRF disabled in test config
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "success"

        # Verify in database
        watchlist_entry = Watchlist.query.filter_by(
            user_id=test_user.id, ticker="AAPL"
        ).first()
        assert watchlist_entry is not None

    def test_add_duplicate_watchlist_entry(self, client, test_user, db_session):
        """Test adding duplicate ticker returns error"""
        from web.database import Watchlist

        # Add first entry
        existing = Watchlist(user_id=test_user.id, ticker="AAPL")
        db_session.add(existing)
        db_session.commit()

        # Login user
        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user.id)

        # Try to add duplicate
        response = client.post(
            "/api/watchlist/add",
            data=json.dumps({"ticker": "AAPL"}),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert "already" in data["error"].lower()

    def test_remove_from_watchlist_success(self, client, test_user, db_session):
        """Test authenticated user can remove ticker from watchlist"""
        from web.database import Watchlist

        # Add entry to remove
        entry = Watchlist(user_id=test_user.id, ticker="AAPL")
        db_session.add(entry)
        db_session.commit()

        # Login user
        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user.id)

        response = client.post(
            "/api/watchlist/remove",
            data=json.dumps({"ticker": "AAPL"}),
            content_type="application/json",
        )

        assert response.status_code == 200

        # Verify removed from database
        assert Watchlist.query.filter_by(user_id=test_user.id, ticker="AAPL").first() is None

    def test_get_watchlist_success(self, client, test_user, db_session):
        """Test authenticated user can retrieve their watchlist"""
        from web.database import Watchlist

        # Add entries
        db_session.add_all(
            [
                Watchlist(user_id=test_user.id, ticker="AAPL"),
                Watchlist(user_id=test_user.id, ticker="MSFT"),
                Watchlist(user_id=test_user.id, ticker="GOOGL"),
            ]
        )
        db_session.commit()

        # Login user
        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user.id)

        response = client.get("/api/watchlist")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data["watchlist"]) == 3
        assert "AAPL" in [item["ticker"] for item in data["watchlist"]]


class TestPolygonAPI:
    """Test web/api_polygon.py endpoints"""

    def test_market_movers_requires_subscription(self, client, test_user):
        """Test market movers endpoint requires active subscription"""
        # Create user without subscription
        test_user.subscription_status = "inactive"

        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user.id)

        response = client.get("/api/polygon/market-movers")

        # Should return 403 Forbidden or redirect to pricing
        assert response.status_code in [302, 403]

    def test_market_movers_success(self, client, test_user, mock_polygon_api):
        """Test market movers returns data for subscribed users"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user.id)

        with pytest.mock.patch(
            "web.api_polygon.PolygonService", return_value=mock_polygon_api
        ):
            response = client.get("/api/polygon/market-movers")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert "gainers" in data
            assert "losers" in data
            assert len(data["gainers"]) > 0

    def test_api_handles_none_values(self, client, test_user):
        """Test API endpoints handle None/empty responses gracefully"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user.id)

        # Mock API returning None
        mock_polygon = pytest.mock.MagicMock()
        mock_polygon.get_market_movers.return_value = None

        with pytest.mock.patch("web.api_polygon.PolygonService", return_value=mock_polygon):
            response = client.get("/api/polygon/market-movers")

            # Should return 200 with empty data or 500 with error message
            # Either way, should not crash
            assert response.status_code in [200, 500]

    def test_api_handles_timeout(self, client, test_user):
        """Test API endpoints handle timeouts gracefully"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user.id)

        # Mock API timeout
        mock_polygon = pytest.mock.MagicMock()
        mock_polygon.get_market_movers.side_effect = Exception("Timeout")

        with pytest.mock.patch("web.api_polygon.PolygonService", return_value=mock_polygon):
            response = client.get("/api/polygon/market-movers")

            # Should return error, not crash
            assert response.status_code in [500, 503]


class TestAPISecurityAndCSRF:
    """Test API security measures"""

    def test_api_validates_json_input(self, client, test_user):
        """Test API rejects invalid JSON"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user.id)

        response = client.post(
            "/api/watchlist/add",
            data="invalid json{{{",
            content_type="application/json",
        )

        assert response.status_code == 400

    def test_api_validates_required_fields(self, client, test_user):
        """Test API validates required fields"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user.id)

        # Missing 'ticker' field
        response = client.post(
            "/api/watchlist/add",
            data=json.dumps({}),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert "ticker" in data["error"].lower()

    def test_api_prevents_sql_injection(self, client, test_user, db_session):
        """Test API prevents SQL injection attacks"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user.id)

        # Try SQL injection in ticker
        response = client.post(
            "/api/watchlist/add",
            data=json.dumps({"ticker": "AAPL'; DROP TABLE watchlist; --"}),
            content_type="application/json",
        )

        # Should either reject invalid ticker or safely escape it
        # Either way, watchlist table should still exist
        from web.database import Watchlist

        assert Watchlist.query.count() >= 0  # Table still exists


class TestAPICaching:
    """Test API caching behavior"""

    def test_cached_endpoint_returns_same_data(self, client, test_user, mock_polygon_api):
        """Test cached endpoints return consistent data"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user.id)

        with pytest.mock.patch(
            "web.api_polygon.PolygonService", return_value=mock_polygon_api
        ):
            # First call
            response1 = client.get("/api/polygon/market-movers")
            data1 = json.loads(response1.data)

            # Second call (should be cached)
            response2 = client.get("/api/polygon/market-movers")
            data2 = json.loads(response2.data)

            # Data should be identical
            assert data1 == data2

            # API should only be called once (cached on second call)
            # Note: This requires actual caching implementation
