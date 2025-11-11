"""
Test trained AI Score model on recent data
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'web'))

from ai_score_system import AIScoreModel, FeatureEngineer
from polygon_service import PolygonService

print("="*80)
print("TESTING QUNEX AI SCORE MODEL")
print("="*80)

# Load trained model
print("\nLoading trained model...")
model = AIScoreModel()
if not model.load('ai_score_model.pkl'):
    print("ERROR: Could not load model!")
    exit(1)

print("Model loaded successfully!")
print(f"Features: {len(model.feature_names)}")

# Initialize Polygon service
polygon = PolygonService()

# Test stocks
test_stocks = [
    'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'TSLA',
    'META', 'AMZN', 'AMD', 'NFLX', 'DIS'
]

print(f"\nTesting on {len(test_stocks)} stocks...\n")
print(f"{'Symbol':<8} {'AI Score':<10} {'Rating':<15}")
print("-" * 40)

results = []

for symbol in test_stocks:
    try:
        # Get recent price data
        price_data = model._fetch_historical_prices(
            symbol,
            '2023-01-01',
            '2024-11-11',
            polygon
        )

        if price_data is None or len(price_data) < 200:
            print(f"{symbol:<8} ERROR: Insufficient data")
            continue

        # Calculate features
        features = FeatureEngineer.calculate_technical_features(price_data)

        if not features:
            print(f"{symbol:<8} ERROR: Could not calculate features")
            continue

        # Predict AI score
        score = model.predict_score(features)

        # Determine rating
        if score >= 75:
            rating = "Strong Buy"
        elif score >= 60:
            rating = "Buy"
        elif score >= 40:
            rating = "Hold"
        elif score >= 25:
            rating = "Sell"
        else:
            rating = "Strong Sell"

        print(f"{symbol:<8} {score:<10} {rating:<15}")
        results.append({
            'symbol': symbol,
            'score': score,
            'rating': rating
        })

    except Exception as e:
        print(f"{symbol:<8} ERROR: {str(e)[:30]}")

print("\n" + "="*80)
print("TEST COMPLETE")
print("="*80)
print(f"\nSuccessfully scored {len(results)}/{len(test_stocks)} stocks")

# Show distribution
if results:
    scores = [r['score'] for r in results]
    print(f"\nScore Distribution:")
    print(f"  Average: {sum(scores)/len(scores):.1f}")
    print(f"  Min: {min(scores)}")
    print(f"  Max: {max(scores)}")
