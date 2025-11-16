"""
Quick script to check if data exists in database
"""

import os
import sys
from datetime import datetime, timedelta

# Add web directory to path
web_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
sys.path.insert(0, web_dir)

from dotenv import load_dotenv

load_dotenv()

# Import after load_dotenv
from web.database import db, NewsArticle, AIScore, EconomicEvent
from web.app import app

with app.app_context():
    print("=" * 80)
    print("DATABASE DATA CHECK")
    print("=" * 80)

    # Check NewsArticle
    total_news = NewsArticle.query.count()
    recent_news = NewsArticle.query.filter(
        NewsArticle.published_at >= datetime.utcnow() - timedelta(hours=24)
    ).count()

    print(f"\nNEWS ARTICLES:")
    print(f"  Total: {total_news}")
    print(f"  Last 24h: {recent_news}")

    if recent_news > 0:
        latest = NewsArticle.query.order_by(NewsArticle.published_at.desc()).first()
        print(f"\n  Latest article:")
        print(f"    Title: {latest.title[:60]}...")
        print(f"    Published: {latest.published_at}")
        print(f"    Rating: {latest.ai_rating}/5")
        print(f"    Source: {latest.source}")

    # Check AIScore
    total_scores = AIScore.query.count()
    recent_scores = AIScore.query.filter(
        AIScore.updated_at >= datetime.utcnow() - timedelta(hours=24)
    ).count()

    print(f"\nAI SCORES:")
    print(f"  Total: {total_scores}")
    print(f"  Last 24h: {recent_scores}")

    if recent_scores > 0:
        latest_score = AIScore.query.order_by(AIScore.updated_at.desc()).first()
        print(f"\n  Latest score:")
        print(f"    Ticker: {latest_score.ticker}")
        print(f"    1H: {latest_score.score_1h}/10")
        print(f"    4H: {latest_score.score_4h}/10")
        print(f"    1D: {latest_score.score_1d}/10")
        print(f"    Updated: {latest_score.updated_at}")

    # Check EconomicEvent
    total_events = EconomicEvent.query.count()
    upcoming_events = EconomicEvent.query.filter(EconomicEvent.date >= datetime.utcnow()).count()

    print(f"\nECONOMIC EVENTS:")
    print(f"  Total: {total_events}")
    print(f"  Upcoming: {upcoming_events}")

    if upcoming_events > 0:
        next_event = (
            EconomicEvent.query.filter(EconomicEvent.date >= datetime.utcnow())
            .order_by(EconomicEvent.date.asc())
            .first()
        )
        print(f"\n  Next event:")
        print(f"    Title: {next_event.title}")
        print(f"    Date: {next_event.date}")
        print(f"    Country: {next_event.country}")
        print(f"    Importance: {next_event.importance}")

    print("\n" + "=" * 80)

    # Summary
    if total_news == 0 and total_scores == 0 and total_events == 0:
        print("WARNING: No data found in database!")
        print("   This could mean:")
        print("   1. GitHub Actions are writing to a different database")
        print("   2. DATABASE_URL mismatch between local and GitHub")
        print("   3. Data collection failed")
    elif recent_news == 0 and recent_scores == 0:
        print("WARNING: No recent data (last 24h)")
        print("   Old data exists but nothing new")
    else:
        print("SUCCESS: Data exists and is recent!")

    print("=" * 80)
