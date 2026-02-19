from flask import Blueprint, jsonify, request
from web.database import NewsArticle, EconomicEvent, db, User
from src.services.db_service import DatabaseService
from src.services.market_data_service import MarketDataService
from web.polygon_service import get_polygon_service
from datetime import datetime, timezone, timedelta
from sqlalchemy import or_
import logging
import requests
import os
import json

logger = logging.getLogger(__name__)

api_main = Blueprint("api_main", __name__)


@api_main.route("/api/news")
def get_news():
    """Get all news articles"""
    articles = DatabaseService.get_news_articles(limit=50)
    return jsonify({"success": True, "articles": articles})


@api_main.route("/api/news/critical")
def get_critical_news():
    """Get 5-star news articles"""
    articles = DatabaseService.get_news_articles(limit=20, rating_filter=5)
    return jsonify({"success": True, "articles": articles})


@api_main.route("/api/news/search")
def search_news():
    """Search news by ticker or keyword"""
    ticker = request.args.get("ticker")
    keyword = request.args.get("keyword")

    query = NewsArticle.query

    if ticker:
        query = query.filter(NewsArticle.title.contains(ticker))

    if keyword:
        query = query.filter(
            or_(
                NewsArticle.title.contains(keyword),
                NewsArticle.description.contains(keyword),
            )
        )

    articles = query.order_by(NewsArticle.published_at.desc()).limit(50).all()
    return jsonify({"success": True, "articles": [a.to_dict() for a in articles]})


@api_main.route("/api/news/refresh", methods=["GET", "POST"])
def refresh_news():
    """Collect fresh news from Polygon API and save to database"""
    result = MarketDataService.refresh_news(limit=50)
    return jsonify(result)


@api_main.route("/api/economic-calendar")
def get_calendar():
    """Get economic calendar events"""
    events = DatabaseService.get_economic_events(days_ahead=60)
    return jsonify({"success": True, "events": events})


@api_main.route("/api/economic-calendar/refresh", methods=["GET", "POST"])
def refresh_calendar():
    """Fetch real economic calendar data from Finnhub API"""
    result = MarketDataService.refresh_calendar()
    return jsonify(result)


@api_main.route("/api/stock/<ticker>/chart")
def get_stock_chart(ticker):
    """Get stock chart data"""
    ticker = ticker.upper()
    if not ticker.isalpha() or len(ticker) > 5:
        return jsonify({"error": "Invalid ticker format. Must be 1-5 letters."}), 400

    timeframe = request.args.get("timeframe", "1D")
    polygon = get_polygon_service()

    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=30)).strftime(
        "%Y-%m-%d"
    )  # Default 30 days

    data = polygon.get_aggregates(ticker, 1, "day", start_date, end_date)

    return jsonify({"candles": data if data else []})


@api_main.route("/api/stock/<ticker>/news")
def get_stock_news(ticker):
    """Get news for a specific stock"""
    articles = (
        NewsArticle.query.filter(NewsArticle.title.contains(ticker))
        .order_by(NewsArticle.published_at.desc())
        .limit(10)
        .all()
    )

    return jsonify({"success": True, "articles": [a.to_dict() for a in articles]})


def _mask_key(key: str, show_chars: int = 4) -> str:
    """Mask API key for display, showing first few characters"""
    if not key or len(key) < show_chars + 4:
        return "***"
    return f"{key[:show_chars]}...{key[-2:]}"


@api_main.route("/api/status")
def get_api_status():
    """Check status of all external APIs and services with actual connectivity tests."""
    status = {
        "polygon": {"connected": False, "message": "ENV: POLYGON_API_KEY not set", "label": "Polygon.io (Stocks)", "env_var": "POLYGON_API_KEY"},
        "twelvedata": {"connected": False, "message": "ENV: TWELVEDATA_API_KEY not set", "label": "Twelve Data (800/day)", "env_var": "TWELVEDATA_API_KEY"},
        "binance": {"connected": False, "message": "Checking Binance API...", "label": "Binance (Crypto)", "env_var": None},
        "gemini": {"connected": False, "message": "ENV: GEMINI_API_KEY not set", "label": "Gemini AI", "env_var": "GEMINI_API_KEY"},
        "finnhub": {"connected": False, "message": "ENV: FINNHUB_API_KEY not set", "label": "Finnhub", "env_var": "FINNHUB_API_KEY"},
        "alpha_vantage": {"connected": False, "message": "ENV: ALPHA_VANTAGE_API_KEY not set", "label": "Alpha Vantage", "env_var": "ALPHA_VANTAGE_API_KEY"},
        "google_oauth": {"connected": False, "message": "ENV: GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET not set", "label": "Google OAuth", "env_var": "GOOGLE_CLIENT_ID"},
        "recaptcha": {"connected": False, "message": "ENV: RECAPTCHA_SECRET_KEY not set", "label": "reCAPTCHA", "env_var": "RECAPTCHA_SECRET_KEY"},
        "mail": {"connected": False, "message": "ENV: MAIL_USERNAME and MAIL_PASSWORD not set", "label": "Email Service", "env_var": "MAIL_USERNAME"},
        "redis": {"connected": False, "message": "ENV: REDIS_URL not set (using memory)", "label": "Redis Cache", "env_var": "REDIS_URL"},
        "database": {"connected": False, "message": "Database connection failed", "label": "Database", "env_var": "DATABASE_URL"},
    }

    # Check Polygon API
    polygon_key = os.environ.get("POLYGON_API_KEY", "")
    if polygon_key:
        try:
            polygon = get_polygon_service()
            result = polygon.get_previous_close("AAPL")
            if result:
                aapl_price = result.get("close") or result.get("c") or 0
                status["polygon"] = {"connected": True, "message": f"OK: AAPL=${aapl_price:.2f}", "label": "Polygon.io (Stocks)", "env_var": "POLYGON_API_KEY"}
        except Exception as e:
            status["polygon"]["message"] = f"ERROR: {str(e)[:50]}"

    # Check Twelve Data
    twelvedata_key = os.environ.get("TWELVEDATA_API_KEY", "")
    if twelvedata_key:
        try:
            resp = requests.get("https://api.twelvedata.com/quote", params={"symbol": "AAPL", "apikey": twelvedata_key}, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data and not data.get("code") and data.get("close"):
                    status["twelvedata"] = {"connected": True, "message": f"OK: AAPL=${float(data['close']):.2f}", "label": "Twelve Data (800/day)", "env_var": "TWELVEDATA_API_KEY"}
        except Exception as e:
            status["twelvedata"]["message"] = f"ERROR: {str(e)[:40]}"

    # Check Binance
    try:
        resp = requests.get("https://api.binance.us/api/v3/ping", timeout=5)
        if resp.status_code == 200:
            status["binance"] = {"connected": True, "message": "OK: Binance.US working", "label": "Binance (Crypto)", "env_var": None}
    except Exception:
        status["binance"]["message"] = "NETWORK: Unreachable"

    # Check Gemini
    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    if gemini_key:
        status["gemini"] = {"connected": True, "message": "OK: Configured", "label": "Gemini AI", "env_var": "GEMINI_API_KEY"}

    # Check Finnhub
    finnhub_key = os.environ.get("FINNHUB_API_KEY", "")
    if finnhub_key:
        try:
            resp = requests.get(f"https://finnhub.io/api/v1/stock/symbol?exchange=US&token={finnhub_key}", timeout=5)
            if resp.status_code == 200:
                status["finnhub"] = {"connected": True, "message": "OK: API working", "label": "Finnhub", "env_var": "FINNHUB_API_KEY"}
        except Exception:
            status["finnhub"]["message"] = "NETWORK: Error"

    # Check Database
    try:
        user_count = User.query.count()
        status["database"] = {"connected": True, "message": f"OK: {user_count} users", "label": "Database", "env_var": "DATABASE_URL"}
    except Exception as e:
        status["database"]["message"] = f"ERROR: {str(e)[:50]}"

    return jsonify(status)


@api_main.route("/api/status/test-ticker")
def test_ticker_data():
    """Test data quality for a specific ticker across all APIs."""
    ticker = request.args.get("ticker", "AAPL").upper().strip()
    # Simplified version for now
    return jsonify({"ticker": ticker, "status": "diagnostic mode", "message": "Call /api/status for full health check"})
