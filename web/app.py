"""
Flask Web Application - Qunex Trade
Professional trading tools with real-time market data
"""

from flask import Flask, render_template, jsonify, request, Response
from flask_login import LoginManager, login_required, current_user
from flask_mail import Mail
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
import os
import sys
import json
import threading
import time
import traceback
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from typing import Dict, List, Any, Optional, Union

# Load environment variables
load_dotenv()

# Add parent directory to path for imports (src/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration Constants
RATE_LIMITS = {"daily": 200, "hourly": 50, "auth_per_minute": 10}
NEWS_COLLECTION_HOURS = 24
NEWS_ANALYSIS_LIMIT = 50
CALENDAR_DAYS_AHEAD = 60
AUTO_REFRESH_INTERVAL = 3600  # 1 hour

# Import database first
try:
    from database import db, User, NewsArticle, EconomicEvent
except ImportError:
    from web.database import db, User, NewsArticle, EconomicEvent

# Configure logging
logger = logging.getLogger(__name__)

# Helper Functions for Database Queries
def get_news_articles(limit: int = 50, rating_filter: Optional[int] = None) -> List[Dict]:
    """
    Get news articles from database.

    Args:
        limit: Maximum number of articles to return
        rating_filter: Optional AI rating filter (e.g., 5 for 5-star only)

    Returns:
        List of news articles as dictionaries
    """
    try:
        query = NewsArticle.query.order_by(NewsArticle.published_at.desc())

        if rating_filter:
            query = query.filter(NewsArticle.ai_rating >= rating_filter)

        articles = query.limit(limit).all()
        return [article.to_dict() for article in articles]
    except Exception as e:
        logger.error(f"Error loading news articles: {e}")
        return []

def get_economic_events(days_ahead: int = 60) -> List[Dict]:
    """
    Get economic calendar events from database.

    Args:
        days_ahead: Number of days ahead to fetch events

    Returns:
        List of economic events as dictionaries
    """
    try:
        from datetime import datetime, timedelta
        end_date = datetime.utcnow() + timedelta(days=days_ahead)

        events = EconomicEvent.query.filter(
            EconomicEvent.date >= datetime.utcnow(),
            EconomicEvent.date <= end_date
        ).order_by(EconomicEvent.date.asc()).all()

        return [event.to_dict() for event in events]
    except Exception as e:
        logger.error(f"Error loading economic events: {e}")
        return []

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Database configuration - Use PostgreSQL in production, SQLite in development
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL:
    # Render provides DATABASE_URL starting with postgres://, convert to postgresql+psycopg:// for psycopg3
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql+psycopg://', 1)
    elif DATABASE_URL.startswith('postgresql://'):
        DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+psycopg://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
else:
    # Local development - use SQLite
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///qunextrade.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Database connection pooling (performance optimization)
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 10,  # Number of connections to keep open
    'pool_recycle': 3600,  # Recycle connections after 1 hour
    'pool_pre_ping': True,  # Verify connections before using them
    'max_overflow': 20,  # Max connections beyond pool_size
    'pool_timeout': 30  # Wait 30 seconds for a connection before timeout
}

# Security configuration
app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS only
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JavaScript access
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.config['WTF_CSRF_TIME_LIMIT'] = None  # CSRF token doesn't expire

# Email configuration (Gmail SMTP)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')  # Gmail address
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')  # Gmail app password
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME', 'noreply@qunextrade.com')

# Initialize extensions
db.init_app(app)
mail = Mail(app)
csrf = CSRFProtect(app)

# Exempt email verification endpoints from CSRF protection
csrf.exempt('auth.send_verification_code')
csrf.exempt('auth.verify_code')

# Initialize rate limiter
# CLOUD-NATIVE: Use Redis for distributed rate limiting (Upstash)
REDIS_URL = os.getenv('REDIS_URL', 'memory://')  # Falls back to memory in development
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=[f"{RATE_LIMITS['daily']} per day", f"{RATE_LIMITS['hourly']} per hour"],
    storage_uri=REDIS_URL
)

if REDIS_URL == 'memory://':
    logger.warning("Rate limiting using memory storage (development mode)")
else:
    logger.info(f"Rate limiting using Redis: {REDIS_URL[:20]}...")

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

# Import blueprints
try:
    from auth import auth, oauth
    from payments import payments
    from api_polygon import api_polygon
    from api_watchlist import api_watchlist
except ImportError:
    from web.auth import auth, oauth
    from web.payments import payments
    from web.api_polygon import api_polygon
    from web.api_watchlist import api_watchlist

# Initialize OAuth with app
oauth.init_app(app)

# Register blueprints
app.register_blueprint(auth, url_prefix='/auth')
app.register_blueprint(payments, url_prefix='/payments')
app.register_blueprint(api_polygon)
app.register_blueprint(api_watchlist)

# Apply rate limiting to auth routes (after blueprint registration)
limiter.limit(f"{RATE_LIMITS['auth_per_minute']} per minute")(app.view_functions['auth.login'])
limiter.limit("5 per minute")(app.view_functions['auth.signup'])
limiter.limit("3 per minute")(app.view_functions['auth.forgot_password'])
limiter.limit("5 per minute")(app.view_functions['auth.reset_password'])
limiter.limit("3 per minute")(app.view_functions['auth.send_verification_code'])
limiter.limit(f"{RATE_LIMITS['auth_per_minute']} per minute")(app.view_functions['auth.verify_code'])
limiter.limit(f"{RATE_LIMITS['auth_per_minute']} per minute")(app.view_functions['auth.google_login'])
limiter.limit(f"{RATE_LIMITS['auth_per_minute']} per minute")(app.view_functions['auth.google_callback'])

@login_manager.user_loader
def load_user(user_id: str) -> Optional[User]:
    """
    Load user by ID for Flask-Login.

    Args:
        user_id: User ID as string

    Returns:
        User object if found, None otherwise
    """
    return db.session.get(User, int(user_id))

# Create tables
with app.app_context():
    db.create_all()

# Security headers middleware
@app.after_request
def set_security_headers(response: Response) -> Response:
    """
    Add security headers to all responses.

    Args:
        response: Flask response object

    Returns:
        Response with security headers added
    """
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://accounts.google.com https://cdn.jsdelivr.net https://fonts.googleapis.com https://unpkg.com https://s3.tradingview.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; img-src 'self' data: https:; font-src 'self' data: https://fonts.gstatic.com; connect-src 'self' https://accounts.google.com; frame-src 'self' https://accounts.google.com;"
    return response

# Security and maintenance checks removed - all features active

def load_signals_history():
    """Load signal history - DISABLED (will be re-enabled with Kiwoom API)"""
    # Pandas not installed to reduce dependencies during maintenance
    return []

def load_today_signals():
    """Load today's signals - DISABLED (will be re-enabled with Kiwoom API)"""
    # Pandas not installed to reduce dependencies during maintenance
    return []

def calculate_statistics(df):
    """Calculate statistics"""
    if not df or (hasattr(df, 'empty') and df.empty):
        return {
            'total_signals': 0,
            'success_rate': 0,
            'win_rate': 0,
            'avg_return': 0,
            'total_tracked': 0
        }

    tracked = df[df['status'].isin(['success', 'partial', 'failed'])]

    if tracked.empty:
        return {
            'total_signals': len(df),
            'success_rate': 0,
            'win_rate': 0,
            'avg_return': 0,
            'total_tracked': 0
        }

    stats = {
        'total_signals': len(df),
        'total_tracked': len(tracked),
        'success_count': len(tracked[tracked['status'] == 'success']),
        'partial_count': len(tracked[tracked['status'] == 'partial']),
        'failed_count': len(tracked[tracked['status'] == 'failed']),
        'pending_count': len(df[df['status'] == 'pending']),
        'success_rate': len(tracked[tracked['status'] == 'success']) / len(tracked) * 100 if len(tracked) > 0 else 0,
        'win_rate': len(tracked[tracked['actual_return'] >= 0]) / len(tracked) * 100 if len(tracked) > 0 else 0,
        'avg_return': tracked['actual_return'].mean() if len(tracked) > 0 else 0,
        'median_return': tracked['actual_return'].median() if len(tracked) > 0 else 0,
        'max_return': tracked['actual_return'].max() if len(tracked) > 0 else 0,
        'min_return': tracked['actual_return'].min() if len(tracked) > 0 else 0
    }

    return stats

def filter_signals_by_subscription(signals):
    """Filter signals based on user subscription - DISABLED"""
    # Return empty during maintenance
    return []

@app.route('/')
def index():
    """Main page - Market indices overview from Polygon API"""
    from polygon_service import PolygonService

    # Initialize Polygon service
    polygon = PolygonService()

    # Get market indices
    market_data = []
    try:
        indices = polygon.get_market_indices()
        
        # Format indices as market_data for display
        for symbol, data in indices.items():
            market_data.append({
                'name': data.get('name', symbol),
                'symbol': symbol,
                'price': data.get('price', 0),
                'change': data.get('change_percent', 0),
                'change_amount': data.get('change', 0),
                'volume': data.get('volume', 0),
                'high': data.get('day_high', 0),
                'low': data.get('day_low', 0)
            })

        stats = {
            'total_indices': len(market_data),
            'market_status': 'Active'
        }

    except Exception as e:
        logger.error(f"Error fetching Polygon indices: {e}")
        # Fallback to empty state
        market_data = []
        stats = {
            'total_indices': 0,
            'market_status': 'Unknown'
        }

    return render_template('index.html',
                         market_data=market_data,
                         stats=stats,
                         user=current_user)

@app.route('/about')
def about():
    """About page"""
    return render_template('about.html', user=current_user)

@app.route('/reset-theme')
def reset_theme():
    """Theme reset utility page"""
    return render_template('reset_theme.html')

@app.route('/force-dark')
def force_dark():
    """Force dark mode page - quick fix"""
    return render_template('FORCE_DARK_MODE.html')

@app.route('/terms')
def terms():
    """Terms of Service"""
    return render_template('terms.html')

@app.route('/privacy')
def privacy():
    """Privacy Policy"""
    return render_template('privacy.html')

@app.route('/market')
def market():
    """Market Dashboard - Real-time indices, sectors, and movers"""
    return render_template('market.html', user=current_user)

@app.route('/screener')
def screener():
    """Stock Screener - Filter stocks by criteria"""
    return render_template('screener.html', user=current_user)

@app.route('/watchlist')
@login_required
def watchlist():
    """Personal Watchlist - Track favorite stocks"""
    return render_template('watchlist.html', user=current_user)

@app.route('/calendar')
def calendar():
    """Economic Calendar - Major economic events"""
    return render_template('calendar.html', user=current_user)

@app.route('/stock/<symbol>')
def stock_chart(symbol):
    """Individual Stock Chart Page with Multi-Timeframe Charts"""
    return render_template('stock_chart.html', symbol=symbol.upper(), user=current_user)

@app.route('/news')
def news() -> str:
    """
    Market News & Analysis page (Beta/Developer Only).

    Returns:
        Rendered news template with access control
    """
    has_access = False
    user_tier = 'guest'

    if current_user.is_authenticated:
        user_tier = current_user.subscription_tier
        if user_tier in ['beta', 'developer']:
            has_access = True

    try:
        # Load news from database
        limit = 3 if not has_access else NEWS_ANALYSIS_LIMIT
        news_data = get_news_articles(limit=limit)

        return render_template('news.html',
                             news_data=news_data,
                             user=current_user,
                             has_access=has_access,
                             user_tier=user_tier)
    except Exception as e:
        logger.error(f"Error loading news: {e}", exc_info=True)
        return render_template('news.html',
                             news_data=[],
                             user=current_user,
                             has_access=False,
                             user_tier=user_tier)

@app.route('/api/news/refresh')
def api_refresh_news() -> Dict[str, Any]:
    """
    Refresh news data by collecting and analyzing latest news.

    Returns:
        JSON response with refresh results
    """
    try:
        from src.news_collector import NewsCollector
        from src.news_analyzer import NewsAnalyzer

        logger.info("Starting news refresh")

        collector = NewsCollector()
        news_list = collector.collect_all_news(hours=NEWS_COLLECTION_HOURS)

        logger.info(f"Collected {len(news_list)} news items")

        if not news_list:
            return jsonify({'success': False, 'message': 'No news collected'})

        analyzer = NewsAnalyzer()
        analyzed_news = analyzer.analyze_news_batch(news_list, max_items=NEWS_ANALYSIS_LIMIT)

        logger.info(f"Analyzed {len(analyzed_news)} news items")

        analyzer.save_analysis(analyzed_news)

        high_impact_count = len([n for n in analyzed_news if n.get('importance', 0) >= 4])

        logger.info(f"News refresh complete: {len(analyzed_news)} analyzed ({high_impact_count} high-impact)")

        return jsonify({
            'success': True,
            'message': f'{len(analyzed_news)} news items analyzed ({high_impact_count} high-impact)',
            'total_analyzed': len(analyzed_news),
            'high_impact_count': high_impact_count,
            'data': analyzed_news
        })

    except Exception as e:
        error_msg = str(e)
        logger.error(f"News refresh failed: {error_msg}", exc_info=True)
        return jsonify({'success': False, 'message': error_msg})

@app.route('/api/news/search')
def api_search_news():
    """Search news by stock ticker or keyword"""
    ticker = request.args.get('ticker', '').upper()
    keyword = request.args.get('keyword', '').lower()

    try:
        # Load news data from database
        news_data = get_news_articles(limit=NEWS_ANALYSIS_LIMIT)

        if not news_data:
            return jsonify({'success': False, 'message': 'No news data available'})

        # Filter news
        filtered_news = []
        for news_item in news_data:
            # Filter by ticker
            if ticker:
                affected_stocks = [s.upper() for s in news_item.get('affected_stocks', [])]
                if ticker not in affected_stocks:
                    continue

            # Filter by keyword
            if keyword:
                title = news_item.get('news_title', '').lower()
                summary = news_item.get('impact_summary', '').lower()
                if keyword not in title and keyword not in summary:
                    continue

            filtered_news.append(news_item)

        return jsonify({
            'success': True,
            'count': len(filtered_news),
            'data': filtered_news
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/news/critical')
def api_critical_news():
    """Get critical news (5-star importance only)"""
    try:
        # Load 5-star news from database
        news_data = get_news_articles(limit=NEWS_ANALYSIS_LIMIT, rating_filter=5)

        # Already filtered for 5-star
        critical_news = [n for n in news_data if n.get('importance', 0) == 5]

        return jsonify({
            'success': True,
            'count': len(critical_news),
            'data': critical_news
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/economic-calendar')
def api_economic_calendar():
    """Get economic calendar events"""
    try:
        # Load calendar from database
        events = get_economic_events(days_ahead=CALENDAR_DAYS_AHEAD)

        if not events:
            return jsonify({'success': False, 'message': 'Calendar not available'})

        # Filter for upcoming events only (configured days ahead)
        today = datetime.now()
        future_date = today + timedelta(days=CALENDAR_DAYS_AHEAD)

        upcoming_events = []
        for event in events:
            event_date = datetime.strptime(event['date'], '%Y-%m-%d')
            if today <= event_date <= future_date:
                upcoming_events.append(event)

        # Sort by date
        upcoming_events.sort(key=lambda x: x['date'])

        return jsonify({
            'success': True,
            'count': len(upcoming_events),
            'events': upcoming_events
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/signals/today')
def api_today_signals():
    """Today's signals API (requires authentication for full access)"""
    signals = load_today_signals()

    if signals.empty:
        return jsonify([])

    # Filter by subscription
    filtered_signals = filter_signals_by_subscription(signals)

    # Convert dates to strings for JSON
    filtered_signals['signal_date'] = filtered_signals['signal_date'].dt.strftime('%Y-%m-%d')
    filtered_signals['trade_date'] = filtered_signals['trade_date'].dt.strftime('%Y-%m-%d')

    return jsonify(filtered_signals.to_dict('records'))

@app.route('/api/signals/history')
@login_required
def api_history():
    """Full history API (Premium only)"""
    if not current_user.is_pro():
        return jsonify({'error': 'Premium subscription required'}), 403

    history = load_signals_history()

    if history.empty:
        return jsonify([])

    # Last 100 signals
    history = history.sort_values('signal_date', ascending=False).head(100)

    # Convert to JSON
    history['signal_date'] = history['signal_date'].dt.strftime('%Y-%m-%d')
    history['trade_date'] = history['trade_date'].dt.strftime('%Y-%m-%d')

    return jsonify(history.to_dict('records'))

@app.route('/api/statistics')
def api_statistics():
    """Statistics API"""
    history = load_signals_history()
    stats = calculate_statistics(history)

    # Add 7-day and 30-day stats
    if not history.empty:
        history_7d = history[history['signal_date'] >= datetime.now() - timedelta(days=7)]
        history_30d = history[history['signal_date'] >= datetime.now() - timedelta(days=30)]

        stats['last_7_days'] = calculate_statistics(history_7d)
        stats['last_30_days'] = calculate_statistics(history_30d)

    return jsonify(stats)

# Sector map moved to /api/market/sector-map (Polygon.io)

@app.route('/api/stock/<symbol>/chart')
def api_stock_chart(symbol):
    """Get multi-timeframe chart data for a stock"""
    try:
        from polygon_service import PolygonService
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ml'))
        from ai_score_system import AIScoreModel, FeatureEngineer

        timeframe = request.args.get('timeframe', '1D')  # Default to daily
        polygon = PolygonService()

        # Map timeframes to Polygon API parameters
        timeframe_map = {
            '1': ('minute', 1),      # 1 minute
            '5': ('minute', 5),      # 5 minutes
            '15': ('minute', 15),    # 15 minutes
            '60': ('minute', 60),    # 1 hour
            '240': ('minute', 240),  # 4 hours
            '1D': ('day', 1),        # Daily
            '1M': ('month', 1)       # Monthly
        }

        unit, multiplier = timeframe_map.get(timeframe, ('day', 1))

        # Calculate date range based on timeframe
        from datetime import datetime, timedelta
        end_date = datetime.now()

        if timeframe in ['1', '5', '15']:
            start_date = end_date - timedelta(days=7)  # 1 week for minute data
        elif timeframe in ['60', '240']:
            start_date = end_date - timedelta(days=30)  # 1 month for hourly
        elif timeframe == '1D':
            start_date = end_date - timedelta(days=365)  # 1 year for daily
        else:  # Monthly
            start_date = end_date - timedelta(days=365*5)  # 5 years for monthly

        # Fetch data from Polygon
        endpoint = f"/v2/aggs/ticker/{symbol.upper()}/range/{multiplier}/{unit}/{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}"
        params = {'adjusted': 'true', 'sort': 'asc', 'limit': 5000}

        data = polygon._make_request(endpoint, params)

        if not data or 'results' not in data:
            return jsonify({'error': 'No data available'}), 404

        # Format data for chart
        candles = []
        for bar in data['results']:
            candles.append({
                'time': bar['t'] // 1000,  # Convert to seconds
                'open': bar['o'],
                'high': bar['h'],
                'low': bar['l'],
                'close': bar['c'],
                'volume': bar['v']
            })

        return jsonify({
            'symbol': symbol.upper(),
            'timeframe': timeframe,
            'candles': candles
        })

    except Exception as e:
        logger.error(f"Error fetching chart data for {symbol}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stock/<symbol>/ai-score')
def api_stock_ai_score(symbol):
    """Get Qunex AI Score for a stock"""
    try:
        from polygon_service import PolygonService
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ml'))
        from ai_score_system import AIScoreModel, FeatureEngineer

        polygon = PolygonService()

        # Load trained model
        model_path = os.path.join(os.path.dirname(__file__), '..', 'ml', 'models')
        model = AIScoreModel(model_dir=model_path)
        if not model.load('ai_score_model.pkl'):
            return jsonify({'error': 'AI model not available'}), 500

        # Get recent price data (need ~200 days for technical indicators)
        from datetime import datetime, timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=400)

        price_data = model._fetch_historical_prices(
            symbol.upper(),
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d'),
            polygon
        )

        if price_data is None or len(price_data) < 200:
            return jsonify({'error': 'Insufficient data for AI score'}), 404

        # Calculate features
        features = FeatureEngineer.calculate_technical_features(price_data)

        if not features:
            return jsonify({'error': 'Could not calculate features'}), 500

        # Predict AI score
        score = model.predict_score(features)

        # Determine rating
        if score >= 75:
            rating = "Strong Buy"
            color = "#00ff88"
        elif score >= 60:
            rating = "Buy"
            color = "#00d9ff"
        elif score >= 40:
            rating = "Hold"
            color = "#ffd700"
        elif score >= 25:
            rating = "Sell"
            color = "#ff8c00"
        else:
            rating = "Strong Sell"
            color = "#ff006e"

        return jsonify({
            'symbol': symbol.upper(),
            'score': score,
            'rating': rating,
            'color': color,
            'features': {
                'rsi': round(features.get('rsi_14', 0), 2),
                'macd': round(features.get('macd', 0), 4),
                'price_to_ma50': round(features.get('price_to_ma50', 0) * 100, 2)
            }
        })

    except Exception as e:
        logger.error(f"Error calculating AI score for {symbol}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stock/<symbol>/news')
def api_stock_news(symbol):
    """Get recent news for a stock"""
    try:
        from polygon_service import PolygonService
        polygon = PolygonService()

        # Fetch news from Polygon
        endpoint = f"/v2/reference/news"
        params = {
            'ticker': symbol.upper(),
            'limit': 10,
            'sort': 'published_utc',
            'order': 'desc'
        }

        data = polygon._make_request(endpoint, params)

        if not data or 'results' not in data:
            return jsonify({'articles': []})

        articles = []
        for article in data['results']:
            articles.append({
                'title': article.get('title', ''),
                'description': article.get('description', ''),
                'url': article.get('article_url', ''),
                'published': article.get('published_utc', ''),
                'publisher': article.get('publisher', {}).get('name', 'Unknown'),
                'image': article.get('image_url', '')
            })

        return jsonify({'articles': articles})

    except Exception as e:
        logger.error(f"Error fetching news for {symbol}: {e}")
        return jsonify({'articles': []}), 500

# Auto-refresh news every hour in background
def auto_refresh_news() -> None:
    """
    Background thread to automatically refresh news data.

    Runs continuously with configured interval between refreshes.
    """
    while True:
        try:
            time.sleep(AUTO_REFRESH_INTERVAL)
            logger.info("Starting auto-refresh news collection")

            from src.news_collector import NewsCollector
            from src.news_analyzer import NewsAnalyzer

            collector = NewsCollector()
            news_list = collector.collect_all_news(hours=NEWS_COLLECTION_HOURS)

            if news_list:
                analyzer = NewsAnalyzer()
                analyzed_news = analyzer.analyze_news_batch(news_list, max_items=NEWS_ANALYSIS_LIMIT)
                analyzer.save_analysis(analyzed_news)

                high_impact = len([n for n in analyzed_news if n.get('importance', 0) >= 4])
                logger.info(f"Auto-refresh complete: {len(analyzed_news)} news analyzed ({high_impact} high-impact)")
            else:
                logger.warning("Auto-refresh: No news collected")

        except Exception as e:
            logger.error(f"Auto-refresh error: {e}", exc_info=True)

# CLOUD-NATIVE: Background tasks moved to Render Cron Jobs
# Auto-refresh is now handled by /scripts/refresh_data_cron.py
# This thread is disabled in production to support stateless deployments
if os.getenv('ENABLE_BACKGROUND_THREAD', 'false').lower() == 'true':
    news_thread = threading.Thread(target=auto_refresh_news, daemon=True)
    news_thread.start()
    logger.info(f"Auto-refresh news thread started (refreshes every {AUTO_REFRESH_INTERVAL//3600} hour(s))")
else:
    logger.info("Background thread disabled (using Render Cron Jobs instead)")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
