#!/usr/bin/env python3
"""
Test Polygon API to diagnose why technical indicators are failing
"""

import os
import sys
from datetime import datetime, timedelta

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
web_dir = os.path.join(parent_dir, "web")
sys.path.insert(0, web_dir)
sys.path.insert(0, parent_dir)

# Set up environment
from dotenv import load_dotenv

load_dotenv()

import logging

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

from polygon_service import PolygonService


def test_polygon_api():
    """Test Polygon API with TSLA to see what's happening"""
    print("=" * 80)
    print("POLYGON API DIAGNOSTIC TEST")
    print("=" * 80)

    # Check API key
    api_key = os.getenv("POLYGON_API_KEY")
    if not api_key:
        print("\nERROR: POLYGON_API_KEY not set in environment")
        return False

    print(f"\nOK - API Key found: {api_key[:8]}...{api_key[-4:]}")

    # Initialize service
    polygon = PolygonService(api_key=api_key)

    # Test with TSLA
    ticker = "TSLA"
    print(f"\n[1/3] Testing get_aggregates for {ticker}...")
    from_date = (datetime.now() - timedelta(days=250)).strftime("%Y-%m-%d")
    to_date = datetime.now().strftime("%Y-%m-%d")

    aggs = polygon.get_aggregates(ticker, 1, "day", from_date, to_date, limit=250)

    if aggs:
        print(f"  OK - Retrieved {len(aggs)} bars")
        print(f"  OK - First bar: {aggs[0]}")
        print(f"  OK - Last bar: {aggs[-1]}")
    else:
        print(f"  ERROR - No aggregates data returned")
        return False

    # Test technical indicators
    print(f"\n[2/3] Testing get_technical_indicators for {ticker}...")
    indicators = polygon.get_technical_indicators(ticker, days=200)

    if indicators:
        print(f"  OK - Technical indicators calculated:")
        for key, value in indicators.items():
            if value is not None:
                if isinstance(value, float):
                    print(f"    {key}: {value:.2f}")
                else:
                    print(f"    {key}: {value}")
    else:
        print(f"  ERROR - No technical indicators returned")
        return False

    # Test with another ticker for comparison
    ticker2 = "AAPL"
    print(f"\n[3/3] Testing get_technical_indicators for {ticker2} (comparison)...")
    indicators2 = polygon.get_technical_indicators(ticker2, days=200)

    if indicators2:
        print(f"  OK - Technical indicators for {ticker2}:")
        for key, value in indicators2.items():
            if value is not None:
                if isinstance(value, float):
                    print(f"    {key}: {value:.2f}")
                else:
                    print(f"    {key}: {value}")
    else:
        print(f"  ERROR - No technical indicators for {ticker2}")

    print("\n" + "=" * 80)
    print("SUCCESS - DIAGNOSTIC TEST COMPLETE")
    print("=" * 80)
    return True


if __name__ == "__main__":
    try:
        success = test_polygon_api()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nERROR - Test failed with exception: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
