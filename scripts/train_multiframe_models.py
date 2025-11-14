#!/usr/bin/env python3
"""
Train Multi-Timeframe ML Models

Trains 3 separate XGBoost models for different investment horizons:
- Short-term (5-day forward returns): For day/swing traders
- Medium-term (20-day forward returns): For position traders
- Long-term (60-day forward returns): For long-term investors

Each model learns different patterns appropriate for its timeframe.
"""

import os
import sys
import logging
import numpy as np
from datetime import datetime

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
sys.path.insert(0, os.path.join(parent_dir, "ml"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def generate_training_data(n_samples=2000, timeframe="medium"):
    """
    Generate synthetic training data for a specific timeframe

    Different timeframes have different return distributions:
    - Short-term (5d): Smaller returns, higher volatility, more noise
    - Medium-term (20d): Moderate returns, balanced signal/noise
    - Long-term (60d): Larger returns, clearer trends, less noise

    Args:
        n_samples: Number of training samples to generate
        timeframe: "short" (5d), "medium" (20d), or "long" (60d)

    Returns:
        tuple: (X, y, feature_names)
    """
    logger.info(f"Generating {n_samples} samples for {timeframe}-term model...")

    np.random.seed(42)

    # Feature schema (same for all timeframes)
    feature_names = [
        # Technical Indicators
        "rsi", "macd", "price_to_ma50", "price_to_ma200",
        "volume_trend", "volatility", "momentum",

        # Fundamental Metrics
        "market_cap_log", "pe_ratio", "pb_ratio", "ps_ratio",
        "eps_growth", "revenue_growth", "profit_margin", "roe", "roa",
        "debt_to_equity", "current_ratio", "peg_ratio",

        # Sentiment
        "news_sentiment_avg", "news_sentiment_trend", "news_volume",
    ]

    n_features = len(feature_names)
    X = np.zeros((n_samples, n_features))

    # Generate realistic feature distributions (same for all timeframes)
    for i, feature in enumerate(feature_names):
        if feature == "rsi":
            X[:, i] = np.clip(np.random.normal(50, 15, n_samples), 0, 100)
        elif feature == "macd":
            X[:, i] = np.random.normal(0, 0.8, n_samples)
        elif feature in ["price_to_ma50", "price_to_ma200"]:
            X[:, i] = np.random.normal(1.0, 0.15, n_samples)
        elif feature == "volume_trend":
            X[:, i] = np.random.normal(0, 0.3, n_samples)
        elif feature == "volatility":
            X[:, i] = np.clip(np.random.gamma(2, 0.1, n_samples), 0, 1)
        elif feature == "momentum":
            X[:, i] = np.random.normal(0, 0.4, n_samples)
        elif feature == "market_cap_log":
            X[:, i] = np.random.normal(9.5, 1.5, n_samples)
        elif feature == "pe_ratio":
            X[:, i] = np.clip(np.random.gamma(3, 8, n_samples), 0, 100)
        elif feature == "pb_ratio":
            X[:, i] = np.clip(np.random.gamma(2, 2, n_samples), 0, 20)
        elif feature == "ps_ratio":
            X[:, i] = np.clip(np.random.gamma(2, 3, n_samples), 0, 30)
        elif feature in ["eps_growth", "revenue_growth"]:
            X[:, i] = np.random.normal(0.15, 0.25, n_samples)
        elif feature == "profit_margin":
            X[:, i] = np.clip(np.random.beta(2, 3, n_samples), 0, 1)
        elif feature in ["roe", "roa"]:
            X[:, i] = np.random.normal(0.12, 0.15, n_samples)
        elif feature == "debt_to_equity":
            X[:, i] = np.clip(np.random.gamma(2, 0.5, n_samples), 0, 5)
        elif feature == "current_ratio":
            X[:, i] = np.clip(np.random.gamma(3, 0.5, n_samples), 0.1, 5)
        elif feature == "peg_ratio":
            X[:, i] = np.clip(np.random.gamma(2, 1, n_samples), 0, 10)
        elif feature == "news_sentiment_avg":
            X[:, i] = np.random.normal(0, 0.3, n_samples)
        elif feature == "news_sentiment_trend":
            X[:, i] = np.random.normal(0, 0.4, n_samples)
        elif feature == "news_volume":
            X[:, i] = np.clip(np.random.poisson(3, n_samples), 0, 30)

    # Generate labels based on timeframe
    # Different timeframes weight features differently
    scores = np.zeros(n_samples)

    rsi_idx = feature_names.index("rsi")
    macd_idx = feature_names.index("macd")
    eps_growth_idx = feature_names.index("eps_growth")
    revenue_growth_idx = feature_names.index("revenue_growth")
    pe_ratio_idx = feature_names.index("pe_ratio")
    roe_idx = feature_names.index("roe")
    sentiment_idx = feature_names.index("news_sentiment_avg")
    sentiment_trend_idx = feature_names.index("news_sentiment_trend")
    momentum_idx = feature_names.index("momentum")
    volatility_idx = feature_names.index("volatility")

    if timeframe == "short":
        # Short-term (5 days): Technical indicators + sentiment dominate
        # Fundamentals matter less, noise is higher
        scores += ((X[:, rsi_idx] - 50) / 50) * 0.25  # RSI: 25%
        scores += X[:, macd_idx] * 0.20  # MACD: 20%
        scores += X[:, momentum_idx] * 0.25  # Momentum: 25%
        scores += X[:, sentiment_idx] * 0.15  # Sentiment: 15%
        scores += X[:, sentiment_trend_idx] * 0.10  # Sentiment trend: 10%
        scores += X[:, eps_growth_idx] * 0.05  # EPS growth: 5% (less important short-term)
        # Add more noise for short-term
        scores += np.random.normal(0, 0.15, n_samples)

    elif timeframe == "medium":
        # Medium-term (20 days): Balanced technical + fundamental
        scores += ((X[:, rsi_idx] - 50) / 50) * 0.15  # RSI: 15%
        scores += X[:, macd_idx] * 0.15  # MACD: 15%
        scores += X[:, eps_growth_idx] * 0.20  # EPS growth: 20%
        scores += X[:, revenue_growth_idx] * 0.15  # Revenue growth: 15%
        scores += (25 - X[:, pe_ratio_idx]) / 25 * 0.10  # P/E: 10%
        scores += X[:, roe_idx] * 0.15  # ROE: 15%
        scores += X[:, sentiment_idx] * 0.10  # Sentiment: 10%
        # Moderate noise
        scores += np.random.normal(0, 0.10, n_samples)

    elif timeframe == "long":
        # Long-term (60 days): Fundamentals dominate, technical less important
        scores += X[:, eps_growth_idx] * 0.30  # EPS growth: 30%
        scores += X[:, revenue_growth_idx] * 0.25  # Revenue growth: 25%
        scores += X[:, roe_idx] * 0.20  # ROE: 20%
        scores += (25 - X[:, pe_ratio_idx]) / 25 * 0.15  # P/E: 15%
        scores += ((X[:, rsi_idx] - 50) / 50) * 0.05  # RSI: 5% (less important long-term)
        scores += X[:, sentiment_idx] * 0.05  # Sentiment: 5%
        # Less noise for long-term
        scores += np.random.normal(0, 0.05, n_samples)

    # Convert scores to labels (5 classes)
    # Thresholds adjusted by timeframe
    y = np.zeros(n_samples, dtype=int)

    if timeframe == "short":
        # Tighter thresholds for short-term (smaller expected returns)
        y[scores < -0.2] = 0  # Strong Sell
        y[(scores >= -0.2) & (scores < -0.05)] = 1  # Sell
        y[(scores >= -0.05) & (scores < 0.05)] = 2  # Hold
        y[(scores >= 0.05) & (scores < 0.2)] = 3  # Buy
        y[scores >= 0.2] = 4  # Strong Buy
    elif timeframe == "medium":
        # Standard thresholds
        y[scores < -0.3] = 0
        y[(scores >= -0.3) & (scores < -0.1)] = 1
        y[(scores >= -0.1) & (scores < 0.1)] = 2
        y[(scores >= 0.1) & (scores < 0.3)] = 3
        y[scores >= 0.3] = 4
    elif timeframe == "long":
        # Wider thresholds for long-term (larger expected returns)
        y[scores < -0.4] = 0
        y[(scores >= -0.4) & (scores < -0.15)] = 1
        y[(scores >= -0.15) & (scores < 0.15)] = 2
        y[(scores >= 0.15) & (scores < 0.4)] = 3
        y[scores >= 0.4] = 4

    logger.info(f"Generated {n_samples} samples for {timeframe}-term")
    logger.info(f"Label distribution: {np.bincount(y)}")

    return X, y, feature_names


def train_multiframe_models():
    """Train all 3 timeframe models"""
    try:
        from ai_score_system import AIScoreModel

        logger.info("=" * 80)
        logger.info("MULTI-TIMEFRAME ML MODEL TRAINING")
        logger.info("=" * 80)

        # Check library versions
        import numpy
        import xgboost
        import sklearn

        logger.info(f"numpy version: {numpy.__version__}")
        logger.info(f"xgboost version: {xgboost.__version__}")
        logger.info(f"scikit-learn version: {sklearn.__version__}")
        logger.info("")

        model_dir = os.path.join(parent_dir, "ml", "models")
        os.makedirs(model_dir, exist_ok=True)

        timeframes = {
            "short": "ai_score_model_5d.pkl",
            "medium": "ai_score_model_20d.pkl",
            "long": "ai_score_model_60d.pkl",
        }

        results = {}

        for timeframe, model_filename in timeframes.items():
            logger.info("=" * 80)
            logger.info(f"TRAINING {timeframe.upper()}-TERM MODEL")
            logger.info("=" * 80)

            # Generate training data
            X, y, feature_names = generate_training_data(n_samples=2000, timeframe=timeframe)

            # Initialize model
            ai_model = AIScoreModel(model_dir=model_dir)
            ai_model.feature_names = feature_names

            # Train model
            logger.info(f"\nTraining XGBoost classifier for {timeframe}-term...")
            ai_model.train(X, y)

            # Save model
            logger.info(f"\nSaving {timeframe}-term model to {model_filename}...")
            ai_model.save(model_filename)

            # Test loading
            logger.info(f"\nTesting {timeframe}-term model load...")
            test_model = AIScoreModel(model_dir=model_dir)
            if test_model.load(model_filename):
                logger.info(f"✓ {timeframe.capitalize()}-term model loaded successfully!")

                # Test prediction
                sample_features = {name: 0.0 for name in feature_names}
                sample_features["rsi"] = 60
                sample_features["eps_growth"] = 0.20
                sample_features["revenue_growth"] = 0.15
                sample_features["news_sentiment_avg"] = 0.3

                score = test_model.predict_score(sample_features)
                logger.info(f"Test prediction ({timeframe}-term): {score}/100")
                results[timeframe] = score
            else:
                logger.error(f"✗ Failed to load {timeframe}-term model!")
                return False

            logger.info("")

        logger.info("=" * 80)
        logger.info("MULTI-TIMEFRAME TRAINING COMPLETED")
        logger.info("=" * 80)
        logger.info("Test predictions with bullish features:")
        logger.info(f"  Short-term (5d):  {results['short']}/100")
        logger.info(f"  Medium-term (20d): {results['medium']}/100")
        logger.info(f"  Long-term (60d):  {results['long']}/100")
        logger.info("")
        logger.info("Expected pattern: Long-term > Medium-term > Short-term")
        logger.info("(Fundamentals matter more for longer timeframes)")
        logger.info("=" * 80)

        return True

    except Exception as e:
        logger.error(f"Multi-timeframe training failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = train_multiframe_models()
    sys.exit(0 if success else 1)
