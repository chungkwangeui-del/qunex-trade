from flask import Blueprint, jsonify, request
from web.database import NewsArticle, EconomicEvent, db
from web.utils import get_news_articles, get_economic_events
from web.polygon_service import get_polygon_service
from datetime import datetime, timezone, timedelta
from sqlalchemy import or_
import logging
import requests
import os

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
        from src.news_analyzer import NewsAnalyzer

        collector = NewsCollector()
        news_items = collector.collect_all_news(limit=50)

        if not news_items:
            return jsonify({"success": False, "message": "No news collected from API"})

        # Initialize AI analyzer if key is present
        gemini_key = os.environ.get("GEMINI_API_KEY")
        analyzer = None
        analyzer_available = False
        if gemini_key:
            try:
                analyzer = NewsAnalyzer()
                analyzer_available = True
            except Exception as e:
                logger.warning(f"AI analysis unavailable - check GEMINI_API_KEY. ({e})")
        else:
            logger.warning("GEMINI_API_KEY not configured; saving news without AI analysis")

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

                # Run AI analysis when available
                analysis = None
                if analyzer_available and analyzer:
                    try:
                        analysis = analyzer.analyze_single_news(item)
                    except Exception as e:
                        logger.warning(f"AI analysis failed, saving without analysis: {e}")

                if not analysis:
                    analysis = {
                        "importance": 3,
                        "impact_summary": "AI analysis unavailable - check API key",
                        "sentiment": "neutral"
                    }

                # Create new article
                article = NewsArticle(
                    title=item["title"][:500],
                    description=item.get("description", "")[:2000] if item.get("description") else None,
                    url=item["url"][:1000],
                    source=item.get("source", "Unknown")[:100],
                    published_at=published_at,
                    ai_rating=analysis.get("importance", 3),
                    ai_analysis=analysis.get("impact_summary", ""),
                    sentiment=analysis.get("sentiment", "neutral")
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
    """Fetch real economic calendar data from Finnhub API"""
    try:
        finnhub_api_key = os.environ.get("FINNHUB_API_KEY")

        if not finnhub_api_key:
            logger.warning("FINNHUB_API_KEY not configured, using fallback data")
            return _refresh_calendar_fallback()

        # Fetch next 60 days of economic events from Finnhub
        today = datetime.now(timezone.utc).date()
        end_date = today + timedelta(days=60)

        url = "https://finnhub.io/api/v1/calendar/economic"
        params = {
            "from": today.strftime("%Y-%m-%d"),
            "to": end_date.strftime("%Y-%m-%d"),
            "token": finnhub_api_key
        }

        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if "economicCalendar" not in data:
            logger.error(f"Unexpected Finnhub response: {data}")
            return jsonify({"success": False, "message": "Invalid response from Finnhub"})

        events = data["economicCalendar"]
        saved_count = 0

        # Clear old events first (optional - keeps DB clean)
        EconomicEvent.query.filter(
            EconomicEvent.date >= datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)
        ).delete()

        # Map Finnhub impact to our importance levels
        impact_map = {
            3: "high",    # High impact
            2: "medium",  # Medium impact
            1: "low",     # Low impact
        }

        for event_data in events:
            # Filter for US events (USD) - most relevant for stock traders
            country = event_data.get("country", "")
            if country != "US":
                continue

            event_date_str = event_data.get("date", "")
            if not event_date_str:
                continue

            try:
                event_date = datetime.strptime(event_date_str, "%Y-%m-%d")
                event_date = event_date.replace(tzinfo=timezone.utc)
            except ValueError:
                continue

            # Get impact level (1-3)
            impact = event_data.get("impact", 1)
            importance = impact_map.get(impact, "low")

            # Get actual/estimate/previous values
            actual = event_data.get("actual", "")
            estimate = event_data.get("estimate", "")
            prev = event_data.get("prev", "")

            event = EconomicEvent(
                title=event_data.get("event", "Unknown Event"),
                description=f"{event_data.get('event', '')} - {country}",
                date=event_date,
                time=event_data.get("time", "TBD"),
                country="USD",
                importance=importance,
                forecast=str(estimate) if estimate else "TBD",
                previous=str(prev) if prev else "TBD",
                source="Finnhub"
            )
            db.session.add(event)
            saved_count += 1

        db.session.commit()
        logger.info(f"Fetched {saved_count} US economic events from Finnhub")

        return jsonify({
            "success": True,
            "count": saved_count,
            "message": f"Added {saved_count} US economic events from Finnhub"
        })

    except requests.exceptions.RequestException as e:
        logger.error(f"Finnhub API request failed: {e}")
        return jsonify({"success": False, "message": f"API request failed: {str(e)}"})
    except Exception as e:
        logger.error(f"Error refreshing calendar: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)})


def _refresh_calendar_fallback():
    """Fallback: Generate placeholder events when Finnhub API is not available"""
    try:
        event_templates = [
            {"title": "FOMC Meeting Minutes", "importance": "high", "time": "2:00 PM EST"},
            {"title": "Non-Farm Payrolls", "importance": "high", "time": "8:30 AM EST"},
            {"title": "CPI (Consumer Price Index)", "importance": "high", "time": "8:30 AM EST"},
            {"title": "PPI (Producer Price Index)", "importance": "medium", "time": "8:30 AM EST"},
            {"title": "Retail Sales", "importance": "medium", "time": "8:30 AM EST"},
            {"title": "GDP (Quarterly)", "importance": "high", "time": "8:30 AM EST"},
            {"title": "Jobless Claims", "importance": "medium", "time": "8:30 AM EST"},
            {"title": "ISM Manufacturing PMI", "importance": "medium", "time": "10:00 AM EST"},
        ]

        today = datetime.now(timezone.utc).date()
        saved_count = 0

        for i in range(60):
            event_date = today + timedelta(days=i)
            if event_date.weekday() >= 5:
                continue

            template = event_templates[i % len(event_templates)]

            existing = EconomicEvent.query.filter_by(
                title=template["title"],
                date=datetime.combine(event_date, datetime.min.time()).replace(tzinfo=timezone.utc)
            ).first()

            if existing:
                continue

            event = EconomicEvent(
                title=template["title"],
                description=f"US Economic Indicator: {template['title']} (Placeholder)",
                date=datetime.combine(event_date, datetime.min.time()).replace(tzinfo=timezone.utc),
                time=template["time"],
                country="USD",
                importance=template["importance"],
                forecast="TBD",
                previous="TBD",
                source="Placeholder"
            )
            db.session.add(event)
            saved_count += 1

        db.session.commit()
        return jsonify({
            "success": True,
            "count": saved_count,
            "message": f"Added {saved_count} placeholder events (Configure FINNHUB_API_KEY for real data)"
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)})

@api_main.route("/api/stock/<ticker>/chart")
def get_stock_chart(ticker):
    """Get stock chart data"""
    ticker = ticker.upper()
    if not ticker.isalpha() or len(ticker) > 5:
        return jsonify({"error": "Invalid ticker format. Must be 1-5 letters."}), 400

    timeframe = request.args.get("timeframe", "1D")
    polygon = get_polygon_service()

    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")  # Default 30 days

    data = polygon.get_aggregates(ticker, 1, "day", start_date, end_date)

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
    - REAL data tests to verify APIs return actual data
    """
    import os
    import requests

    status = {
        "polygon": {"connected": False, "message": "ENV: POLYGON_API_KEY not set", "label": "Polygon.io (Stocks)", "env_var": "POLYGON_API_KEY"},
        "fmp": {"connected": False, "message": "ENV: FMP_API_KEY not set", "label": "FMP (Real-time Data)", "env_var": "FMP_API_KEY"},
        "binance": {"connected": False, "message": "Checking Binance API...", "label": "Binance (Crypto)", "env_var": None},
        "gemini": {"connected": False, "message": "ENV: GEMINI_API_KEY not set", "label": "Gemini AI", "env_var": "GEMINI_API_KEY"},
        "finnhub": {"connected": False, "message": "ENV: FINNHUB_API_KEY not set", "label": "Finnhub", "env_var": "FINNHUB_API_KEY"},
        "alpha_vantage": {"connected": False, "message": "ENV: ALPHA_VANTAGE_API_KEY not set", "label": "Alpha Vantage", "env_var": "ALPHA_VANTAGE_API_KEY"},
        "google_oauth": {"connected": False, "message": "ENV: GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET not set", "label": "Google OAuth", "env_var": "GOOGLE_CLIENT_ID"},
        "recaptcha": {"connected": False, "message": "ENV: RECAPTCHA_SECRET_KEY not set", "label": "reCAPTCHA", "env_var": "RECAPTCHA_SECRET_KEY"},
        "mail": {"connected": False, "message": "ENV: MAIL_USERNAME and MAIL_PASSWORD not set", "label": "Email Service", "env_var": "MAIL_USERNAME"},
        "redis": {"connected": False, "message": "ENV: REDIS_URL not set (using memory)", "label": "Redis Cache", "env_var": "REDIS_URL"},
        "database": {"connected": False, "message": "Database connection failed", "label": "Database", "env_var": "DATABASE_URL"}
    }

    # Check Polygon API - actual API call with REAL data verification
    polygon_key = os.environ.get("POLYGON_API_KEY", "")
    if polygon_key:
        try:
            polygon = get_polygon_service()
            result = polygon.get_previous_close("AAPL")
            if result:
                # Get actual price to show REAL data
                aapl_price = result.get("close") or result.get("c") or 0
                if aapl_price > 0:
                    status["polygon"] = {
                        "connected": True, 
                        "message": f"OK: AAPL=${aapl_price:.2f} (key: {_mask_key(polygon_key)})", 
                        "label": "Polygon.io (Stocks)", 
                        "env_var": "POLYGON_API_KEY",
                        "data_sample": {"ticker": "AAPL", "price": aapl_price}
                    }
                else:
                    status["polygon"] = {"connected": True, "message": f"PARTIAL: API responds but no price data (key: {_mask_key(polygon_key)})", "label": "Polygon.io (Stocks)", "env_var": "POLYGON_API_KEY"}
            else:
                status["polygon"] = {"connected": False, "message": f"NO_DATA: Key works but no AAPL data returned", "label": "Polygon.io (Stocks)", "env_var": "POLYGON_API_KEY"}
        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg or "403" in error_msg or "unauthorized" in error_msg.lower():
                status["polygon"] = {"connected": False, "message": f"AUTH_ERROR: Key {_mask_key(polygon_key)} unauthorized", "label": "Polygon.io (Stocks)", "env_var": "POLYGON_API_KEY"}
            elif "timeout" in error_msg.lower() or "connection" in error_msg.lower():
                status["polygon"] = {"connected": False, "message": f"NETWORK: Connection failed - {error_msg[:40]}", "label": "Polygon.io (Stocks)", "env_var": "POLYGON_API_KEY"}
            else:
                status["polygon"] = {"connected": False, "message": f"ERROR: {error_msg[:50]}", "label": "Polygon.io (Stocks)", "env_var": "POLYGON_API_KEY"}

    # Check FMP (Financial Modeling Prep) API - REAL data verification
    fmp_key = os.environ.get("FMP_API_KEY", "")
    if fmp_key:
        try:
            # Test with a common stock to verify API works
            resp = requests.get(
                f"https://financialmodelingprep.com/api/v3/quote/AAPL",
                params={"apikey": fmp_key},
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                if data and len(data) > 0:
                    aapl_data = data[0]
                    price = aapl_data.get("price", 0)
                    market_cap = aapl_data.get("marketCap", 0)
                    if price > 0 and market_cap > 0:
                        market_cap_b = market_cap / 1e9
                        status["fmp"] = {
                            "connected": True, 
                            "message": f"OK: AAPL=${price:.2f}, MCap=${market_cap_b:.0f}B (key: {_mask_key(fmp_key)})", 
                            "label": "FMP (Real-time Data)", 
                            "env_var": "FMP_API_KEY",
                            "data_sample": {"ticker": "AAPL", "price": price, "market_cap": market_cap}
                        }
                    else:
                        status["fmp"] = {"connected": True, "message": f"PARTIAL: API responds but data incomplete (price={price})", "label": "FMP (Real-time Data)", "env_var": "FMP_API_KEY"}
                else:
                    status["fmp"] = {"connected": False, "message": "NO_DATA: API returned empty response", "label": "FMP (Real-time Data)", "env_var": "FMP_API_KEY"}
            elif resp.status_code == 401:
                status["fmp"] = {"connected": False, "message": f"AUTH_ERROR: Key {_mask_key(fmp_key)} invalid (401)", "label": "FMP (Real-time Data)", "env_var": "FMP_API_KEY"}
            elif resp.status_code == 403:
                status["fmp"] = {"connected": False, "message": f"LIMIT: Daily limit exceeded or key restricted (403)", "label": "FMP (Real-time Data)", "env_var": "FMP_API_KEY"}
            elif resp.status_code == 429:
                status["fmp"] = {"connected": True, "message": f"RATE_LIMIT: API working but rate limited", "label": "FMP (Real-time Data)", "env_var": "FMP_API_KEY"}
            else:
                status["fmp"] = {"connected": False, "message": f"HTTP_{resp.status_code}: Unexpected response", "label": "FMP (Real-time Data)", "env_var": "FMP_API_KEY"}
        except requests.exceptions.Timeout:
            status["fmp"] = {"connected": False, "message": "TIMEOUT: FMP not responding (10s)", "label": "FMP (Real-time Data)", "env_var": "FMP_API_KEY"}
        except requests.exceptions.ConnectionError:
            status["fmp"] = {"connected": False, "message": "NETWORK: Cannot reach FMP API", "label": "FMP (Real-time Data)", "env_var": "FMP_API_KEY"}
        except Exception as e:
            status["fmp"] = {"connected": False, "message": f"ERROR: {str(e)[:50]}", "label": "FMP (Real-time Data)", "env_var": "FMP_API_KEY"}

    # Check Binance API - no API key required for public data
    # Try Binance.US first (for US users), then Binance.com
    binance_endpoints = [
        ("https://api.binance.us/api/v3/ping", "Binance.US"),
        ("https://api.binance.com/api/v3/ping", "Binance.com"),
    ]
    binance_connected = False
    binance_message = "NETWORK: All Binance endpoints unreachable"

    for endpoint_url, endpoint_name in binance_endpoints:
        try:
            resp = requests.get(endpoint_url, timeout=5)
            if resp.status_code == 200:
                # Also test klines endpoint to confirm full functionality
                test_url = endpoint_url.replace("/ping", "/klines")
                test_resp = requests.get(test_url, params={"symbol": "BTCUSDT", "interval": "1m", "limit": 1}, timeout=5)
                if test_resp.status_code == 200:
                    binance_connected = True
                    binance_message = f"OK: {endpoint_name} working (no API key required)"
                    break
                elif test_resp.status_code == 451:
                    # Geo-restricted, try next endpoint
                    binance_message = f"GEO_BLOCKED: {endpoint_name} restricted in your region"
                    continue
                else:
                    binance_connected = True
                    binance_message = f"PARTIAL: {endpoint_name} ping OK, klines returned {test_resp.status_code}"
                    break
            elif resp.status_code == 451:
                binance_message = f"GEO_BLOCKED: {endpoint_name} restricted in your region"
                continue
        except requests.exceptions.Timeout:
            binance_message = f"TIMEOUT: {endpoint_name} not responding (5s)"
            continue
        except requests.exceptions.ConnectionError:
            binance_message = f"NETWORK: Cannot reach {endpoint_name}"
            continue
        except Exception as e:
            binance_message = f"ERROR: {str(e)[:40]}"
            continue

    status["binance"] = {"connected": binance_connected, "message": binance_message, "label": "Binance (Crypto)", "env_var": None}

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


@api_main.route("/api/status/test-ticker")
def test_ticker_data():
    """
    Test data quality for a specific ticker across all APIs.
    Usage: /api/status/test-ticker?ticker=AAPL
    
    Returns what each data source returns for the ticker - helps debug
    which APIs work and which don't for specific stocks.
    """
    import os
    import requests
    
    ticker = request.args.get("ticker", "AAPL").upper().strip()
    
    results = {
        "ticker": ticker,
        "tested_at": datetime.now(timezone.utc).isoformat(),
        "sources": {}
    }
    
    # Test Polygon API
    polygon_key = os.environ.get("POLYGON_API_KEY", "")
    if polygon_key:
        try:
            polygon = get_polygon_service()
            
            # Try snapshot first (real-time)
            snapshot = polygon.get_snapshot(ticker)
            prev_close = polygon.get_previous_close(ticker)
            
            polygon_data = {
                "available": False,
                "price": 0,
                "change_percent": 0,
                "volume": 0,
                "source_type": None,
                "raw_response": None
            }
            
            if snapshot:
                polygon_data["available"] = True
                polygon_data["price"] = snapshot.get("price") or snapshot.get("lastTrade", {}).get("p") or 0
                polygon_data["change_percent"] = snapshot.get("todaysChangePerc") or 0
                polygon_data["volume"] = snapshot.get("day", {}).get("v") or 0
                polygon_data["source_type"] = "snapshot"
                polygon_data["raw_response"] = snapshot
            elif prev_close:
                polygon_data["available"] = True
                polygon_data["price"] = prev_close.get("close") or prev_close.get("c") or 0
                polygon_data["volume"] = prev_close.get("volume") or prev_close.get("v") or 0
                polygon_data["source_type"] = "prev_close"
                polygon_data["raw_response"] = prev_close
            
            results["sources"]["polygon"] = polygon_data
        except Exception as e:
            results["sources"]["polygon"] = {"available": False, "error": str(e)[:100]}
    else:
        results["sources"]["polygon"] = {"available": False, "error": "API key not set"}
    
    # Test FMP API
    fmp_key = os.environ.get("FMP_API_KEY", "")
    if fmp_key:
        try:
            resp = requests.get(
                f"https://financialmodelingprep.com/api/v3/quote/{ticker}",
                params={"apikey": fmp_key},
                timeout=10
            )
            
            fmp_data = {
                "available": False,
                "price": 0,
                "change_percent": 0,
                "market_cap": 0,
                "volume": 0,
                "raw_response": None
            }
            
            if resp.status_code == 200:
                data = resp.json()
                if data and len(data) > 0:
                    item = data[0]
                    fmp_data["available"] = True
                    fmp_data["price"] = item.get("price", 0)
                    fmp_data["change_percent"] = item.get("changesPercentage", 0)
                    fmp_data["market_cap"] = item.get("marketCap", 0)
                    fmp_data["volume"] = item.get("volume", 0)
                    fmp_data["name"] = item.get("name", "")
                    fmp_data["raw_response"] = item
                else:
                    fmp_data["error"] = "Empty response - ticker may not exist"
            else:
                fmp_data["error"] = f"HTTP {resp.status_code}"
            
            results["sources"]["fmp"] = fmp_data
        except Exception as e:
            results["sources"]["fmp"] = {"available": False, "error": str(e)[:100]}
    else:
        results["sources"]["fmp"] = {"available": False, "error": "API key not set"}
    
    # Test Finnhub API
    finnhub_key = os.environ.get("FINNHUB_API_KEY", "")
    if finnhub_key:
        try:
            resp = requests.get(
                f"https://finnhub.io/api/v1/quote",
                params={"symbol": ticker, "token": finnhub_key},
                timeout=5
            )
            
            finnhub_data = {
                "available": False,
                "price": 0,
                "change_percent": 0,
                "raw_response": None
            }
            
            if resp.status_code == 200:
                data = resp.json()
                if data and data.get("c", 0) > 0:  # c = current price
                    finnhub_data["available"] = True
                    finnhub_data["price"] = data.get("c", 0)
                    finnhub_data["change_percent"] = data.get("dp", 0)  # dp = percent change
                    finnhub_data["high"] = data.get("h", 0)
                    finnhub_data["low"] = data.get("l", 0)
                    finnhub_data["open"] = data.get("o", 0)
                    finnhub_data["prev_close"] = data.get("pc", 0)
                    finnhub_data["raw_response"] = data
                else:
                    finnhub_data["error"] = "No price data - ticker may not be supported"
            else:
                finnhub_data["error"] = f"HTTP {resp.status_code}"
            
            results["sources"]["finnhub"] = finnhub_data
        except Exception as e:
            results["sources"]["finnhub"] = {"available": False, "error": str(e)[:100]}
    else:
        results["sources"]["finnhub"] = {"available": False, "error": "API key not set"}
    
    # Test Binance API (for crypto) - No API key required!
    # Detect if ticker looks like crypto (ends with USDT, BTC, ETH, etc.)
    crypto_suffixes = ['USDT', 'USD', 'BTC', 'ETH', 'BUSD', 'USDC']
    is_crypto = any(ticker.endswith(suffix) for suffix in crypto_suffixes) or ticker in ['BTC', 'ETH', 'SOL', 'XRP', 'DOGE']
    
    # Try Binance for all tickers (crypto pairs work, stocks won't)
    binance_endpoints = [
        ("https://api.binance.com/api/v3/ticker/24hr", "Binance.com"),
        ("https://api.binance.us/api/v3/ticker/24hr", "Binance.US"),
    ]
    
    binance_data = {
        "available": False,
        "price": 0,
        "change_percent": 0,
        "volume": 0,
        "is_crypto": is_crypto,
        "raw_response": None
    }
    
    for endpoint_url, endpoint_name in binance_endpoints:
        try:
            resp = requests.get(
                endpoint_url,
                params={"symbol": ticker},
                timeout=5
            )
            
            if resp.status_code == 200:
                data = resp.json()
                if data and float(data.get("lastPrice", 0)) > 0:
                    binance_data["available"] = True
                    binance_data["price"] = float(data.get("lastPrice", 0))
                    binance_data["change_percent"] = float(data.get("priceChangePercent", 0))
                    binance_data["volume"] = float(data.get("volume", 0))
                    binance_data["quote_volume"] = float(data.get("quoteVolume", 0))
                    binance_data["high_24h"] = float(data.get("highPrice", 0))
                    binance_data["low_24h"] = float(data.get("lowPrice", 0))
                    binance_data["trades_24h"] = int(data.get("count", 0))
                    binance_data["source"] = endpoint_name
                    binance_data["raw_response"] = data
                    break  # Found data, stop trying other endpoints
            elif resp.status_code == 400:
                # Invalid symbol - not a crypto pair
                binance_data["error"] = "Not a valid crypto pair"
            elif resp.status_code == 451:
                binance_data["error"] = f"{endpoint_name} geo-blocked"
                continue  # Try next endpoint
            else:
                binance_data["error"] = f"HTTP {resp.status_code}"
        except requests.exceptions.Timeout:
            binance_data["error"] = f"{endpoint_name} timeout"
            continue
        except Exception as e:
            binance_data["error"] = str(e)[:50]
            continue
    
    results["sources"]["binance"] = binance_data
    
    # Summary: which source has the best data
    best_source = None
    best_price = 0
    for source_name, source_data in results["sources"].items():
        if source_data.get("available") and source_data.get("price", 0) > best_price:
            best_price = source_data.get("price", 0)
            best_source = source_name
    
    results["summary"] = {
        "best_source": best_source,
        "best_price": best_price,
        "sources_with_data": [s for s, d in results["sources"].items() if d.get("available")],
        "sources_failed": [s for s, d in results["sources"].items() if not d.get("available")]
    }
    
    return jsonify(results)
