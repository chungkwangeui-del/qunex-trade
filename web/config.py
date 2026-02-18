import os
from datetime import timedelta
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# Get the project root directory (parent of 'web' folder)
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_db_path = os.path.join(_project_root, "instance", "qunextrade.db")

class Config:
    # Security
    SECRET_KEY = os.getenv("SECRET_KEY")
    if not SECRET_KEY:
        if os.getenv("RENDER"):
            raise ValueError("SECRET_KEY environment variable must be set in production!")
        else:
            SECRET_KEY = "dev-secret-key-for-testing-only"

    # Database - use DATABASE_URL for production (PostgreSQL), fallback to SQLite for local
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", f"sqlite:///{_db_path}")

    # Handle Render's postgres:// prefix (SQLAlchemy requires postgresql://)
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Engine options - only use pooling for PostgreSQL, not SQLite
    if SQLALCHEMY_DATABASE_URI and ("postgresql" in SQLALCHEMY_DATABASE_URI or "mysql" in SQLALCHEMY_DATABASE_URI):
        SQLALCHEMY_ENGINE_OPTIONS = {
            "pool_size": 10,
            "pool_recycle": 3600,
            "pool_pre_ping": True,
            "max_overflow": 20,
            "pool_timeout": 30,
        }
    else:
        # SQLite does not support these pooling options in create_engine via Flask-SQLAlchemy
        SQLALCHEMY_ENGINE_OPTIONS = {
            "pool_pre_ping": True,
        }

    # Security Headers & Cookies
    SESSION_COOKIE_SECURE = os.getenv("RENDER") is not None  # Only True in production
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    WTF_CSRF_TIME_LIMIT = None

    # Mail
    MAIL_SERVER = "smtp.gmail.com"
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_USERNAME", "noreply@qunextrade.com")

    # Redis / Cache
    _raw_redis_url = os.getenv("REDIS_URL", "memory://")
    if not _raw_redis_url or _raw_redis_url.strip() == "" or _raw_redis_url == "redis://default:password@host:port":
        REDIS_URL = "memory://"
    else:
        REDIS_URL = _raw_redis_url

    CACHE_TYPE = "RedisCache" if REDIS_URL != "memory://" else "SimpleCache"
    CACHE_REDIS_URL = REDIS_URL if REDIS_URL != "memory://" else None
    CACHE_DEFAULT_TIMEOUT = 300
    CACHE_KEY_PREFIX = "qunex_"

    # Redis Cache Options (for production stability)
    if CACHE_TYPE == "RedisCache":
        CACHE_OPTIONS = {
            "socket_connect_timeout": 5,
            "socket_timeout": 5,
            "retry_on_timeout": True,
        }

    # Session Configuration (use Redis in production for better scaling)
    SESSION_TYPE = "redis" if REDIS_URL != "memory://" else "filesystem"
    SESSION_REDIS = REDIS_URL if REDIS_URL != "memory://" else None
    SESSION_KEY_PREFIX = "qunex_session:"
    SESSION_USE_SIGNER = True
    SESSION_PERMANENT = True

    # App Constants
    RATE_LIMITS = {"daily": 200, "hourly": 50, "auth_per_minute": 10}
    NEWS_COLLECTION_HOURS = 24
    NEWS_ANALYSIS_LIMIT = 50
    CALENDAR_DAYS_AHEAD = 60
    AUTO_REFRESH_INTERVAL = 3600
