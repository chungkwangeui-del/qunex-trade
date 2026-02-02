"""
Database models for user authentication and subscriptions
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
from datetime import timezone
from typing import Optional

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """User model for authentication"""

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(200), nullable=True)  # Nullable for OAuth users
    # Fix deprecated datetime.utcnow() - use timezone-aware datetime
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)

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
        return self.subscription_tier == "premium" and self.subscription_status == "active"

    def is_developer(self):
        """Check if user is Developer (site creator)"""
        return self.subscription_tier == "developer" and self.subscription_status == "active"

    def __repr__(self):
        return f"<User {self.username}>"

class Payment(db.Model):
    """Payment history model"""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default="USD")
    status = db.Column(db.String(20), nullable=False, index=True)  # succeeded, failed, pending
    stripe_payment_id = db.Column(db.String(100), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    user = db.relationship("User", backref=db.backref("payments", lazy=True))

    def __repr__(self):
        return f"<Payment {self.id} - ${self.amount}>"

class Watchlist(db.Model):
    """User watchlist for tracking favorite stocks"""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    ticker = db.Column(db.String(10), nullable=False, index=True)
    company_name = db.Column(db.String(200), nullable=True)
    added_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    notes = db.Column(db.Text, nullable=True)  # User's personal notes about the stock

    # Price alerts (optional)
    alert_price_above = db.Column(db.Float, nullable=True)  # Alert when price goes above this
    alert_price_below = db.Column(db.Float, nullable=True)  # Alert when price goes below this

    user = db.relationship(
        "User", backref=db.backref("watchlist", lazy=True, cascade="all, delete-orphan")
    )

    # Unique constraint: one ticker per user
    __table_args__ = (db.UniqueConstraint("user_id", "ticker", name="unique_user_ticker"),)

    def __repr__(self):
        return f"<Watchlist {self.user_id} - {self.ticker}>"

class SavedScreener(db.Model):
    """Saved screener criteria for quick access"""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
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

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    last_used = db.Column(db.DateTime, nullable=True)

    user = db.relationship(
        "User", backref=db.backref("saved_screeners", lazy=True, cascade="all, delete-orphan")
    )

    def __repr__(self):
        return f"<SavedScreener {self.name} by User {self.user_id}>"

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
    sentiment = db.Column(db.String(20), nullable=True, index=True)  # positive, negative, neutral

    # Metadata
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
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
    importance = db.Column(db.String(20), nullable=True, index=True)  # low, medium, high

    # Impact fields
    actual = db.Column(db.String(50), nullable=True)
    forecast = db.Column(db.String(50), nullable=True)
    previous = db.Column(db.String(50), nullable=True)

    # Metadata
    source = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
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
    rating = db.Column(db.String(20), nullable=False)  # Strong Buy/Buy/Hold/Sell/Strong Sell

    # Short-term scores (5-day) - for day/swing traders
    short_term_score = db.Column(db.Integer, nullable=True, index=True)  # 0-100
    short_term_rating = db.Column(db.String(20), nullable=True)

    # Long-term scores (60-day) - for long-term investors
    long_term_score = db.Column(db.Integer, nullable=True, index=True)  # 0-100
    long_term_rating = db.Column(db.String(20), nullable=True)

    features_json = db.Column(db.Text, nullable=True)  # JSON string of features
    explanation_json = db.Column(db.Text, nullable=True)  # SHAP values (feature contributions)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        index=True,
    )

    def to_dict(self):
        """Convert to dictionary for JSON serialization with all timeframes"""
        import json

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
            "explanation": json.loads(self.explanation_json) if self.explanation_json else {},
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class Transaction(db.Model):
    """
    User portfolio transactions (buy/sell).

    Tracks all stock purchases and sales for portfolio management.
    Allows calculating current holdings and profit/loss.
    """

    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    ticker = db.Column(db.String(10), nullable=False, index=True)
    shares = db.Column(
        db.Numeric(precision=10, scale=4), nullable=False
    )  # Supports fractional shares
    price = db.Column(db.Numeric(precision=10, scale=2), nullable=False)  # Price per share
    transaction_type = db.Column(db.String(10), nullable=False, index=True)  # 'buy' or 'sell'
    transaction_date = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )
    notes = db.Column(db.Text, nullable=True)  # Optional user notes

    # Relationship
    user = db.relationship("User", backref=db.backref("transactions", lazy=True))

    def __repr__(self):
        return f"<Transaction {self.transaction_type.upper()} {self.shares} {self.ticker} @ ${self.price}>"

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "ticker": self.ticker,
            "shares": float(self.shares),
            "price": float(self.price),
            "transaction_type": self.transaction_type,
            "transaction_date": (
                self.transaction_date.isoformat() if self.transaction_date else None
            ),
            "total_cost": float(self.shares * self.price),
            "notes": self.notes,
        }

class BacktestJob(db.Model):
    """
    Backtest job for testing AI trading strategies.

    Users can submit backtest requests which are processed asynchronously
    by a cron job. Results are stored in result_json.
    """

    __tablename__ = "backtest_jobs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    status = db.Column(
        db.String(20), default="pending", index=True
    )  # pending, running, completed, failed
    ticker = db.Column(db.String(10), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    initial_capital = db.Column(db.Numeric(precision=12, scale=2), default=10000)
    result_json = db.Column(db.Text, nullable=True)  # Backtest results as JSON
    error_message = db.Column(db.Text, nullable=True)  # Error message if failed
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    completed_at = db.Column(db.DateTime, nullable=True)

    # Relationship
    user = db.relationship("User", backref=db.backref("backtest_jobs", lazy=True))

    def __repr__(self):
        return f"<BacktestJob {self.id} {self.ticker} {self.status}>"

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        import json

        return {
            "id": self.id,
            "user_id": self.user_id,
            "status": self.status,
            "ticker": self.ticker,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "initial_capital": float(self.initial_capital) if self.initial_capital else 10000,
            "result": json.loads(self.result_json) if self.result_json else None,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

class PriceAlert(db.Model):
    """
    Price alerts for watchlist stocks.

    Users can set alerts to be notified when a stock price crosses a threshold.
    Checked every 5 minutes by cron_check_alerts.py cron job.
    """

    __tablename__ = "price_alerts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    ticker = db.Column(db.String(10), nullable=False, index=True)
    condition = db.Column(db.String(10), nullable=False)  # 'above' or 'below'
    threshold = db.Column(db.Numeric(precision=10, scale=2), nullable=False)  # Alert price
    is_triggered = db.Column(db.Boolean, default=False, index=True)
    triggered_at = db.Column(db.DateTime, nullable=True)
    triggered_price = db.Column(db.Numeric(precision=10, scale=2), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    # Relationship
    user = db.relationship("User", backref=db.backref("price_alerts", lazy=True))

    def __repr__(self):
        return f"<PriceAlert {self.ticker} {self.condition} ${self.threshold}>"

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "ticker": self.ticker,
            "condition": self.condition,
            "threshold": float(self.threshold),
            "is_triggered": self.is_triggered,
            "triggered_at": self.triggered_at.isoformat() if self.triggered_at else None,
            "triggered_price": float(self.triggered_price) if self.triggered_price else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

class InsiderTrade(db.Model):
    """
    Insider trading transactions.

    Tracks insider buy/sell activity for stocks in watchlists.
    Updated daily by cron_refresh_insider.py cron job.
    """

    __tablename__ = "insider_trades"

    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(10), nullable=False, index=True)
    insider_name = db.Column(db.String(200), nullable=False)
    position = db.Column(db.String(100), nullable=True)  # CEO, CFO, Director, etc.
    transaction_type = db.Column(db.String(10), nullable=False, index=True)  # 'buy' or 'sell'
    shares = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Numeric(precision=10, scale=2), nullable=True)
    transaction_date = db.Column(db.Date, nullable=False, index=True)
    filing_date = db.Column(db.Date, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    # Unique constraint to avoid duplicates
    __table_args__ = (
        db.UniqueConstraint("ticker", "filing_date", "insider_name", name="unique_insider_trade"),
    )

    def __repr__(self):
        return f"<InsiderTrade {self.ticker} {self.insider_name} {self.transaction_type}>"

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "ticker": self.ticker,
            "insider_name": self.insider_name,
            "position": self.position,
            "transaction_type": self.transaction_type,
            "shares": self.shares,
            "price": float(self.price) if self.price else None,
            "transaction_date": (
                self.transaction_date.isoformat() if self.transaction_date else None
            ),
            "filing_date": self.filing_date.isoformat() if self.filing_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

class Signal(db.Model):
    """
    Trading signals generated by the system or admin.
    """

    __tablename__ = "signals"

    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(10), nullable=False, index=True)
    signal_type = db.Column(db.String(10), nullable=False)  # 'buy' or 'sell'
    status = db.Column(
        db.String(20), default="pending", index=True
    )  # pending, active, success, partial, failed

    # Price levels
    entry_price = db.Column(db.Float, nullable=False)
    target_price = db.Column(db.Float, nullable=True)
    stop_loss = db.Column(db.Float, nullable=True)

    # Performance tracking
    exit_price = db.Column(db.Float, nullable=True)
    actual_return = db.Column(db.Float, nullable=True)  # Percentage return

    # Timing
    signal_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    closed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Signal {self.ticker} {self.signal_type} {self.status}>"

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "ticker": self.ticker,
            "signal_type": self.signal_type,
            "status": self.status,
            "entry_price": self.entry_price,
            "target_price": self.target_price,
            "stop_loss": self.stop_loss,
            "exit_price": self.exit_price,
            "actual_return": self.actual_return,
            "signal_date": self.signal_date.isoformat() if self.signal_date else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

class Announcement(db.Model):
    """Site-wide announcement banner managed by admin"""

    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(500), nullable=False)
    link_text = db.Column(db.String(100), nullable=True)  # Optional link text
    link_url = db.Column(db.String(500), nullable=True)   # Optional link URL
    banner_type = db.Column(db.String(20), default="info")  # info, warning, success, error
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
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

class PaperAccount(db.Model):
    """
    Paper trading account for practice trading with virtual money.
    Each user has one paper account with a starting balance.
    """

    __tablename__ = "paper_accounts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, unique=True, index=True)
    balance = db.Column(db.Numeric(precision=12, scale=2), default=100000)  # Starting $100k
    initial_balance = db.Column(db.Numeric(precision=12, scale=2), default=100000)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_reset = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", backref=db.backref("paper_account", uselist=False))

    def __repr__(self):
        return f"<PaperAccount {self.user_id} ${self.balance}>"

    def to_dict(self):
        return {
            "id": self.id,
            "balance": float(self.balance),
            "initial_balance": float(self.initial_balance),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_reset": self.last_reset.isoformat() if self.last_reset else None,
        }

class PaperTrade(db.Model):
    """
    Paper trade records - buy/sell with virtual money.
    """

    __tablename__ = "paper_trades"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    ticker = db.Column(db.String(10), nullable=False, index=True)
    shares = db.Column(db.Numeric(precision=10, scale=4), nullable=False)
    price = db.Column(db.Numeric(precision=10, scale=2), nullable=False)
    trade_type = db.Column(db.String(10), nullable=False, index=True)  # 'buy' or 'sell'
    trade_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    notes = db.Column(db.Text, nullable=True)

    # For closed positions - track P&L
    is_closed = db.Column(db.Boolean, default=False, index=True)
    close_price = db.Column(db.Numeric(precision=10, scale=2), nullable=True)
    close_date = db.Column(db.DateTime, nullable=True)
    realized_pnl = db.Column(db.Numeric(precision=12, scale=2), nullable=True)

    user = db.relationship("User", backref=db.backref("paper_trades", lazy=True))

    def __repr__(self):
        return f"<PaperTrade {self.trade_type.upper()} {self.shares} {self.ticker} @ ${self.price}>"

    def to_dict(self):
        return {
            "id": self.id,
            "ticker": self.ticker,
            "shares": float(self.shares),
            "price": float(self.price),
            "trade_type": self.trade_type,
            "trade_date": self.trade_date.isoformat() if self.trade_date else None,
            "notes": self.notes,
            "is_closed": self.is_closed,
            "close_price": float(self.close_price) if self.close_price else None,
            "close_date": self.close_date.isoformat() if self.close_date else None,
            "realized_pnl": float(self.realized_pnl) if self.realized_pnl else None,
            "total_value": float(self.shares * self.price),
        }

class TradeJournal(db.Model):
    """
    Trade Journal for tracking and improving trading performance.

    Helps traders log trades with psychology notes, screenshots,
    and lessons learned for continuous improvement.
    """

    __tablename__ = "trade_journal"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    ticker = db.Column(db.String(10), nullable=False, index=True)

    # Trade details
    trade_type = db.Column(db.String(10), nullable=False)  # 'long' or 'short'
    entry_price = db.Column(db.Numeric(precision=10, scale=4), nullable=False)
    exit_price = db.Column(db.Numeric(precision=10, scale=4), nullable=True)
    shares = db.Column(db.Numeric(precision=10, scale=4), nullable=False)

    # Strategy & Setup
    strategy = db.Column(db.String(50), nullable=True)  # 'scalp', 'swing', 'breakout', 'reversal'
    setup_type = db.Column(db.String(100), nullable=True)  # 'order_block', 'fvg', 'liquidity_sweep'
    timeframe = db.Column(db.String(10), nullable=True)  # '1m', '5m', '15m', '1h', '4h', 'D'

    # Risk management
    stop_loss = db.Column(db.Numeric(precision=10, scale=4), nullable=True)
    take_profit = db.Column(db.Numeric(precision=10, scale=4), nullable=True)
    planned_risk_reward = db.Column(db.Float, nullable=True)
    actual_risk_reward = db.Column(db.Float, nullable=True)

    # Outcome
    pnl = db.Column(db.Numeric(precision=12, scale=2), nullable=True)
    pnl_percent = db.Column(db.Float, nullable=True)
    outcome = db.Column(db.String(20), nullable=True, index=True)  # 'win', 'loss', 'breakeven'

    # Psychology & Self-Assessment
    emotion_before = db.Column(db.String(50), nullable=True)  # 'confident', 'fearful', 'fomo', 'revenge'
    emotion_after = db.Column(db.String(50), nullable=True)
    confidence_level = db.Column(db.Integer, nullable=True)  # 1-10
    followed_plan = db.Column(db.Boolean, default=True)

    # Notes & Learning
    entry_reason = db.Column(db.Text, nullable=True)  # Why did you enter?
    exit_reason = db.Column(db.Text, nullable=True)  # Why did you exit?
    mistakes = db.Column(db.Text, nullable=True)  # What went wrong?
    lessons_learned = db.Column(db.Text, nullable=True)  # Key takeaways
    notes = db.Column(db.Text, nullable=True)  # General notes

    # Screenshots (URLs or base64)
    entry_screenshot = db.Column(db.Text, nullable=True)
    exit_screenshot = db.Column(db.Text, nullable=True)

    # Market context
    market_condition = db.Column(db.String(50), nullable=True)  # 'trending', 'ranging', 'volatile'
    news_catalyst = db.Column(db.String(200), nullable=True)

    # Timestamps
    entry_date = db.Column(db.DateTime, nullable=False, index=True)
    exit_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                          onupdate=lambda: datetime.now(timezone.utc))

    # Relationship
    user = db.relationship("User", backref=db.backref("trade_journal", lazy=True))

    def __repr__(self):
        return f"<TradeJournal {self.ticker} {self.trade_type} {self.outcome}>"

    def to_dict(self):
        return {
            "id": self.id,
            "ticker": self.ticker,
            "trade_type": self.trade_type,
            "entry_price": float(self.entry_price) if self.entry_price else None,
            "exit_price": float(self.exit_price) if self.exit_price else None,
            "shares": float(self.shares) if self.shares else None,
            "strategy": self.strategy,
            "setup_type": self.setup_type,
            "timeframe": self.timeframe,
            "stop_loss": float(self.stop_loss) if self.stop_loss else None,
            "take_profit": float(self.take_profit) if self.take_profit else None,
            "planned_risk_reward": self.planned_risk_reward,
            "actual_risk_reward": self.actual_risk_reward,
            "pnl": float(self.pnl) if self.pnl else None,
            "pnl_percent": self.pnl_percent,
            "outcome": self.outcome,
            "emotion_before": self.emotion_before,
            "emotion_after": self.emotion_after,
            "confidence_level": self.confidence_level,
            "followed_plan": self.followed_plan,
            "entry_reason": self.entry_reason,
            "exit_reason": self.exit_reason,
            "mistakes": self.mistakes,
            "lessons_learned": self.lessons_learned,
            "notes": self.notes,
            "market_condition": self.market_condition,
            "news_catalyst": self.news_catalyst,
            "entry_date": self.entry_date.isoformat() if self.entry_date else None,
            "exit_date": self.exit_date.isoformat() if self.exit_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

class PortfolioSnapshot(db.Model):
    """
    Daily portfolio snapshots for tracking performance over time.

    Stores daily value, P&L, and key metrics for analytics.
    """

    __tablename__ = "portfolio_snapshots"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    snapshot_date = db.Column(db.Date, nullable=False, index=True)

    # Portfolio values
    total_value = db.Column(db.Numeric(precision=14, scale=2), nullable=False)
    cash_balance = db.Column(db.Numeric(precision=14, scale=2), default=0)
    invested_value = db.Column(db.Numeric(precision=14, scale=2), default=0)

    # Daily metrics
    daily_pnl = db.Column(db.Numeric(precision=12, scale=2), nullable=True)
    daily_pnl_percent = db.Column(db.Float, nullable=True)

    # Cumulative metrics
    total_pnl = db.Column(db.Numeric(precision=12, scale=2), nullable=True)
    total_pnl_percent = db.Column(db.Float, nullable=True)

    # Holdings count
    positions_count = db.Column(db.Integer, default=0)

    # Risk metrics
    largest_position_pct = db.Column(db.Float, nullable=True)  # % of portfolio in largest position

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Unique constraint: one snapshot per user per day
    __table_args__ = (
        db.UniqueConstraint("user_id", "snapshot_date", name="unique_daily_snapshot"),
    )

    user = db.relationship("User", backref=db.backref("portfolio_snapshots", lazy=True))

    def to_dict(self):
        return {
            "id": self.id,
            "snapshot_date": self.snapshot_date.isoformat() if self.snapshot_date else None,
            "total_value": float(self.total_value) if self.total_value else 0,
            "cash_balance": float(self.cash_balance) if self.cash_balance else 0,
            "invested_value": float(self.invested_value) if self.invested_value else 0,
            "daily_pnl": float(self.daily_pnl) if self.daily_pnl else 0,
            "daily_pnl_percent": self.daily_pnl_percent,
            "total_pnl": float(self.total_pnl) if self.total_pnl else 0,
            "total_pnl_percent": self.total_pnl_percent,
            "positions_count": self.positions_count,
        }

class SentimentData(db.Model):
    """
    Social media sentiment data for stocks.

    Aggregated sentiment from Reddit, Twitter, StockTwits, etc.
    """

    __tablename__ = "sentiment_data"

    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(10), nullable=False, index=True)

    # Sentiment scores (0-100)
    overall_score = db.Column(db.Integer, nullable=False)  # 0=very bearish, 50=neutral, 100=very bullish
    reddit_score = db.Column(db.Integer, nullable=True)
    twitter_score = db.Column(db.Integer, nullable=True)
    news_score = db.Column(db.Integer, nullable=True)

    # Volume metrics
    mentions_24h = db.Column(db.Integer, default=0)
    mentions_change_pct = db.Column(db.Float, nullable=True)  # vs previous 24h

    # Sentiment breakdown
    bullish_pct = db.Column(db.Float, nullable=True)
    bearish_pct = db.Column(db.Float, nullable=True)
    neutral_pct = db.Column(db.Float, nullable=True)

    # Top keywords/themes
    keywords = db.Column(db.Text, nullable=True)  # JSON array of top keywords

    # Metadata
    sources_count = db.Column(db.Integer, default=0)
    data_quality = db.Column(db.String(20), default="medium")  # low, medium, high

    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                          onupdate=lambda: datetime.now(timezone.utc), index=True)

    def to_dict(self):
        import json
        return {
            "ticker": self.ticker,
            "overall_score": self.overall_score,
            "reddit_score": self.reddit_score,
            "twitter_score": self.twitter_score,
            "news_score": self.news_score,
            "mentions_24h": self.mentions_24h,
            "mentions_change_pct": self.mentions_change_pct,
            "bullish_pct": self.bullish_pct,
            "bearish_pct": self.bearish_pct,
            "neutral_pct": self.neutral_pct,
            "keywords": json.loads(self.keywords) if self.keywords else [],
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class ChartPattern(db.Model):
    """
    Detected chart patterns for stocks.

    AI-detected patterns like head & shoulders, triangles, etc.
    """

    __tablename__ = "chart_patterns"

    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(10), nullable=False, index=True)
    timeframe = db.Column(db.String(10), nullable=False)  # '1H', '4H', 'D', 'W'

    # Pattern info
    pattern_type = db.Column(db.String(50), nullable=False, index=True)
    # Types: 'head_shoulders', 'double_top', 'double_bottom', 'triangle_ascending',
    #        'triangle_descending', 'wedge_rising', 'wedge_falling', 'flag', 'pennant',
    #        'cup_handle', 'channel_up', 'channel_down'

    pattern_direction = db.Column(db.String(10), nullable=False)  # 'bullish', 'bearish', 'neutral'

    # Price levels
    pattern_start_price = db.Column(db.Numeric(precision=10, scale=4), nullable=True)
    pattern_end_price = db.Column(db.Numeric(precision=10, scale=4), nullable=True)
    breakout_level = db.Column(db.Numeric(precision=10, scale=4), nullable=True)
    target_price = db.Column(db.Numeric(precision=10, scale=4), nullable=True)
    stop_loss = db.Column(db.Numeric(precision=10, scale=4), nullable=True)

    # Confidence & Status
    confidence = db.Column(db.Integer, nullable=False)  # 0-100
    status = db.Column(db.String(20), default="forming")  # 'forming', 'complete', 'triggered', 'failed'

    # Dates
    pattern_start_date = db.Column(db.DateTime, nullable=True)
    pattern_end_date = db.Column(db.DateTime, nullable=True)
    detected_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "ticker": self.ticker,
            "timeframe": self.timeframe,
            "pattern_type": self.pattern_type,
            "pattern_direction": self.pattern_direction,
            "breakout_level": float(self.breakout_level) if self.breakout_level else None,
            "target_price": float(self.target_price) if self.target_price else None,
            "stop_loss": float(self.stop_loss) if self.stop_loss else None,
            "confidence": self.confidence,
            "status": self.status,
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
        }