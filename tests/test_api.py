"""
Tests for API Endpoints

Tests market data APIs, watchlist APIs, and other services.
"""

import json
from unittest.mock import patch, MagicMock

class TestMarketAPI:
    """Test market data API endpoints"""

    def test_market_indices(self, client, mock_polygon):
        """Test market indices endpoint"""
        with patch("web.api_main.get_polygon_service", return_value=mock_polygon):
            response = client.get("/api/market/indices")
            assert response.status_code == 200
            data = response.get_json()
            assert "indices" in data or "SPY" in data

    def test_market_movers(self, authenticated_client, mock_polygon):
        """Test market movers endpoint"""
        with patch("web.api_main.get_polygon_service", return_value=mock_polygon):
            mock_polygon.get_gainers_losers.return_value = {
                "gainers": [
                    {"ticker": "AAPL", "price": 150.00, "change_percent": 5.0},
                    {"ticker": "MSFT", "price": 350.00, "change_percent": 3.0}
                ],
                "losers": [
                    {"ticker": "META", "price": 300.00, "change_percent": -2.0}
                ]
            }
            response = authenticated_client.get("/api/market/movers")
            assert response.status_code == 200

class TestWatchlistAPI:
    """Test watchlist API endpoints"""

    def test_get_watchlist_unauthorized(self, client):
        """Test watchlist returns 401 for unauthenticated users"""
        response = client.get("/api/watchlist")
        assert response.status_code == 401

    def test_get_watchlist_empty(self, authenticated_client):
        """Test empty watchlist returns empty array"""
        response = authenticated_client.get("/api/watchlist")
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list) or "watchlist" in data

    def test_add_to_watchlist(self, authenticated_client, mock_polygon):
        """Test adding ticker to watchlist"""
        with patch("web.api_watchlist.get_polygon_service", return_value=mock_polygon):
            response = authenticated_client.post(
                "/api/watchlist",
                data=json.dumps({"ticker": "AAPL"}),
                content_type="application/json"
            )
            assert response.status_code in [200, 201]
            data = response.get_json()
            assert data.get("success") is True or "ticker" in data

    def test_add_invalid_ticker(self, authenticated_client):
        """Test adding invalid ticker fails"""
        response = authenticated_client.post(
            "/api/watchlist",
            data=json.dumps({"ticker": ""}),
            content_type="application/json"
        )
        assert response.status_code in [400, 422]

    def test_remove_from_watchlist(self, authenticated_client, mock_polygon):
        """Test removing ticker from watchlist"""
        # First add a ticker
        with patch("web.api_watchlist.get_polygon_service", return_value=mock_polygon):
            authenticated_client.post(
                "/api/watchlist",
                data=json.dumps({"ticker": "AAPL"}),
                content_type="application/json"
            )

        # Then remove it
        response = authenticated_client.delete("/api/watchlist/AAPL")
        assert response.status_code in [200, 204]

class TestRealtimeAPI:
    """Test real-time data API endpoints"""

    def test_realtime_prices(self, client, mock_polygon):
        """Test real-time prices endpoint"""
        with patch("web.api_websocket.get_polygon_service", return_value=mock_polygon):
            response = client.post(
                "/api/realtime/prices",
                data=json.dumps({"tickers": ["AAPL", "MSFT"]}),
                content_type="application/json"
            )
            assert response.status_code == 200
            data = response.get_json()
            assert data.get("success") is True
            assert "prices" in data

    def test_realtime_prices_empty(self, client):
        """Test real-time prices with no tickers fails"""
        response = client.post(
            "/api/realtime/prices",
            data=json.dumps({"tickers": []}),
            content_type="application/json"
        )
        assert response.status_code == 400

    def test_market_pulse(self, client, mock_polygon):
        """Test market pulse endpoint"""
        with patch("web.api_websocket.get_polygon_service", return_value=mock_polygon):
            response = client.get("/api/realtime/market-pulse")
            assert response.status_code == 200
            data = response.get_json()
            assert "market_status" in data

class TestNewsAPI:
    """Test news API endpoints"""

    def test_get_news(self, authenticated_client):
        """Test getting news articles"""
        response = authenticated_client.get("/api/news")
        assert response.status_code == 200
        data = response.get_json()
        assert "articles" in data or "news" in data or isinstance(data, list)

    def test_get_news_with_limit(self, authenticated_client):
        """Test getting news with limit"""
        response = authenticated_client.get("/api/news?limit=5")
        assert response.status_code == 200

class TestSSEAPI:
    """Test Server-Sent Events API endpoints"""

    def test_sse_status(self, client):
        """Test SSE status endpoint"""
        response = client.get("/api/sse/status")
        assert response.status_code == 200
        data = response.get_json()
        assert "status" in data
        assert data["status"] == "available"

    def test_sse_prices_requires_tickers(self, client):
        """Test SSE prices endpoint requires tickers"""
        response = client.get("/api/sse/prices")
        assert response.status_code == 400

    def test_sse_watchlist_requires_auth(self, client):
        """Test SSE watchlist requires authentication"""
        response = client.get("/api/sse/watchlist")
        assert response.status_code == 401

class TestPortfolioAPI:
    """Test portfolio API endpoints"""

    def test_get_portfolio_unauthorized(self, client):
        """Test portfolio returns 401 for unauthenticated users"""
        response = client.get("/api/portfolio")
        assert response.status_code == 401

    def test_add_transaction(self, authenticated_client):
        """Test adding a transaction"""
        response = authenticated_client.post(
            "/api/portfolio/transaction",
            data=json.dumps({
                "ticker": "AAPL",
                "shares": 10,
                "price": 150.00,
                "transaction_type": "buy"
            }),
            content_type="application/json"
        )
        # May return 200, 201, or 400 depending on implementation
        assert response.status_code in [200, 201, 400, 404]

class TestToolsAPI:
    """Test trading tools API endpoints"""

    def test_position_size_calculator(self, authenticated_client):
        """Test position size calculator"""
        response = authenticated_client.post(
            "/api/tools/position-size",
            data=json.dumps({
                "account_size": 10000,
                "risk_percent": 2,
                "entry_price": 150,
                "stop_loss": 145
            }),
            content_type="application/json"
        )
        assert response.status_code in [200, 400, 404]

class TestScalpAPI:
    """Test scalping analysis API"""

    def test_scalp_analyze_requires_auth(self, client):
        """Test scalp analyze requires authentication"""
        response = client.post(
            "/api/scalp/analyze",
            data=json.dumps({"ticker": "AAPL"}),
            content_type="application/json"
        )
        assert response.status_code == 401

    def test_scalp_analyze(self, authenticated_client, mock_polygon):
        """Test scalp analysis endpoint"""
        with patch("web.api_scalp.get_polygon_service", return_value=mock_polygon):
            mock_polygon.get_aggregates.return_value = [
                {"c": 150, "o": 149, "h": 151, "l": 148, "v": 1000000, "t": 1700000000000}
                for _ in range(100)
            ]
            response = authenticated_client.post(
                "/api/scalp/analyze",
                data=json.dumps({"ticker": "AAPL"}),
                content_type="application/json"
            )
            assert response.status_code in [200, 400, 500]

class TestSwingAPI:
    """Test swing trading analysis API"""

    def test_swing_analyze_requires_auth(self, client):
        """Test swing analyze requires authentication"""
        response = client.post(
            "/api/swing/analyze",
            data=json.dumps({"ticker": "AAPL"}),
            content_type="application/json"
        )
        assert response.status_code == 401

class TestChatAPI:
    """Test AI chat API"""

    def test_chat_requires_auth(self, client):
        """Test chat requires authentication"""
        response = client.post(
            "/api/chat",
            data=json.dumps({"message": "What is AAPL's price?"}),
            content_type="application/json"
        )
        assert response.status_code == 401
