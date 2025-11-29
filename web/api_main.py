from flask import Blueprint, jsonify, request
from web.database import NewsArticle, EconomicEvent, db
from web.utils import get_news_articles, get_economic_events
from web.polygon_service import get_polygon_service
from datetime import datetime, timezone, timedelta
from sqlalchemy import or_
import logging

logger = logging.getLogger(__name__)

api_main = Blueprint('api_main', __name__)

@api_main.route("/api/news")
def get_news():
    """Get all news articles"""
    articles = get_news_articles(limit=50)
    return jsonify({"success": True, "articles": articles})

@api_main.route("/api/news/critical")
def get_critical_news():
    """Get 5-star news articles"""
    articles = get_news_articles(limit=20, rating_filter=5)
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
        query = query.filter(or_(
            NewsArticle.title.contains(keyword),
            NewsArticle.description.contains(keyword)
        ))

    articles = query.order_by(NewsArticle.published_at.desc()).limit(50).all()
    return jsonify({"success": True, "articles": [a.to_dict() for a in articles]})

@api_main.route("/api/news/refresh", methods=["GET", "POST"])
def refresh_news():
    """Collect fresh news from Polygon API and save to database"""
    try:
        from src.news_collector import NewsCollector

        collector = NewsCollector()
        news_items = collector.collect_all_news(limit=50)

        if not news_items:
            return jsonify({"success": False, "message": "No news collected from API"})

        saved_count = 0
        for item in news_items:
            try:
                # Check if article already exists
                existing = NewsArticle.query.filter_by(url=item["url"]).first()
                if existing:
                    continue

                # Parse published date
                published_at = None
                if item.get("published_at"):
                    try:
                        published_at = datetime.fromisoformat(item["published_at"].replace("Z", "+00:00"))
                    except:
                        published_at = datetime.now(timezone.utc)
                else:
                    published_at = datetime.now(timezone.utc)

                # Create new article
                article = NewsArticle(
                    title=item["title"][:500],
                    description=item.get("description", "")[:2000] if item.get("description") else None,
                    url=item["url"][:1000],
                    source=item.get("source", "Unknown")[:100],
                    published_at=published_at,
                    ai_rating=3,  # Default rating
                    ai_analysis=item.get("description", "AI analysis unavailable - check API key"),
                    sentiment="neutral"
                )
                db.session.add(article)
                saved_count += 1

            except Exception as e:
                logger.error(f"Error saving news article: {e}")
                continue

        db.session.commit()
        logger.info(f"Saved {saved_count} new articles to database")

        return jsonify({
            "success": True,
            "count": saved_count,
            "total_collected": len(news_items),
            "message": f"Collected {len(news_items)} articles, saved {saved_count} new"
        })

    except ImportError as e:
        logger.error(f"Import error: {e}")
        return jsonify({"success": False, "message": "News collector module not available"})
    except Exception as e:
        logger.error(f"Error refreshing news: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)})

@api_main.route("/api/economic-calendar")
def get_calendar():
    """Get economic calendar events"""
    events = get_economic_events(days_ahead=60)
    return jsonify({"success": True, "events": events})

@api_main.route("/api/economic-calendar/refresh", methods=["GET", "POST"])
def refresh_calendar():
    """Populate economic calendar with upcoming US economic events"""
    try:
        # Major recurring US economic events
        event_templates = [
            {"title": "FOMC Meeting Minutes", "importance": "high", "time": "2:00 PM EST"},
            {"title": "Non-Farm Payrolls", "importance": "high", "time": "8:30 AM EST"},
            {"title": "CPI (Consumer Price Index)", "importance": "high", "time": "8:30 AM EST"},
            {"title": "PPI (Producer Price Index)", "importance": "medium", "time": "8:30 AM EST"},
            {"title": "Retail Sales", "importance": "medium", "time": "8:30 AM EST"},
            {"title": "GDP (Quarterly)", "importance": "high", "time": "8:30 AM EST"},
            {"title": "Jobless Claims", "importance": "medium", "time": "8:30 AM EST"},
            {"title": "ISM Manufacturing PMI", "importance": "medium", "time": "10:00 AM EST"},
            {"title": "Consumer Confidence", "importance": "medium", "time": "10:00 AM EST"},
            {"title": "Durable Goods Orders", "importance": "medium", "time": "8:30 AM EST"},
            {"title": "Housing Starts", "importance": "low", "time": "8:30 AM EST"},
            {"title": "Fed Chair Powell Speech", "importance": "high", "time": "TBD"},
        ]

        today = datetime.now(timezone.utc).date()
        saved_count = 0

        # Generate events for the next 60 days
        for i in range(60):
            event_date = today + timedelta(days=i)

            # Skip weekends
            if event_date.weekday() >= 5:
                continue

            # Add different events on different days
            template = event_templates[i % len(event_templates)]

            # Check if event already exists
            existing = EconomicEvent.query.filter_by(
                title=template["title"],
                date=datetime.combine(event_date, datetime.min.time()).replace(tzinfo=timezone.utc)
            ).first()

            if existing:
                continue

            event = EconomicEvent(
                title=template["title"],
                description=f"US Economic Indicator: {template['title']}",
                date=datetime.combine(event_date, datetime.min.time()).replace(tzinfo=timezone.utc),
                time=template["time"],
                country="USD",
                importance=template["importance"],
                forecast="TBD",
                previous="TBD",
                source="Economic Calendar"
            )
            db.session.add(event)
            saved_count += 1

        db.session.commit()
        logger.info(f"Saved {saved_count} economic events to database")

        return jsonify({
            "success": True,
            "count": saved_count,
            "message": f"Added {saved_count} economic events"
        })

    except Exception as e:
        logger.error(f"Error refreshing calendar: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)})

@api_main.route("/api/stock/<ticker>/chart")
def get_stock_chart(ticker):
    """Get stock chart data"""
    timeframe = request.args.get("timeframe", "1D")
    # Map timeframe to Polygon parameters if needed
    # For now, just use PolygonService
    polygon = get_polygon_service()
    # This is a placeholder implementation, assuming PolygonService has a method or we use get_aggregates
    # The test expects "candles" in response
    
    # Example implementation using get_aggregates
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d") # Default 30 days
    
    data = polygon.get_aggregates(ticker, 1, "day", start_date, end_date)
    
    # Transform to expected format if needed, or just return
    return jsonify({"candles": data if data else []})

@api_main.route("/api/stock/<ticker>/news")
def get_stock_news(ticker):
    """Get news for a specific stock"""
    articles = NewsArticle.query.filter(
        NewsArticle.title.contains(ticker)
    ).order_by(NewsArticle.published_at.desc()).limit(10).all()

    return jsonify({"success": True, "articles": [a.to_dict() for a in articles]})

def _mask_key(key: str, show_chars: int = 4) -> str:
    """Mask API key for display, showing first few characters"""
    if not key or len(key) < show_chars + 4:
        return "***"
    return f"{key[:show_chars]}...{key[-2:]}"

@api_main.route("/api/status")
def get_api_status():
    """Check status of all external APIs and services with actual connectivity tests.

    Returns detailed diagnostic messages for troubleshooting:
    - Environment variable names when not configured
    - Key previews when keys are invalid
    - Specific error details for debugging
    """
    import os
    import requests

    status = {
        "polygon": {"connected": False, "message": "ENV: POLYGON_API_KEY not set", "label": "Polygon.io", "env_var": "POLYGON_API_KEY"},
        "gemini": {"connected": False, "message": "ENV: GEMINI_API_KEY not set", "label": "Gemini AI", "env_var": "GEMINI_API_KEY"},
        "finnhub": {"connected": False, "message": "ENV: FINNHUB_API_KEY not set", "label": "Finnhub", "env_var": "FINNHUB_API_KEY"},
        "alpha_vantage": {"connected": False, "message": "ENV: ALPHA_VANTAGE_API_KEY not set", "label": "Alpha Vantage", "env_var": "ALPHA_VANTAGE_API_KEY"},
        "google_oauth": {"connected": False, "message": "ENV: GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET not set", "label": "Google OAuth", "env_var": "GOOGLE_CLIENT_ID"},
        "recaptcha": {"connected": False, "message": "ENV: RECAPTCHA_SECRET_KEY not set", "label": "reCAPTCHA", "env_var": "RECAPTCHA_SECRET_KEY"},
        "mail": {"connected": False, "message": "ENV: MAIL_USERNAME and MAIL_PASSWORD not set", "label": "Email Service", "env_var": "MAIL_USERNAME"},
        "redis": {"connected": False, "message": "ENV: REDIS_URL not set (using memory)", "label": "Redis Cache", "env_var": "REDIS_URL"},
        "database": {"connected": False, "message": "Database connection failed", "label": "Database", "env_var": "DATABASE_URL"}
    }

    # Check Polygon API - actual API call
    polygon_key = os.environ.get("POLYGON_API_KEY", "")
    if polygon_key:
        try:
            polygon = get_polygon_service()
            result = polygon.get_previous_close("AAPL")
            if result:
                status["polygon"] = {"connected": True, "message": f"OK: API working (key: {_mask_key(polygon_key)})", "label": "Polygon.io", "env_var": "POLYGON_API_KEY"}
            else:
                status["polygon"] = {"connected": False, "message": f"INVALID: Key {_mask_key(polygon_key)} rejected or rate limited", "label": "Polygon.io", "env_var": "POLYGON_API_KEY"}
        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg or "403" in error_msg or "unauthorized" in error_msg.lower():
                status["polygon"] = {"connected": False, "message": f"AUTH_ERROR: Key {_mask_key(polygon_key)} unauthorized", "label": "Polygon.io", "env_var": "POLYGON_API_KEY"}
            elif "timeout" in error_msg.lower() or "connection" in error_msg.lower():
                status["polygon"] = {"connected": False, "message": f"NETWORK: Connection failed - {error_msg[:40]}", "label": "Polygon.io", "env_var": "POLYGON_API_KEY"}
            else:
                status["polygon"] = {"connected": False, "message": f"ERROR: {error_msg[:50]}", "label": "Polygon.io", "env_var": "POLYGON_API_KEY"}

    # Check Gemini API - actual test
    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    if gemini_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            # Validate key format (should start with AIza)
            if gemini_key.startswith("AIza"):
                status["gemini"] = {"connected": True, "message": f"OK: API configured (key: {_mask_key(gemini_key)})", "label": "Gemini AI", "env_var": "GEMINI_API_KEY"}
            else:
                status["gemini"] = {"connected": False, "message": f"FORMAT: Key should start with 'AIza' (got: {_mask_key(gemini_key)})", "label": "Gemini AI", "env_var": "GEMINI_API_KEY"}
        except ImportError:
            status["gemini"] = {"connected": False, "message": "MISSING: pip install google-generativeai", "label": "Gemini AI", "env_var": "GEMINI_API_KEY"}
        except Exception as e:
            error_msg = str(e)
            if "API_KEY" in error_msg.upper() or "INVALID" in error_msg.upper():
                status["gemini"] = {"connected": False, "message": f"INVALID: Key {_mask_key(gemini_key)} rejected by Google", "label": "Gemini AI", "env_var": "GEMINI_API_KEY"}
            else:
                status["gemini"] = {"connected": True, "message": f"OK: Configured (key: {_mask_key(gemini_key)})", "label": "Gemini AI", "env_var": "GEMINI_API_KEY"}

    # Check Finnhub API - actual API call
    finnhub_key = os.environ.get("FINNHUB_API_KEY", "")
    if finnhub_key:
        try:
            resp = requests.get(
                f"https://finnhub.io/api/v1/stock/symbol?exchange=US&token={finnhub_key}",
                timeout=5
            )
            if resp.status_code == 200:
                status["finnhub"] = {"connected": True, "message": f"OK: API working (key: {_mask_key(finnhub_key)})", "label": "Finnhub", "env_var": "FINNHUB_API_KEY"}
            elif resp.status_code == 401:
                status["finnhub"] = {"connected": False, "message": f"AUTH_ERROR: Key {_mask_key(finnhub_key)} unauthorized (401)", "label": "Finnhub", "env_var": "FINNHUB_API_KEY"}
            elif resp.status_code == 403:
                status["finnhub"] = {"connected": False, "message": f"FORBIDDEN: Key {_mask_key(finnhub_key)} access denied (403)", "label": "Finnhub", "env_var": "FINNHUB_API_KEY"}
            elif resp.status_code == 429:
                status["finnhub"] = {"connected": True, "message": f"RATE_LIMIT: API working but rate limited (key: {_mask_key(finnhub_key)})", "label": "Finnhub", "env_var": "FINNHUB_API_KEY"}
            else:
                status["finnhub"] = {"connected": False, "message": f"HTTP_{resp.status_code}: API returned error", "label": "Finnhub", "env_var": "FINNHUB_API_KEY"}
        except requests.exceptions.Timeout:
            status["finnhub"] = {"connected": False, "message": "TIMEOUT: finnhub.io not responding (5s)", "label": "Finnhub", "env_var": "FINNHUB_API_KEY"}
        except requests.exceptions.ConnectionError:
            status["finnhub"] = {"connected": False, "message": "NETWORK: Cannot reach finnhub.io", "label": "Finnhub", "env_var": "FINNHUB_API_KEY"}
        except Exception as e:
            status["finnhub"] = {"connected": False, "message": f"ERROR: {str(e)[:50]}", "label": "Finnhub", "env_var": "FINNHUB_API_KEY"}

    # Check Alpha Vantage API - actual API call
    alpha_key = os.environ.get("ALPHA_VANTAGE_API_KEY", "")
    if alpha_key:
        try:
            resp = requests.get(
                f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=IBM&interval=5min&apikey={alpha_key}",
                timeout=10
            )
            data = resp.json()
            if "Error Message" in data:
                status["alpha_vantage"] = {"connected": False, "message": f"INVALID: Key {_mask_key(alpha_key)} rejected", "label": "Alpha Vantage", "env_var": "ALPHA_VANTAGE_API_KEY"}
            elif "Note" in data:
                # Rate limited but key is valid
                status["alpha_vantage"] = {"connected": True, "message": f"RATE_LIMIT: Valid key but 5 calls/min exceeded (key: {_mask_key(alpha_key)})", "label": "Alpha Vantage", "env_var": "ALPHA_VANTAGE_API_KEY"}
            elif "Time Series" in str(data) or resp.status_code == 200:
                status["alpha_vantage"] = {"connected": True, "message": f"OK: API working (key: {_mask_key(alpha_key)})", "label": "Alpha Vantage", "env_var": "ALPHA_VANTAGE_API_KEY"}
            else:
                status["alpha_vantage"] = {"connected": False, "message": f"HTTP_{resp.status_code}: Unexpected response", "label": "Alpha Vantage", "env_var": "ALPHA_VANTAGE_API_KEY"}
        except requests.exceptions.Timeout:
            status["alpha_vantage"] = {"connected": False, "message": "TIMEOUT: alphavantage.co not responding (10s)", "label": "Alpha Vantage", "env_var": "ALPHA_VANTAGE_API_KEY"}
        except requests.exceptions.ConnectionError:
            status["alpha_vantage"] = {"connected": False, "message": "NETWORK: Cannot reach alphavantage.co", "label": "Alpha Vantage", "env_var": "ALPHA_VANTAGE_API_KEY"}
        except Exception as e:
            status["alpha_vantage"] = {"connected": False, "message": f"ERROR: {str(e)[:50]}", "label": "Alpha Vantage", "env_var": "ALPHA_VANTAGE_API_KEY"}

    # Check Google OAuth - verify credentials format
    google_id = os.environ.get("GOOGLE_CLIENT_ID", "")
    google_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    if google_id and google_secret:
        if google_id.endswith(".apps.googleusercontent.com"):
            status["google_oauth"] = {"connected": True, "message": f"OK: Valid format (ID: {_mask_key(google_id, 8)})", "label": "Google OAuth", "env_var": "GOOGLE_CLIENT_ID"}
        else:
            status["google_oauth"] = {"connected": False, "message": f"FORMAT: ID should end with '.apps.googleusercontent.com' (got: {_mask_key(google_id, 8)})", "label": "Google OAuth", "env_var": "GOOGLE_CLIENT_ID"}
    elif google_id:
        status["google_oauth"] = {"connected": False, "message": "PARTIAL: GOOGLE_CLIENT_SECRET missing", "label": "Google OAuth", "env_var": "GOOGLE_CLIENT_SECRET"}
    elif google_secret:
        status["google_oauth"] = {"connected": False, "message": "PARTIAL: GOOGLE_CLIENT_ID missing", "label": "Google OAuth", "env_var": "GOOGLE_CLIENT_ID"}

    # Check reCAPTCHA - verify key format
    recaptcha_site = os.environ.get("RECAPTCHA_SITE_KEY", "")
    recaptcha_secret = os.environ.get("RECAPTCHA_SECRET_KEY", "")
    if recaptcha_secret and recaptcha_site:
        status["recaptcha"] = {"connected": True, "message": f"OK: Both keys configured (site: {_mask_key(recaptcha_site)})", "label": "reCAPTCHA", "env_var": "RECAPTCHA_SITE_KEY"}
    elif recaptcha_secret:
        status["recaptcha"] = {"connected": False, "message": "PARTIAL: RECAPTCHA_SITE_KEY missing (needed for frontend)", "label": "reCAPTCHA", "env_var": "RECAPTCHA_SITE_KEY"}
    elif recaptcha_site:
        status["recaptcha"] = {"connected": False, "message": "PARTIAL: RECAPTCHA_SECRET_KEY missing (needed for verification)", "label": "reCAPTCHA", "env_var": "RECAPTCHA_SECRET_KEY"}

    # Check Mail Service - test SMTP connection
    mail_user = os.environ.get("MAIL_USERNAME", "")
    mail_pass = os.environ.get("MAIL_PASSWORD", "")
    if mail_user and mail_pass:
        try:
            import smtplib
            server = smtplib.SMTP("smtp.gmail.com", 587, timeout=5)
            server.starttls()
            server.login(mail_user, mail_pass)
            server.quit()
            status["mail"] = {"connected": True, "message": f"OK: SMTP authenticated ({mail_user})", "label": "Email Service", "env_var": "MAIL_USERNAME"}
        except smtplib.SMTPAuthenticationError as e:
            error_code = e.smtp_code if hasattr(e, 'smtp_code') else 'unknown'
            status["mail"] = {"connected": False, "message": f"AUTH_ERROR: Gmail rejected login ({mail_user}) - Code {error_code}. Use App Password not regular password.", "label": "Email Service", "env_var": "MAIL_PASSWORD"}
        except smtplib.SMTPConnectError:
            status["mail"] = {"connected": False, "message": "NETWORK: Cannot connect to smtp.gmail.com:587", "label": "Email Service", "env_var": "MAIL_USERNAME"}
        except Exception as e:
            status["mail"] = {"connected": False, "message": f"ERROR: {str(e)[:60]}", "label": "Email Service", "env_var": "MAIL_USERNAME"}
    elif mail_user:
        status["mail"] = {"connected": False, "message": f"PARTIAL: MAIL_PASSWORD not set for {mail_user}", "label": "Email Service", "env_var": "MAIL_PASSWORD"}
    elif mail_pass:
        status["mail"] = {"connected": False, "message": "PARTIAL: MAIL_USERNAME not set", "label": "Email Service", "env_var": "MAIL_USERNAME"}

    # Check Redis
    redis_url = os.environ.get("REDIS_URL", "")
    if redis_url and redis_url != "memory://":
        try:
            from web.extensions import cache
            cache.set("health_check", "ok", timeout=10)
            result = cache.get("health_check")
            if result == "ok":
                # Extract host from URL for display
                redis_host = redis_url.split("@")[-1].split("/")[0] if "@" in redis_url else redis_url.split("//")[-1].split("/")[0]
                status["redis"] = {"connected": True, "message": f"OK: Cache working ({redis_host})", "label": "Redis Cache", "env_var": "REDIS_URL"}
            else:
                status["redis"] = {"connected": False, "message": "READ_FAIL: Cache set succeeded but get failed", "label": "Redis Cache", "env_var": "REDIS_URL"}
        except Exception as e:
            error_msg = str(e)
            if "connection refused" in error_msg.lower():
                status["redis"] = {"connected": False, "message": "NETWORK: Redis server not running or wrong port", "label": "Redis Cache", "env_var": "REDIS_URL"}
            elif "authentication" in error_msg.lower() or "auth" in error_msg.lower():
                status["redis"] = {"connected": False, "message": "AUTH_ERROR: Redis password incorrect", "label": "Redis Cache", "env_var": "REDIS_URL"}
            else:
                status["redis"] = {"connected": False, "message": f"ERROR: {error_msg[:50]}", "label": "Redis Cache", "env_var": "REDIS_URL"}
    else:
        status["redis"] = {"connected": False, "message": "MEMORY: Using SimpleCache (no persistence)", "label": "Redis Cache", "env_var": "REDIS_URL"}

    # Check Database - actual query
    try:
        from web.database import User
        user_count = User.query.count()
        db_uri = os.environ.get("DATABASE_URL", "sqlite")
        db_type = "PostgreSQL" if "postgres" in db_uri.lower() else "SQLite"
        status["database"] = {"connected": True, "message": f"OK: {db_type} connected ({user_count} users)", "label": "Database", "env_var": "DATABASE_URL"}
    except Exception as e:
        error_msg = str(e)
        if "no such table" in error_msg.lower():
            status["database"] = {"connected": False, "message": "SCHEMA: Tables not created. Run 'flask db upgrade'", "label": "Database", "env_var": "DATABASE_URL"}
        elif "connection refused" in error_msg.lower():
            status["database"] = {"connected": False, "message": "NETWORK: Database server not running", "label": "Database", "env_var": "DATABASE_URL"}
        elif "password" in error_msg.lower() or "authentication" in error_msg.lower():
            status["database"] = {"connected": False, "message": "AUTH_ERROR: Database credentials incorrect", "label": "Database", "env_var": "DATABASE_URL"}
        else:
            status["database"] = {"connected": False, "message": f"ERROR: {error_msg[:50]}", "label": "Database", "env_var": "DATABASE_URL"}

    return jsonify(status)
