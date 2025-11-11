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

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def refresh_news_data():
    """
    Fetch and analyze latest news articles from NewsAPI.

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
        from src.news_collector import collect_news
        from src.news_analyzer import analyze_with_claude
        from web.database import db, NewsArticle
        from web.app import app

        logger.info("Starting news refresh...")

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
                    existing = NewsArticle.query.filter_by(url=article_data['url']).first()
                    if existing:
                        logger.debug(f"Article already exists: {article_data['title'][:50]}")
                        continue

                    # Analyze with Claude AI
                    analysis = analyze_with_claude(article_data)

                    # Create new article
                    article = NewsArticle(
                        title=article_data['title'],
                        description=article_data.get('description'),
                        url=article_data['url'],
                        source=article_data.get('source'),
                        published_at=datetime.fromisoformat(article_data['published'])
                                    if isinstance(article_data['published'], str)
                                    else article_data['published'],
                        ai_rating=analysis.get('rating'),
                        ai_analysis=analysis.get('analysis'),
                        sentiment=analysis.get('sentiment')
                    )

                    db.session.add(article)
                    saved_count += 1

                except Exception as e:
                    logger.error(f"Error processing article: {e}")
                    continue

            # Commit all new articles
            db.session.commit()
            logger.info(f"Saved {saved_count} new articles to database")

            # Clean up old articles (keep last 30 days)
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            deleted = NewsArticle.query.filter(
                NewsArticle.published_at < cutoff_date
            ).delete()
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
        from web.database import db, EconomicEvent
        from web.app import app
        import requests
        from datetime import datetime, timedelta

        logger.info("Starting calendar refresh...")

        # Get API key from environment
        api_key = os.getenv('FINNHUB_API_KEY')
        if not api_key:
            logger.warning("FINNHUB_API_KEY not set - skipping calendar refresh")
            logger.info("To enable: Get free API key from https://finnhub.io")
            return True  # Not a failure, just skipped

        with app.app_context():
            # Fetch economic calendar from Finnhub
            # Date range: today to 60 days ahead
            from_date = datetime.utcnow().strftime('%Y-%m-%d')
            to_date = (datetime.utcnow() + timedelta(days=60)).strftime('%Y-%m-%d')

            url = f"https://finnhub.io/api/v1/calendar/economic"
            params = {
                'from': from_date,
                'to': to_date,
                'token': api_key
            }

            logger.info(f"Fetching calendar events from {from_date} to {to_date}")
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            events_data = data.get('economicCalendar', [])

            if not events_data:
                logger.info("No economic events found")
                return True

            logger.info(f"Retrieved {len(events_data)} economic events")

            # Process and store events
            saved_count = 0
            updated_count = 0

            for event_data in events_data:
                try:
                    # Parse event data
                    event_time = datetime.strptime(event_data['time'], '%Y-%m-%d %H:%M:%S')
                    title = event_data.get('event', 'Economic Event')
                    country = event_data.get('country', 'US')

                    # Determine importance (Finnhub uses 'impact': low/medium/high)
                    impact = event_data.get('impact', '').lower()
                    importance = 'medium'  # default
                    if impact in ['low', 'medium', 'high']:
                        importance = impact

                    # Check if event already exists
                    existing = EconomicEvent.query.filter_by(
                        title=title,
                        date=event_time
                    ).first()

                    if existing:
                        # Update existing event
                        existing.actual = event_data.get('actual')
                        existing.forecast = event_data.get('estimate')
                        existing.previous = event_data.get('previous')
                        existing.importance = importance
                        existing.country = country
                        existing.updated_at = datetime.utcnow()
                        updated_count += 1
                    else:
                        # Create new event
                        event = EconomicEvent(
                            title=title,
                            date=event_time,
                            time=event_time.strftime('%H:%M EST'),
                            country=country,
                            importance=importance,
                            actual=event_data.get('actual'),
                            forecast=event_data.get('estimate'),
                            previous=event_data.get('previous'),
                            source='Finnhub'
                        )
                        db.session.add(event)
                        saved_count += 1

                except Exception as e:
                    logger.error(f"Error processing event: {e}")
                    continue

            # Commit all changes
            db.session.commit()
            logger.info(f"Saved {saved_count} new events, updated {updated_count} events")

            # Clean up old events (older than 7 days)
            cutoff_date = datetime.utcnow() - timedelta(days=7)
            deleted = EconomicEvent.query.filter(
                EconomicEvent.date < cutoff_date
            ).delete()
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


if __name__ == '__main__':
    main()
