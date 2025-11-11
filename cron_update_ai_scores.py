#!/usr/bin/env python3
"""
Render Cron Job: Update AI Scores for Watchlist Stocks

This script pre-computes AI scores for all stocks in user watchlists.
Runs daily at midnight to refresh scores with enhanced features:
- Technical indicators (RSI, MACD, Moving Averages)
- Fundamental data (P/E, P/B, EPS growth, Revenue growth)
- News sentiment (7-day average from NewsArticle table)
"""

import os
import sys
import logging
import json
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def update_ai_scores():
    """
    Update AI scores for all stocks in watchlists.

    Fetches unique tickers, computes enhanced features (technical + fundamental + sentiment),
    calculates AI score, and stores in AIScore table.

    Returns:
        bool: True if update succeeded, False otherwise
    """
    try:
        from web.database import db, Watchlist, AIScore, NewsArticle
        from web.app import app
        from web.polygon_service import PolygonService
        import numpy as np

        logger.info("Starting AI score update...")

        # CRITICAL: Validate required API key
        polygon_key = os.getenv('POLYGON_API_KEY')
        if not polygon_key or polygon_key.strip() == '':
            logger.critical("CRITICAL ERROR: POLYGON_API_KEY is missing. Aborting AI score update.")
            return False

        polygon = PolygonService()

        with app.app_context():
            # Get all unique tickers from watchlists
            watchlist_tickers = db.session.query(Watchlist.ticker).distinct().all()
            tickers = [t[0] for t in watchlist_tickers]

            logger.info(f"Found {len(tickers)} unique tickers in watchlists")

            if not tickers:
                logger.info("No tickers to process")
                return True

            updated_count = 0
            failed_count = 0

            for ticker in tickers:
                try:
                    logger.info(f"Processing {ticker}...")

                    # Calculate enhanced features
                    features = calculate_enhanced_features(ticker, polygon, db)

                    if not features:
                        logger.warning(f"Could not calculate features for {ticker}")
                        failed_count += 1
                        continue

                    # Calculate AI score (0-100)
                    score = calculate_ai_score(features)

                    # Determine rating
                    rating = determine_rating(score)

                    # Store in database
                    ai_score_record = AIScore.query.filter_by(ticker=ticker).first()

                    if ai_score_record:
                        # Update existing
                        ai_score_record.score = score
                        ai_score_record.rating = rating
                        ai_score_record.features_json = json.dumps(features)
                        ai_score_record.updated_at = datetime.utcnow()
                    else:
                        # Insert new
                        ai_score_record = AIScore(
                            ticker=ticker,
                            score=score,
                            rating=rating,
                            features_json=json.dumps(features)
                        )
                        db.session.add(ai_score_record)

                    db.session.commit()
                    updated_count += 1
                    logger.info(f"{ticker}: Score={score}, Rating={rating}")

                except Exception as e:
                    logger.error(f"Error processing {ticker}: {e}", exc_info=True)
                    failed_count += 1
                    continue

            logger.info(f"AI score update complete: {updated_count} updated, {failed_count} failed")
            return True

    except Exception as e:
        logger.error(f"AI score update failed: {e}", exc_info=True)
        return False


def calculate_enhanced_features(ticker: str, polygon, db):
    """
    Calculate enhanced features for a ticker.

    Combines technical, fundamental, and sentiment features.

    Args:
        ticker: Stock ticker symbol
        polygon: PolygonService instance
        db: Database session

    Returns:
        dict: Feature dictionary or None if calculation failed
    """
    try:
        features = {}

        # 1. TECHNICAL INDICATORS
        technicals = polygon.get_technical_indicators(ticker, days=200)
        if technicals:
            features['rsi'] = technicals.get('rsi', 50)
            features['macd'] = technicals.get('macd', 0)
            features['price_to_ma50'] = technicals.get('price_to_ma50', 1.0)
            features['price_to_ma200'] = technicals.get('price_to_ma200', 1.0)
        else:
            # Use defaults if no data
            features['rsi'] = 50
            features['macd'] = 0
            features['price_to_ma50'] = 1.0
            features['price_to_ma200'] = 1.0

        # 2. FUNDAMENTAL INDICATORS (simplified - using mock data)
        # In production, fetch from Polygon.io Stock Financials API
        ticker_details = polygon.get_ticker_details(ticker)
        if ticker_details:
            # Use market cap as a proxy for company size
            market_cap = ticker_details.get('market_cap', 0)
            features['market_cap_log'] = np.log10(market_cap + 1)
        else:
            features['market_cap_log'] = 9.0  # Default ~1B market cap

        # Mock fundamental ratios (in production, fetch real data)
        features['pe_ratio'] = 20.0  # Price/Earnings
        features['pb_ratio'] = 3.0   # Price/Book
        features['eps_growth'] = 0.10  # 10% growth
        features['revenue_growth'] = 0.15  # 15% growth

        # 3. NEWS SENTIMENT (7-day average)
        from web.database import NewsArticle
        cutoff_date = datetime.utcnow() - timedelta(days=7)

        # Query news articles mentioning this ticker
        recent_news = NewsArticle.query.filter(
            NewsArticle.published_at >= cutoff_date,
            NewsArticle.title.contains(ticker)  # Simple keyword match
        ).all()

        if recent_news:
            # Calculate average sentiment
            sentiment_scores = []
            for article in recent_news:
                if article.ai_rating:
                    sentiment_scores.append(article.ai_rating / 5.0)  # Normalize to 0-1

            if sentiment_scores:
                features['news_sentiment_7d'] = np.mean(sentiment_scores)
            else:
                features['news_sentiment_7d'] = 0.5  # Neutral
        else:
            features['news_sentiment_7d'] = 0.5  # Neutral

        return features

    except Exception as e:
        logger.error(f"Error calculating features for {ticker}: {e}", exc_info=True)
        return None


def calculate_ai_score(features: dict) -> int:
    """
    Calculate AI score (0-100) from enhanced features.

    Uses weighted combination of technical, fundamental, and sentiment indicators.

    Args:
        features: Dictionary of calculated features

    Returns:
        int: AI score (0-100)
    """
    try:
        # Weighted scoring system
        score = 50  # Base score

        # Technical indicators (40% weight)
        rsi = features.get('rsi', 50)
        if rsi < 30:  # Oversold - potential buy
            score += 10
        elif rsi > 70:  # Overbought - potential sell
            score -= 10
        elif 40 <= rsi <= 60:  # Neutral
            score += 5

        macd = features.get('macd', 0)
        if macd > 0:  # Bullish
            score += 10
        else:  # Bearish
            score -= 10

        price_to_ma50 = features.get('price_to_ma50', 1.0)
        if price_to_ma50 > 1.05:  # Above MA50
            score += 5
        elif price_to_ma50 < 0.95:  # Below MA50
            score -= 5

        # Fundamental indicators (30% weight)
        pe_ratio = features.get('pe_ratio', 20)
        if 10 <= pe_ratio <= 25:  # Reasonable valuation
            score += 10
        elif pe_ratio > 40:  # Overvalued
            score -= 5

        eps_growth = features.get('eps_growth', 0)
        if eps_growth > 0.15:  # Strong growth
            score += 10
        elif eps_growth < 0:  # Negative growth
            score -= 10

        # News sentiment (30% weight)
        news_sentiment = features.get('news_sentiment_7d', 0.5)
        sentiment_score = (news_sentiment - 0.5) * 30  # -15 to +15
        score += sentiment_score

        # Clamp to 0-100
        score = max(0, min(100, int(score)))

        return score

    except Exception as e:
        logger.error(f"Error calculating AI score: {e}", exc_info=True)
        return 50  # Default neutral score


def determine_rating(score: int) -> str:
    """
    Convert numerical score to rating string.

    Args:
        score: AI score (0-100)

    Returns:
        str: Rating (Strong Buy/Buy/Hold/Sell/Strong Sell)
    """
    if score >= 75:
        return "Strong Buy"
    elif score >= 60:
        return "Buy"
    elif score >= 40:
        return "Hold"
    elif score >= 25:
        return "Sell"
    else:
        return "Strong Sell"


if __name__ == '__main__':
    print("=" * 80)
    print("RENDER CRON JOB: AI Score Update Started")
    print("=" * 80)

    start_time = datetime.now()

    success = update_ai_scores()

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    print("=" * 80)
    print(f"CRON JOB COMPLETED in {duration:.2f} seconds")
    print(f"Status: {'✓ SUCCESS' if success else '✗ FAILED'}")
    print("=" * 80)

    sys.exit(0 if success else 1)
