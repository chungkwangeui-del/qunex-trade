"""
Flask Web Application - Qunex Trade (MAINTENANCE MODE)
System upgrade in progress - Kiwoom API integration
"""

from flask import Flask, render_template, jsonify, request
from flask_login import LoginManager, login_required, current_user
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# MAINTENANCE MODE FLAG
MAINTENANCE_MODE = False  # Disabled - show website shell

# Import database and blueprints
try:
    from database import db, User
    from auth import auth, oauth
    from payments import payments
except ImportError:
    # If running from parent directory
    from web.database import db, User
    from web.auth import auth, oauth
    from web.payments import payments

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///qunextrade.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize OAuth with app
oauth.init_app(app)

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

# Register blueprints
app.register_blueprint(auth, url_prefix='/auth')
app.register_blueprint(payments, url_prefix='/payments')

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Create tables
with app.app_context():
    db.create_all()

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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
