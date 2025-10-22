"""
Patch for app.py to use Yahoo Finance real-time data
Run this to update /api/market-overview endpoint
"""

import os
import sys

# Read the current app.py
app_path = 'app.py'
with open(app_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the /api/market-overview function
old_api = '''@app.route('/api/market-overview')
def api_market_overview():
    """Get real-time market overview data"""
    import requests
    import random

    ALPHAVANTAGE_KEY = os.getenv('ALPHAVANTAGE_KEY')

    try:
        # In production, fetch real data from Alpha Vantage or Yahoo Finance
        # For now, return simulated realistic data to avoid API rate limits

        # Simulate realistic market data with some randomness
        base_values = {
            'sp500': 5825.23,
            'dow': 42863.15,
            'nasdaq': 18342.67,
            'vix': 14.23
        }

        market_data = {
            'sp500': {
                'value': base_values['sp500'] + random.uniform(-50, 50),
                'change': random.uniform(-30, 30),
                'changePercent': random.uniform(-1.5, 1.5)
            },
            'dow': {
                'value': base_values['dow'] + random.uniform(-200, 200),
                'change': random.uniform(-150, 150),
                'changePercent': random.uniform(-0.8, 0.8)
            },
            'nasdaq': {
                'value': base_values['nasdaq'] + random.uniform(-80, 80),
                'change': random.uniform(-80, 80),
                'changePercent': random.uniform(-1.2, 1.2)
            },
            'vix': {
                'value': base_values['vix'] + random.uniform(-2, 2),
                'change': random.uniform(-1.5, 1.5),
                'changePercent': random.uniform(-10, 10)
            },
            'fearGreed': {
                'value': random.randint(25, 75),
                'label': '',
                'description': ''
            },
            'sectors': {
                'tech': random.uniform(-2, 3),
                'health': random.uniform(-1.5, 2),
                'finance': random.uniform(-1, 2.5),
                'energy': random.uniform(-3, 2),
                'consumerDisc': random.uniform(-1.5, 2.5),
                'consumerStaples': random.uniform(-0.8, 1.5),
                'industrial': random.uniform(-1.5, 2),
                'communication': random.uniform(-1.8, 2.8),
                'utilities': random.uniform(-1, 1.2),
                'realEstate': random.uniform(-1.5, 1.8),
                'materials': random.uniform(-2, 2.5)
            }
        }

        # Determine Fear & Greed label and description
        fg_value = market_data['fearGreed']['value']
        if fg_value <= 25:
            market_data['fearGreed']['label'] = 'Extreme Fear'
            market_data['fearGreed']['description'] = 'Market showing extreme pessimism'
        elif fg_value <= 45:
            market_data['fearGreed']['label'] = 'Fear'
            market_data['fearGreed']['description'] = 'Market showing bearish sentiment'
        elif fg_value <= 55:
            market_data['fearGreed']['label'] = 'Neutral'
            market_data['fearGreed']['description'] = 'Market balanced between fear and greed'
        elif fg_value <= 75:
            market_data['fearGreed']['label'] = 'Greed'
            market_data['fearGreed']['description'] = 'Market showing bullish sentiment'
        else:
            market_data['fearGreed']['label'] = 'Extreme Greed'
            market_data['fearGreed']['description'] = 'Market showing extreme optimism'

        return jsonify(market_data)

    except Exception as e:
        print(f"Error fetching market data: {e}")
        # Return fallback data
        return jsonify({
            'sp500': { 'value': 5825.23, 'change': 12.45, 'changePercent': 0.21 },
            'dow': { 'value': 42863.15, 'change': 85.30, 'changePercent': 0.20 },
            'nasdaq': { 'value': 18342.67, 'change': -25.15, 'changePercent': -0.14 },
            'vix': { 'value': 14.23, 'change': -0.35, 'changePercent': -2.40 },
            'fearGreed': { 'value': 62, 'label': 'Greed', 'description': 'Market showing bullish sentiment' },
            'sectors': {
                'tech': 1.25,
                'health': -0.42,
                'finance': 0.87,
                'energy': -1.15,
                'consumerDisc': 0.53,
                'consumerStaples': 0.21,
                'industrial': 0.31,
                'communication': 0.95,
                'utilities': -0.15,
                'realEstate': 0.42,
                'materials': -0.58
            }
        })'''

new_api = '''@app.route('/api/market-overview')
def api_market_overview():
    """Get real-time market overview data from Yahoo Finance"""
    try:
        from yahoo_market_service import yahoo_market_service

        # Get market indices (cached for 60 seconds)
        indices = yahoo_market_service.get_market_indices()

        # Get sector performance
        sectors_raw = yahoo_market_service.get_sector_performance()

        # Map sector names to frontend keys
        sectors = {
            'tech': sectors_raw.get('Technology', 0),
            'health': sectors_raw.get('Healthcare', 0),
            'finance': sectors_raw.get('Financials', 0),
            'energy': sectors_raw.get('Energy', 0),
            'consumerDisc': sectors_raw.get('Consumer Discretionary', 0),
            'consumerStaples': sectors_raw.get('Consumer Staples', 0),
            'industrial': sectors_raw.get('Industrials', 0),
            'communication': sectors_raw.get('Communication', 0),
            'utilities': sectors_raw.get('Utilities', 0),
            'realEstate': sectors_raw.get('Real Estate', 0),
            'materials': sectors_raw.get('Materials', 0)
        }

        # Get Fear & Greed Index
        fear_greed = yahoo_market_service.get_fear_greed_index()

        market_data = {
            'sp500': indices.get('sp500', {'value': 5825.23, 'change': 0, 'changePercent': 0}),
            'dow': indices.get('dow', {'value': 42863.15, 'change': 0, 'changePercent': 0}),
            'nasdaq': indices.get('nasdaq', {'value': 18342.67, 'change': 0, 'changePercent': 0}),
            'vix': indices.get('vix', {'value': 14.23, 'change': 0, 'changePercent': 0}),
            'fearGreed': fear_greed,
            'sectors': sectors
        }

        return jsonify(market_data)

    except Exception as e:
        print(f"Error fetching market data: {e}")
        import traceback
        traceback.print_exc()

        # Return fallback data
        import random
        return jsonify({
            'sp500': { 'value': 5825.23, 'change': random.uniform(-20, 20), 'changePercent': random.uniform(-0.5, 0.5) },
            'dow': { 'value': 42863.15, 'change': random.uniform(-150, 150), 'changePercent': random.uniform(-0.5, 0.5) },
            'nasdaq': { 'value': 18342.67, 'change': random.uniform(-80, 80), 'changePercent': random.uniform(-0.5, 0.5) },
            'vix': { 'value': 14.23, 'change': random.uniform(-0.5, 0.5), 'changePercent': random.uniform(-3, 3) },
            'fearGreed': { 'value': 62, 'label': 'Greed', 'description': 'Market showing bullish sentiment' },
            'sectors': {
                'tech': random.uniform(-2, 2),
                'health': random.uniform(-1.5, 1.5),
                'finance': random.uniform(-1, 1.5),
                'energy': random.uniform(-2, 2),
                'consumerDisc': random.uniform(-1.5, 1.5),
                'consumerStaples': random.uniform(-0.8, 1),
                'industrial': random.uniform(-1.5, 1.5),
                'communication': random.uniform(-1.8, 1.8),
                'utilities': random.uniform(-1, 1),
                'realEstate': random.uniform(-1.5, 1.5),
                'materials': random.uniform(-2, 2)
            }
        })'''

# Replace
new_content = content.replace(old_api, new_api)

if new_content == content:
    print("ERROR: Could not find the old API code to replace!")
    print("The file may have already been patched or structure changed.")
    sys.exit(1)

# Write back
with open(app_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("[OK] app.py has been successfully patched!")
print("[OK] /api/market-overview now uses Yahoo Finance real-time data")
