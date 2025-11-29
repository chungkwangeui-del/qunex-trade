"""
Flask Web Application - Qunex Trade
Professional trading tools with real-time market data
"""

from flask import Flask, Response
from werkzeug.middleware.proxy_fix import ProxyFix
import os
import sys
import logging
from web.config import Config
from web.database import db, User
from web.extensions import mail, csrf, cache, limiter, login_manager

# Add parent directory to path for imports (src/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure structured logging
try:
    from web.logging_config import configure_structured_logging, get_logger
    configure_structured_logging()
    logger = get_logger(__name__)
except ImportError:
    # Fallback to standard logging
    logger = logging.getLogger(__name__)

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Trust proxy headers (required for Render and other reverse proxies)
    # This fixes HTTPS detection and secure cookie issues
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # Initialize extensions
    db.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)
    cache.init_app(app)
    limiter.init_app(app)
    login_manager.init_app(app)
    
    login_manager.login_view = "auth.login"

    @login_manager.user_loader
    def load_user(user_id: str):
        return db.session.get(User, int(user_id))

    # Exempt email verification endpoints from CSRF protection
    csrf.exempt("web.auth.send_verification_code")
    csrf.exempt("web.auth.verify_code")

    # Exempt announcement management endpoints from CSRF protection
    csrf.exempt("web.auth.get_announcements")
    csrf.exempt("web.auth.create_announcement")
    csrf.exempt("web.auth.delete_announcement")
    csrf.exempt("web.auth.toggle_announcement")
    csrf.exempt("web.auth.get_active_announcement")

    # Register Blueprints
    # Register Blueprints
    from web.auth import auth, oauth
    from web.api_polygon import api_polygon
    from web.api_watchlist import api_watchlist
    from web.api_portfolio import api_portfolio
    from web.main import main as main_blueprint
    from web.api_main import api_main

    oauth.init_app(app)

    app.register_blueprint(auth, url_prefix="/auth")
    app.register_blueprint(api_polygon)
    app.register_blueprint(api_watchlist)
    app.register_blueprint(api_portfolio)
    app.register_blueprint(main_blueprint)
    app.register_blueprint(api_main)

    # Apply rate limiting to auth routes
    auth_routes = [
        ("auth.login", f"{app.config['RATE_LIMITS']['auth_per_minute']} per minute"),
        ("auth.signup", "5 per minute"),
        ("auth.forgot_password", "3 per minute"),
        ("auth.reset_password", "5 per minute"),
        ("auth.send_verification_code", "3 per minute"),
        ("auth.verify_code", f"{app.config['RATE_LIMITS']['auth_per_minute']} per minute"),
        ("auth.google_login", f"{app.config['RATE_LIMITS']['auth_per_minute']} per minute"),
        ("auth.google_callback", f"{app.config['RATE_LIMITS']['auth_per_minute']} per minute"),
    ]

    for route_name, rate_limit in auth_routes:
        # Note: We need to check if the view function exists after blueprint registration
        # The endpoint names might be prefixed with the blueprint name
        if route_name in app.view_functions:
            limiter.limit(rate_limit)(app.view_functions[route_name])

    # Initialize Flask-Admin
    try:
        from web.admin_views import init_admin
        init_admin(app)
    except ImportError as e:
        logger.warning(f"Failed to import admin_views: {e}. Admin interface will not be available.")

    # Security headers middleware
    @app.after_request
    def set_security_headers(response: Response) -> Response:
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' 'unsafe-inline' https://accounts.google.com https://cdn.jsdelivr.net https://fonts.googleapis.com https://unpkg.com https://s3.tradingview.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; img-src 'self' data: https:; font-src 'self' data: https://fonts.gstatic.com; connect-src 'self' https://accounts.google.com; frame-src 'self' https://accounts.google.com https://www.tradingview.com https://s.tradingview.com;"
        )
        return response

    # Create tables
    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            logger.warning(f"Failed to create database tables: {e}")

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
