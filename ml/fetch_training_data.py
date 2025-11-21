"""
Fetch training data from Polygon API for ML model training.
Uses DVC for data versioning.
"""

import os
import sys
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

# Configure logging
try:
    from web.logging_config import configure_structured_logging, get_logger
    configure_structured_logging()
    logger = get_logger(__name__)
except ImportError:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

def fetch_training_data():
    """Fetch historical stock data from Polygon API for training."""
    try:
        from web.polygon_service import PolygonService

        polygon = PolygonService()

        # Training tickers (diverse set)
        tickers = [
            "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "JNJ",
            "WMT", "PG", "MA", "UNH", "HD", "DIS", "BAC", "XOM", "PFE", "CSCO",
        ]

        all_data = []

        # Fetch last 365 days of data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)

        logger.info(f"Fetching training data from {start_date.date()} to {end_date.date()}")

        for ticker in tickers:
            try:
                # Get historical bars
                bars = polygon.get_aggregates(
                    ticker=ticker,
                    multiplier=1,
                    timespan="day",
                    from_date=start_date.strftime("%Y-%m-%d"),
                    to_date=end_date.strftime("%Y-%m-%d"),
                )

                if bars and len(bars) > 0:
                    for bar in bars:
                        all_data.append(
                            {
                                "ticker": ticker,
                                "date": datetime.fromtimestamp(bar["t"] / 1000).date(),
                                "open": bar.get("o"),
                                "high": bar.get("h"),
                                "low": bar.get("l"),
                                "close": bar.get("c"),
                                "volume": bar.get("v"),
                            }
                        )

                    logger.info(f"  ✓ {ticker}: {len(bars)} bars")
                else:
                    logger.warning(f"  ✗ {ticker}: No data")

            except Exception as e:
                logger.error(f"  ✗ {ticker}: {e}")
                continue

        # Convert to DataFrame
        df = pd.DataFrame(all_data)

        if df.empty:
            raise ValueError("No training data fetched")

        # Calculate technical features
        df = df.sort_values(["ticker", "date"])

        for ticker in df["ticker"].unique():
            ticker_df = df[df["ticker"] == ticker].copy()

            # Price changes
            ticker_df["price_change"] = ticker_df["close"].pct_change()
            ticker_df["price_change_5d"] = ticker_df["close"].pct_change(periods=5)
            ticker_df["price_change_20d"] = ticker_df["close"].pct_change(periods=20)

            # Moving averages
            ticker_df["ma_5"] = ticker_df["close"].rolling(window=5).mean()
            ticker_df["ma_20"] = ticker_df["close"].rolling(window=20).mean()
            ticker_df["ma_50"] = ticker_df["close"].rolling(window=50).mean()

            # Volume
            ticker_df["volume_ma_20"] = ticker_df["volume"].rolling(window=20).mean()
            ticker_df["volume_ratio"] = ticker_df["volume"] / ticker_df["volume_ma_20"]

            # RSI (simplified)
            delta = ticker_df["close"].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            ticker_df["rsi"] = 100 - (100 / (1 + rs))

            # Update main dataframe
            df.update(ticker_df)

        # Drop NaN rows
        df = df.dropna()

        # Save to CSV
        output_dir = os.path.join(os.path.dirname(__file__), "data")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "training_data.csv")
        df.to_csv(output_path, index=False)

        logger.info(f"\n✓ Training data saved: {len(df)} rows")
        logger.info(f"  Location: {output_path}")

        return True

    except Exception as e:
        logger.error(f"✗ Error fetching training data: {e}")
        return False


if __name__ == "__main__":
    success = fetch_training_data()
    sys.exit(0 if success else 1)
