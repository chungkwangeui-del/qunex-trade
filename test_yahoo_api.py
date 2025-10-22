"""
Test Yahoo Finance Market Data Service
"""

import sys
sys.path.insert(0, 'web')

from yahoo_market_service import yahoo_market_service
import json

print("=" * 60)
print("Testing Yahoo Finance Market Data Service")
print("=" * 60)

# Test 1: Market Indices
print("\n1. Testing Market Indices...")
print("-" * 60)
indices = yahoo_market_service.get_market_indices()
print(json.dumps(indices, indent=2))

# Test 2: Sector Performance
print("\n2. Testing Sector Performance...")
print("-" * 60)
sectors = yahoo_market_service.get_sector_performance()
print(json.dumps(sectors, indent=2))

# Test 3: Fear & Greed Index
print("\n3. Testing Fear & Greed Index...")
print("-" * 60)
fear_greed = yahoo_market_service.get_fear_greed_index()
print(json.dumps(fear_greed, indent=2))

# Test 4: Batch Stock Quotes
print("\n4. Testing Batch Stock Quotes (sample stocks)...")
print("-" * 60)
test_symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA']
quotes = yahoo_market_service.get_stock_batch_quotes(test_symbols)
print(json.dumps(quotes, indent=2))

print("\n" + "=" * 60)
print("All tests completed!")
print("=" * 60)
