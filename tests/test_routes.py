"""
Tests for Main Routes

Tests public pages, authenticated pages, and redirects.
"""

import pytest
from flask import url_for


class TestPublicRoutes:
    """Test routes accessible without authentication"""
    
    def test_index_page(self, client, mock_polygon):
        """Test homepage loads successfully"""
        response = client.get("/")
        assert response.status_code == 200
        assert b"Qunex" in response.data or b"qunex" in response.data.lower()
    
    def test_about_page(self, client):
        """Test about page loads"""
        response = client.get("/about")
        assert response.status_code == 200
    
    def test_terms_page(self, client):
        """Test terms page loads"""
        response = client.get("/terms")
        assert response.status_code == 200
    
    def test_privacy_page(self, client):
        """Test privacy page loads"""
        response = client.get("/privacy")
        assert response.status_code == 200
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "healthy"
    
    def test_leaderboard_public(self, client):
        """Test leaderboard is accessible without auth"""
        response = client.get("/leaderboard")
        assert response.status_code == 200


class TestAuthRedirects:
    """Test authentication redirects"""
    
    def test_login_redirect(self, client):
        """Test /login redirects to /auth/login"""
        response = client.get("/login", follow_redirects=False)
        assert response.status_code in [301, 302]
    
    def test_register_redirect(self, client):
        """Test /register redirects to /auth/signup"""
        response = client.get("/register", follow_redirects=False)
        assert response.status_code in [301, 302]
    
    def test_logout_redirect(self, client):
        """Test /logout redirects to /auth/logout"""
        response = client.get("/logout", follow_redirects=False)
        assert response.status_code == 302


class TestProtectedRoutes:
    """Test routes requiring authentication"""
    
    def test_dashboard_requires_auth(self, client):
        """Test dashboard redirects unauthenticated users"""
        response = client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 302
        assert "/auth/login" in response.location or "/login" in response.location
    
    def test_dashboard_authenticated(self, authenticated_client, mock_polygon):
        """Test dashboard loads for authenticated users"""
        response = authenticated_client.get("/dashboard")
        assert response.status_code == 200
        assert b"Dashboard" in response.data
    
    def test_watchlist_requires_auth(self, client):
        """Test watchlist requires authentication"""
        response = client.get("/watchlist", follow_redirects=False)
        assert response.status_code == 302
    
    def test_watchlist_authenticated(self, authenticated_client):
        """Test watchlist loads for authenticated users"""
        response = authenticated_client.get("/watchlist")
        assert response.status_code == 200
    
    def test_portfolio_requires_auth(self, client):
        """Test portfolio requires authentication"""
        response = client.get("/portfolio", follow_redirects=False)
        assert response.status_code == 302
    
    def test_portfolio_authenticated(self, authenticated_client, mock_polygon):
        """Test portfolio loads for authenticated users"""
        response = authenticated_client.get("/portfolio")
        assert response.status_code == 200
    
    def test_screener_requires_auth(self, client):
        """Test screener requires authentication"""
        response = client.get("/screener", follow_redirects=False)
        assert response.status_code == 302
    
    def test_market_requires_auth(self, client):
        """Test market page requires authentication"""
        response = client.get("/market", follow_redirects=False)
        assert response.status_code == 302


class TestTradingRoutes:
    """Test trading-related routes"""
    
    def test_scalping_requires_auth(self, client):
        """Test scalping page requires auth"""
        response = client.get("/scalping", follow_redirects=False)
        assert response.status_code == 302
    
    def test_scalping_authenticated(self, authenticated_client):
        """Test scalping loads for authenticated users"""
        response = authenticated_client.get("/scalping")
        assert response.status_code == 200
    
    def test_swing_requires_auth(self, client):
        """Test swing trading page requires auth"""
        response = client.get("/swing", follow_redirects=False)
        assert response.status_code == 302
    
    def test_swing_authenticated(self, authenticated_client):
        """Test swing trading loads for authenticated users"""
        response = authenticated_client.get("/swing")
        assert response.status_code == 200
    
    def test_day_trading_requires_auth(self, client):
        """Test day trading page requires auth"""
        response = client.get("/day-trading", follow_redirects=False)
        assert response.status_code == 302
    
    def test_paper_trading_requires_auth(self, client):
        """Test paper trading requires auth"""
        response = client.get("/paper-trading", follow_redirects=False)
        assert response.status_code == 302


class TestStockRoutes:
    """Test stock-related routes"""
    
    def test_stocks_list_requires_auth(self, client):
        """Test stocks list requires auth"""
        response = client.get("/stocks", follow_redirects=False)
        assert response.status_code == 302
    
    def test_stock_detail_requires_auth(self, client):
        """Test stock detail requires auth"""
        response = client.get("/stocks/AAPL", follow_redirects=False)
        assert response.status_code == 302
    
    def test_stock_detail_authenticated(self, authenticated_client, mock_polygon):
        """Test stock detail loads for authenticated users"""
        response = authenticated_client.get("/stocks/AAPL")
        assert response.status_code == 200
    
    def test_stock_detail_uppercase(self, authenticated_client, mock_polygon):
        """Test ticker is uppercased"""
        response = authenticated_client.get("/stocks/aapl")
        assert response.status_code == 200


class TestAnalysisRoutes:
    """Test analysis and tools routes"""
    
    def test_analytics_requires_auth(self, client):
        """Test analytics requires auth"""
        response = client.get("/analytics", follow_redirects=False)
        assert response.status_code == 302
    
    def test_compare_requires_auth(self, client):
        """Test compare requires auth"""
        response = client.get("/compare", follow_redirects=False)
        assert response.status_code == 302
    
    def test_patterns_requires_auth(self, client):
        """Test patterns requires auth"""
        response = client.get("/patterns", follow_redirects=False)
        assert response.status_code == 302
    
    def test_sentiment_requires_auth(self, client):
        """Test sentiment requires auth"""
        response = client.get("/sentiment", follow_redirects=False)
        assert response.status_code == 302
    
    def test_options_requires_auth(self, client):
        """Test options requires auth"""
        response = client.get("/options", follow_redirects=False)
        assert response.status_code == 302
    
    def test_tools_requires_auth(self, client):
        """Test tools requires auth"""
        response = client.get("/tools", follow_redirects=False)
        assert response.status_code == 302


class TestContentRoutes:
    """Test content-related routes"""
    
    def test_news_requires_auth(self, client):
        """Test news requires auth"""
        response = client.get("/news", follow_redirects=False)
        assert response.status_code == 302
    
    def test_calendar_requires_auth(self, client):
        """Test calendar requires auth"""
        response = client.get("/calendar", follow_redirects=False)
        assert response.status_code == 302
    
    def test_earnings_requires_auth(self, client):
        """Test earnings requires auth"""
        response = client.get("/earnings", follow_redirects=False)
        assert response.status_code == 302
    
    def test_chat_requires_auth(self, client):
        """Test AI chat requires auth"""
        response = client.get("/chat", follow_redirects=False)
        assert response.status_code == 302
    
    def test_journal_requires_auth(self, client):
        """Test trade journal requires auth"""
        response = client.get("/journal", follow_redirects=False)
        assert response.status_code == 302

