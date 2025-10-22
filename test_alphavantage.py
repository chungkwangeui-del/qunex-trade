"""Test Alpha Vantage API"""
import sys
sys.path.append('web')

from alphavantage_market_service import alphavantage_market_service

print("Testing Alpha Vantage Market Service...")
print("=" * 50)

# Test market indices
print("\n1. Market Indices:")
indices = alphavantage_market_service.get_market_indices()
for key, value in indices.items():
    print(f"  {key.upper()}: {value['value']} ({value['changePercent']:+.2f}%)")

# Test sector performance
print("\n2. Sector Performance:")
sectors = alphavantage_market_service.get_sector_performance()
for sector, perf in sectors.items():
    print(f"  {sector}: {perf:+.2f}%")

# Test fear & greed
print("\n3. Fear & Greed Index:")
fg = alphavantage_market_service.get_fear_greed_index()
print(f"  Value: {fg['value']} - {fg['label']}")
print(f"  {fg['description']}")

print("\n" + "=" * 50)
print("Test completed!")
