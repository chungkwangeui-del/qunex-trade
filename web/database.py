"""
Database models for user authentication and subscriptions
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """User model for authentication"""
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(200), nullable=True)  # Nullable for OAuth users
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # OAuth fields
    google_id = db.Column(db.String(200), unique=True, nullable=True, index=True)
    oauth_provider = db.Column(db.String(50), nullable=True, index=True)  # 'google', 'apple', etc
    profile_picture = db.Column(db.String(500), nullable=True)

    # Email verification
    email_verified = db.Column(db.Boolean, default=False, index=True)
    verification_code = db.Column(db.String(6), nullable=True)
    verification_code_expiry = db.Column(db.DateTime, nullable=True)

    # Password reset
    reset_token = db.Column(db.String(100), nullable=True, index=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)

    # Subscription info
    subscription_tier = db.Column(db.String(20), default='free', index=True)  # free, pro, premium, developer
    subscription_status = db.Column(db.String(20), default='inactive', index=True)  # active, inactive, cancelled
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
        return self.subscription_tier in ['pro', 'premium', 'developer'] and self.subscription_status == 'active'

    def is_premium(self):
        """Check if user has Premium subscription"""
        return self.subscription_tier == 'premium' and self.subscription_status == 'active'

    def is_developer(self):
        """Check if user is Developer (site creator)"""
        return self.subscription_tier == 'developer' and self.subscription_status == 'active'

    def __repr__(self):
        return f'<User {self.username}>'


class Payment(db.Model):
    """Payment history model"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default='USD')
    status = db.Column(db.String(20), nullable=False, index=True)  # succeeded, failed, pending
    stripe_payment_id = db.Column(db.String(100), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user = db.relationship('User', backref=db.backref('payments', lazy=True))

    def __repr__(self):
        return f'<Payment {self.id} - ${self.amount}>'


class Watchlist(db.Model):
    """User watchlist for tracking favorite stocks"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    ticker = db.Column(db.String(10), nullable=False, index=True)
    company_name = db.Column(db.String(200), nullable=True)
    added_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    notes = db.Column(db.Text, nullable=True)  # User's personal notes about the stock

    # Price alerts (optional)
    alert_price_above = db.Column(db.Float, nullable=True)  # Alert when price goes above this
    alert_price_below = db.Column(db.Float, nullable=True)  # Alert when price goes below this

    user = db.relationship('User', backref=db.backref('watchlist', lazy=True, cascade='all, delete-orphan'))

    # Unique constraint: one ticker per user
    __table_args__ = (db.UniqueConstraint('user_id', 'ticker', name='unique_user_ticker'),)

    def __repr__(self):
        return f'<Watchlist {self.user_id} - {self.ticker}>'


class SavedScreener(db.Model):
    """Saved screener criteria for quick access"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)  # User-defined name
    description = db.Column(db.Text, nullable=True)

    # Screening criteria stored as JSON-like fields
    min_price = db.Column(db.Float, nullable=True)
    max_price = db.Column(db.Float, nullable=True)
    min_volume = db.Column(db.Integer, nullable=True)
    min_market_cap = db.Column(db.Float, nullable=True)
    max_market_cap = db.Column(db.Float, nullable=True)
    min_change_percent = db.Column(db.Float, nullable=True)
    max_change_percent = db.Column(db.Float, nullable=True)

    # Technical indicators
    rsi_min = db.Column(db.Float, nullable=True)
    rsi_max = db.Column(db.Float, nullable=True)
    has_macd_signal = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    last_used = db.Column(db.DateTime, nullable=True)

    user = db.relationship('User', backref=db.backref('saved_screeners', lazy=True, cascade='all, delete-orphan'))

    def __repr__(self):
        return f'<SavedScreener {self.name} by User {self.user_id}>'
