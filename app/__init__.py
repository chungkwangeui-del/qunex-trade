import os
import logging
from datetime import timedelta
from flask import Flask
from flask_login import LoginManager
from flask_mail import Mail
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from flask_caching import Cache
from dotenv import load_dotenv
from app.models import db, User

# Load environment variables
load_dotenv()

# Initialize extensions
mail = Mail()
csrf = CSRFProtect()
cache = Cache()
login_manager = LoginManager()
limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")

def create_app(config_class=None):
    app = Flask(__name__)

    # Configuration
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key-for-testing-only")
    
    # Database
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
        elif database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    else:
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///qunextrade.db"
    
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # Security
    app.config["SESSION_COOKIE_SECURE"] = True
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)
    
    # Email
    app.config["MAIL_SERVER"] = "smtp.gmail.com"
    app.config["MAIL_PORT"] = 587
    app.config["MAIL_USE_TLS"] = True
    app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
    app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")
    app.config["MAIL_DEFAULT_SENDER"] = os.getenv("MAIL_USERNAME", "noreply@qunextrade.com")

    # Caching
    redis_url = os.getenv("REDIS_URL", "memory://")
    if not redis_url or redis_url.strip() == "":
        redis_url = "memory://"
        
    cache_config = {
        "CACHE_TYPE": "RedisCache" if redis_url != "memory://" else "SimpleCache",
        "CACHE_DEFAULT_TIMEOUT": 300,
    }
    if redis_url != "memory://":
        cache_config["CACHE_REDIS_URL"] = redis_url
        
    app.config.from_mapping(cache_config)

    # Initialize Extensions
    db.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)
    cache.init_app(app)
    login_manager.init_app(app)
    limiter.init_app(app)

    login_manager.login_view = "auth.login"

    # Register Blueprints
    from app.routes import main_bp
    app.register_blueprint(main_bp)
    
    # TODO: Register Auth and other blueprints after refactoring them
    # from app.auth import auth_bp
    # app.register_blueprint(auth_bp)

    # Create tables
    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            logging.warning(f"DB Init warning: {e}")

    return app

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
