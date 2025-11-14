#!/usr/bin/env python3
"""
Render Cron Job: Refresh News and Calendar Data

This script is executed by Render.com's Cron Job feature to:
1. Fetch latest news articles
2. Analyze news with Claude AI
3. Update economic calendar events
4. Store everything in PostgreSQL database

This replaces the old threading-based background task system.
"""

import os
import sys
import logging
from datetime import datetime, timedelta

# Add parent directory and web directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
web_dir = os.path.join(parent_dir, "web")
sys.path.insert(0, web_dir)
sys.path.insert(0, parent_dir)

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def refresh_news_data():
    """
    Fetch and analyze latest news articles from Polygon News API.

    Collects news articles, analyzes them with Claude AI to generate
    ratings and sentiment, and stores results in PostgreSQL database.
    Automatically removes articles older than 30 days.

    Returns:
        bool: True if refresh succeeded, False otherwise

    Side Effects:
        - Adds new NewsArticle records to database
        - Deletes NewsArticle records older than 30 days
        - Commits database transactions
    """
    try:
        # Import app first to ensure proper initialization
        from web.app import app
        from web.database import db, NewsArticle
        from src.news_collector import collect_news
        from src.news_analyzer import analyze_with_claude

        logger.info("Starting news refresh...")

        # CRITICAL: Validate required API keys
        polygon_key = os.getenv("POLYGON_API_KEY")
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")

        if not polygon_key or polygon_key.strip() == "":
            logger.critical(
                "CRITICAL ERROR: POLYGON_API_KEY is missing or empty. Aborting news refresh."
            )
            logger.critical("Get API key from: https://polygon.io/dashboard/api-keys")
            return False

        if not anthropic_key or anthropic_key.strip() == "":
            logger.critical(
                "CRITICAL ERROR: ANTHROPIC_API_KEY is missing or empty. Aborting news refresh."
            )
            logger.critical("Get an API key from: https://console.anthropic.com/")
            return False

        # Use app context for database operations
        with app.app_context():
            # Collect news from APIs
            news_articles = collect_news()
            logger.info(f"Collected {len(news_articles)} articles")

            # Analyze and store each article
            saved_count = 0
            for article_data in news_articles:
                try:
                    # Check if article already exists (by URL)
                    existing = NewsArticle.query.filter_by(url=article_data["url"]).first()
                    if existing:
                        logger.debug(f"Article already exists: {article_data['title'][:50]}")
                        continue

                    # Analyze with Claude AI
                    analysis = analyze_with_claude(article_data)

                    # Create new article
                    # Parse published_at (Polygon uses 'published_at' field)
                    published_at_str = article_data.get("published_at", "")
                    if published_at_str:
                        try:
                            # Polygon format: "2025-01-13T12:00:00Z"
                            if published_at_str.endswith('Z'):
                                published_at_str = published_at_str[:-1] + '+00:00'
                            published_at = datetime.fromisoformat(published_at_str)
                        except ValueError:
                            published_at = datetime.utcnow()
                    else:
                        published_at = datetime.utcnow()

                    article = NewsArticle(
                        title=article_data["title"],
                        description=article_data.get("description"),
                        url=article_data["url"],
                        source=article_data.get("source"),
                        published_at=published_at,
                        ai_rating=analysis.get("rating"),
                        ai_analysis=analysis.get("analysis"),
                        sentiment=analysis.get("sentiment"),
                    )

                    db.session.add(article)
                    saved_count += 1

                except Exception as e:
                    logger.error(f"Error processing article: {e}", exc_info=True)
                    continue

            # Commit all new articles
            db.session.commit()
            logger.info(f"Saved {saved_count} new articles to database")

            # Clean up old articles (keep last 30 days)
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            deleted = NewsArticle.query.filter(NewsArticle.published_at < cutoff_date).delete()
            db.session.commit()
            logger.info(f"Deleted {deleted} old articles")

            return True

    except Exception as e:
        logger.error(f"News refresh failed: {e}", exc_info=True)
        return False


def refresh_calendar_data():
    """
    Fetch and update economic calendar events from Finnhub API.

    Uses Finnhub's economic calendar endpoint to retrieve upcoming
    economic events and updates the database. Handles duplicates by
    checking existing events before insertion.

    Returns:
        bool: True if refresh succeeded, False otherwise
    """
    try:
        # Import app first to ensure proper initialization
        from web.app import app
        from web.database import db, EconomicEvent
        import requests
        from datetime import datetime, timedelta

        logger.info("Starting calendar refresh...")

        # CRITICAL: Validate required API key
        api_key = os.getenv("FINNHUB_API_KEY")
        if not api_key or api_key.strip() == "":
            logger.critical(
                "CRITICAL ERROR: FINNHUB_API_KEY is missing or empty. Aborting calendar refresh."
            )
            logger.critical("Get a free API key from: https://finnhub.io/")
            return False

        with app.app_context():
            # Fetch economic calendar from Finnhub
            # Date range: today to 30 days ahead
            from_date = datetime.utcnow().strftime("%Y-%m-%d")
            to_date = (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d")

            url = f"https://finnhub.io/api/v1/calendar/economic"
            params = {"token": api_key, "from": from_date, "to": to_date}

            logger.info(f"Fetching calendar events from {from_date} to {to_date}")

            # Fetch from Finnhub API
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            api_data = response.json()

            # Finnhub returns: {"economicCalendar": [...events...]}
            events_data = api_data.get("economicCalendar", [])

            if not events_data:
                logger.info("No economic events found")
                return True

            logger.info(f"Retrieved {len(events_data)} economic events")

            # Process and store events
            saved_count = 0
            updated_count = 0

            for event_data in events_data:
                try:
                    # Parse Finnhub event data
                    # Finnhub format: {"actual": "...", "country": "US", "estimate": "...",
                    #                  "event": "GDP", "impact": "high", "prev": "...", "time": "2024-01-15 08:30:00"}

                    # Parse event time
                    time_str = event_data.get("time", "")
                    try:
                        # Finnhub format: "YYYY-MM-DD HH:MM:SS"
                        event_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        # Try alternative format if primary fails
                        try:
                            event_time = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S")
                        except ValueError:
                            logger.warning(f"Skipping event with invalid time format: {time_str}")
                            continue

                    title = event_data.get("event", "Economic Event")
                    country = event_data.get("country", "US")

                    # Determine importance (Finnhub uses 'impact': low/medium/high)
                    impact = event_data.get("impact", "").lower()
                    importance = "medium"  # default
                    if impact in ["low", "medium", "high"]:
                        importance = impact

                    # Check if event already exists
                    existing = EconomicEvent.query.filter_by(title=title, date=event_time).first()

                    if existing:
                        # Update existing event
                        existing.actual = event_data.get("actual")
                        existing.forecast = event_data.get("estimate")
                        existing.previous = event_data.get(
                            "prev"
                        )  # Finnhub uses 'prev' not 'previous'
                        existing.importance = importance
                        existing.country = country
                        existing.updated_at = datetime.utcnow()
                        updated_count += 1
                    else:
                        # Create new event
                        event = EconomicEvent(
                            title=title,
                            date=event_time,
                            time=event_time.strftime("%H:%M EST"),
                            country=country,
                            importance=importance,
                            actual=event_data.get("actual"),
                            forecast=event_data.get("estimate"),
                            previous=event_data.get("prev"),  # Finnhub uses 'prev' not 'previous'
                            source="Finnhub",
                        )
                        db.session.add(event)
                        saved_count += 1

                except Exception as e:
                    logger.error(f"Error processing event: {e}", exc_info=True)
                    continue

            # Commit all changes
            db.session.commit()
            logger.info(f"Saved {saved_count} new events, updated {updated_count} events")

            # Clean up old events (older than 7 days)
            cutoff_date = datetime.utcnow() - timedelta(days=7)
            deleted = EconomicEvent.query.filter(EconomicEvent.date < cutoff_date).delete()
            db.session.commit()
            logger.info(f"Deleted {deleted} old events")

            return True

    except requests.RequestException as e:
        logger.error(f"Calendar API request failed: {e}", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"Calendar refresh failed: {e}", exc_info=True)
        return False


def main():
    """Main execution function"""
    logger.info("=" * 80)
    logger.info("RENDER CRON JOB: Data Refresh Started")
    logger.info("=" * 80)

    start_time = datetime.utcnow()

    # Refresh news
    news_success = refresh_news_data()

    # Refresh calendar
    calendar_success = refresh_calendar_data()

    end_time = datetime.utcnow()
    duration = (end_time - start_time).total_seconds()

    logger.info("=" * 80)
    logger.info(f"CRON JOB COMPLETED in {duration:.2f} seconds")
    logger.info(f"News: {'✓ SUCCESS' if news_success else '✗ FAILED'}")
    logger.info(f"Calendar: {'✓ SUCCESS' if calendar_success else '✗ FAILED'}")
    logger.info("=" * 80)

    # Exit with status code
    sys.exit(0 if (news_success and calendar_success) else 1)


if __name__ == "__main__":
    main()
