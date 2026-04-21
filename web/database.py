"""
Database models for user authentication and subscriptions
"""

import json
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
from typing import Optional

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """User model for authentication"""

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(200), nullable=True)  # Nullable for OAuth users
    # Fix deprecated datetime.utcnow() - use timezone-aware datetime
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )

    # OAuth fields
    google_id = db.Column(db.String(200), unique=True, nullable=True, index=True)
    oauth_provider = db.Column(
        db.String(50), nullable=True, index=True
    )  # 'google', 'apple', etc
    profile_picture = db.Column(db.String(500), nullable=True)

    # Email verification
    email_verified = db.Column(db.Boolean, default=False, index=True)
    verification_code = db.Column(db.String(6), nullable=True)
    verification_code_expiry = db.Column(db.DateTime, nullable=True)

    # Password reset
    reset_token = db.Column(db.String(100), nullable=True, index=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)

    # Subscription info
    subscription_tier = db.Column(
        db.String(20), default="free", index=True
    )  # free, pro, premium, developer
    subscription_status = db.Column(
        db.String(20), default="inactive", index=True
    )  # active, inactive, cancelled
    subscription_start = db.Column(db.DateTime, nullable=True)
    subscription_end = db.Column(db.DateTime, nullable=True, index=True)
    stripe_customer_id = db.Column(db.String(100), nullable=True, index=True)
    stripe_subscription_id = db.Column(db.String(100), nullable=True, index=True)

    def set_password(self, password):
        """Hash and set password"""
        if password:
            self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check if password is correct"""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def is_pro(self):
        """Check if user has Pro subscription"""
        return (
            self.subscription_tier in ["pro", "premium", "developer"]
            and self.subscription_status == "active"
        )

    def is_premium(self):
        """Check if user has Premium subscription"""
        return (
            self.subscription_tier == "premium" and self.subscription_status == "active"
        )

    def is_developer(self):
        """Check if user is Developer (site creator)"""
        return (
            self.subscription_tier == "developer"
            and self.subscription_status == "active"
        )

    def __repr__(self):
        return f"<User {self.username}>"


class Watchlist(db.Model):
    """User watchlist for tracking favorite stocks"""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False, index=True
    )
    ticker = db.Column(db.String(10), nullable=False, index=True)
    company_name = db.Column(db.String(200), nullable=True)
    added_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )
    notes = db.Column(db.Text, nullable=True)  # User's personal notes about the stock

    # Price alerts (optional)
    alert_price_above = db.Column(
        db.Float, nullable=True
    )  # Alert when price goes above this
    alert_price_below = db.Column(
        db.Float, nullable=True
    )  # Alert when price goes below this

    user = db.relationship(
        "User", backref=db.backref("watchlist", lazy=True, cascade="all, delete-orphan")
    )

    # Unique constraint: one ticker per user
    __table_args__ = (
        db.UniqueConstraint("user_id", "ticker", name="unique_user_ticker"),
    )

    def __repr__(self):
        return f"<Watchlist {self.user_id} - {self.ticker}>"


class NewsArticle(db.Model):
    """Cached news articles with AI analysis"""

    __tablename__ = "news_articles"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    url = db.Column(db.String(1000), unique=True, nullable=False, index=True)
    source = db.Column(db.String(100), nullable=True, index=True)
    published_at = db.Column(db.DateTime, nullable=False, index=True)

    # AI Analysis fields
    ai_rating = db.Column(db.Integer, nullable=True, index=True)  # 1-5 stars
    ai_analysis = db.Column(db.Text, nullable=True)  # Claude's analysis
    sentiment = db.Column(
        db.String(20), nullable=True, index=True
    )  # positive, negative, neutral

    # Metadata
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self):
        return f"<NewsArticle {self.id} - {self.title[:50]}>"

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "url": self.url,
            "source": self.source,
            "published": self.published_at.isoformat() if self.published_at else None,
            "ai_rating": self.ai_rating,
            "ai_analysis": self.ai_analysis,
            "sentiment": self.sentiment,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class EconomicEvent(db.Model):
    """Economic calendar events"""

    __tablename__ = "economic_events"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    date = db.Column(db.DateTime, nullable=False, index=True)
    time = db.Column(db.String(20), nullable=True)  # e.g., "8:30 AM EST"
    country = db.Column(db.String(50), nullable=True, index=True)
    importance = db.Column(
        db.String(20), nullable=True, index=True
    )  # low, medium, high

    # Impact fields
    actual = db.Column(db.String(50), nullable=True)
    forecast = db.Column(db.String(50), nullable=True)
    previous = db.Column(db.String(50), nullable=True)

    # Metadata
    source = db.Column(db.String(100), nullable=True)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Unique constraint to avoid duplicates
    __table_args__ = (db.UniqueConstraint("title", "date", name="unique_event_date"),)

    def __repr__(self):
        return f"<EconomicEvent {self.title} on {self.date}>"

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        # Format date as YYYY-MM-DD for calendar display
        date_str = self.date.strftime("%Y-%m-%d") if self.date else None
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "date": date_str,
            "time": self.time,
            "country": self.country,
            "currency": self.country or "USD",  # Alias for calendar template
            "importance": self.importance,
            "impact": self.importance or "medium",  # Alias for calendar template
            "actual": self.actual,
            "forecast": self.forecast,
            "previous": self.previous,
            "source": self.source,
        }


class AIScore(db.Model):
    """Pre-computed AI scores for stocks with SHAP explainability and multi-timeframe support"""

    __tablename__ = "ai_scores"

    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(10), unique=True, nullable=False, index=True)

    # Medium-term scores (20-day, primary/default)
    score = db.Column(db.Integer, nullable=False, index=True)  # 0-100
    rating = db.Column(
        db.String(20), nullable=False
    )  # Strong Buy/Buy/Hold/Sell/Strong Sell

    # Short-term scores (5-day) - for day/swing traders
    short_term_score = db.Column(db.Integer, nullable=True, index=True)  # 0-100
    short_term_rating = db.Column(db.String(20), nullable=True)

    # Long-term scores (60-day) - for long-term investors
    long_term_score = db.Column(db.Integer, nullable=True, index=True)  # 0-100
    long_term_rating = db.Column(db.String(20), nullable=True)

    features_json = db.Column(db.Text, nullable=True)  # JSON string of features
    explanation_json = db.Column(
        db.Text, nullable=True
    )  # SHAP values (feature contributions)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        index=True,
    )

    def to_dict(self):
        """Convert to dictionary for JSON serialization with all timeframes"""
        return {
            "ticker": self.ticker,
            # Medium-term (default/primary)
            "score": self.score,
            "rating": self.rating,
            # Short-term (5-day)
            "short_term_score": self.short_term_score,
            "short_term_rating": self.short_term_rating,
            # Long-term (60-day)
            "long_term_score": self.long_term_score,
            "long_term_rating": self.long_term_rating,
            # Metadata
            "features": json.loads(self.features_json) if self.features_json else {},
            "explanation": (
                json.loads(self.explanation_json) if self.explanation_json else {}
            ),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Announcement(db.Model):
    """Site-wide announcement banner managed by admin"""

    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(500), nullable=False)
    link_text = db.Column(db.String(100), nullable=True)  # Optional link text
    link_url = db.Column(db.String(500), nullable=True)  # Optional link URL
    banner_type = db.Column(
        db.String(20), default="info"
    )  # info, warning, success, error
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

    def __repr__(self):
        return f"<Announcement {self.id}: {self.message[:30]}...>"

    def to_dict(self):
        return {
            "id": self.id,
            "message": self.message,
            "link_text": self.link_text,
            "link_url": self.link_url,
            "banner_type": self.banner_type,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

