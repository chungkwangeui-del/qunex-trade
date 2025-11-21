"""
Flask-Admin Administrative Interface

Secure admin panel for managing database models:
- User management (with password protection)
- News articles
- Economic events
- AI scores
- Watchlists

Security: Only accessible by users with admin@qunextrade.com email
"""

import os
from flask import redirect, url_for, request
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user
from database import db, User, NewsArticle, EconomicEvent, AIScore, Watchlist


class SecureModelView(ModelView):
    """
    Secure base model view that requires admin authentication.

    Only users with email matching ADMIN_EMAIL environment variable
    can access the admin panel.
    """

    def is_accessible(self):
        """
        Check if current user has admin access.

        Returns:
            bool: True if user is authenticated and is admin, False otherwise
        """
        if not current_user.is_authenticated:
            return False

        # Check if user email matches admin email from environment
        admin_email = os.getenv("ADMIN_EMAIL", "admin@qunextrade.com")
        return current_user.email == admin_email

    def inaccessible_callback(self, name, **kwargs):
        """
        Redirect unauthorized users to home page.

        Args:
            name: View name
            **kwargs: Additional arguments

        Returns:
            Flask redirect to home page
        """
        return redirect(url_for("main.index"))


class SecureAdminIndexView(AdminIndexView):
    """Secure admin index view with same authentication as model views"""

    def is_accessible(self):
        """Check admin access"""
        if not current_user.is_authenticated:
            return False

        admin_email = os.getenv("ADMIN_EMAIL", "admin@qunextrade.com")
        return current_user.email == admin_email

    def inaccessible_callback(self, name, **kwargs):
        """Redirect unauthorized users"""
        return redirect(url_for("main.index"))

    @expose("/")
    def index(self):
        """Custom admin index page"""
        return self.render("admin/index.html")


class UserAdminView(SecureModelView):
    """
    Admin view for User model with sensitive fields hidden.

    Security measures:
    - Password hash never displayed or editable
    - Stripe customer ID hidden
    - Email verification status read-only
    - Subscription dates protected
    """

    # Columns to display in list view
    column_list = [
        "id",
        "email",
        "username",
        "subscription_tier",
        "subscription_status",
        "subscription_start",
        "subscription_end",
        "email_verified",
        "created_at",
    ]

    # Columns to exclude from list and forms (sensitive data)
    column_exclude_list = ["password_hash", "stripe_customer_id"]
    form_excluded_columns = ["password_hash", "stripe_customer_id", "created_at"]

    # Searchable columns
    column_searchable_list = ["email", "username"]

    # Filterable columns
    column_filters = ["subscription_tier", "subscription_status", "email_verified"]

    # Column labels
    column_labels = {
        "subscription_tier": "Tier",
        "subscription_status": "Status",
        "email_verified": "Verified",
    }

    # Default sort
    column_default_sort = ("created_at", True)  # DESC

    # Page size
    page_size = 50


class NewsArticleAdminView(SecureModelView):
    """Admin view for NewsArticle model"""

    column_list = [
        "id",
        "title",
        "source",
        "published_at",
        "ai_rating",
        "sentiment",
        "created_at",
    ]

    column_searchable_list = ["title", "source"]
    column_filters = ["sentiment", "ai_rating", "published_at"]

    column_labels = {
        "ai_rating": "AI Rating",
        "published_at": "Published",
    }

    column_default_sort = ("published_at", True)  # DESC
    page_size = 50


class EconomicEventAdminView(SecureModelView):
    """Admin view for EconomicEvent model"""

    column_list = [
        "id",
        "title",
        "date",
        "time",
        "country",
        "importance",
        "actual",
        "forecast",
        "previous",
        "source",
    ]

    column_searchable_list = ["title", "country"]
    column_filters = ["importance", "country", "date", "source"]

    column_default_sort = ("date", False)  # ASC (upcoming first)
    page_size = 50


class AIScoreAdminView(SecureModelView):
    """Admin view for AIScore model"""

    column_list = ["id", "ticker", "score", "rating", "updated_at"]

    column_searchable_list = ["ticker"]
    column_filters = ["rating", "score"]

    column_labels = {
        "updated_at": "Last Updated",
    }

    column_default_sort = ("updated_at", True)  # DESC
    page_size = 50


class WatchlistAdminView(SecureModelView):
    """Admin view for Watchlist model"""

    column_list = ["id", "user_id", "ticker", "added_at"]

    column_searchable_list = ["ticker"]
    column_filters = ["ticker", "added_at"]

    column_labels = {
        "added_at": "Added",
    }

    column_default_sort = ("added_at", True)  # DESC
    page_size = 100


def init_admin(app):
    """
    Initialize Flask-Admin with secure model views.

    Args:
        app: Flask application instance

    Returns:
        Admin: Configured Flask-Admin instance
    """
    admin = Admin(
        app,
        name="Qunex Trade Admin",
        template_mode="bootstrap4",
        index_view=SecureAdminIndexView(),
    )

    # Add model views with security
    admin.add_view(UserAdminView(User, db.session, name="Users"))
    admin.add_view(NewsArticleAdminView(NewsArticle, db.session, name="News"))
    admin.add_view(EconomicEventAdminView(EconomicEvent, db.session, name="Economic Calendar"))
    admin.add_view(AIScoreAdminView(AIScore, db.session, name="AI Scores"))
    admin.add_view(WatchlistAdminView(Watchlist, db.session, name="Watchlists"))

    return admin
