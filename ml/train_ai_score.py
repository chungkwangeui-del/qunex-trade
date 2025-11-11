"""
Train Qunex AI Score Model on Real Historical Data

This script:
1. Downloads 8+ years of historical data for S&P 500 stocks
2. Calculates technical features for each time period
3. Labels data based on future performance
4. Trains XGBoost model
5. Validates on holdout data (2023-2024)
6. Saves model for production use

Run: python train_ai_score.py
"""

import os
import sys
import logging
import argparse
from datetime import datetime
import pandas as pd
import numpy as np
from tqdm import tqdm

# Add web directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'web'))

from ai_score_system import AIScoreModel, FeatureEngineer
from polygon_service import PolygonService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('training.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# S&P 500 stock symbols (Top 100 most liquid stocks for initial training)
SP500_SYMBOLS = [
    # Mega-cap tech
    'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'NVDA', 'META', 'TSLA', 'AVGO', 'ORCL',

    # Finance
    'BRK.B', 'JPM', 'V', 'MA', 'BAC', 'WFC', 'GS', 'MS', 'C', 'AXP',

    # Healthcare
    'UNH', 'JNJ', 'LLY', 'ABBV', 'MRK', 'TMO', 'ABT', 'DHR', 'PFE', 'BMY',

    # Consumer
    'WMT', 'HD', 'PG', 'KO', 'PEP', 'COST', 'MCD', 'NKE', 'SBUX', 'TGT',

    # Energy
    'XOM', 'CVX', 'COP', 'SLB', 'EOG', 'MPC', 'PSX', 'VLO', 'OXY', 'HAL',

    # Industrials
    'UPS', 'RTX', 'HON', 'UNP', 'BA', 'CAT', 'DE', 'LMT', 'GE', 'MMM',

    # Tech/Semi
    'CSCO', 'ADBE', 'CRM', 'INTC', 'AMD', 'QCOM', 'TXN', 'AMAT', 'MU', 'LRCX',

    # Communications
    'T', 'VZ', 'TMUS', 'DIS', 'CMCSA', 'NFLX', 'CHTR',

    # Consumer Discretionary
    'AMZN', 'TSLA', 'HOME', 'LOW', 'TJX', 'BKNG',

    # Materials
    'LIN', 'APD', 'ECL', 'SHW', 'FCX', 'NEM',

    # Utilities
    'NEE', 'DUK', 'SO', 'D', 'AEP'
]


def main():
    parser = argparse.ArgumentParser(description='Train Qunex AI Score Model')
    parser.add_argument('--start-date', default='2015-01-01', help='Training data start date')
    parser.add_argument('--end-date', default='2023-12-31', help='Training data end date')
    parser.add_argument('--symbols', nargs='+', default=None, help='Stock symbols (default: top 100 S&P 500)')
    parser.add_argument('--output', default='ai_score_model.pkl', help='Output model filename')
    args = parser.parse_args()

    print("="*80)
    print(" " * 20 + "QUNEX AI SCORE MODEL TRAINING")
    print("="*80)
    print()
    print("Training Configuration:")
    print(f"  Start Date: {args.start_date}")
    print(f"  End Date: {args.end_date}")
    print(f"  Symbols: {len(SP500_SYMBOLS) if args.symbols is None else len(args.symbols)}")
    print(f"  Output: {args.output}")
    print()

    # Initialize services
    polygon = PolygonService()
    ai_model = AIScoreModel()

    symbols = args.symbols if args.symbols else SP500_SYMBOLS

    # Step 1: Collect Training Data
    print("="*80)
    print("STEP 1: COLLECTING HISTORICAL DATA")
    print("="*80)
    print(f"Downloading price data for {len(symbols)} stocks...")
    print(f"Date range: {args.start_date} to {args.end_date}")
    print(f"This may take 30-60 minutes depending on API rate limits...\n")

    all_samples = []
    successful = 0
    failed = 0

    for symbol in tqdm(symbols, desc="Downloading data"):
        try:
            # Fetch historical prices
            price_data = ai_model._fetch_historical_prices(
                symbol,
                args.start_date,
                args.end_date,
                polygon
            )

            if price_data is None or len(price_data) < 250:
                logger.warning(f"Insufficient data for {symbol} (got {len(price_data) if price_data is not None else 0} days)")
                failed += 1
                continue

            # Generate training samples
            # For each trading day (after warmup period), calculate features and label
            for i in range(200, len(price_data) - 30):  # Need 200 days for features, 30 for forward return
                try:
                    sample_data = price_data.iloc[:i+1].copy()

                    # Calculate technical features
                    tech_features = FeatureEngineer.calculate_technical_features(sample_data)

                    if not tech_features:
                        continue

                    # Calculate forward return (label)
                    current_price = price_data.iloc[i]['close']
                    future_price_20d = price_data.iloc[i+20]['close']  # 20 trading days
                    forward_return = (future_price_20d / current_price) - 1

                    # Create sample
                    sample = {
                        'symbol': symbol,
                        'date': price_data.iloc[i]['date'],
                        'forward_return_20d': forward_return,
                        **tech_features
                    }

                    all_samples.append(sample)

                except Exception as e:
                    logger.error(f"Error processing {symbol} at index {i}: {e}")
                    continue

            successful += 1
            logger.info(f"✓ {symbol}: Collected {len(price_data)} days of data")

        except Exception as e:
            logger.error(f"✗ {symbol}: Failed - {e}")
            failed += 1
            continue

    print()
    print(f"Data collection complete!")
    print(f"  Successful: {successful}/{len(symbols)}")
    print(f"  Failed: {failed}/{len(symbols)}")
    print(f"  Total samples: {len(all_samples):,}")
    print()

    if len(all_samples) < 1000:
        print("ERROR: Not enough training samples!")
        print("Need at least 1000 samples. Please check your Polygon API key and try again.")
        return

    # Convert to DataFrame
    df = pd.DataFrame(all_samples)
    print(f"Training data shape: {df.shape}")
    print()

    # Save raw training data
    training_data_path = 'training_data.csv'
    df.to_csv(training_data_path, index=False)
    print(f"✓ Raw training data saved to {training_data_path}")
    print()

    # Step 2: Prepare Features and Labels
    print("="*80)
    print("STEP 2: PREPARING FEATURES AND LABELS")
    print("="*80)

    X, y = ai_model.prepare_features_and_labels(df)

    print(f"Feature matrix shape: {X.shape}")
    print(f"Features: {len(ai_model.feature_names)}")
    print(f"Samples: {len(X):,}")
    print()
    print("Label distribution:")
    label_counts = np.bincount(y.astype(int))
    label_names = ['Strong Sell', 'Sell', 'Hold', 'Buy', 'Strong Buy']
    for i, (name, count) in enumerate(zip(label_names, label_counts)):
        pct = (count / len(y)) * 100
        print(f"  {name:12} {count:6,} ({pct:5.1f}%)")
    print()

    # Step 3: Train Model
    print("="*80)
    print("STEP 3: TRAINING MODEL")
    print("="*80)
    print("Training XGBoost classifier...")
    print("This may take 5-10 minutes...\n")

    ai_model.train(X, y)

    print()
    print("✓ Model training complete!")
    print()

    # Step 4: Save Model
    print("="*80)
    print("STEP 4: SAVING MODEL")
    print("="*80)

    ai_model.save(args.output)
    print(f"✓ Model saved to models/{args.output}")
    print()

    # Step 5: Test Model on Recent Data (2024)
    print("="*80)
    print("STEP 5: VALIDATION ON RECENT DATA (2024)")
    print("="*80)
    print("Testing model on 2024 data (not seen during training)...\n")

    test_symbols = ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'META']
    print(f"Testing on: {', '.join(test_symbols)}\n")

    for symbol in test_symbols:
        try:
            # Get recent data
            recent_data = ai_model._fetch_historical_prices(
                symbol,
                '2023-01-01',
                '2024-12-31',
                polygon
            )

            if recent_data is None or len(recent_data) < 200:
                print(f"✗ {symbol}: Insufficient recent data")
                continue

            # Calculate features for latest day
            features = FeatureEngineer.calculate_technical_features(recent_data)

            if not features:
                print(f"✗ {symbol}: Could not calculate features")
                continue

            # Predict score
            score = ai_model.predict_score(features)

            # Get actual forward return (if available)
            if len(recent_data) >= 220:
                current_price = recent_data.iloc[-20]['close']
                future_price = recent_data.iloc[-1]['close']
                actual_return = ((future_price / current_price) - 1) * 100
                print(f"✓ {symbol:6} AI Score: {score:3d}/100  |  Actual 20-day return: {actual_return:+6.2f}%")
            else:
                print(f"✓ {symbol:6} AI Score: {score:3d}/100")

        except Exception as e:
            print(f"✗ {symbol}: Error - {e}")

    print()
    print("="*80)
    print(" " * 25 + "TRAINING COMPLETE!")
    print("="*80)
    print()
    print("Next steps:")
    print("  1. Review training.log for detailed results")
    print("  2. Test the model: python test_ai_score.py")
    print("  3. Integrate into web app: Update polygon_service.py")
    print()


if __name__ == '__main__':
    main()
