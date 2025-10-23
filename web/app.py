"""
Flask Web Application - Qunex Trade (MAINTENANCE MODE)
System upgrade in progress - Kiwoom API integration
"""

from flask import Flask, render_template, jsonify, request
from flask_login import LoginManager, login_required, current_user
from flask_mail import Mail
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# MAINTENANCE MODE FLAG
MAINTENANCE_MODE = False  # Disabled - show website shell

# Import database first
try:
    from database import db, User
except ImportError:
    from web.database import db, User

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
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

# Import blueprints
try:
    from auth import auth, oauth
    from payments import payments
except ImportError:
    from web.auth import auth, oauth
    from web.payments import payments

# Initialize OAuth with app
oauth.init_app(app)

# Register blueprints
app.register_blueprint(auth, url_prefix='/auth')
app.register_blueprint(payments, url_prefix='/payments')

# Apply rate limiting to auth routes (after blueprint registration)
limiter.limit("10 per minute")(app.view_functions['auth.login'])
limiter.limit("5 per minute")(app.view_functions['auth.signup'])
limiter.limit("3 per minute")(app.view_functions['auth.forgot_password'])
limiter.limit("5 per minute")(app.view_functions['auth.reset_password'])
limiter.limit("3 per minute")(app.view_functions['auth.send_verification_code'])
limiter.limit("10 per minute")(app.view_functions['auth.verify_code'])
limiter.limit("10 per minute")(app.view_functions['auth.google_login'])
limiter.limit("10 per minute")(app.view_functions['auth.google_callback'])

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Create tables
with app.app_context():
    db.create_all()

# Security headers middleware
@app.after_request
def set_security_headers(response):
    """Add security headers to all responses"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://accounts.google.com https://cdn.jsdelivr.net https://fonts.googleapis.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; img-src 'self' data: https:; font-src 'self' https://fonts.gstatic.com; connect-src 'self' https://accounts.google.com; frame-src 'self' https://accounts.google.com;"
    return response

# Maintenance mode middleware
@app.before_request
def check_maintenance():
    if MAINTENANCE_MODE and not request.path.startswith('/static'):
        return render_template('maintenance.html')

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

@app.route('/terms')
def terms():
    """Terms of Service"""
    return render_template('terms.html')

@app.route('/privacy')
def privacy():
    """Privacy Policy"""
    return render_template('privacy.html')

@app.route('/news')
def news():
    """Market News & Analysis (Beta/Developer Only)"""
    import json
    import os
    import sys

    # Add parent directory to path for imports
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # Check user access level
    # Tier hierarchy: Free < Pro < Premium < Beta Tester < Developer
    # News Section is in BETA - only Beta Testers and Developers can access
    has_access = False
    user_tier = 'guest'

    if current_user.is_authenticated:
        user_tier = current_user.subscription_tier
        # Grant access to Beta Testers and Developers only
        # Pro and Premium users will see "Coming Soon" overlay
        if user_tier in ['beta', 'developer']:
            has_access = True

    try:
        # Load analyzed news from JSON file
        news_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'news_analysis.json')

        if os.path.exists(news_file):
            with open(news_file, 'r', encoding='utf-8') as f:
                news_data = json.load(f)
        else:
            news_data = []

        # If no access, only show preview (first 3 items, blurred)
        preview_data = news_data[:3] if not has_access else news_data

        return render_template('news.html',
                             news_data=preview_data,
                             user=current_user,
                             has_access=has_access,
                             user_tier=user_tier)
    except Exception as e:
        print(f"Error loading news: {e}")
        return render_template('news.html',
                             news_data=[],
                             user=current_user,
                             has_access=False,
                             user_tier=user_tier)

@app.route('/api/news/refresh')
def api_refresh_news():
    """Refresh news data (collects and analyzes latest news - focus on government/Fed news)"""
    import sys
    import os

    # Add parent directory to path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    try:
        from src.news_collector import NewsCollector
        from src.news_analyzer import NewsAnalyzer

        # Collect news (prioritized by government/Fed news)
        collector = NewsCollector()
        news_list = collector.collect_all_news(hours=24)

        if not news_list:
            return jsonify({'success': False, 'message': 'No news collected'})

        # Analyze news (increased to 50 items)
        analyzer = NewsAnalyzer()
        analyzed_news = analyzer.analyze_news_batch(news_list, max_items=50)

        # Save analysis
        analyzer.save_analysis(analyzed_news)

        # Count high-impact news (4-5 stars)
        high_impact_count = len([n for n in analyzed_news if n.get('importance', 0) >= 4])

        return jsonify({
            'success': True,
            'message': f'{len(analyzed_news)} news items analyzed ({high_impact_count} high-impact)',
            'total_analyzed': len(analyzed_news),
            'high_impact_count': high_impact_count,
            'data': analyzed_news
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/news/search')
def api_search_news():
    """Search news by stock ticker or keyword"""
    import json
    import os

    ticker = request.args.get('ticker', '').upper()
    keyword = request.args.get('keyword', '').lower()

    try:
        # Load analyzed news from JSON file
        news_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'news_analysis.json')

        if not os.path.exists(news_file):
            return jsonify({'success': False, 'message': 'No news data available'})

        with open(news_file, 'r', encoding='utf-8') as f:
            news_data = json.load(f)

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
    import json
    import os

    try:
        # Load analyzed news from JSON file
        news_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'news_analysis.json')

        if not os.path.exists(news_file):
            return jsonify({'success': False, 'message': 'No news data available'})

        with open(news_file, 'r', encoding='utf-8') as f:
            news_data = json.load(f)

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
    import json
    import os
    from datetime import datetime, timedelta

    try:
        # Load calendar from JSON file
        calendar_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'economic_calendar.json')

        if not os.path.exists(calendar_file):
            return jsonify({'success': False, 'message': 'Calendar not available'})

        with open(calendar_file, 'r', encoding='utf-8') as f:
            events = json.load(f)

        # Filter for upcoming events only (within next 60 days)
        today = datetime.now()
        future_date = today + timedelta(days=60)

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

@app.route('/api/sector-map')
def api_sector_map():
    """Get sector map data with individual stocks"""
    import random

    # Top stocks by sector with realistic market caps (in billions)
    stock_data = [
        # Technology
        {'ticker': 'AAPL', 'name': 'Apple', 'sector': 'Technology', 'marketCap': 3000, 'change': random.uniform(-3, 4)},
        {'ticker': 'MSFT', 'name': 'Microsoft', 'sector': 'Technology', 'marketCap': 2800, 'change': random.uniform(-2, 3)},
        {'ticker': 'NVDA', 'name': 'NVIDIA', 'sector': 'Technology', 'marketCap': 1200, 'change': random.uniform(-4, 6)},
        {'ticker': 'AVGO', 'name': 'Broadcom', 'sector': 'Technology', 'marketCap': 700, 'change': random.uniform(-2, 3)},
        {'ticker': 'ORCL', 'name': 'Oracle', 'sector': 'Technology', 'marketCap': 350, 'change': random.uniform(-2, 2)},
        {'ticker': 'CRM', 'name': 'Salesforce', 'sector': 'Technology', 'marketCap': 280, 'change': random.uniform(-2, 3)},
        {'ticker': 'ADBE', 'name': 'Adobe', 'sector': 'Technology', 'marketCap': 250, 'change': random.uniform(-2, 3)},
        {'ticker': 'AMD', 'name': 'AMD', 'sector': 'Technology', 'marketCap': 240, 'change': random.uniform(-3, 4)},

        # Healthcare
        {'ticker': 'LLY', 'name': 'Eli Lilly', 'sector': 'Healthcare', 'marketCap': 750, 'change': random.uniform(-2, 3)},
        {'ticker': 'UNH', 'name': 'UnitedHealth', 'sector': 'Healthcare', 'marketCap': 500, 'change': random.uniform(-1, 2)},
        {'ticker': 'JNJ', 'name': 'Johnson & Johnson', 'sector': 'Healthcare', 'marketCap': 380, 'change': random.uniform(-1, 2)},
        {'ticker': 'ABBV', 'name': 'AbbVie', 'sector': 'Healthcare', 'marketCap': 320, 'change': random.uniform(-2, 2)},
        {'ticker': 'MRK', 'name': 'Merck', 'sector': 'Healthcare', 'marketCap': 280, 'change': random.uniform(-1, 2)},

        # Financials
        {'ticker': 'BRK-B', 'name': 'Berkshire', 'sector': 'Financials', 'marketCap': 900, 'change': random.uniform(-1, 2)},
        {'ticker': 'JPM', 'name': 'JPMorgan', 'sector': 'Financials', 'marketCap': 580, 'change': random.uniform(-2, 2)},
        {'ticker': 'V', 'name': 'Visa', 'sector': 'Financials', 'marketCap': 550, 'change': random.uniform(-1, 2)},
        {'ticker': 'MA', 'name': 'Mastercard', 'sector': 'Financials', 'marketCap': 420, 'change': random.uniform(-1, 2)},
        {'ticker': 'BAC', 'name': 'Bank of America', 'sector': 'Financials', 'marketCap': 320, 'change': random.uniform(-2, 2)},

        # Consumer Discretionary
        {'ticker': 'AMZN', 'name': 'Amazon', 'sector': 'Consumer Disc.', 'marketCap': 1900, 'change': random.uniform(-2, 3)},
        {'ticker': 'TSLA', 'name': 'Tesla', 'sector': 'Consumer Disc.', 'marketCap': 800, 'change': random.uniform(-5, 6)},
        {'ticker': 'HD', 'name': 'Home Depot', 'sector': 'Consumer Disc.', 'marketCap': 380, 'change': random.uniform(-1, 2)},
        {'ticker': 'MCD', 'name': 'McDonald\'s', 'sector': 'Consumer Disc.', 'marketCap': 210, 'change': random.uniform(-1, 2)},
        {'ticker': 'NKE', 'name': 'Nike', 'sector': 'Consumer Disc.', 'marketCap': 180, 'change': random.uniform(-2, 2)},

        # Communication
        {'ticker': 'GOOGL', 'name': 'Alphabet', 'sector': 'Communication', 'marketCap': 1950, 'change': random.uniform(-2, 3)},
        {'ticker': 'META', 'name': 'Meta', 'sector': 'Communication', 'marketCap': 1300, 'change': random.uniform(-3, 4)},
        {'ticker': 'NFLX', 'name': 'Netflix', 'sector': 'Communication', 'marketCap': 280, 'change': random.uniform(-2, 3)},
        {'ticker': 'DIS', 'name': 'Disney', 'sector': 'Communication', 'marketCap': 200, 'change': random.uniform(-2, 2)},

        # Industrials
        {'ticker': 'GE', 'name': 'GE Aerospace', 'sector': 'Industrials', 'marketCap': 180, 'change': random.uniform(-2, 3)},
        {'ticker': 'CAT', 'name': 'Caterpillar', 'sector': 'Industrials', 'marketCap': 170, 'change': random.uniform(-2, 2)},
        {'ticker': 'RTX', 'name': 'RTX Corp', 'sector': 'Industrials', 'marketCap': 150, 'change': random.uniform(-1, 2)},
        {'ticker': 'UPS', 'name': 'UPS', 'sector': 'Industrials', 'marketCap': 120, 'change': random.uniform(-2, 2)},

        # Consumer Staples
        {'ticker': 'WMT', 'name': 'Walmart', 'sector': 'Consumer Staples', 'marketCap': 550, 'change': random.uniform(-1, 2)},
        {'ticker': 'PG', 'name': 'Procter & Gamble', 'sector': 'Consumer Staples', 'marketCap': 390, 'change': random.uniform(-1, 1.5)},
        {'ticker': 'KO', 'name': 'Coca-Cola', 'sector': 'Consumer Staples', 'marketCap': 280, 'change': random.uniform(-1, 1.5)},
        {'ticker': 'PEP', 'name': 'PepsiCo', 'sector': 'Consumer Staples', 'marketCap': 230, 'change': random.uniform(-1, 1.5)},

        # Energy
        {'ticker': 'XOM', 'name': 'Exxon Mobil', 'sector': 'Energy', 'marketCap': 480, 'change': random.uniform(-3, 3)},
        {'ticker': 'CVX', 'name': 'Chevron', 'sector': 'Energy', 'marketCap': 280, 'change': random.uniform(-3, 3)},
        {'ticker': 'COP', 'name': 'ConocoPhillips', 'sector': 'Energy', 'marketCap': 140, 'change': random.uniform(-3, 3)},

        # Utilities
        {'ticker': 'NEE', 'name': 'NextEra Energy', 'sector': 'Utilities', 'marketCap': 150, 'change': random.uniform(-1, 1.5)},
        {'ticker': 'DUK', 'name': 'Duke Energy', 'sector': 'Utilities', 'marketCap': 80, 'change': random.uniform(-1, 1)},
        {'ticker': 'SO', 'name': 'Southern Co', 'sector': 'Utilities', 'marketCap': 90, 'change': random.uniform(-1, 1)},

        # Real Estate
        {'ticker': 'PLD', 'name': 'Prologis', 'sector': 'Real Estate', 'marketCap': 120, 'change': random.uniform(-2, 2)},
        {'ticker': 'AMT', 'name': 'American Tower', 'sector': 'Real Estate', 'marketCap': 100, 'change': random.uniform(-1, 2)},
        {'ticker': 'CCI', 'name': 'Crown Castle', 'sector': 'Real Estate', 'marketCap': 70, 'change': random.uniform(-1, 2)},

        # Materials
        {'ticker': 'LIN', 'name': 'Linde', 'sector': 'Materials', 'marketCap': 210, 'change': random.uniform(-2, 2)},
        {'ticker': 'APD', 'name': 'Air Products', 'sector': 'Materials', 'marketCap': 70, 'change': random.uniform(-2, 2)},
        {'ticker': 'ECL', 'name': 'Ecolab', 'sector': 'Materials', 'marketCap': 60, 'change': random.uniform(-1, 2)},
    ]

    return jsonify({'stocks': stock_data})

# Market data API routes removed

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
