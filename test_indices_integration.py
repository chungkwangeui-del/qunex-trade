"""
Test Polygon Indices Free API Integration

This script tests the new IndicesService and verifies it works correctly
with the existing polygon_service.py integration.

Run this AFTER setting POLYGON_INDICES_API_KEY and USE_FREE_INDICES=true in .env
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from web.indices_service import IndicesService, get_indices_service
from web.polygon_service import PolygonService


def test_indices_service():
    """Test IndicesService directly"""
    print("\n" + "="*70)
    print("TEST 1: IndicesService Direct Test")
    print("="*70)

    api_key = os.getenv("POLYGON_INDICES_API_KEY")

    if not api_key:
        print("[!] POLYGON_INDICES_API_KEY not found in .env")
        print("    This is optional. The app will use ETF proxy if not configured.")
        return False

    print(f"[OK] API Key found: {api_key[:10]}...")

    service = IndicesService()
    indices = service.get_indices_snapshot()

    if not indices:
        print("[X] Failed to fetch indices data")
        return False

    print(f"\n[OK] Successfully fetched {len(indices)} indices:")
    print("-" * 70)

    for ticker, data in indices.items():
        change_symbol = "[-]" if data["change"] < 0 else "[+]"
        print(f"{change_symbol} {data['name']:20s} ({ticker:3s})")
        print(f"    Value: ${data['value']:,.2f}")
        print(f"    Change: {data['change']:+.2f} ({data['change_percent']:+.2f}%)")
        print(f"    Updated: {data['updated_at']}")
        print()

    return True


def test_polygon_service_integration():
    """Test PolygonService integration with IndicesService"""
    print("\n" + "="*70)
    print("TEST 2: PolygonService Integration Test")
    print("="*70)

    use_free_indices = os.getenv("USE_FREE_INDICES", "false").lower() == "true"

    print(f"USE_FREE_INDICES = {use_free_indices}")

    polygon = PolygonService()
    indices = polygon.get_market_indices()

    if not indices:
        print("[X] Failed to fetch market indices")
        return False

    print(f"\n[OK] Successfully fetched {len(indices)} market indices:")
    print("-" * 70)

    for ticker, data in indices.items():
        change_symbol = "[-]" if data["change_percent"] < 0 else "[+]"
        print(f"{change_symbol} {data['name']:25s} ({ticker:3s})")
        print(f"    Price: ${data['price']:,.2f}")
        print(f"    Change: {data['change']:+.2f} ({data['change_percent']:+.2f}%)")
        print(f"    Prev Close: ${data['prev_close']:,.2f}")
        print()

    return True


def test_fallback_mechanism():
    """Test that fallback to ETF proxy works when Indices API is disabled"""
    print("\n" + "="*70)
    print("TEST 3: Fallback Mechanism Test")
    print("="*70)

    # Temporarily disable USE_FREE_INDICES
    original_value = os.getenv("USE_FREE_INDICES")
    os.environ["USE_FREE_INDICES"] = "false"

    polygon = PolygonService()
    # Clear cache to force fresh fetch
    polygon.cache.clear()

    indices = polygon.get_market_indices()

    # Restore original value
    if original_value:
        os.environ["USE_FREE_INDICES"] = original_value
    else:
        del os.environ["USE_FREE_INDICES"]

    if not indices:
        print("[X] Fallback to ETF proxy failed")
        return False

    print("[OK] Fallback to ETF proxy working")
    print(f"    Fetched {len(indices)} indices using ETF proxies")
    print("    Tickers:", ", ".join(indices.keys()))

    return True


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print(" POLYGON INDICES FREE API - INTEGRATION TEST")
    print("="*70)

    print("\nCurrent Configuration:")
    print(f"  POLYGON_API_KEY (Stocks): {'[OK] Set' if os.getenv('POLYGON_API_KEY') else '[X] Not set'}")
    print(f"  POLYGON_INDICES_API_KEY: {'[OK] Set' if os.getenv('POLYGON_INDICES_API_KEY') else '[!] Not set (optional)'}")
    print(f"  USE_FREE_INDICES: {os.getenv('USE_FREE_INDICES', 'false')}")

    results = []

    # Test 1: Direct IndicesService test
    try:
        result = test_indices_service()
        results.append(("IndicesService Direct Test", result))
    except Exception as e:
        print(f"[X] Test 1 failed with error: {e}")
        results.append(("IndicesService Direct Test", False))

    # Test 2: PolygonService integration
    try:
        result = test_polygon_service_integration()
        results.append(("PolygonService Integration", result))
    except Exception as e:
        print(f"[X] Test 2 failed with error: {e}")
        results.append(("PolygonService Integration", False))

    # Test 3: Fallback mechanism
    try:
        result = test_fallback_mechanism()
        results.append(("Fallback Mechanism", result))
    except Exception as e:
        print(f"[X] Test 3 failed with error: {e}")
        results.append(("Fallback Mechanism", False))

    # Summary
    print("\n" + "="*70)
    print(" TEST SUMMARY")
    print("="*70)

    for test_name, passed in results:
        status = "[OK] PASS" if passed else "[X] FAIL"
        print(f"{status:10s} - {test_name}")

    total_tests = len(results)
    passed_tests = sum(1 for _, passed in results if passed)

    print("\n" + "="*70)
    print(f"Total: {passed_tests}/{total_tests} tests passed")
    print("="*70)

    if passed_tests == total_tests:
        print("\n[OK] All tests passed! Integration is working correctly.")
    elif passed_tests > 0:
        print("\n[!] Some tests passed. Check configuration if Indices API test failed.")
        print("    Note: POLYGON_INDICES_API_KEY is optional. ETF proxy works as fallback.")
    else:
        print("\n[X] All tests failed. Please check your configuration and API keys.")

    return passed_tests == total_tests


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
