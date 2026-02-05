"""
Test Polygon.io API Integration
"""

import sys
from dotenv import load_dotenv
from datetime import timedelta

# Load environment variables
load_dotenv()

# Add web directory to path
sys.path.insert(0, 'web')

from polygon_service import PolygonService
import logging

logger = logging.getLogger(__name__)

def test_polygon():
    """Test all Polygon.io service methods"""

    logger.info("=" * 60)
    logger.info("POLYGON.IO API TEST")
    logger.info("=" * 60)

    # Initialize service
    polygon = PolygonService()
    logger.info("\n[OK] Polygon service initialized")
    logger.info(f"API Key: {polygon.api_key[:10]}...")

    # Test 1: Market Status
    logger.info("\n" + "-" * 60)
    logger.info("TEST 1: Market Status")
    logger.info("-" * 60)
    status = polygon.get_market_status()
    if status:
        logger.info(f"[OK] Market: {status.get('market')}")
        logger.info(f"     NYSE: {status.get('exchanges', {}).get('nyse')}")
        logger.info(f"     NASDAQ: {status.get('exchanges', {}).get('nasdaq')}")
    else:
        logger.info("[ERROR] Failed to get market status")

    # Test 2: Stock Quote
    logger.info("\n" + "-" * 60)
    logger.info("TEST 2: Stock Quote (AAPL)")
    logger.info("-" * 60)
    quote = polygon.get_stock_quote('AAPL')
    if quote:
        logger.info(f"[OK] Ticker: {quote.get('ticker')}")
        logger.info(f"     Price: ${quote.get('price')}")
        logger.info(f"     Size: {quote.get('size')}")
        logger.info(f"     Exchange: {quote.get('exchange')}")
    else:
        logger.info("[ERROR] Failed to get quote")

    # Test 3: Previous Close
    logger.info("\n" + "-" * 60)
    logger.info("TEST 3: Previous Close (MSFT)")
    logger.info("-" * 60)
    prev = polygon.get_previous_close('MSFT')
    if prev:
        logger.info(f"[OK] Ticker: {prev.get('ticker')}")
        logger.info(f"     Open: ${prev.get('open')}")
        logger.info(f"     High: ${prev.get('high')}")
        logger.info(f"     Low: ${prev.get('low')}")
        logger.info(f"     Close: ${prev.get('close')}")
        logger.info(f"     Volume: {prev.get('volume'):,}")
    else:
        logger.info("[ERROR] Failed to get previous close")

    # Test 4: Historical Data
    logger.info("\n" + "-" * 60)
    logger.info("TEST 4: Historical Data (GOOGL, 7 days)")
    logger.info("-" * 60)
    from datetime import datetime, timedelta
    to_date = datetime.now().strftime('%Y-%m-%d')
    from_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

    history = polygon.get_aggregates('GOOGL', 1, 'day', from_date, to_date)
    if history:
        logger.info(f"[OK] Got {len(history)} bars")
        if history:
            latest = history[-1]
            logger.info(f"     Latest: Open=${latest.get('open')}, Close=${latest.get('close')}, Volume={latest.get('volume'):,}")
    else:
        logger.info("[ERROR] Failed to get historical data")

    # Test 5: Ticker Details
    logger.info("\n" + "-" * 60)
    logger.info("TEST 5: Ticker Details (TSLA)")
    logger.info("-" * 60)
    details = polygon.get_ticker_details('TSLA')
    if details:
        logger.info(f"[OK] Name: {details.get('name')}")
        logger.info(f"     Market: {details.get('market')}")
        logger.info(f"     Exchange: {details.get('primary_exchange')}")
        logger.info(f"     Type: {details.get('type')}")
        logger.info(f"     Active: {details.get('active')}")
    else:
        logger.info("[ERROR] Failed to get ticker details")

    # Test 6: Search Tickers
    logger.info("\n" + "-" * 60)
    logger.info("TEST 6: Search Tickers (query: 'apple')")
    logger.info("-" * 60)
    results = polygon.search_tickers('apple', limit=5)
    if results:
        logger.info(f"[OK] Found {len(results)} results")
        for r in results[:3]:
            logger.info(f"     - {r.get('ticker')}: {r.get('name')}")
    else:
        logger.info("[ERROR] Failed to search tickers")

    # Test 7: Gainers
    logger.info("\n" + "-" * 60)
    logger.info("TEST 7: Top Gainers")
    logger.info("-" * 60)
    gainers = polygon.get_gainers_losers('gainers')
    if gainers:
        logger.info(f"[OK] Got {len(gainers)} gainers")
        for i, g in enumerate(gainers[:5], 1):
            logger.info(f"     {i}. {g.get('ticker')}: {g.get('change_percent'):.2f}% (${g.get('price')})")
    else:
        logger.info("[ERROR] Failed to get gainers")

    # Test 8: Losers
    logger.info("\n" + "-" * 60)
    logger.info("TEST 8: Top Losers")
    logger.info("-" * 60)
    losers = polygon.get_gainers_losers('losers')
    if losers:
        logger.info(f"[OK] Got {len(losers)} losers")
        for i, l in enumerate(losers[:5], 1):
            logger.info(f"     {i}. {l.get('ticker')}: {l.get('change_percent'):.2f}% (${l.get('price')})")
    else:
        logger.info("[ERROR] Failed to get losers")

    # Test 9: Technical Indicators
    logger.info("\n" + "-" * 60)
    logger.info("TEST 9: Technical Indicators (NVDA)")
    logger.info("-" * 60)
    technicals = polygon.get_technical_indicators('NVDA', days=30)
    if technicals:
        logger.info(f"[OK] Current Price: ${technicals.get('current_price')}")
        logger.info(f"     SMA 20: ${technicals.get('sma_20'):.2f}" if technicals.get('sma_20') else "     SMA 20: N/A")
        logger.info(f"     SMA 50: ${technicals.get('sma_50'):.2f}" if technicals.get('sma_50') else "     SMA 50: N/A")
        logger.info(f"     RSI 14: {technicals.get('rsi_14'):.2f}" if technicals.get('rsi_14') else "     RSI 14: N/A")
        logger.info(f"     52W High: ${technicals.get('high_52w')}")
        logger.info(f"     52W Low: ${technicals.get('low_52w')}")
    else:
        logger.info("[ERROR] Failed to get technical indicators")

    # Test 10: Market Snapshot
    logger.info("\n" + "-" * 60)
    logger.info("TEST 10: Market Snapshot (Multiple Tickers)")
    logger.info("-" * 60)
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META']
    snapshot = polygon.get_market_snapshot(tickers)
    if snapshot:
        logger.info(f"[OK] Got snapshot for {len(snapshot)} tickers")
        for ticker, data in list(snapshot.items())[:3]:
            logger.info(f"     {ticker}: ${data.get('price')} ({data.get('change_percent'):.2f}%)")
    else:
        logger.info("[ERROR] Failed to get market snapshot")

    logger.info("\n" + "=" * 60)
    logger.info("ALL TESTS COMPLETED!")
    logger.info("=" * 60)

if __name__ == '__main__':
    test_polygon()
