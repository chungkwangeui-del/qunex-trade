from typing import List, Optional, Dict, Any
from sqlalchemy import or_, desc
from web.database import db, User, Watchlist, NewsArticle, EconomicEvent, AIScore, Transaction, PaperAccount, PaperTrade, TradeJournal

class DatabaseService:
    @staticmethod
    def get_news_articles(limit: int = 50, rating_filter: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get news articles from database with optional rating filter"""
        query = NewsArticle.query

        if rating_filter:
            query = query.filter(NewsArticle.ai_rating >= rating_filter)

        articles = query.order_by(desc(NewsArticle.published_at)).limit(limit).all()
        return [a.to_dict() for a in articles]

    @staticmethod
    def get_economic_events(days_ahead: int = 30) -> List[Dict[str, Any]]:
        """Get economic events for the specified number of days ahead"""
        from datetime import datetime, timezone, timedelta

        today = datetime.now(timezone.utc).date()
        end_date = today + timedelta(days=days_ahead)

        events = EconomicEvent.query.filter(
            EconomicEvent.date >= datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc),
            EconomicEvent.date <= datetime.combine(end_date, datetime.max.time()).replace(tzinfo=timezone.utc)
        ).order_by(EconomicEvent.date.asc()).all()

        return [e.to_dict() for e in events]

    @staticmethod
    def get_user_watchlist(user_id: int) -> List[Dict[str, Any]]:
        """Get watchlist for a specific user"""
        watchlist = Watchlist.query.filter_by(user_id=user_id).all()
        return [
            {
                "ticker": item.ticker,
                "company_name": item.company_name,
                "added_at": item.added_at.isoformat() if item.added_at else None,
                "notes": item.notes,
                "alert_price_above": item.alert_price_above,
                "alert_price_below": item.alert_price_below
            } for item in watchlist
        ]

    @staticmethod
    def get_ai_score(ticker: str) -> Optional[Dict[str, Any]]:
        """Get AI score for a specific ticker"""
        score = AIScore.query.filter_by(ticker=ticker.upper()).first()
        return score.to_dict() if score else None

    @staticmethod
    def get_user_portfolio_value(user_id: int) -> float:
        """Calculate current total value of a user's portfolio"""
        # Note: This is a placeholder as it requires real-time prices
        # In a real implementation, this would fetch current prices and multiply by shares
        return 0.0
