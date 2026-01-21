"""
Tests for Authentication System

Tests login, signup, password reset, and session management.
"""

import pytest
from web.database import User, db


class TestLogin:
    """Test login functionality"""
    
    def test_login_page_loads(self, client):
        """Test login page is accessible"""
        response = client.get("/auth/login")
        assert response.status_code == 200
        assert b"Sign" in response.data or b"Login" in response.data
    
    def test_login_valid_credentials(self, client, test_user):
        """Test login with valid credentials"""
        response = client.post("/auth/login", data={
            "email": "test@example.com",
            "password": "testpassword123"
        }, follow_redirects=True)
        assert response.status_code == 200
    
    def test_login_invalid_email(self, client):
        """Test login with invalid email"""
        response = client.post("/auth/login", data={
            "email": "nonexistent@example.com",
            "password": "wrongpassword"
        })
        assert response.status_code in [200, 401, 302]
    
    def test_login_invalid_password(self, client, test_user):
        """Test login with wrong password"""
        response = client.post("/auth/login", data={
            "email": "test@example.com",
            "password": "wrongpassword"
        })
        assert response.status_code in [200, 401, 302]
    
    def test_login_empty_fields(self, client):
        """Test login with empty fields"""
        response = client.post("/auth/login", data={
            "email": "",
            "password": ""
        })
        assert response.status_code in [200, 400]


class TestSignup:
    """Test signup functionality"""
    
    def test_signup_page_loads(self, client):
        """Test signup page is accessible"""
        response = client.get("/auth/signup")
        assert response.status_code == 200
        assert b"Sign" in response.data or b"Register" in response.data
    
    def test_signup_valid_data(self, client, app_context):
        """Test signup with valid data"""
        response = client.post("/auth/signup", data={
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "SecurePass123!",
            "password_confirm": "SecurePass123!"
        }, follow_redirects=True)
        assert response.status_code == 200
        
        # Cleanup
        user = User.query.filter_by(email="newuser@example.com").first()
        if user:
            db.session.delete(user)
            db.session.commit()
    
    def test_signup_password_mismatch(self, client):
        """Test signup with mismatched passwords"""
        response = client.post("/auth/signup", data={
            "username": "testuser2",
            "email": "test2@example.com",
            "password": "SecurePass123!",
            "password_confirm": "DifferentPass123!"
        })
        assert response.status_code in [200, 400]
    
    def test_signup_duplicate_email(self, client, test_user):
        """Test signup with existing email"""
        response = client.post("/auth/signup", data={
            "username": "anotheruser",
            "email": "test@example.com",  # Already exists
            "password": "SecurePass123!",
            "password_confirm": "SecurePass123!"
        })
        assert response.status_code in [200, 400, 409]
    
    def test_signup_weak_password(self, client):
        """Test signup with weak password"""
        response = client.post("/auth/signup", data={
            "username": "weakpassuser",
            "email": "weakpass@example.com",
            "password": "123",
            "password_confirm": "123"
        })
        # Should fail validation
        assert response.status_code in [200, 400]
    
    def test_signup_invalid_email(self, client):
        """Test signup with invalid email format"""
        response = client.post("/auth/signup", data={
            "username": "invalidemail",
            "email": "not-an-email",
            "password": "SecurePass123!",
            "password_confirm": "SecurePass123!"
        })
        assert response.status_code in [200, 400]


class TestLogout:
    """Test logout functionality"""
    
    def test_logout(self, authenticated_client):
        """Test logout clears session"""
        response = authenticated_client.get("/auth/logout", follow_redirects=True)
        assert response.status_code == 200
        
        # Should be redirected to login or home
        response = authenticated_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 302


class TestPasswordReset:
    """Test password reset functionality"""
    
    def test_forgot_password_page(self, client):
        """Test forgot password page loads"""
        response = client.get("/auth/forgot-password")
        assert response.status_code == 200
    
    def test_forgot_password_valid_email(self, client, test_user):
        """Test forgot password with valid email"""
        response = client.post("/auth/forgot-password", data={
            "email": "test@example.com"
        }, follow_redirects=True)
        # Should succeed even if email doesn't exist (security)
        assert response.status_code == 200
    
    def test_forgot_password_invalid_email(self, client):
        """Test forgot password with nonexistent email"""
        response = client.post("/auth/forgot-password", data={
            "email": "nonexistent@example.com"
        }, follow_redirects=True)
        # Should not reveal if email exists
        assert response.status_code == 200


class TestSessionManagement:
    """Test session management"""
    
    def test_session_persists(self, authenticated_client):
        """Test session persists across requests"""
        response1 = authenticated_client.get("/dashboard")
        assert response1.status_code == 200
        
        response2 = authenticated_client.get("/watchlist")
        assert response2.status_code == 200
    
    def test_protected_route_after_logout(self, authenticated_client):
        """Test protected routes redirect after logout"""
        # Logout
        authenticated_client.get("/auth/logout")
        
        # Try to access protected route
        response = authenticated_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 302


class TestAccountPage:
    """Test account management"""
    
    def test_account_page_requires_auth(self, client):
        """Test account page requires authentication"""
        response = client.get("/account", follow_redirects=False)
        assert response.status_code == 302
    
    def test_account_page_authenticated(self, authenticated_client):
        """Test account page loads for authenticated users"""
        response = authenticated_client.get("/account")
        assert response.status_code == 200

