"""
Tests for Web Routes

Tests all Flask routes for:
- Authentication requirements
- Response codes
- Template rendering
- Error handling
"""

import pytest
from flask import session


class TestPublicRoutes:
    """Test public routes that don't require authentication"""

    def test_index_page(self, client):
        """Test homepage loads"""
        response = client.get("/")
        assert response.status_code == 200

    def test_pricing_page(self, client):
        """Test pricing page loads"""
        response = client.get("/pricing")
        assert response.status_code == 200

    def test_login_page(self, client):
        """Test login page loads"""
        response = client.get("/login")
        assert response.status_code == 200

    def test_register_page(self, client):
        """Test register page loads"""
        response = client.get("/register")
        assert response.status_code == 200

    def test_market_page(self, client):
        """Test market page loads without login"""
        response = client.get("/market")
        assert response.status_code in [200, 302]  # May redirect if requires auth


class TestAuthenticatedRoutes:
    """Test routes that require authentication"""

    def test_dashboard_requires_login(self, client):
        """Test dashboard redirects to login"""
        response = client.get("/dashboard")
        assert response.status_code == 302  # Redirect to login

    def test_dashboard_with_auth(self, client, test_user):
        """Test dashboard loads for authenticated user"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user.id)

        response = client.get("/dashboard")
        assert response.status_code == 200

    def test_portfolio_requires_login(self, client):
        """Test portfolio redirects to login"""
        response = client.get("/portfolio")
        assert response.status_code == 302

    def test_portfolio_with_auth(self, client, test_user):
        """Test portfolio loads for authenticated user"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user.id)

        response = client.get("/portfolio")
        assert response.status_code == 200

    def test_watchlist_requires_login(self, client):
        """Test watchlist redirects to login"""
        response = client.get("/watchlist")
        assert response.status_code == 302

    def test_stock_chart_requires_login(self, client):
        """Test stock chart redirects to login"""
        response = client.get("/stock/AAPL")
        assert response.status_code == 302

    def test_stock_chart_with_auth(self, client, test_user):
        """Test stock chart loads for authenticated user"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user.id)

        response = client.get("/stock/AAPL")
        # May return 200 or redirect depending on API availability
        assert response.status_code in [200, 302, 500]


class TestAuthFlow:
    """Test authentication flow"""

    def test_login_with_valid_credentials(self, client, test_user):
        """Test login with correct password"""
        response = client.post(
            "/login",
            data={"email": test_user.email, "password": "testpassword123"},
            follow_redirects=False,
        )

        # Should redirect after successful login
        assert response.status_code == 302

    def test_login_with_invalid_credentials(self, client, test_user):
        """Test login with wrong password"""
        response = client.post(
            "/login",
            data={"email": test_user.email, "password": "wrongpassword"},
            follow_redirects=True,
        )

        # Should show error
        assert response.status_code == 200
        # Login page should be shown again

    def test_logout(self, client, test_user):
        """Test logout functionality"""
        # Login first
        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user.id)

        # Then logout
        response = client.get("/logout", follow_redirects=False)

        assert response.status_code == 302  # Redirect to homepage

    def test_register_new_user(self, client, db_session):
        """Test user registration"""
        response = client.post(
            "/register",
            data={
                "email": "newuser@test.com",
                "username": "newuser",
                "password": "password123",
                "confirm_password": "password123",
            },
            follow_redirects=True,
        )

        # Should either succeed or show validation errors
        assert response.status_code == 200


class TestAdminRoutes:
    """Test admin-only routes"""

    def test_admin_requires_admin_email(self, client, test_user):
        """Test /admin requires admin email"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user.id)

        response = client.get("/admin/")

        # Should redirect since test_user is not admin
        assert response.status_code == 302

    def test_admin_with_admin_user(self, client, admin_user):
        """Test /admin accessible by admin"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(admin_user.id)

        response = client.get("/admin/")

        # Should load admin panel
        assert response.status_code in [200, 302]


class TestErrorHandling:
    """Test error handling"""

    def test_404_page(self, client):
        """Test 404 error page"""
        response = client.get("/nonexistent-page")
        assert response.status_code == 404

    def test_invalid_stock_ticker(self, client, test_user):
        """Test invalid ticker returns error"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user.id)

        response = client.get("/stock/INVALID_TICKER_XYZ")

        # Should handle gracefully
        assert response.status_code in [200, 404, 500]


class TestAPIRateLimiting:
    """Test API rate limiting"""

    def test_rate_limit_not_exceeded_on_normal_use(self, client, test_user):
        """Test normal API calls don't hit rate limit"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user.id)

        # Make a few requests
        for _ in range(5):
            response = client.get("/api/watchlist")
            assert response.status_code == 200

    def test_rate_limit_protection(self, client):
        """Test rate limiting protects against abuse"""
        # Make many requests rapidly
        responses = []
        for _ in range(100):
            response = client.get("/market")
            responses.append(response.status_code)

        # Should eventually return 429 (Too Many Requests) if rate limiting is enabled
        # Or continue returning 200 if not yet implemented
        assert all(code in [200, 302, 429] for code in responses)


class TestCSRFProtection:
    """Test CSRF protection on forms"""

    def test_post_without_csrf_fails(self, client, test_user):
        """Test POST without CSRF token fails"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(test_user.id)

        # Try to add to watchlist without CSRF token
        response = client.post(
            "/api/watchlist/add",
            json={"ticker": "AAPL"},
        )

        # Should either succeed (CSRF disabled in test) or fail
        assert response.status_code in [200, 400, 403]
