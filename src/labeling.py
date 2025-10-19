"""
Labeling System for Surge Detection
Labels stocks based on future price movements
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Tuple


class SurgeLabeler:
    """Label stocks based on surge patterns"""

    def __init__(self, config):
        self.config = config
        self.time_windows = config['surge']['time_windows']
        self.thresholds = config['surge']['surge_thresholds']
        self.default_threshold = config['surge']['default_threshold']
        self.volume_surge_multiplier = config['surge']['volume_surge_multiplier']
        self.logger = logging.getLogger(__name__)

    def calculate_future_returns(self, df: pd.DataFrame, window: int) -> pd.Series:
        """
        Calculate forward returns for a given window (exact day)

        Args:
            df: DataFrame with stock data
            window: Number of days to look ahead

        Returns:
            Series with forward returns at exact window day
        """
        # Group by ticker and calculate future returns
        future_returns = df.groupby('ticker')['close'].shift(-window) / df['close'] - 1
        return future_returns

    def calculate_max_return_within_window(self, df: pd.DataFrame, window: int) -> pd.Series:
        """
        Calculate MAXIMUM return achieved within a given window (OPTIMIZED)
        Uses vectorized pandas operations for speed

        Args:
            df: DataFrame with stock data
            window: Number of days to look ahead

        Returns:
            Series with maximum return achieved within window
        """
        df = df.copy().sort_values(['ticker', 'date'])

        # For each row, calculate rolling max of future prices within window
        max_returns = []

        for ticker in df['ticker'].unique():
            ticker_df = df[df['ticker'] == ticker].copy()

            # For each row, get max of next 'window' rows
            max_future_prices = []
            closes = ticker_df['close'].values

            for i in range(len(closes)):
                # Get next 'window' prices
                future_prices = closes[i+1:min(i+1+window, len(closes))]

                if len(future_prices) > 0:
                    max_price = np.max(future_prices)
                    max_ret = (max_price - closes[i]) / closes[i]
                else:
                    max_ret = np.nan

                max_future_prices.append(max_ret)

            ticker_df['max_return_temp'] = max_future_prices
            max_returns.append(ticker_df[['max_return_temp']])

        combined = pd.concat(max_returns)
        return combined['max_return_temp']

    def label_surge_binary(self, df: pd.DataFrame, window: int = 5,
                          threshold: float = None) -> pd.DataFrame:
        """
        Create binary labels for surge detection

        Args:
            df: DataFrame with stock data
            window: Days to look ahead
            threshold: Threshold for surge (default from config)

        Returns:
            DataFrame with surge labels
        """
        df = df.copy()
        if threshold is None:
            threshold = self.default_threshold

        # Calculate future returns
        df[f'future_return_{window}d'] = self.calculate_future_returns(df, window)

        # Create binary label
        df[f'surge_{window}d'] = (df[f'future_return_{window}d'] >= threshold).astype(int)

        # Log statistics
        surge_count = df[f'surge_{window}d'].sum()
        total_count = df[f'surge_{window}d'].notna().sum()
        surge_pct = surge_count / total_count * 100 if total_count > 0 else 0

        self.logger.info(f"Window {window}d, Threshold {threshold:.1%}: "
                        f"{surge_count:,} surges ({surge_pct:.2f}%) out of {total_count:,}")

        return df

    def label_surge_multiclass(self, df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
        """
        Create multi-class labels for surge detection
        Classes: 0=no_surge, 1=mild, 2=moderate, 3=strong, 4=extreme

        Args:
            df: DataFrame with stock data
            window: Days to look ahead

        Returns:
            DataFrame with multi-class labels
        """
        df = df.copy()

        # Calculate future returns if not already present
        if f'future_return_{window}d' not in df.columns:
            df[f'future_return_{window}d'] = self.calculate_future_returns(df, window)

        # Create multi-class labels
        conditions = [
            df[f'future_return_{window}d'] < self.thresholds['mild'],
            (df[f'future_return_{window}d'] >= self.thresholds['mild']) &
            (df[f'future_return_{window}d'] < self.thresholds['moderate']),
            (df[f'future_return_{window}d'] >= self.thresholds['moderate']) &
            (df[f'future_return_{window}d'] < self.thresholds['strong']),
            (df[f'future_return_{window}d'] >= self.thresholds['strong']) &
            (df[f'future_return_{window}d'] < self.thresholds['extreme']),
            df[f'future_return_{window}d'] >= self.thresholds['extreme']
        ]

        choices = [0, 1, 2, 3, 4]
        df[f'surge_class_{window}d'] = np.select(conditions, choices, default=np.nan)

        # Log statistics
        for i, label in enumerate(['no_surge', 'mild', 'moderate', 'strong', 'extreme']):
            count = (df[f'surge_class_{window}d'] == i).sum()
            pct = count / df[f'surge_class_{window}d'].notna().sum() * 100
            self.logger.info(f"Class {i} ({label}): {count:,} ({pct:.2f}%)")

        return df

    def detect_volume_surge(self, df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
        """
        Detect volume surges

        Args:
            df: DataFrame with stock data
            window: Window for calculating average volume

        Returns:
            DataFrame with volume surge indicators
        """
        df = df.copy()

        # Calculate average volume
        df['avg_volume'] = df.groupby('ticker')['volume'].rolling(window=window).mean().reset_index(0, drop=True)

        # Detect volume surge
        df['volume_surge'] = (df['volume'] >= df['avg_volume'] * self.volume_surge_multiplier).astype(int)

        # Calculate volume ratio
        df['volume_ratio'] = df['volume'] / df['avg_volume']

        return df

    def detect_gap_up(self, df: pd.DataFrame, threshold: float = 0.05) -> pd.DataFrame:
        """
        Detect gap-up patterns

        Args:
            df: DataFrame with stock data
            threshold: Minimum gap percentage

        Returns:
            DataFrame with gap-up indicators
        """
        df = df.copy()

        # Calculate gap
        df['prev_close'] = df.groupby('ticker')['close'].shift(1)
        df['gap_pct'] = (df['open'] - df['prev_close']) / df['prev_close']

        # Detect gap-up
        df['gap_up'] = (df['gap_pct'] >= threshold).astype(int)

        return df

    def label_all_windows(self, df: pd.DataFrame, label_type: str = 'binary') -> pd.DataFrame:
        """
        Label data for all time windows

        Args:
            df: DataFrame with stock data
            label_type: 'binary' or 'multiclass'

        Returns:
            DataFrame with labels for all windows
        """
        df = df.copy()

        for window in self.time_windows:
            if label_type == 'binary':
                df = self.label_surge_binary(df, window)
            elif label_type == 'multiclass':
                df = self.label_surge_multiclass(df, window)

        # Add volume surge detection
        df = self.detect_volume_surge(df)

        # Add gap-up detection
        df = self.detect_gap_up(df)

        return df

    def analyze_surge_patterns(self, df: pd.DataFrame, window: int = 5) -> Dict:
        """
        Analyze characteristics of surge patterns

        Args:
            df: DataFrame with labeled data
            window: Time window to analyze

        Returns:
            Dictionary with surge pattern statistics
        """
        surge_col = f'surge_{window}d'

        if surge_col not in df.columns:
            df = self.label_surge_binary(df, window)

        surge_stocks = df[df[surge_col] == 1]
        non_surge_stocks = df[df[surge_col] == 0]

        analysis = {
            'total_samples': len(df),
            'surge_samples': len(surge_stocks),
            'surge_rate': len(surge_stocks) / len(df) * 100,

            # Price characteristics
            'avg_price_surge': surge_stocks['close'].mean(),
            'avg_price_non_surge': non_surge_stocks['close'].mean(),

            # Volume characteristics
            'avg_volume_surge': surge_stocks['volume'].mean(),
            'avg_volume_non_surge': non_surge_stocks['volume'].mean(),

            # Returns
            'avg_return_surge': surge_stocks[f'future_return_{window}d'].mean(),
            'max_return_surge': surge_stocks[f'future_return_{window}d'].max(),
            'min_return_surge': surge_stocks[f'future_return_{window}d'].min(),

            # Volume surge correlation
            'volume_surge_in_surge': surge_stocks['volume_surge'].mean() if 'volume_surge' in surge_stocks.columns else None,
            'volume_surge_in_non_surge': non_surge_stocks['volume_surge'].mean() if 'volume_surge' in non_surge_stocks.columns else None,
        }

        # Log analysis
        self.logger.info(f"\n=== Surge Pattern Analysis ({window}d window) ===")
        for key, value in analysis.items():
            if isinstance(value, float):
                self.logger.info(f"{key}: {value:.4f}")
            else:
                self.logger.info(f"{key}: {value}")

        return analysis

    def create_training_labels(self, df: pd.DataFrame, target_window: int = 5,
                              label_type: str = 'binary') -> Tuple[pd.DataFrame, str]:
        """
        Create labels for training

        Args:
            df: DataFrame with stock data
            target_window: Target prediction window
            label_type: 'binary' or 'multiclass'

        Returns:
            Tuple of (DataFrame with labels, target column name)
        """
        df = df.copy()

        if label_type == 'binary':
            df = self.label_surge_binary(df, target_window)
            target_col = f'surge_{target_window}d'
        elif label_type == 'multiclass':
            df = self.label_surge_multiclass(df, target_window)
            target_col = f'surge_class_{target_window}d'
        else:
            raise ValueError(f"Unknown label_type: {label_type}")

        # Add supplementary labels
        df = self.detect_volume_surge(df)
        df = self.detect_gap_up(df)

        # Remove rows with missing labels (at the end of the time series)
        df = df.dropna(subset=[target_col])

        self.logger.info(f"Created training labels: {len(df)} samples, target: {target_col}")

        return df, target_col

    def balance_dataset(self, df: pd.DataFrame, target_col: str,
                       method: str = 'undersample') -> pd.DataFrame:
        """
        Balance the dataset

        Args:
            df: DataFrame with labeled data
            target_col: Target column name
            method: 'undersample', 'oversample', or 'none'

        Returns:
            Balanced DataFrame
        """
        if method == 'none':
            return df

        df = df.copy()

        # Get class counts
        class_counts = df[target_col].value_counts()
        self.logger.info(f"Class distribution before balancing:\n{class_counts}")

        if method == 'undersample':
            # Undersample majority class
            min_count = class_counts.min()
            balanced_dfs = []

            for class_value in class_counts.index:
                class_df = df[df[target_col] == class_value]
                sampled_df = class_df.sample(n=min(len(class_df), min_count), random_state=42)
                balanced_dfs.append(sampled_df)

            balanced_df = pd.concat(balanced_dfs, ignore_index=True)

        elif method == 'oversample':
            # Oversample minority class
            max_count = class_counts.max()
            balanced_dfs = []

            for class_value in class_counts.index:
                class_df = df[df[target_col] == class_value]
                sampled_df = class_df.sample(n=max_count, replace=True, random_state=42)
                balanced_dfs.append(sampled_df)

            balanced_df = pd.concat(balanced_dfs, ignore_index=True)

        else:
            raise ValueError(f"Unknown balancing method: {method}")

        # Shuffle
        balanced_df = balanced_df.sample(frac=1, random_state=42).reset_index(drop=True)

        self.logger.info(f"Class distribution after balancing:\n{balanced_df[target_col].value_counts()}")

        return balanced_df
