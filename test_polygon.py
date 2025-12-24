"""
Test Polygon.io API Integration
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add web directory to path
sys.path.insert(0, 'web')

from polygon_service import PolygonService

def test_polygon():
    """Test all Polygon.io service methods"""

    print("=" * 60)
    print("POLYGON.IO API TEST")
    print("=" * 60)

    # Initialize service
    polygon = PolygonService()
    print(f"\n[OK] Polygon service initialized")
    print(f"API Key: {polygon.api_key[:10]}...")

    # Test 1: Market Status
    print("\n" + "-" * 60)
    print("TEST 1: Market Status")
    print("-" * 60)
    status = polygon.get_market_status()
    if status:
        print(f"[OK] Market: {status.get('market')}")
        print(f"     NYSE: {status.get('exchanges', {}).get('nyse')}")
        print(f"     NASDAQ: {status.get('exchanges', {}).get('nasdaq')}")
    else:
        print("[ERROR] Failed to get market status")

    # Test 2: Stock Quote
    print("\n" + "-" * 60)
    print("TEST 2: Stock Quote (AAPL)")
    print("-" * 60)
    quote = polygon.get_stock_quote('AAPL')
    if quote:
        print(f"[OK] Ticker: {quote.get('ticker')}")
        print(f"     Price: ${quote.get('price')}")
        print(f"     Size: {quote.get('size')}")
        print(f"     Exchange: {quote.get('exchange')}")
    else:
        print("[ERROR] Failed to get quote")

    # Test 3: Previous Close
    print("\n" + "-" * 60)
    print("TEST 3: Previous Close (MSFT)")
    print("-" * 60)
    prev = polygon.get_previous_close('MSFT')
    if prev:
        print(f"[OK] Ticker: {prev.get('ticker')}")
        print(f"     Open: ${prev.get('open')}")
        print(f"     High: ${prev.get('high')}")
        print(f"     Low: ${prev.get('low')}")
        print(f"     Close: ${prev.get('close')}")
        print(f"     Volume: {prev.get('volume'):,}")
    else:
        print("[ERROR] Failed to get previous close")

    # Test 4: Historical Data
    print("\n" + "-" * 60)
    print("TEST 4: Historical Data (GOOGL, 7 days)")
    print("-" * 60)
    from datetime import datetime, timedelta
    to_date = datetime.now().strftime('%Y-%m-%d')
    from_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

    history = polygon.get_aggregates('GOOGL', 1, 'day', from_date, to_date)
    if history:
        print(f"[OK] Got {len(history)} bars")
        if history:
            latest = history[-1]
            print(f"     Latest: Open=${latest.get('open')}, Close=${latest.get('close')}, Volume={latest.get('volume'):,}")
    else:
        print("[ERROR] Failed to get historical data")

    # Test 5: Ticker Details
    print("\n" + "-" * 60)
    print("TEST 5: Ticker Details (TSLA)")
    print("-" * 60)
    details = polygon.get_ticker_details('TSLA')
    if details:
        print(f"[OK] Name: {details.get('name')}")
        print(f"     Market: {details.get('market')}")
        print(f"     Exchange: {details.get('primary_exchange')}")
        print(f"     Type: {details.get('type')}")
        print(f"     Active: {details.get('active')}")
    else:
        print("[ERROR] Failed to get ticker details")

    # Test 6: Search Tickers
    print("\n" + "-" * 60)
    print("TEST 6: Search Tickers (query: 'apple')")
    print("-" * 60)
    results = polygon.search_tickers('apple', limit=5)
    if results:
        print(f"[OK] Found {len(results)} results")
        for r in results[:3]:
            print(f"     - {r.get('ticker')}: {r.get('name')}")
    else:
        print("[ERROR] Failed to search tickers")

    # Test 7: Gainers
    print("\n" + "-" * 60)
    print("TEST 7: Top Gainers")
    print("-" * 60)
    gainers = polygon.get_gainers_losers('gainers')
    if gainers:
        print(f"[OK] Got {len(gainers)} gainers")
        for i, g in enumerate(gainers[:5], 1):
            print(f"     {i}. {g.get('ticker')}: {g.get('change_percent'):.2f}% (${g.get('price')})")
    else:
        print("[ERROR] Failed to get gainers")

    # Test 8: Losers
    print("\n" + "-" * 60)
    print("TEST 8: Top Losers")
    print("-" * 60)
    losers = polygon.get_gainers_losers('losers')
    if losers:
        print(f"[OK] Got {len(losers)} losers")
        for i, l in enumerate(losers[:5], 1):
            print(f"     {i}. {l.get('ticker')}: {l.get('change_percent'):.2f}% (${l.get('price')})")
    else:
        print("[ERROR] Failed to get losers")

    # Test 9: Technical Indicators
    print("\n" + "-" * 60)
    print("TEST 9: Technical Indicators (NVDA)")
    print("-" * 60)
    technicals = polygon.get_technical_indicators('NVDA', days=30)
    if technicals:
        print(f"[OK] Current Price: ${technicals.get('current_price')}")
        print(f"     SMA 20: ${technicals.get('sma_20'):.2f}" if technicals.get('sma_20') else "     SMA 20: N/A")
        print(f"     SMA 50: ${technicals.get('sma_50'):.2f}" if technicals.get('sma_50') else "     SMA 50: N/A")
        print(f"     RSI 14: {technicals.get('rsi_14'):.2f}" if technicals.get('rsi_14') else "     RSI 14: N/A")
        print(f"     52W High: ${technicals.get('high_52w')}")
        print(f"     52W Low: ${technicals.get('low_52w')}")
    else:
        print("[ERROR] Failed to get technical indicators")

    # Test 10: Market Snapshot
    print("\n" + "-" * 60)
    print("TEST 10: Market Snapshot (Multiple Tickers)")
    print("-" * 60)
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META']
    snapshot = polygon.get_market_snapshot(tickers)
    if snapshot:
        print(f"[OK] Got snapshot for {len(snapshot)} tickers")
        for ticker, data in list(snapshot.items())[:3]:
            print(f"     {ticker}: ${data.get('price')} ({data.get('change_percent'):.2f}%)")
    else:
        print("[ERROR] Failed to get market snapshot")

    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETED!")
    print("=" * 60)


if __name__ == '__main__':
    test_polygon()
