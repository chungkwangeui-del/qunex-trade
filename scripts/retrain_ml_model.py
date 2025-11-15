#!/usr/bin/env python3
"""
Retrain ML Model with Current Library Versions

This script retrains the AI Score ML model with the current versions of
numpy, xgboost, and scikit-learn to fix pickle compatibility issues.

Uses synthetic training data based on the feature schema to create a
compatible model file.
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


def generate_synthetic_training_data(n_samples=1000):
    """
    Generate synthetic training data for AI Score model

    Creates realistic feature distributions based on typical stock metrics:
    - Technical indicators (RSI, MACD, Moving Averages, etc.)
    - Fundamental metrics (P/E, P/B, Growth rates, etc.)
    - Sentiment scores

    Returns:
        tuple: (X, y, feature_names) where X is feature matrix, y is labels
    """
    logger.info(f"Generating {n_samples} synthetic training samples...")

    np.random.seed(42)

    # Define features (matching the production feature schema)
    feature_names = [
        # Technical Indicators
        "rsi",
        "macd",
        "price_to_ma50",
        "price_to_ma200",
        "volume_trend",
        "volatility",
        "momentum",
        # Fundamental Metrics
        "market_cap_log",
        "pe_ratio",
        "pb_ratio",
        "ps_ratio",
        "eps_growth",
        "revenue_growth",
        "profit_margin",
        "roe",
        "roa",
        "debt_to_equity",
        "current_ratio",
        "peg_ratio",
        # Sentiment
        "news_sentiment_avg",
        "news_sentiment_trend",
        "news_volume",
    ]

    n_features = len(feature_names)
    X = np.zeros((n_samples, n_features))

    # Generate realistic feature distributions
    for i, feature in enumerate(feature_names):
        if feature == "rsi":
            # RSI: 0-100, typically 30-70
            X[:, i] = np.clip(np.random.normal(50, 15, n_samples), 0, 100)

        elif feature == "macd":
            # MACD: typically -2 to +2
            X[:, i] = np.random.normal(0, 0.8, n_samples)

        elif feature in ["price_to_ma50", "price_to_ma200"]:
            # Price/MA ratio: typically 0.8-1.2
            X[:, i] = np.random.normal(1.0, 0.15, n_samples)

        elif feature == "volume_trend":
            # Volume trend: -1 to +1
            X[:, i] = np.random.normal(0, 0.3, n_samples)

        elif feature == "volatility":
            # Volatility: 0-1 (typically 0.1-0.5)
            X[:, i] = np.clip(np.random.gamma(2, 0.1, n_samples), 0, 1)

        elif feature == "momentum":
            # Momentum: -1 to +1
            X[:, i] = np.random.normal(0, 0.4, n_samples)

        elif feature == "market_cap_log":
            # Log market cap: typically 7-12 (1M to 1T)
            X[:, i] = np.random.normal(9.5, 1.5, n_samples)

        elif feature == "pe_ratio":
            # P/E ratio: typically 5-50
            X[:, i] = np.clip(np.random.gamma(3, 8, n_samples), 0, 100)

        elif feature == "pb_ratio":
            # P/B ratio: typically 0.5-10
            X[:, i] = np.clip(np.random.gamma(2, 2, n_samples), 0, 20)

        elif feature == "ps_ratio":
            # P/S ratio: typically 0.5-15
            X[:, i] = np.clip(np.random.gamma(2, 3, n_samples), 0, 30)

        elif feature in ["eps_growth", "revenue_growth"]:
            # Growth rates: typically -0.2 to +0.5
            X[:, i] = np.random.normal(0.15, 0.25, n_samples)

        elif feature == "profit_margin":
            # Profit margin: 0-0.5
            X[:, i] = np.clip(np.random.beta(2, 3, n_samples), 0, 1)

        elif feature in ["roe", "roa"]:
            # ROE/ROA: -0.2 to +0.4
            X[:, i] = np.random.normal(0.12, 0.15, n_samples)

        elif feature == "debt_to_equity":
            # Debt/Equity: 0-3
            X[:, i] = np.clip(np.random.gamma(2, 0.5, n_samples), 0, 5)

        elif feature == "current_ratio":
            # Current ratio: typically 0.5-3
            X[:, i] = np.clip(np.random.gamma(3, 0.5, n_samples), 0.1, 5)

        elif feature == "peg_ratio":
            # PEG ratio: typically 0.5-3
            X[:, i] = np.clip(np.random.gamma(2, 1, n_samples), 0, 10)

        elif feature == "news_sentiment_avg":
            # Sentiment: -1 to +1
            X[:, i] = np.random.normal(0, 0.3, n_samples)

        elif feature == "news_sentiment_trend":
            # Sentiment trend: -1 to +1
            X[:, i] = np.random.normal(0, 0.4, n_samples)

        elif feature == "news_volume":
            # News volume: 0-20 articles
            X[:, i] = np.clip(np.random.poisson(3, n_samples), 0, 30)

    # Generate labels based on feature combinations
    # Create a scoring function that mimics real stock performance prediction
    scores = np.zeros(n_samples)

    # Technical contribution (30%)
    rsi_idx = feature_names.index("rsi")
    macd_idx = feature_names.index("macd")
    scores += ((X[:, rsi_idx] - 50) / 50) * 0.15  # RSI contribution
    scores += X[:, macd_idx] * 0.15  # MACD contribution

    # Fundamental contribution (50%)
    eps_growth_idx = feature_names.index("eps_growth")
    revenue_growth_idx = feature_names.index("revenue_growth")
    pe_ratio_idx = feature_names.index("pe_ratio")
    roe_idx = feature_names.index("roe")

    scores += X[:, eps_growth_idx] * 0.20  # EPS growth
    scores += X[:, revenue_growth_idx] * 0.15  # Revenue growth
    scores += (25 - X[:, pe_ratio_idx]) / 25 * 0.10  # Lower P/E is better
    scores += X[:, roe_idx] * 0.15  # ROE contribution

    # Sentiment contribution (20%)
    sentiment_idx = feature_names.index("news_sentiment_avg")
    sentiment_trend_idx = feature_names.index("news_sentiment_trend")
    scores += X[:, sentiment_idx] * 0.15
    scores += X[:, sentiment_trend_idx] * 0.05

    # Convert scores to labels (5 classes)
    # Strong Sell: 0, Sell: 1, Hold: 2, Buy: 3, Strong Buy: 4
    y = np.zeros(n_samples, dtype=int)
    y[scores < -0.3] = 0  # Strong Sell
    y[(scores >= -0.3) & (scores < -0.1)] = 1  # Sell
    y[(scores >= -0.1) & (scores < 0.1)] = 2  # Hold
    y[(scores >= 0.1) & (scores < 0.3)] = 3  # Buy
    y[scores >= 0.3] = 4  # Strong Buy

    logger.info(f"Generated {n_samples} samples with {n_features} features")
    logger.info(f"Label distribution: {np.bincount(y)}")

    return X, y, feature_names


def retrain_model():
    """Retrain the AI Score model with current library versions"""
    try:
        from ai_score_system import AIScoreModel

        logger.info("=" * 80)
        logger.info("ML MODEL RETRAINING STARTED")
        logger.info("=" * 80)

        # Check library versions
        import numpy
        import xgboost
        import sklearn

        logger.info(f"numpy version: {numpy.__version__}")
        logger.info(f"xgboost version: {xgboost.__version__}")
        logger.info(f"scikit-learn version: {sklearn.__version__}")

        # Generate synthetic training data
        X, y, feature_names = generate_synthetic_training_data(n_samples=2000)

        # Initialize model
        model_dir = os.path.join(parent_dir, "ml", "models")
        os.makedirs(model_dir, exist_ok=True)

        ai_model = AIScoreModel(model_dir=model_dir)
        ai_model.feature_names = feature_names

        # Train model
        logger.info("\nTraining XGBoost classifier...")
        ai_model.train(X, y)

        # Save model
        logger.info("\nSaving model...")
        ai_model.save("ai_score_model.pkl")

        # Test loading
        logger.info("\nTesting model load...")
        test_model = AIScoreModel(model_dir=model_dir)
        if test_model.load("ai_score_model.pkl"):
            logger.info("Model loaded successfully!")

            # Test prediction with sample features
            sample_features = {name: 0.0 for name in feature_names}
            sample_features["rsi"] = 60  # Bullish RSI
            sample_features["eps_growth"] = 0.20  # 20% EPS growth
            sample_features["revenue_growth"] = 0.15  # 15% revenue growth
            sample_features["news_sentiment_avg"] = 0.3  # Positive sentiment

            score = test_model.predict_score(sample_features)
            logger.info(f"\nTest prediction with bullish features: {score}/100")
        else:
            logger.error("Failed to load saved model!")
            return False

        logger.info("=" * 80)
        logger.info("ML MODEL RETRAINING COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)

        return True

    except Exception as e:
        logger.error(f"Model retraining failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = retrain_model()
    sys.exit(0 if success else 1)
