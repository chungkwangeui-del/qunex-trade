from flask import Blueprint, jsonify, request
from web.database import NewsArticle, EconomicEvent, db
from web.utils import get_news_articles, get_economic_events
from web.polygon_service import get_polygon_service
from datetime import datetime, timezone
from sqlalchemy import or_

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

@api_main.route("/api/economic-calendar")
def get_calendar():
    """Get economic calendar events"""
    events = get_economic_events(days_ahead=60)
    return jsonify({"success": True, "events": events})

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
