from flask import render_template, jsonify, current_app, request, redirect, url_for
from flask_login import login_required, current_user
from web.database import db, NewsArticle, AIScore
from web.polygon_service import PolygonService
from . import main
import logging
from sqlalchemy import or_

logger = logging.getLogger(__name__)

@main.route("/health")
def health_check():
    try:
        db.session.execute(db.select(1)).scalar()
        return jsonify({"status": "healthy", "database": "connected"}), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({"status": "unhealthy", "error": str(e)}), 503

@main.route("/")
def index():
    polygon = PolygonService()
    market_data = []
    try:
        indices = polygon.get_market_indices()
        for symbol, data in indices.items():
            market_data.append(
                {
                    "name": data.get("name", symbol),
                    "symbol": symbol,
                    "price": data.get("price", 0),
                    "change": data.get("change_percent", 0),
                    "change_amount": data.get("change", 0),
                    "volume": data.get("volume", 0),
                    "high": data.get("day_high", 0),
                    "low": data.get("day_low", 0),
                }
            )
        stats = {"total_indices": len(market_data), "market_status": "Active"}
    except Exception as e:
        logger.error(f"Error fetching Polygon indices: {e}")
        market_data = []
        stats = {"total_indices": 0, "market_status": "Unknown"}

    return render_template("index.html", market_data=market_data, stats=stats, user=current_user)

@main.route("/about")
def about():
    return render_template("about.html", user=current_user)

@main.route("/account")
@login_required
def account():
    return render_template("account.html", user=current_user)

@main.route("/terms")
def terms():
    return render_template("terms.html")

@main.route("/privacy")
def privacy():
    return render_template("privacy.html")

@main.route("/market")
@login_required
def market():
    return render_template("market.html", user=current_user)

@main.route("/dashboard")
@login_required
def dashboard():
    try:
        related_news = (
            NewsArticle.query.order_by(NewsArticle.published_at.desc()).limit(10).all()
        )
        unique_news = [article.to_dict() for article in related_news]

        return render_template(
            "dashboard.html",
            user=current_user,
            watchlist=[],
            ai_scores={},
            related_news=unique_news,
        )
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}", exc_info=True)
        return render_template(
            "dashboard.html", user=current_user, watchlist=[], ai_scores={}, related_news=[]
        )

@main.route("/login")
def login_redirect():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    return redirect(url_for("auth.login"), code=301)

@main.route("/register")
def register_redirect():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    return redirect(url_for("auth.signup"), code=301)

@main.route("/logout")
def logout_redirect():
    return redirect(url_for("auth.logout"))

@main.route("/pricing")
def pricing():
    return render_template("about.html")

@main.route("/stocks")
@login_required
def stocks():
    return render_template("stocks.html", ticker=None, user=current_user)

@main.route("/stocks/<ticker>")
@login_required
def stock_detail(ticker):
    polygon = PolygonService()
    try:
        ticker = ticker.upper()
        quote = polygon.get_stock_quote(ticker)
        details = polygon.get_ticker_details(ticker)
        return render_template(
            "stock_chart.html",
            ticker=ticker,
            quote=quote,
            details=details,
            user=current_user,
        )
    except Exception as e:
        logger.error(f"Error fetching stock {ticker}: {e}")
        return render_template(
            "stock_chart.html",
            ticker=ticker,
            quote=None,
            details=None,
            user=current_user,
        )

@main.route("/news")
@login_required
def news():
    return render_template("news.html", user=current_user)

@main.route("/admin")
@login_required
def admin():
    if not current_user.email.endswith("@admin.com"):
        return redirect(url_for("main.index"))
    return redirect(url_for("auth.admin_dashboard"))
