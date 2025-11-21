from flask import Blueprint, render_template, jsonify, request, current_app
from flask_login import login_required, current_user
from app.models import db, User, NewsArticle, EconomicEvent, Signal, Watchlist, AIScore, Transaction
from sqlalchemy import or_
from sqlalchemy.orm import joinedload
from datetime import datetime, timezone
from collections import defaultdict
from decimal import Decimal

main_bp = Blueprint('main', __name__)

# --- Helper Functions ---

def get_news_articles(limit=50, rating_filter=None):
    try:
        query = NewsArticle.query.order_by(NewsArticle.published_at.desc())
        if rating_filter:
            query = query.filter(NewsArticle.ai_rating >= rating_filter)
        articles = query.limit(limit).all()
        return [article.to_dict() for article in articles]
    except Exception as e:
        current_app.logger.error(f"Error loading news: {e}")
        return []

# --- Routes ---

@main_bp.route("/health")
def health_check():
    try:
        db.session.execute(db.select(1)).scalar()
        return jsonify({"status": "healthy", "database": "connected"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 503

@main_bp.route("/")
def index():
    # Placeholder for Polygon service integration
    market_data = [] 
    stats = {"total_indices": 0, "market_status": "Unknown"}
    return render_template("index.html", market_data=market_data, stats=stats, user=current_user)

@main_bp.route("/dashboard")
@login_required
def dashboard():
    try:
        user_watchlist = Watchlist.query.filter_by(user_id=current_user.id).all()
        watchlist_tickers = [w.ticker for w in user_watchlist]
        
        ai_scores = {}
        if watchlist_tickers:
            scores = AIScore.query.filter(AIScore.ticker.in_(watchlist_tickers)).all()
            ai_scores = {score.ticker: score.to_dict() for score in scores}
            
        related_news = []
        if watchlist_tickers:
            search_tickers = watchlist_tickers[:5]
            filters = [NewsArticle.title.contains(ticker) for ticker in search_tickers]
            ticker_news = NewsArticle.query.filter(or_(*filters)).order_by(NewsArticle.published_at.desc()).limit(15).all()
            related_news = [article.to_dict() for article in ticker_news]

        return render_template("dashboard.html", user=current_user, watchlist=watchlist_tickers, ai_scores=ai_scores, related_news=related_news)
    except Exception as e:
        current_app.logger.error(f"Dashboard error: {e}")
        return render_template("dashboard.html", user=current_user, watchlist=[], ai_scores={}, related_news=[])

@main_bp.route("/market")
def market():
    return render_template("market.html", user=current_user)

@main_bp.route("/screener")
def screener():
    return render_template("screener.html", user=current_user)

@main_bp.route("/portfolio")
@login_required
def portfolio():
    # Simplified portfolio logic for initial migration
    return render_template("portfolio.html", user=current_user, transactions=[], portfolio=[], total_cost=0, total_value=0, total_pnl=0, total_pnl_percent=0)

@main_bp.route("/about")
def about():
    return render_template("about.html", user=current_user)

@main_bp.route("/terms")
def terms():
    return render_template("terms.html")

@main_bp.route("/privacy")
def privacy():
    return render_template("privacy.html")
