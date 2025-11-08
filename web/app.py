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
    from database import db, User
except ImportError:
    from web.database import db, User

# Configure logging
logger = logging.getLogger(__name__)

# Helper Functions
def load_json_data(filename: str, default: Optional[Any] = None) -> Any:
    """
    Load JSON data from data directory.

    Args:
        filename: Name of the JSON file to load
        default: Default value to return if file not found or error occurs

    Returns:
        Loaded JSON data or default value
    """
    try:
        file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', filename)
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading {filename}: {e}")
    return default or []

def save_json_data(filename: str, data: Any) -> bool:
    """
    Save JSON data to data directory.

    Args:
        filename: Name of the JSON file to save
        data: Data to save as JSON

    Returns:
        True if successful, False otherwise
    """
    try:
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
        os.makedirs(data_dir, exist_ok=True)
        file_path = os.path.join(data_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Error saving {filename}: {e}")
        return False

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
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=[f"{RATE_LIMITS['daily']} per day", f"{RATE_LIMITS['hourly']} per hour"],
    storage_uri="memory://"
)

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
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://accounts.google.com https://cdn.jsdelivr.net https://fonts.googleapis.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; img-src 'self' data: https:; font-src 'self' https://fonts.gstatic.com; connect-src 'self' https://accounts.google.com; frame-src 'self' https://accounts.google.com;"
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
    """Main page - Empty state until Kiwoom API integration"""
    # Empty signals for now
    today_signals = []
    filtered_signals = []
    history = []

    # Empty statistics
    stats = {
        'total_signals': 0,
        'success_rate': 0,
        'win_rate': 0,
        'avg_return': 0,
        'total_tracked': 0
    }
    stats_30d = stats

    # No upgrade banner needed
    show_upgrade_banner = False

    return render_template('index.html',
                         today_signals=[],
                         total_signals=0,
                         stats=stats,
                         stats_30d=stats_30d,
                         show_upgrade_banner=False,
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
        news_data = load_json_data('news_analysis.json', [])
        preview_data = news_data[:3] if not has_access else news_data

        return render_template('news.html',
                             news_data=preview_data,
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
        # Load news data using helper
        news_data = load_json_data('news_analysis.json', [])

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
        # Load news data using helper
        news_data = load_json_data('news_analysis.json', [])

        # Filter for 5-star news only
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
        # Load calendar using helper
        events = load_json_data('economic_calendar.json', [])

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

# Start background news refresh thread
news_thread = threading.Thread(target=auto_refresh_news, daemon=True)
news_thread.start()
logger.info(f"Auto-refresh news thread started (refreshes every {AUTO_REFRESH_INTERVAL//3600} hour(s))")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
