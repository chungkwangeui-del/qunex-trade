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
    """Fetch and analyze latest news articles"""
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
    """Fetch and update economic calendar events"""
    try:
        from web.database import db, EconomicEvent
        from web.app import app
        import requests

        logger.info("Starting calendar refresh...")

        with app.app_context():
            # Fetch calendar data from Trading Economics or similar API
            # For now, using a placeholder - you'll need to implement actual API call
            logger.info("Calendar API integration needed - placeholder for now")

            # Example structure:
            # events = fetch_from_calendar_api()
            # for event_data in events:
            #     event = EconomicEvent(...)
            #     db.session.add(event)
            # db.session.commit()

            return True

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
