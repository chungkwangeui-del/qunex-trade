"""
Qunex AI Score - Machine Learning Based Stock Scoring System

This module trains ML models on historical data to predict stock performance
and generate accurate AI scores (0-100) for stocks.

Architecture:
1. Data Collection: Gather historical technical, fundamental, sentiment data
2. Feature Engineering: Calculate 50+ features per stock per timeframe
3. Label Generation: Forward returns (1-month, 3-month)
4. Model Training: XGBoost, Random Forest, Neural Networks
5. Validation: Backtest on 2023-2024 holdout data
6. Production: Real-time scoring API
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
import pickle
import os
import sys
from datetime import timedelta
from typing import List
from typing import Optional
from typing import Tuple

# ML libraries
try:
    import xgboost as xgb
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.model_selection import train_test_split, cross_val_score
    from sklearn.metrics import accuracy_score, classification_report, roc_auc_score
    from sklearn.preprocessing import StandardScaler
except ImportError:
    print("WARNING: ML libraries not installed. Run: pip install xgboost scikit-learn")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "web"))
from polygon_service import PolygonService

# Configure logging
try:
    from web.logging_config import configure_structured_logging, get_logger
    configure_structured_logging()
    logger = get_logger(__name__)
except ImportError:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

class FeatureEngineer:
    """
    Calculate technical, fundamental, and sentiment features for ML model
    """

    @staticmethod
    def calculate_technical_features(price_data: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate technical indicators from price/volume data

        Args:
            price_data: DataFrame with columns: date, open, high, low, close, volume

        Returns:
            Dictionary of technical features
        """
        features = {}

        if len(price_data) < 200:
            logger.warning("Insufficient data for technical features")
            return features

        close = price_data["close"].values
        high = price_data["high"].values
        low = price_data["low"].values
        volume = price_data["volume"].values

        # Moving Averages
        features["ma_20"] = np.mean(close[-20:])
        features["ma_50"] = np.mean(close[-50:])
        features["ma_200"] = np.mean(close[-200:])

        # Price position relative to MAs
        current_price = close[-1]
        features["price_to_ma20"] = (current_price / features["ma_20"]) - 1
        features["price_to_ma50"] = (current_price / features["ma_50"]) - 1
        features["price_to_ma200"] = (current_price / features["ma_200"]) - 1

        # MA trends
        features["ma20_slope"] = (features["ma_20"] - np.mean(close[-25:-5])) / np.mean(
            close[-25:-5]
        )
        features["ma50_slope"] = (features["ma_50"] - np.mean(close[-55:-5])) / np.mean(
            close[-55:-5]
        )

        # RSI (14-day)
        features["rsi_14"] = FeatureEngineer._calculate_rsi(close, 14)

        # MACD
        macd, signal = FeatureEngineer._calculate_macd(close)
        features["macd"] = macd
        features["macd_signal"] = signal
        features["macd_histogram"] = macd - signal

        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = FeatureEngineer._calculate_bollinger_bands(close, 20, 2)
        features["bb_position"] = (
            (current_price - bb_lower) / (bb_upper - bb_lower) if bb_upper != bb_lower else 0.5
        )
        features["bb_width"] = (bb_upper - bb_lower) / bb_middle if bb_middle != 0 else 0

        # Volume features
        features["volume_ma_20"] = np.mean(volume[-20:])
        features["volume_ratio"] = (
            volume[-1] / features["volume_ma_20"] if features["volume_ma_20"] > 0 else 1
        )

        # Momentum features
        features["return_1d"] = (close[-1] / close[-2]) - 1 if len(close) > 1 else 0
        features["return_5d"] = (close[-1] / close[-6]) - 1 if len(close) > 5 else 0
        features["return_20d"] = (close[-1] / close[-21]) - 1 if len(close) > 20 else 0
        features["return_60d"] = (close[-1] / close[-61]) - 1 if len(close) > 60 else 0

        # Volatility (standard deviation of returns)
        returns_20d = np.diff(close[-21:]) / close[-21:-1]
        features["volatility_20d"] = np.std(returns_20d) * np.sqrt(252)  # Annualized

        # ATR (Average True Range)
        features["atr_14"] = FeatureEngineer._calculate_atr(high[-14:], low[-14:], close[-14:])

        return features

    @staticmethod
    def _calculate_rsi(prices: np.ndarray, period: int = 14) -> float:
        """Calculate Relative Strength Index"""
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])

        if avg_loss == 0:
            return 100

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    @staticmethod
    def _calculate_macd(
        prices: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9
    ) -> Tuple[float, float]:
        """Calculate MACD and Signal line using EMA series."""
        if len(prices) < slow + signal:
            return 0.0, 0.0

        ema_fast_series = FeatureEngineer._ema_series(prices, fast)
        ema_slow_series = FeatureEngineer._ema_series(prices, slow)
        macd_series = ema_fast_series - ema_slow_series
        signal_series = FeatureEngineer._ema_series(macd_series, signal)

        return macd_series[-1], signal_series[-1]

    @staticmethod
    def _ema(prices: np.ndarray, period: int) -> float:
        """Calculate Exponential Moving Average (last value)."""
        multiplier = 2 / (period + 1)
        ema = prices[0]
        for price in prices[1:]:
            ema = (price - ema) * multiplier + ema
        return ema

    @staticmethod
    def _ema_series(prices: np.ndarray, period: int) -> np.ndarray:
        """Calculate full EMA series for a price array."""
        if len(prices) == 0:
            return np.array([])
        multiplier = 2 / (period + 1)
        ema_values = [prices[0]]
        for price in prices[1:]:
            ema_values.append((price - ema_values[-1]) * multiplier + ema_values[-1])
        return np.array(ema_values)

    @staticmethod
    def _calculate_bollinger_bands(
        prices: np.ndarray, period: int = 20, num_std: float = 2
    ) -> Tuple[float, float, float]:
        """Calculate Bollinger Bands"""
        middle = np.mean(prices[-period:])
        std = np.std(prices[-period:])
        upper = middle + (num_std * std)
        lower = middle - (num_std * std)
        return upper, middle, lower

    @staticmethod
    def _calculate_atr(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> float:
        """Calculate Average True Range"""
        tr_list = []
        for i in range(1, len(close)):
            tr = max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))
            tr_list.append(tr)
        return np.mean(tr_list) if tr_list else 0

    @staticmethod
    def calculate_fundamental_features(financials: Dict) -> Dict[str, float]:
        """
        Calculate fundamental features from financial data

        Args:
            financials: Dict containing financial metrics

        Returns:
            Dictionary of fundamental features
        """
        features = {}

        # Valuation ratios
        features["pe_ratio"] = financials.get("pe_ratio", 0)
        features["pb_ratio"] = financials.get("pb_ratio", 0)
        features["ps_ratio"] = financials.get("ps_ratio", 0)
        features["peg_ratio"] = financials.get("peg_ratio", 0)

        # Profitability
        features["profit_margin"] = financials.get("profit_margin", 0)
        features["operating_margin"] = financials.get("operating_margin", 0)
        features["roe"] = financials.get("return_on_equity", 0)
        features["roa"] = financials.get("return_on_assets", 0)

        # Growth rates
        features["revenue_growth"] = financials.get("revenue_growth_yoy", 0)
        features["earnings_growth"] = financials.get("earnings_growth_yoy", 0)

        # Financial health
        features["debt_to_equity"] = financials.get("debt_to_equity", 0)
        features["current_ratio"] = financials.get("current_ratio", 0)

        # Dividend
        features["dividend_yield"] = financials.get("dividend_yield", 0)

        return features

    @staticmethod
    def calculate_sentiment_features(news_data: List[Dict]) -> Dict[str, float]:
        """
        Calculate sentiment features from news data

        Args:
            news_data: List of news articles with sentiment scores

        Returns:
            Dictionary of sentiment features
        """
        features = {}

        if not news_data:
            features["news_sentiment_avg"] = 0
            features["news_sentiment_trend"] = 0
            features["news_volume"] = 0
            return features

        # Average sentiment
        sentiments = [article.get("sentiment", 0) for article in news_data]
        features["news_sentiment_avg"] = np.mean(sentiments)

        # Sentiment trend (recent vs older)
        if len(sentiments) >= 10:
            recent = np.mean(sentiments[:5])
            older = np.mean(sentiments[5:10])
            features["news_sentiment_trend"] = recent - older
        else:
            features["news_sentiment_trend"] = 0

        # News volume
        features["news_volume"] = len(news_data)

        return features

class AIScoreModel:
    """
    Machine Learning model for predicting stock performance and generating AI scores
    """

    def __init__(self, model_dir: str = "models"):
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)

        self.model = None
        self.scaler = StandardScaler()
        self.feature_names = []
        self.is_trained = False

    def collect_training_data(
        self, symbols: List[str], start_date: str, end_date: str, polygon: PolygonService
    ) -> pd.DataFrame:
        """
        Collect historical data for training

        Args:
            symbols: List of stock symbols
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            polygon: PolygonService instance

        Returns:
            DataFrame with features and labels
        """
        logger.info(
            f"Collecting training data for {len(symbols)} symbols from {start_date} to {end_date}"
        )

        all_data = []

        for symbol in symbols:
            try:
                # Get historical price data
                price_data = self._fetch_historical_prices(symbol, start_date, end_date, polygon)

                if price_data is None or len(price_data) < 200:
                    logger.warning(f"Insufficient data for {symbol}")
                    continue

                # Generate samples for each month
                for i in range(
                    200, len(price_data) - 30
                ):  # Need 200 for features, 30 for forward return
                    sample_data = price_data.iloc[: i + 1].copy()

                    # Calculate features
                    tech_features = FeatureEngineer.calculate_technical_features(sample_data)

                    # Calculate forward return (label)
                    current_price = price_data.iloc[i]["close"]
                    future_price = price_data.iloc[i + 20]["close"]  # 20 trading days (~1 month)
                    forward_return = (future_price / current_price) - 1

                    # Combine features
                    sample = {
                        "symbol": symbol,
                        "date": price_data.iloc[i]["date"],
                        "forward_return_20d": forward_return,
                        **tech_features,
                    }

                    all_data.append(sample)

                logger.info(f"Collected {len(all_data)} samples for {symbol}")

            except Exception as e:
                logger.error(f"Error collecting data for {symbol}: {e}", exc_info=True)
                continue

        df = pd.DataFrame(all_data)
        logger.info(f"Total training samples: {len(df)}")

        return df

    def _fetch_historical_prices(
        self, symbol: str, start_date: str, end_date: str, polygon: PolygonService
    ) -> Optional[pd.DataFrame]:
        """Fetch historical price data from Polygon"""
        try:
            endpoint = f"/v2/aggs/ticker/{symbol}/range/1/day/{start_date}/{end_date}"
            params = {"adjusted": "true", "sort": "asc", "limit": 50000}

            data = polygon._make_request(endpoint, params)

            if not data or "results" not in data:
                return None

            results = data["results"]

            df = pd.DataFrame(results)
            df.rename(
                columns={
                    "o": "open",
                    "h": "high",
                    "l": "low",
                    "c": "close",
                    "v": "volume",
                    "t": "timestamp",
                },
                inplace=True,
            )
            df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
            df = df[["date", "open", "high", "low", "close", "volume"]]

            return df

        except Exception as e:
            logger.error(f"Error fetching historical prices for {symbol}: {e}", exc_info=True)
            return None

    def prepare_features_and_labels(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prepare features (X) and labels (y) for training

        Args:
            df: DataFrame with features and forward returns

        Returns:
            X (features), y (labels)
        """

        # Create classification labels based on forward returns
        # Strong Buy: > 10%, Buy: 5-10%, Hold: -5 to 5%, Sell: -10 to -5%, Strong Sell: < -10%
        def label_return(ret):
            if ret > 0.10:
                return 4  # Strong Buy
            elif ret > 0.05:
                return 3  # Buy
            elif ret > -0.05:
                return 2  # Hold
            elif ret > -0.10:
                return 1  # Sell
            else:
                return 0  # Strong Sell

        df["label"] = df["forward_return_20d"].apply(label_return)

        # Select feature columns (exclude meta columns and label)
        feature_cols = [
            col
            for col in df.columns
            if col not in ["symbol", "date", "forward_return_20d", "label"]
        ]
        self.feature_names = feature_cols

        X = df[feature_cols].values
        y = df["label"].values

        # Remove any NaN or inf values
        mask = np.isfinite(X).all(axis=1)
        X = X[mask]
        y = y[mask]

        logger.info(f"Prepared {len(X)} samples with {len(feature_cols)} features")
        logger.info(f"Label distribution: {np.bincount(y.astype(int))}")

        return X, y

    def train(self, X: np.ndarray, y: np.ndarray):
        """
        Train the AI Score model

        Args:
            X: Feature matrix
            y: Labels
        """
        logger.info("Training AI Score model...")

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        # Train XGBoost model
        self.model = xgb.XGBClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.1,
            random_state=42,
            eval_metric="mlogloss",
        )

        self.model.fit(X_train_scaled, y_train)

        # Evaluate
        y_pred = self.model.predict(X_test_scaled)
        accuracy = accuracy_score(y_test, y_pred)

        logger.info(f"Model accuracy: {accuracy:.4f}")
        logger.info("\nClassification Report:")
        logger.info(
            classification_report(
                y_test, y_pred, target_names=["Strong Sell", "Sell", "Hold", "Buy", "Strong Buy"]
            )
        )

        self.is_trained = True

    def predict_score(self, features: Dict[str, float]) -> int:
        """
        Predict AI score (0-100) for a stock

        Args:
            features: Dictionary of features

        Returns:
            AI score (0-100)
        """
        if not self.is_trained:
            logger.warning("Model not trained yet!")
            return 50

        # Prepare feature vector
        X = np.array([[features.get(feat, 0) for feat in self.feature_names]])
        X_scaled = self.scaler.transform(X)

        # Get prediction probabilities
        proba = self.model.predict_proba(X_scaled)[0]

        # Convert to 0-100 score
        # Weighted average: Strong Sell=0, Sell=25, Hold=50, Buy=75, Strong Buy=100
        score = proba[0] * 0 + proba[1] * 25 + proba[2] * 50 + proba[3] * 75 + proba[4] * 100

        return int(score)

    def save(self, filename: str = "ai_score_model.pkl"):
        """Save trained model to disk"""
        if not self.is_trained:
            logger.warning("Cannot save untrained model")
            return

        model_path = os.path.join(self.model_dir, filename)

        model_data = {
            "model": self.model,
            "scaler": self.scaler,
            "feature_names": self.feature_names,
        }

        with open(model_path, "wb") as f:
            pickle.dump(model_data, f)

        logger.info(f"Model saved to {model_path}")

    def load(self, filename: str = "ai_score_model.pkl"):
        """Load trained model from disk with numpy compatibility handling"""
        model_path = os.path.join(self.model_dir, filename)

        if not os.path.exists(model_path):
            logger.warning(f"Model file not found: {model_path}")
            return False

        try:
            # Try loading with default pickle
            # Security note: Only loading model files we created ourselves
            with open(model_path, "rb") as f:
                model_data = pickle.load(f)  # nosec B301 - loading trusted model files
        except (ModuleNotFoundError, AttributeError) as e:
            # Handle numpy version incompatibility
            logger.warning(f"Model pickle incompatible with current numpy version: {e}")
            logger.warning("Attempting to load with compatibility mode...")

            try:
                # Try with encoding parameter for older pickle files
                with open(model_path, "rb") as f:
                    model_data = pickle.load(f, encoding="latin1")  # nosec B301
                logger.info("Model loaded successfully with latin1 encoding")
            except Exception as e2:
                logger.error(f"Failed to load model even with compatibility mode: {e2}")
                logger.error(
                    "Model needs to be retrained with current numpy/sklearn/xgboost versions"
                )
                return False

        try:
            self.model = model_data["model"]
            self.scaler = model_data["scaler"]
            self.feature_names = model_data["feature_names"]
            self.is_trained = True

            logger.info(f"Model loaded successfully from {model_path}")
            logger.info(f"Model type: {type(self.model).__name__}")
            logger.info(f"Features: {len(self.feature_names)}")
            return True
        except Exception as e:
            logger.error(f"Error extracting model components: {e}")
            return False

class MultiTimeframeAIScoreModel:
    """
    Multi-timeframe AI Score predictor

    Loads and manages 3 separate models for different investment horizons:
    - Short-term (5-day): For day/swing traders
    - Medium-term (20-day): For position traders
    - Long-term (60-day): For long-term investors
    """

    def __init__(self, model_dir: str = "models"):
        self.model_dir = model_dir
        self.short_term_model = None
        self.medium_term_model = None
        self.long_term_model = None

    def load_all_models(self) -> bool:
        """
        Load all 3 timeframe models

        Returns:
            True if all models loaded successfully
        """
        logger.info("Loading multi-timeframe AI Score models...")

        # Load short-term model (5-day)
        self.short_term_model = AIScoreModel(model_dir=self.model_dir)
        short_loaded = self.short_term_model.load("ai_score_model_5d.pkl")

        # Load medium-term model (20-day)
        self.medium_term_model = AIScoreModel(model_dir=self.model_dir)
        medium_loaded = self.medium_term_model.load("ai_score_model_20d.pkl")

        # Load long-term model (60-day)
        self.long_term_model = AIScoreModel(model_dir=self.model_dir)
        long_loaded = self.long_term_model.load("ai_score_model_60d.pkl")

        if short_loaded and medium_loaded and long_loaded:
            logger.info("✓ All 3 timeframe models loaded successfully")
            return True
        else:
            logger.warning(
                f"Some models failed to load: short={short_loaded}, medium={medium_loaded}, long={long_loaded}"
            )
            return False

    def predict_all_timeframes(self, features: Dict[str, float]) -> Dict[str, int]:
        """
        Predict AI scores for all timeframes

        Args:
            features: Dictionary of stock features

        Returns:
            Dictionary with keys: short_term_score, medium_term_score, long_term_score
        """
        scores = {}

        if self.short_term_model and self.short_term_model.is_trained:
            scores["short_term_score"] = self.short_term_model.predict_score(features)
        else:
            scores["short_term_score"] = None
            logger.warning("Short-term model not available")

        if self.medium_term_model and self.medium_term_model.is_trained:
            scores["medium_term_score"] = self.medium_term_model.predict_score(features)
        else:
            scores["medium_term_score"] = None
            logger.warning("Medium-term model not available")

        if self.long_term_model and self.long_term_model.is_trained:
            scores["long_term_score"] = self.long_term_model.predict_score(features)
        else:
            scores["long_term_score"] = None
            logger.warning("Long-term model not available")

        return scores

    def get_ratings(self, scores: Dict[str, int]) -> Dict[str, str]:
        """
        Convert scores to ratings for all timeframes

        Args:
            scores: Dictionary with timeframe scores

        Returns:
            Dictionary with ratings (Strong Sell, Sell, Hold, Buy, Strong Buy)
        """

        def score_to_rating(score: int) -> str:
            if score >= 75:
                return "Strong Buy"
            elif score >= 60:
                return "Buy"
            elif score >= 40:
                return "Hold"
            elif score >= 25:
                return "Sell"
            else:
                return "Strong Sell"

        ratings = {}

        if scores.get("short_term_score") is not None:
            ratings["short_term_rating"] = score_to_rating(scores["short_term_score"])
        else:
            ratings["short_term_rating"] = None

        if scores.get("medium_term_score") is not None:
            ratings["medium_term_rating"] = score_to_rating(scores["medium_term_score"])
        else:
            ratings["medium_term_rating"] = None

        if scores.get("long_term_score") is not None:
            ratings["long_term_rating"] = score_to_rating(scores["long_term_score"])
        else:
            ratings["long_term_rating"] = None

        return ratings

if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)

    # Initialize
    polygon = PolygonService()
    ai_model = AIScoreModel()

    # S&P 500 symbols (sample - you'd want all 500)
    sp500_symbols = [
        "AAPL",
        "MSFT",
        "GOOGL",
        "AMZN",
        "NVDA",
        "META",
        "TSLA",
        "BRK.B",
        "UNH",
        "JNJ",
        "V",
        "WMT",
        "JPM",
        "PG",
        "XOM",
        "MA",
        "HD",
        "CVX",
        "MRK",
        "ABBV",
        "PEP",
        "KO",
        "COST",
        "AVGO",
        "TMO",
        "MCD",
        "CSCO",
        "ACN",
        "LLY",
        "ABT",
    ]

    print("=" * 80)
    print("QUNEX AI SCORE - ML MODEL TRAINING")
    print("=" * 80)

    # Collect training data (2015-2023)
    print("\n[1/4] Collecting historical data...")
    training_data = ai_model.collect_training_data(
        symbols=sp500_symbols, start_date="2015-01-01", end_date="2023-12-31", polygon=polygon
    )

    # Prepare features and labels
    print("\n[2/4] Preparing features and labels...")
    X, y = ai_model.prepare_features_and_labels(training_data)

    # Train model
    print("\n[3/4] Training model...")
    ai_model.train(X, y)

    # Save model
    print("\n[4/4] Saving model...")
    ai_model.save()

    print("\n" + "=" * 80)
    print("TRAINING COMPLETE!")
    print("=" * 80)
