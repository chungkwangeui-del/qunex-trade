"""
Automatic News Refresh Scheduler
- Runs news collection and analysis every 6 hours
- Focuses on government/Fed news (high impact)
"""

import time
import schedule
import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.news_collector import NewsCollector
from src.news_analyzer import NewsAnalyzer


def refresh_news():
    """Collect and analyze news (automated task)"""
    print(f"\n{'='*60}")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting automated news refresh...")
    print(f"{'='*60}\n")

    try:
        # Collect news (prioritized by government/Fed news)
        print("Step 1: Collecting news from multiple sources...")
        collector = NewsCollector()
        news_list = collector.collect_all_news(hours=24)

        if not news_list:
            print("[WARNING] No news collected. Skipping analysis.")
            return

        print(f"\n✓ Collected {len(news_list)} news items")

        # Analyze news (50 items, prioritized)
        print("\nStep 2: Analyzing news impact with AI...")
        analyzer = NewsAnalyzer()
        analyzed_news = analyzer.analyze_news_batch(news_list, max_items=50)

        # Count high-impact news (4-5 stars)
        high_impact = [n for n in analyzed_news if n.get('importance', 0) >= 4]
        critical_impact = [n for n in analyzed_news if n.get('importance', 0) == 5]

        print(f"\n✓ Analyzed {len(analyzed_news)} news items")
        print(f"  - Critical (⭐⭐⭐⭐⭐): {len(critical_impact)} items")
        print(f"  - High Impact (⭐⭐⭐⭐+): {len(high_impact)} items")

        # Save analysis
        print("\nStep 3: Saving analysis results...")
        analyzer.save_analysis(analyzed_news)

        print(f"\n{'='*60}")
        print(f"✓ News refresh completed successfully!")
        print(f"{'='*60}\n")

    except Exception as e:
        print(f"\n[ERROR] News refresh failed: {e}")


def run_scheduler():
    """Run the news refresh scheduler"""
    print("="*60)
    print("📰 News Refresh Scheduler Started")
    print("="*60)
    print("Schedule: Every 6 hours")
    print("Focus: Government/Fed news (high impact)")
    print("Analysis: Up to 50 news items per run")
    print("="*60)

    # Run immediately on start
    print("\n🔄 Running initial news refresh...")
    refresh_news()

    # Schedule to run every 6 hours
    schedule.every(6).hours.do(refresh_news)

    print("\n⏰ Scheduler is now running. Press Ctrl+C to stop.")
    print("Next refresh in 6 hours.\n")

    # Keep running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute


if __name__ == '__main__':
    try:
        run_scheduler()
    except KeyboardInterrupt:
        print("\n\n⏹ Scheduler stopped by user.")
