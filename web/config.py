import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Security
    SECRET_KEY = os.getenv("SECRET_KEY")
    if not SECRET_KEY:
        if os.getenv("RENDER"):
            raise ValueError("SECRET_KEY environment variable must be set in production!")
        else:
            SECRET_KEY = "dev-secret-key-for-testing-only"
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    if SQLALCHEMY_DATABASE_URI:
        if SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
            SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgres://", "postgresql+psycopg://", 1)
        elif SQLALCHEMY_DATABASE_URI.startswith("postgresql://"):
            SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgresql://", "postgresql+psycopg://", 1)
    else:
        SQLALCHEMY_DATABASE_URI = "sqlite:///qunextrade.db"
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 10,
        "pool_recycle": 3600,
        "pool_pre_ping": True,
        "max_overflow": 20,
        "pool_timeout": 30,
    }

    # Security Headers & Cookies
    SESSION_COOKIE_SECURE = True
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
    REDIS_URL = os.getenv("REDIS_URL", "memory://")
    if not REDIS_URL or REDIS_URL.strip() == "":
        REDIS_URL = "memory://"
    
    CACHE_TYPE = "RedisCache" if REDIS_URL != "memory://" else "SimpleCache"
    CACHE_REDIS_URL = REDIS_URL if REDIS_URL != "memory://" else None
    CACHE_DEFAULT_TIMEOUT = 300
    CACHE_KEY_PREFIX = "qunex_"

    # App Constants
    RATE_LIMITS = {"daily": 200, "hourly": 50, "auth_per_minute": 10}
    NEWS_COLLECTION_HOURS = 24
    NEWS_ANALYSIS_LIMIT = 50
    CALENDAR_DAYS_AHEAD = 60
    AUTO_REFRESH_INTERVAL = 3600
