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
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=True)  # Nullable for OAuth users
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # OAuth fields
    google_id = db.Column(db.String(200), unique=True, nullable=True)
    oauth_provider = db.Column(db.String(50), nullable=True)  # 'google', 'apple', etc
    profile_picture = db.Column(db.String(500), nullable=True)

    # Email verification
    email_verified = db.Column(db.Boolean, default=False)
    verification_code = db.Column(db.String(6), nullable=True)
    verification_code_expiry = db.Column(db.DateTime, nullable=True)

    # Subscription info
    subscription_tier = db.Column(db.String(20), default='free')  # free, pro, premium, developer
    subscription_status = db.Column(db.String(20), default='inactive')  # active, inactive, cancelled
    subscription_start = db.Column(db.DateTime, nullable=True)
    subscription_end = db.Column(db.DateTime, nullable=True)
    stripe_customer_id = db.Column(db.String(100), nullable=True)
    stripe_subscription_id = db.Column(db.String(100), nullable=True)

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
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default='USD')
    status = db.Column(db.String(20), nullable=False)  # succeeded, failed, pending
    stripe_payment_id = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('payments', lazy=True))

    def __repr__(self):
        return f'<Payment {self.id} - ${self.amount}>'
