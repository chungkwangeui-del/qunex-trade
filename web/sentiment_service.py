"""
Social Sentiment Analysis Service

Analyzes sentiment from various sources:
- News articles
- Basic keyword analysis
- Volume/price sentiment indicators

For full social media sentiment (Reddit, Twitter),
specialized APIs are needed (not included here for API key requirements).
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
import logging
import re
from datetime import timedelta
from datetime import timezone
from typing import List
from typing import Optional

logger = logging.getLogger(__name__)

class SentimentAnalyzer:
    """
    Analyze sentiment from text and market data.
    """

    # Sentiment word lists
    BULLISH_WORDS = [
        "bullish", "buy", "long", "moon", "rocket", "breakout", "surge", "rally",
        "soar", "jump", "spike", "explode", "boom", "strong", "beat", "upgrade",
        "growth", "profit", "gain", "winner", "outperform", "undervalued",
        "accumulate", "positive", "optimistic", "momentum", "upside", "catalyst",
        "squeeze", "rip", "pump", "calls", "bullrun", "ath", "green"
    ]

    BEARISH_WORDS = [
        "bearish", "sell", "short", "crash", "dump", "plunge", "tank", "drop",
        "fall", "sink", "collapse", "weak", "miss", "downgrade", "loss",
        "loser", "underperform", "overvalued", "avoid", "negative", "pessimistic",
        "downside", "warning", "risk", "puts", "red", "dead", "rekt", "bag"
    ]

    NEUTRAL_WORDS = [
        "hold", "neutral", "wait", "watch", "sideways", "consolidate", "range",
        "stable", "flat", "unchanged", "maintain", "steady"
    ]

    def __init__(self):
        # Compile regex patterns for efficiency
        self.bullish_pattern = re.compile(
            r'\b(' + '|'.join(self.BULLISH_WORDS) + r')\b',
            re.IGNORECASE
        )
        self.bearish_pattern = re.compile(
            r'\b(' + '|'.join(self.BEARISH_WORDS) + r')\b',
            re.IGNORECASE
        )
        self.neutral_pattern = re.compile(
            r'\b(' + '|'.join(self.NEUTRAL_WORDS) + r')\b',
            re.IGNORECASE
        )

    def analyze_text(self, text: str) -> Dict:
        """
        Analyze sentiment of a text string.

        Returns:
            score: 0-100 (0=very bearish, 50=neutral, 100=very bullish)
            sentiment: 'bullish', 'bearish', 'neutral'
            confidence: 0-100
        """
        if not text:
            return {"score": 50, "sentiment": "neutral", "confidence": 0}

        text = text.lower()

        bullish_matches = len(self.bullish_pattern.findall(text))
        bearish_matches = len(self.bearish_pattern.findall(text))
        neutral_matches = len(self.neutral_pattern.findall(text))

        total_matches = bullish_matches + bearish_matches + neutral_matches

        if total_matches == 0:
            return {"score": 50, "sentiment": "neutral", "confidence": 20}

        # Calculate weighted score
        bullish_weight = bullish_matches / total_matches
        bearish_weight = bearish_matches / total_matches

        # Score: 0-100 where 50 is neutral
        score = 50 + (bullish_weight * 50) - (bearish_weight * 50)
        score = max(0, min(100, score))

        # Determine sentiment
        if score >= 60:
            sentiment = "bullish"
        elif score <= 40:
            sentiment = "bearish"
        else:
            sentiment = "neutral"

        # Confidence based on total matches
        confidence = min(100, total_matches * 10 + 30)

        return {
            "score": round(score, 1),
            "sentiment": sentiment,
            "confidence": confidence,
            "bullish_words": bullish_matches,
            "bearish_words": bearish_matches,
            "neutral_words": neutral_matches,
        }

    def analyze_news_batch(self, articles: List[Dict]) -> Dict:
        """
        Analyze sentiment from a batch of news articles.

        Args:
            articles: List of dicts with 'title' and optional 'description'

        Returns:
            Aggregated sentiment analysis
        """
        if not articles:
            return {
                "overall_score": 50,
                "overall_sentiment": "neutral",
                "articles_analyzed": 0,
            }

        scores = []
        sentiments = {"bullish": 0, "bearish": 0, "neutral": 0}

        for article in articles:
            text = article.get("title", "") + " " + article.get("description", "")
            analysis = self.analyze_text(text)

            scores.append(analysis["score"])
            sentiments[analysis["sentiment"]] += 1

        avg_score = sum(scores) / len(scores) if scores else 50

        # Determine overall sentiment
        max_sentiment = max(sentiments.items(), key=lambda x: x[1])
        overall_sentiment = max_sentiment[0]

        return {
            "overall_score": round(avg_score, 1),
            "overall_sentiment": overall_sentiment,
            "articles_analyzed": len(articles),
            "sentiment_breakdown": {
                "bullish": sentiments["bullish"],
                "bearish": sentiments["bearish"],
                "neutral": sentiments["neutral"],
            },
            "bullish_pct": round((sentiments["bullish"] / len(articles)) * 100, 1),
            "bearish_pct": round((sentiments["bearish"] / len(articles)) * 100, 1),
            "neutral_pct": round((sentiments["neutral"] / len(articles)) * 100, 1),
        }

def calculate_price_sentiment(current_price: float, sma_20: float, sma_50: float,
                              rsi: float, volume_ratio: float) -> Dict:
    """
    Calculate sentiment based on technical indicators.

    Returns technical sentiment score 0-100.
    """
    score = 50  # Start neutral
    factors = []

    # Price vs SMAs
    if current_price > sma_20:
        score += 10
        factors.append("Above SMA 20")
    else:
        score -= 10
        factors.append("Below SMA 20")

    if current_price > sma_50:
        score += 10
        factors.append("Above SMA 50")
    else:
        score -= 10
        factors.append("Below SMA 50")

    # RSI
    if rsi:
        if rsi > 70:
            score -= 10
            factors.append("RSI overbought")
        elif rsi < 30:
            score += 10
            factors.append("RSI oversold")
        elif 50 < rsi < 70:
            score += 5
            factors.append("RSI bullish")
        elif 30 < rsi < 50:
            score -= 5
            factors.append("RSI bearish")

    # Volume
    if volume_ratio:
        if volume_ratio > 2:
            score += 5
            factors.append("High volume")
        elif volume_ratio < 0.5:
            score -= 5
            factors.append("Low volume")

    score = max(0, min(100, score))

    if score >= 60:
        sentiment = "bullish"
    elif score <= 40:
        sentiment = "bearish"
    else:
        sentiment = "neutral"

    return {
        "score": round(score, 1),
        "sentiment": sentiment,
        "factors": factors,
    }

def get_fear_greed_proxy() -> Dict:
    """
    Calculate a Fear & Greed index proxy using available data.

    This is a simplified version - real Fear & Greed uses:
    - VIX
    - Put/Call ratio
    - Market breadth
    - Safe haven demand
    - Junk bond demand
    - Market momentum
    """
    try:
        import yfinance as yf

        # Get VIX data
        vix = yf.Ticker("^VIX")
        vix_history = vix.history(period="5d")

        if vix_history.empty:
            return {"error": "Unable to fetch VIX data"}

        current_vix = vix_history["Close"].iloc[-1]

        # VIX-based fear/greed (inverse relationship)
        # VIX < 15: Extreme Greed
        # VIX 15-20: Greed
        # VIX 20-25: Neutral
        # VIX 25-30: Fear
        # VIX > 30: Extreme Fear

        if current_vix < 15:
            score = 85
            level = "Extreme Greed"
        elif current_vix < 20:
            score = 70
            level = "Greed"
        elif current_vix < 25:
            score = 50
            level = "Neutral"
        elif current_vix < 30:
            score = 30
            level = "Fear"
        else:
            score = 15
            level = "Extreme Fear"

        # Get SPY for market momentum
        spy = yf.Ticker("SPY")
        spy_history = spy.history(period="1mo")

        if not spy_history.empty:
            spy_change = (
                (spy_history["Close"].iloc[-1] - spy_history["Close"].iloc[0])
                / spy_history["Close"].iloc[0] * 100
            )

            # Adjust score based on momentum
            if spy_change > 5:
                score = min(100, score + 10)
            elif spy_change < -5:
                score = max(0, score - 10)

        return {
            "score": round(score, 1),
            "level": level,
            "vix": round(current_vix, 2),
            "description": _get_fear_greed_description(level),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Error calculating fear/greed: {e}")
        return {"error": str(e)}

def _get_fear_greed_description(level: str) -> str:
    """Get description for fear/greed level."""
    descriptions = {
        "Extreme Greed": "Investors are extremely bullish. Be cautious of overextension.",
        "Greed": "Investors are optimistic. Market may be overbought.",
        "Neutral": "Market sentiment is balanced.",
        "Fear": "Investors are cautious. Potential buying opportunity.",
        "Extreme Fear": "Investors are very fearful. Historically a good buying opportunity.",
    }
    return descriptions.get(level, "")

def analyze_ticker_sentiment(ticker: str) -> Dict:
    """
    Get comprehensive sentiment analysis for a ticker.

    Combines:
    - News sentiment
    - Technical sentiment
    - Overall score
    """
    try:
        from web.polygon_service import get_polygon_service
        from web.database import NewsArticle
    except ImportError:
        return {"error": "Required modules not available"}

    polygon = get_polygon_service()
    analyzer = SentimentAnalyzer()

    result = {
        "ticker": ticker,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Get technical data
    try:
        technicals = polygon.get_technical_indicators(ticker, days=50)
        quote = polygon.get_stock_quote(ticker)

        if technicals and quote:
            current_price = quote.get("price", 0)
            tech_sentiment = calculate_price_sentiment(
                current_price=current_price,
                sma_20=technicals.get("sma_20", current_price),
                sma_50=technicals.get("sma_50", current_price),
                rsi=technicals.get("rsi_14"),
                volume_ratio=1.0  # Would need volume data
            )
            result["technical_sentiment"] = tech_sentiment
    except Exception as e:
        logger.error(f"Error getting technical sentiment: {e}")
        result["technical_sentiment"] = {"error": str(e)}

    # Get news sentiment
    try:
        # Check for news in database
        recent_news = NewsArticle.query.filter(
            NewsArticle.title.contains(ticker)
        ).order_by(NewsArticle.published_at.desc()).limit(10).all()

        if recent_news:
            articles = [{"title": n.title, "description": n.description} for n in recent_news]
            news_sentiment = analyzer.analyze_news_batch(articles)
            result["news_sentiment"] = news_sentiment
        else:
            result["news_sentiment"] = {"message": "No recent news found"}
    except Exception as e:
        logger.error(f"Error getting news sentiment: {e}")
        result["news_sentiment"] = {"error": str(e)}

    # Calculate overall sentiment
    scores = []

    if "technical_sentiment" in result and "score" in result.get("technical_sentiment", {}):
        scores.append(result["technical_sentiment"]["score"])

    if "news_sentiment" in result and "overall_score" in result.get("news_sentiment", {}):
        scores.append(result["news_sentiment"]["overall_score"])

    if scores:
        overall_score = sum(scores) / len(scores)

        if overall_score >= 60:
            overall_sentiment = "bullish"
        elif overall_score <= 40:
            overall_sentiment = "bearish"
        else:
            overall_sentiment = "neutral"

        result["overall"] = {
            "score": round(overall_score, 1),
            "sentiment": overall_sentiment,
            "components_analyzed": len(scores),
        }

    return result
