"""Test Finnhub API"""
import sys
sys.path.append('web')

from finnhub_market_service import finnhub_market_service

print("Testing Finnhub Market Service...")
print("=" * 50)

# Test market indices
print("\n1. Market Indices:")
indices = finnhub_market_service.get_market_indices()
for key, value in indices.items():
    print(f"  {key.upper()}: ${value['value']:,.2f} ({value['changePercent']:+.2f}%)")

# Test sector performance
print("\n2. Sector Performance:")
sectors = finnhub_market_service.get_sector_performance()
for sector, perf in sectors.items():
    print(f"  {sector}: {perf:+.2f}%")

# Test fear & greed
print("\n3. Fear & Greed Index:")
fg = finnhub_market_service.get_fear_greed_index()
print(f"  Value: {fg['value']} - {fg['label']}")
print(f"  {fg['description']}")

print("\n" + "=" * 50)
print("Test completed!")
