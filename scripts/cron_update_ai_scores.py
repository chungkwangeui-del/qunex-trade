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
import time
from datetime import datetime, timedelta

# Add parent directory and web directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
web_dir = os.path.join(parent_dir, "web")
sys.path.insert(0, web_dir)
sys.path.insert(0, parent_dir)

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
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
        # Import app first to ensure proper initialization
        import numpy as np
        from web.app import app
        from web.database import db, Watchlist, AIScore, NewsArticle
        from web.polygon_service import PolygonService
        from alpha_vantage.fundamentaldata import FundamentalData

        logger.info("Starting AI score update...")

        # CRITICAL: Validate required API keys
        alpha_vantage_key = os.getenv("ALPHA_VANTAGE_API_KEY")
        if not alpha_vantage_key or alpha_vantage_key.strip() == "":
            logger.critical(
                "CRITICAL ERROR: ALPHA_VANTAGE_API_KEY is missing. Aborting AI score update."
            )
            logger.critical("Get a free API key from: https://www.alphavantage.co/support/#api-key")
            return False

        polygon_key = os.getenv("POLYGON_API_KEY")
        if not polygon_key or polygon_key.strip() == "":
            logger.warning(
                "WARNING: POLYGON_API_KEY is missing. Technical indicators will be limited."
            )
            # Continue anyway - we can still use Alpha Vantage for fundamentals

        # Initialize API services
        polygon = PolygonService() if polygon_key else None
        alpha_vantage = FundamentalData(key=alpha_vantage_key, output_format="json")

        with app.app_context():
            # RATE LIMITING STRATEGY: Update only 20 oldest stocks per day
            # This keeps us within Alpha Vantage's 500 calls/day limit
            # (we make ~2-3 calls per stock: OVERVIEW + INCOME_STATEMENT)

            # Get 20 stocks with oldest updated_at timestamp
            oldest_stocks = AIScore.query.order_by(AIScore.updated_at.asc()).limit(20).all()

            if oldest_stocks:
                tickers = [stock.ticker for stock in oldest_stocks]
                logger.info(f"Rate limiting: Updating 20 oldest stocks from AIScore table")
            else:
                # First run - get stocks from watchlists
                watchlist_tickers = db.session.query(Watchlist.ticker).distinct().limit(20).all()
                tickers = [t[0] for t in watchlist_tickers]

                # If no watchlist tickers, use default popular stocks
                if not tickers:
                    logger.info("No watchlist tickers found. Using default popular stocks.")
                    tickers = [
                        # FAANG + Popular Tech (Top 20)
                        "AAPL",
                        "MSFT",
                        "GOOGL",
                        "AMZN",
                        "META",
                        "NVDA",
                        "TSLA",
                        "NFLX",
                        "AMD",
                        "AVGO",
                        "CRM",
                        "ORCL",
                        "ADBE",
                        "INTC",
                        # Major Indices ETFs
                        "SPY",
                        "QQQ",
                        "DIA",
                        # Financials
                        "JPM",
                        "BAC",
                        "V",
                    ][
                        :20
                    ]  # Ensure max 20
                    logger.info(f"Processing {len(tickers)} default tickers")

            logger.info(f"Processing {len(tickers)} tickers: {', '.join(tickers)}")

            updated_count = 0
            failed_count = 0

            for i, ticker in enumerate(tickers):
                # RATE LIMITING: 15-second delay between API calls to stay within 4 calls/minute
                if i > 0:
                    logger.info(f"Rate limiting: Waiting 15 seconds before next API call...")
                    time.sleep(15)
                try:
                    logger.info(f"Processing {ticker}... ({i+1}/{len(tickers)})")

                    # Calculate enhanced features with Alpha Vantage
                    features = calculate_enhanced_features(ticker, polygon, alpha_vantage, db)

                    if not features:
                        logger.warning(f"Could not calculate features for {ticker}")
                        failed_count += 1
                        continue

                    # Calculate AI score (0-100)
                    score = calculate_ai_score(features)

                    # Determine rating
                    rating = determine_rating(score)

                    # Calculate feature explanations (simplified SHAP-like)
                    explanation = calculate_feature_contributions(features)

                    # Store in database
                    ai_score_record = AIScore.query.filter_by(ticker=ticker).first()

                    if ai_score_record:
                        # Update existing
                        ai_score_record.score = score
                        ai_score_record.rating = rating
                        ai_score_record.features_json = json.dumps(features)
                        ai_score_record.explanation_json = json.dumps(explanation)
                        ai_score_record.updated_at = datetime.utcnow()
                    else:
                        # Insert new
                        ai_score_record = AIScore(
                            ticker=ticker,
                            score=score,
                            rating=rating,
                            explanation_json=json.dumps(explanation),
                            features_json=json.dumps(features),
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


def calculate_enhanced_features(ticker: str, polygon, alpha_vantage, db):
    """
    Calculate enhanced features for a ticker.

    Combines technical, fundamental, and sentiment features.

    Args:
        ticker: Stock ticker symbol
        polygon: PolygonService instance (for technical indicators)
        alpha_vantage: Alpha Vantage FundamentalData instance (for fundamentals)
        db: Database session

    Returns:
        dict: Feature dictionary or None if calculation failed
    """
    try:
        import numpy as np
        from web.database import NewsArticle

        features = {}

        # 1. TECHNICAL INDICATORS (from Polygon if available)
        if polygon:
            technicals = polygon.get_technical_indicators(ticker, days=200)
            if technicals:
                features["rsi"] = technicals.get("rsi", 50)
                features["macd"] = technicals.get("macd", 0)
                features["price_to_ma50"] = technicals.get("price_to_ma50", 1.0)
                features["price_to_ma200"] = technicals.get("price_to_ma200", 1.0)
            else:
                # Use defaults if no data
                features["rsi"] = 50
                features["macd"] = 0
                features["price_to_ma50"] = 1.0
                features["price_to_ma200"] = 1.0
        else:
            # No Polygon - use defaults
            features["rsi"] = 50
            features["macd"] = 0
            features["price_to_ma50"] = 1.0
            features["price_to_ma200"] = 1.0

        # 2. FUNDAMENTAL INDICATORS (from Alpha Vantage)
        try:
            logger.info(f"Fetching fundamental data from Alpha Vantage for {ticker}...")

            # Fetch company overview (P/E, P/B, Market Cap, etc.)
            overview_data, overview_meta = alpha_vantage.get_company_overview(ticker)

            if overview_data and isinstance(overview_data, dict):
                # Parse market cap
                market_cap_str = overview_data.get("MarketCapitalization", "0")
                try:
                    market_cap = float(market_cap_str) if market_cap_str else 0
                    features["market_cap_log"] = np.log10(market_cap + 1) if market_cap > 0 else 9.0
                except (ValueError, TypeError):
                    features["market_cap_log"] = 9.0

                # Parse P/E ratio
                pe_str = overview_data.get("PERatio", "20.0")
                try:
                    features["pe_ratio"] = float(pe_str) if pe_str and pe_str != "None" else 20.0
                except (ValueError, TypeError):
                    features["pe_ratio"] = 20.0

                # Parse P/B ratio
                pb_str = overview_data.get("PriceToBookRatio", "3.0")
                try:
                    features["pb_ratio"] = float(pb_str) if pb_str and pb_str != "None" else 3.0
                except (ValueError, TypeError):
                    features["pb_ratio"] = 3.0

                # Parse EPS
                eps_str = overview_data.get("EPS", "0")
                try:
                    eps = float(eps_str) if eps_str and eps_str != "None" else 0
                except (ValueError, TypeError):
                    eps = 0

                # Parse quarterly earnings growth (YoY)
                earnings_growth_str = overview_data.get("QuarterlyEarningsGrowthYOY", "0.10")
                try:
                    # Alpha Vantage returns as percentage string like "0.15" for 15%
                    features["eps_growth"] = (
                        float(earnings_growth_str)
                        if earnings_growth_str and earnings_growth_str != "None"
                        else 0.10
                    )
                except (ValueError, TypeError):
                    features["eps_growth"] = 0.10

                # Parse quarterly revenue growth (YoY)
                revenue_growth_str = overview_data.get("QuarterlyRevenueGrowthYOY", "0.15")
                try:
                    features["revenue_growth"] = (
                        float(revenue_growth_str)
                        if revenue_growth_str and revenue_growth_str != "None"
                        else 0.15
                    )
                except (ValueError, TypeError):
                    features["revenue_growth"] = 0.15

                logger.info(
                    f"Alpha Vantage data fetched: P/E={features['pe_ratio']:.2f}, P/B={features['pb_ratio']:.2f}, EPS Growth={features['eps_growth']:.2%}"
                )

            else:
                # Alpha Vantage returned empty or error - use defaults
                logger.warning(
                    f"Alpha Vantage returned no data for {ticker}. Using default fundamental values."
                )
                features["market_cap_log"] = 9.0
                features["pe_ratio"] = 20.0
                features["pb_ratio"] = 3.0
                features["eps_growth"] = 0.10
                features["revenue_growth"] = 0.15

        except Exception as av_error:
            logger.error(f"Alpha Vantage API error for {ticker}: {av_error}", exc_info=True)
            # Use defaults on API error
            features["market_cap_log"] = 9.0
            features["pe_ratio"] = 20.0
            features["pb_ratio"] = 3.0
            features["eps_growth"] = 0.10
            features["revenue_growth"] = 0.15

        # 3. NEWS SENTIMENT (7-day average)
        cutoff_date = datetime.utcnow() - timedelta(days=7)

        # Query news articles mentioning this ticker
        recent_news = NewsArticle.query.filter(
            NewsArticle.published_at >= cutoff_date,
            NewsArticle.title.contains(ticker),  # Simple keyword match
        ).all()

        if recent_news:
            # Calculate average sentiment
            sentiment_scores = []
            for article in recent_news:
                if article.ai_rating:
                    sentiment_scores.append(article.ai_rating / 5.0)  # Normalize to 0-1

            if sentiment_scores:
                features["news_sentiment_7d"] = np.mean(sentiment_scores)
            else:
                features["news_sentiment_7d"] = 0.5  # Neutral
        else:
            features["news_sentiment_7d"] = 0.5  # Neutral

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
        rsi = features.get("rsi", 50)
        if rsi < 30:  # Oversold - potential buy
            score += 10
        elif rsi > 70:  # Overbought - potential sell
            score -= 10
        elif 40 <= rsi <= 60:  # Neutral
            score += 5

        macd = features.get("macd", 0)
        if macd > 0:  # Bullish
            score += 10
        else:  # Bearish
            score -= 10

        price_to_ma50 = features.get("price_to_ma50", 1.0)
        if price_to_ma50 > 1.05:  # Above MA50
            score += 5
        elif price_to_ma50 < 0.95:  # Below MA50
            score -= 5

        # Fundamental indicators (30% weight)
        pe_ratio = features.get("pe_ratio", 20)
        if 10 <= pe_ratio <= 25:  # Reasonable valuation
            score += 10
        elif pe_ratio > 40:  # Overvalued
            score -= 5

        eps_growth = features.get("eps_growth", 0)
        if eps_growth > 0.15:  # Strong growth
            score += 10
        elif eps_growth < 0:  # Negative growth
            score -= 10

        # News sentiment (30% weight)
        news_sentiment = features.get("news_sentiment_7d", 0.5)
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


def calculate_feature_contributions(features: dict) -> dict:
    """
    Calculate feature contributions to AI score (simplified SHAP-like).

    Provides explainability by showing which features contributed
    positively or negatively to the final score.

    Args:
        features: Dictionary of calculated features

    Returns:
        dict: Feature names mapped to contribution values
    """
    contributions = {}

    # Technical indicators contributions
    rsi = features.get("rsi", 50)
    if rsi < 30:
        contributions["RSI (Oversold)"] = +0.10
    elif rsi > 70:
        contributions["RSI (Overbought)"] = -0.10
    else:
        contributions["RSI"] = 0.05

    macd = features.get("macd", 0)
    if macd > 0:
        contributions["MACD (Bullish)"] = +0.10
    else:
        contributions["MACD (Bearish)"] = -0.10

    price_to_ma50 = features.get("price_to_ma50", 1.0)
    if price_to_ma50 > 1.05:
        contributions["Price vs MA50"] = +0.05
    elif price_to_ma50 < 0.95:
        contributions["Price vs MA50"] = -0.05

    # Fundamental indicators contributions
    pe_ratio = features.get("pe_ratio", 20)
    if 10 <= pe_ratio <= 25:
        contributions["P/E Ratio"] = +0.10
    elif pe_ratio > 40:
        contributions["P/E Ratio (High)"] = -0.05

    eps_growth = features.get("eps_growth", 0)
    if eps_growth > 0.15:
        contributions["EPS Growth (Strong)"] = +0.10
    elif eps_growth < 0:
        contributions["EPS Growth (Negative)"] = -0.10
    else:
        contributions["EPS Growth"] = 0.05

    # News sentiment contribution
    news_sentiment = features.get("news_sentiment_7d", 0.5)
    sentiment_contrib = (news_sentiment - 0.5) * 0.30
    if sentiment_contrib > 0.05:
        contributions["News Sentiment (Positive)"] = sentiment_contrib
    elif sentiment_contrib < -0.05:
        contributions["News Sentiment (Negative)"] = sentiment_contrib
    else:
        contributions["News Sentiment"] = sentiment_contrib

    return contributions


if __name__ == "__main__":
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
