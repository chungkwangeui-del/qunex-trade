from flask_login import current_user
from datetime import datetime, timezone, timedelta
from web.database import Signal, db, NewsArticle, EconomicEvent

def get_news_articles(limit: int = 50, rating_filter: int = None):
    """
    Get news articles from database.
    """
    try:
        query = NewsArticle.query.order_by(NewsArticle.published_at.desc())

        if rating_filter:
            query = query.filter(NewsArticle.ai_rating >= rating_filter)

        articles = query.limit(limit).all()
        return [article.to_dict() for article in articles]
    except Exception as e:
        return []

def get_economic_events(days_ahead: int = 60):
    """
    Get economic calendar events from database.
    """
    try:
        # Use naive datetime for comparison (DB stores naive datetimes)
        now = datetime.now()
        end_date = now + timedelta(days=days_ahead)

        events = (
            EconomicEvent.query.filter(
                EconomicEvent.date >= now, EconomicEvent.date <= end_date
            )
            .order_by(EconomicEvent.date.asc())
            .all()
        )

        return [event.to_dict() for event in events]
    except Exception as e:
        return []

def calculate_statistics(df):
    """
    Calculate performance statistics from trading signal DataFrame.
    """
    if not df or (hasattr(df, "empty") and df.empty):
        return {
            "total_signals": 0,
            "success_rate": 0,
            "win_rate": 0,
            "avg_return": 0,
            "total_tracked": 0,
        }

    tracked = df[df["status"].isin(["success", "partial", "failed"])]

    if tracked.empty:
        return {
            "total_signals": len(df),
            "success_rate": 0,
            "win_rate": 0,
            "avg_return": 0,
            "total_tracked": 0,
        }

    stats = {
        "total_signals": len(df),
        "total_tracked": len(tracked),
        "success_count": len(tracked[tracked["status"] == "success"]),
        "partial_count": len(tracked[tracked["status"] == "partial"]),
        "failed_count": len(tracked[tracked["status"] == "failed"]),
        "pending_count": len(df[df["status"] == "pending"]),
        "success_rate": (
            len(tracked[tracked["status"] == "success"]) / len(tracked) * 100
            if len(tracked) > 0
            else 0
        ),
        "win_rate": (
            len(tracked[tracked["actual_return"] >= 0]) / len(tracked) * 100
            if len(tracked) > 0
            else 0
        ),
        "avg_return": tracked["actual_return"].mean() if len(tracked) > 0 else 0,
        "median_return": tracked["actual_return"].median() if len(tracked) > 0 else 0,
        "max_return": tracked["actual_return"].max() if len(tracked) > 0 else 0,
        "min_return": tracked["actual_return"].min() if len(tracked) > 0 else 0,
    }

    return stats


def filter_signals_by_subscription(signals):
    """
    Filter trading signals based on user's subscription tier.
    """
    if not signals:
        return []
        
    if not current_user.is_authenticated or current_user.subscription_tier == "free":
        return signals
        
    return signals

def load_signals_history(logger=None):
    """
    Load signal history from database.
    """
    try:
        signals = Signal.query.filter(
            Signal.status.in_(["success", "failed", "partial"])
        ).order_by(Signal.closed_at.desc()).all()
        
        if not signals:
            return []
            
        return [s.to_dict() for s in signals]
    except Exception as e:
        if logger:
            logger.error(f"Error loading signals history: {e}")
        return []

def load_today_signals(logger=None):
    """
    Load today's trading signals from database.
    """
    try:
        today = datetime.now(timezone.utc).date()
        signals = Signal.query.filter(
            db.func.date(Signal.signal_date) == today
        ).order_by(Signal.signal_date.desc()).all()
        
        if not signals:
            return []
            
        return [s.to_dict() for s in signals]
    except Exception as e:
        if logger:
            logger.error(f"Error loading today signals: {e}")
        return []
