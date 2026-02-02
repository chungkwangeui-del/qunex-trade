"""
Manual News Refresh Script
Run this to collect and analyze latest news
"""

import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from src.news_collector import NewsCollector
from src.news_analyzer import NewsAnalyzer
import logging

logger = logging.getLogger(__name__)



def main():
    """Collect and analyze latest news"""

    logger.info("\n" + "=" * 70)
    logger.info("  REAL-TIME NEWS COLLECTION & ANALYSIS")
    logger.info("  Only credible and important news (4-5 stars)")
    logger.info("=" * 70 + "\n")

    try:
        # Step 1: Collect news
        logger.info("STEP 1: Collecting news from reliable sources...")
        logger.info("-" * 70)
        collector = NewsCollector()
        news_list = collector.collect_all_news()  # Last 2 hours (hardcoded in collector)

        if not news_list:
            logger.info("\n[ERROR] No news collected. Please check your API keys.")
            return

        # Step 2: Analyze news
        logger.info("\nSTEP 2: Analyzing news with AI (filtering for importance)...")
        logger.info("-" * 70)
        analyzer = NewsAnalyzer()
        analyzed_news = analyzer.analyze_news_batch(news_list, max_items=40)

        if not analyzed_news:
            logger.info("\n[WARN] No important news found in this batch.")
            return

        # Step 3: Save results
        logger.info("\nSTEP 3: Saving results...")
        logger.info("-" * 70)
        analyzer.save_analysis(analyzed_news)

        # Step 4: Summary
        market_wide = [n for n in analyzed_news if n.get("market_wide_impact", False)]

        logger.info("\n" + "=" * 70)
        logger.info("  SUMMARY")
        logger.info("=" * 70)
        logger.info(f"  Total collected: {len(news_list)} news items")
        logger.info(f"  Important news: {len(analyzed_news)} items")
        logger.info(f"  Market-Wide Impact: {len(market_wide)} items (Fed, Trump, GDP, etc.)")
        logger.info(
            f"  Critical (5 stars): {len([n for n in analyzed_news if n.get('importance') == 5])}"
        )
        logger.info(
            f"  Very Important (4 stars): {len([n for n in analyzed_news if n.get('importance') == 4])}"
        )
        logger.info("\n  Top 5 Most Important News (Market-Wide First):")
        logger.info("  " + "-" * 66)

        for i, news in enumerate(analyzed_news[:5], 1):
            importance = news.get("importance", 0)
            market_wide_flag = news.get("market_wide_impact", False)
            title = news.get("news_title", "N/A")
            stars = "*" * importance
            label = "[MARKET-WIDE]" if market_wide_flag else "[SPECIFIC]"
            logger.info(f"  {i}. [{stars}] {label} {title[:40]}...")

        logger.info("\n" + "=" * 70)
        logger.info("  [SUCCESS] News updated and ready to display!")
        logger.info("=" * 70 + "\n")

    except Exception as e:
        logger.info(f"\n[ERROR] Failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
