"""Manually refresh news"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("Manual News Refresh")
print("=" * 60)

try:
    from src.news_collector import NewsCollector
    from src.news_analyzer import NewsAnalyzer

    print("\n[1/3] Collecting news...")
    collector = NewsCollector()
    news_list = collector.collect_all_news(hours=24)

    if not news_list:
        print("[ERROR] No news collected!")
        sys.exit(1)

    print(f"[OK] Collected {len(news_list)} news items")

    print("\n[2/3] Analyzing news with AI...")
    analyzer = NewsAnalyzer()
    analyzed_news = analyzer.analyze_news_batch(news_list, max_items=50)

    print(f"[OK] Analyzed {len(analyzed_news)} news items")

    print("\n[3/3] Saving analysis...")
    analyzer.save_analysis(analyzed_news)

    high_impact = len([n for n in analyzed_news if n.get('importance', 0) >= 4])
    print(f"\n[SUCCESS] {len(analyzed_news)} news analyzed ({high_impact} high-impact)")

    # Show sample
    if analyzed_news:
        print("\nSample news:")
        sample = analyzed_news[0]
        print(f"  Title: {sample.get('title', 'N/A')}")
        print(f"  Importance: {sample.get('importance', 0)} stars")
        print(f"  Impact: {sample.get('market_impact', 'N/A')}")

except Exception as e:
    print(f"\n[ERROR] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
