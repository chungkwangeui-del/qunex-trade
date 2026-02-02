"""
Sentiment Analysis API

Provides sentiment data for stocks based on news, technicals, and market indicators.
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required
from datetime import datetime
import logging

try:
    from web.sentiment_service import (
        SentimentAnalyzer,
        analyze_ticker_sentiment,
        get_fear_greed_proxy,
        calculate_price_sentiment
    )
    from web.polygon_service import get_polygon_service
    from web.extensions import cache
except ImportError:
    from sentiment_service import (
        SentimentAnalyzer,
        analyze_ticker_sentiment,
        get_fear_greed_proxy,
        calculate_price_sentiment
    )
    from polygon_service import get_polygon_service
    from extensions import cache

logger = logging.getLogger(__name__)

api_sentiment = Blueprint("api_sentiment", __name__)


@api_sentiment.route("/api/sentiment/<ticker>")
@login_required
def get_ticker_sentiment(ticker):
    """
    Get comprehensive sentiment analysis for a stock.

    Combines:
    - News sentiment
    - Technical indicators sentiment
    - Overall score
    """
    ticker = ticker.upper()

    result = analyze_ticker_sentiment(ticker)

    return jsonify(result)


@api_sentiment.route("/api/sentiment/fear-greed")
@login_required
@cache.cached(timeout=300, key_prefix="fear_greed")
def get_fear_greed():
    """
    Get Fear & Greed Index proxy.

    Based on VIX and market momentum.
    """
    result = get_fear_greed_proxy()
    return jsonify(result)


@api_sentiment.route("/api/sentiment/analyze-text", methods=["POST"])
@login_required
def analyze_text():
    """
    Analyze sentiment of provided text.

    Request JSON:
        text: str - Text to analyze
    """
    data = request.get_json() or {}
    text = data.get("text", "")

    if not text:
        return jsonify({"error": "Text is required"}), 400

    analyzer = SentimentAnalyzer()
    result = analyzer.analyze_text(text)

    return jsonify(result)


@api_sentiment.route("/api/sentiment/market-mood")
@login_required
@cache.cached(timeout=300, key_prefix="market_mood")
def get_market_mood():
    """
    Get overall market mood based on multiple indicators.
    """
    polygon = get_polygon_service()

    # Get sector performance
    sectors = polygon.get_sector_performance()

    # Get market indices
    indices = polygon.get_market_indices()

    # Count positive/negative sectors
    positive_sectors = sum(1 for s in sectors if s.get("change_percent", 0) > 0)
    negative_sectors = len(sectors) - positive_sectors

    # Count positive/negative indices
    positive_indices = sum(1 for k, v in indices.items() if v.get("change_percent", 0) > 0)

    # Get fear/greed
    fear_greed = get_fear_greed_proxy()

    # Calculate mood score
    sector_score = (positive_sectors / len(sectors) * 100) if sectors else 50
    index_score = (positive_indices / len(indices) * 100) if indices else 50
    fg_score = fear_greed.get("score", 50) if "score" in fear_greed else 50

    overall_score = (sector_score + index_score + fg_score) / 3

    if overall_score >= 65:
        mood = "Bullish"
        emoji = "🚀"
    elif overall_score >= 55:
        mood = "Slightly Bullish"
        emoji = "📈"
    elif overall_score >= 45:
        mood = "Neutral"
        emoji = "➡️"
    elif overall_score >= 35:
        mood = "Slightly Bearish"
        emoji = "📉"
    else:
        mood = "Bearish"
        emoji = "🔻"

    return jsonify({
        "mood": mood,
        "emoji": emoji,
        "score": round(overall_score, 1),
        "components": {
            "sector_score": round(sector_score, 1),
            "index_score": round(index_score, 1),
            "fear_greed_score": round(fg_score, 1),
        },
        "details": {
            "positive_sectors": positive_sectors,
            "negative_sectors": negative_sectors,
            "positive_indices": positive_indices,
            "total_indices": len(indices),
            "fear_greed": fear_greed.get("level", "Unknown"),
        },
        "timestamp": datetime.now().isoformat(),
    })


@api_sentiment.route("/api/sentiment/trending")
@login_required
@cache.cached(timeout=600, key_prefix="trending_sentiment")
def get_trending_sentiment():
    """
    Get sentiment for trending/popular stocks.
    """
    # Popular stocks to analyze
    tickers = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
        "AMD", "NFLX", "DIS", "BA", "JPM", "V", "CRM", "COIN"
    ]

    polygon = get_polygon_service()
    results = []

    for ticker in tickers:
        try:
            # Get technical data
            technicals = polygon.get_technical_indicators(ticker, days=30)
            quote = polygon.get_stock_quote(ticker)

            if not technicals or not quote:
                continue

            current_price = quote.get("price", 0)

            tech_sentiment = calculate_price_sentiment(
                current_price=current_price,
                sma_20=technicals.get("sma_20", current_price),
                sma_50=technicals.get("sma_50", current_price),
                rsi=technicals.get("rsi_14"),
                volume_ratio=1.0
            )

            results.append({
                "ticker": ticker,
                "price": current_price,
                "sentiment": tech_sentiment["sentiment"],
                "score": tech_sentiment["score"],
                "rsi": technicals.get("rsi_14"),
                "factors": tech_sentiment.get("factors", []),
            })

        except Exception as e:
            logger.debug(f"Error analyzing {ticker}: {e}")
            continue

    # Sort by score (most bullish first)
    results.sort(key=lambda x: x["score"], reverse=True)

    # Summary
    bullish = sum(1 for r in results if r["sentiment"] == "bullish")
    bearish = sum(1 for r in results if r["sentiment"] == "bearish")
    neutral = len(results) - bullish - bearish

    return jsonify({
        "stocks": results,
        "summary": {
            "bullish": bullish,
            "bearish": bearish,
            "neutral": neutral,
            "most_bullish": results[0]["ticker"] if results else None,
            "most_bearish": results[-1]["ticker"] if results else None,
        },
        "timestamp": datetime.now().isoformat(),
    })


@api_sentiment.route("/api/sentiment/watchlist")
@login_required
def get_watchlist_sentiment():
    """
    Get sentiment analysis for user's watchlist stocks.
    """
    try:
        from web.database import Watchlist
    except ImportError:
        return jsonify({"error": "Database not available"}), 500

    from flask_login import current_user

    watchlist = Watchlist.query.filter_by(user_id=current_user.id).all()

    if not watchlist:
        return jsonify({
            "message": "No stocks in watchlist",
            "stocks": [],
        })

    polygon = get_polygon_service()
    results = []

    for item in watchlist[:20]:  # Max 20
        ticker = item.ticker

        try:
            technicals = polygon.get_technical_indicators(ticker, days=30)
            quote = polygon.get_stock_quote(ticker)

            if not technicals or not quote:
                continue

            current_price = quote.get("price", 0)

            tech_sentiment = calculate_price_sentiment(
                current_price=current_price,
                sma_20=technicals.get("sma_20", current_price),
                sma_50=technicals.get("sma_50", current_price),
                rsi=technicals.get("rsi_14"),
                volume_ratio=1.0
            )

            results.append({
                "ticker": ticker,
                "company_name": item.company_name,
                "price": current_price,
                "sentiment": tech_sentiment["sentiment"],
                "score": tech_sentiment["score"],
                "rsi": technicals.get("rsi_14"),
            })

        except Exception as e:
            logger.debug(f"Error analyzing {ticker}: {e}")
            continue

    # Sort by score
    results.sort(key=lambda x: x["score"], reverse=True)

    return jsonify({
        "stocks": results,
        "total": len(results),
        "timestamp": datetime.now().isoformat(),
    })

