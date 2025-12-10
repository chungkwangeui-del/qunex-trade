from datetime import datetime, timedelta
from typing import List, Dict
from web.database import NewsArticle, EconomicEvent

def get_news_articles(limit: int = 50, rating_filter: int = None) -> List[Dict]:
    """Fetch latest news articles, optionally filtered by AI rating."""
    try:
        query = NewsArticle.query.order_by(NewsArticle.published_at.desc())

        if rating_filter:
            query = query.filter(NewsArticle.ai_rating >= rating_filter)

        articles = query.limit(limit).all()
        return [article.to_dict() for article in articles]
    except Exception:
        return []

def get_economic_events(days_ahead: int = 60) -> List[Dict]:
    """Fetch upcoming economic events within the given horizon."""
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
    except Exception:
        return []
