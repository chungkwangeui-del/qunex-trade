#!/usr/bin/env python3
"""
Test ETF detection to ensure we skip fundamental data collection for ETFs
"""

import os
import sys

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
web_dir = os.path.join(parent_dir, "web")
sys.path.insert(0, web_dir)
sys.path.insert(0, parent_dir)

# Set up environment
from dotenv import load_dotenv
load_dotenv()

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Import after sys.path setup
sys.path.insert(0, os.path.join(parent_dir, "scripts"))
from cron_update_ai_scores import is_etf
from polygon_service import PolygonService


def test_etf_detection():
    """Test ETF detection function"""
    print("=" * 80)
    print("ETF DETECTION TEST")
    print("=" * 80)

    # Initialize Polygon service
    api_key = os.getenv("POLYGON_API_KEY")
    polygon = PolygonService(api_key=api_key) if api_key else None

    if not polygon:
        print("\nWARNING: No POLYGON_API_KEY - using fallback detection only")
        print("Set POLYGON_API_KEY in .env for accurate ETF detection\n")

    # Test tickers
    test_cases = [
        ("SPY", True, "SPDR S&P 500 ETF - Popular ETF"),
        ("QQQ", True, "Invesco QQQ ETF - Nasdaq 100"),
        ("AAPL", False, "Apple Inc - Stock"),
        ("TSLA", False, "Tesla Inc - Stock"),
        ("VOO", True, "Vanguard S&P 500 ETF"),
        ("NVDA", False, "Nvidia Corporation - Stock"),
    ]

    print("\nTesting ETF detection:\n")
    results = []

    for ticker, expected_etf, description in test_cases:
        result = is_etf(ticker, polygon)
        status = "OK" if result == expected_etf else "FAIL"
        results.append((ticker, result, expected_etf, status))

        print(f"  {ticker:6} - Expected: {'ETF' if expected_etf else 'Stock':5} | Detected: {'ETF' if result else 'Stock':5} | {status:4} - {description}")

    print("\n" + "=" * 80)
    passed = sum(1 for _, _, _, status in results if status == "OK")
    total = len(results)
    print(f"Test Results: {passed}/{total} passed")

    if passed == total:
        print("SUCCESS - All ETF detections correct!")
    else:
        print("PARTIAL - Some detections failed (may need Polygon API key)")

    print("=" * 80)

    return passed == total


if __name__ == "__main__":
    try:
        success = test_etf_detection()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nERROR - Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
