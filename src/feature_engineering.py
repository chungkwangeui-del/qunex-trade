"""
Feature Engineering Module
Creates technical indicators and features for ML/DL models
"""

import pandas as pd
import numpy as np
import logging
from typing import List, Dict
import warnings
warnings.filterwarnings('ignore')

try:
    import talib as ta
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False
    logging.warning("TA-Lib not available. Using ta library instead.")

try:
    import pandas_ta as pta
    PANDAS_TA_AVAILABLE = True
except ImportError:
    PANDAS_TA_AVAILABLE = False
    logging.warning("pandas-ta not available. Using basic ta library instead.")
    # Basic TA library imports
    from ta import trend, momentum, volatility, volume as ta_volume


class FeatureEngineer:
    """Create features for stock prediction"""

    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)

    def add_price_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add price-based features"""
        df = df.copy()

        # Price changes for multiple periods
        for period in [1, 2, 3, 5, 7, 10, 15, 20]:
            df[f'return_{period}d'] = df.groupby('ticker')['close'].pct_change(periods=period)
            df[f'high_low_range_{period}d'] = (
                df.groupby('ticker')['high'].rolling(period).max() -
                df.groupby('ticker')['low'].rolling(period).min()
            ).reset_index(0, drop=True) / df['close']

        # Volatility
        for window in [5, 10, 20]:
            df[f'volatility_{window}d'] = df.groupby('ticker')['return_1d'].rolling(window).std().reset_index(0, drop=True)

        # Price position in range
        df['price_position'] = (df['close'] - df['low']) / (df['high'] - df['low'] + 1e-10)

        # Gaps
        df['gap_open'] = df.groupby('ticker')['open'].shift(1) / df.groupby('ticker')['close'].shift(1) - 1
        df['gap_close'] = df['close'] / df['open'] - 1

        # Candle body and shadow
        df['body'] = abs(df['close'] - df['open']) / df['open']
        df['upper_shadow'] = (df['high'] - df[['close', 'open']].max(axis=1)) / df['open']
        df['lower_shadow'] = (df[['close', 'open']].min(axis=1) - df['low']) / df['open']

        self.logger.info("Price features added")
        return df

    def add_moving_averages(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add moving average features"""
        df = df.copy()

        # Simple Moving Averages
        for window in [5, 10, 20, 50, 100, 200]:
            df[f'sma_{window}'] = df.groupby('ticker')['close'].rolling(window=window).mean().reset_index(0, drop=True)
            df[f'price_to_sma_{window}'] = df['close'] / df[f'sma_{window}'] - 1

        # Exponential Moving Averages
        for window in [9, 12, 21, 26, 50]:
            df[f'ema_{window}'] = df.groupby('ticker')['close'].ewm(span=window, adjust=False).mean().reset_index(0, drop=True)
            df[f'price_to_ema_{window}'] = df['close'] / df[f'ema_{window}'] - 1

        # Moving average crosses
        df['sma_cross_50_200'] = (df['sma_50'] / df['sma_200'] - 1) if 'sma_50' in df.columns and 'sma_200' in df.columns else 0
        df['ema_cross_12_26'] = (df['ema_12'] / df['ema_26'] - 1) if 'ema_12' in df.columns and 'ema_26' in df.columns else 0

        self.logger.info("Moving average features added")
        return df

    def add_momentum_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add momentum indicators"""
        df = df.copy()

        grouped = df.groupby('ticker')

        for ticker, group in grouped:
            if len(group) < 50:
                continue

            try:
                if PANDAS_TA_AVAILABLE:
                    # RSI
                    df.loc[group.index, 'rsi_14'] = pta.rsi(group['close'], length=14)
                    # Stochastic Oscillator
                    stoch = pta.stoch(group['high'], group['low'], group['close'])
                    if stoch is not None and not stoch.empty:
                        df.loc[group.index, 'stoch_k'] = stoch.iloc[:, 0]
                        df.loc[group.index, 'stoch_d'] = stoch.iloc[:, 1]
                    # CCI
                    df.loc[group.index, 'cci_20'] = pta.cci(group['high'], group['low'], group['close'], length=20)
                    # Williams %R
                    df.loc[group.index, 'williams_r'] = pta.willr(group['high'], group['low'], group['close'], length=14)
                    # ROC
                    for period in [5, 10, 20]:
                        df.loc[group.index, f'roc_{period}'] = pta.roc(group['close'], length=period)
                else:
                    # Use ta library
                    from ta.momentum import RSIIndicator, StochasticOscillator, WilliamsRIndicator, ROCIndicator
                    # RSI
                    rsi = RSIIndicator(close=group['close'], window=14)
                    df.loc[group.index, 'rsi_14'] = rsi.rsi()
                    # Williams %R
                    wr = WilliamsRIndicator(high=group['high'], low=group['low'], close=group['close'], lbp=14)
                    df.loc[group.index, 'williams_r'] = wr.williams_r()
                    # ROC
                    for period in [5, 10, 20]:
                        roc = ROCIndicator(close=group['close'], window=period)
                        df.loc[group.index, f'roc_{period}'] = roc.roc()
            except Exception as e:
                self.logger.warning(f"Error adding momentum indicators for {ticker}: {str(e)}")

        self.logger.info("Momentum indicators added")
        return df

    def add_trend_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add trend indicators"""
        df = df.copy()

        grouped = df.groupby('ticker')

        for ticker, group in grouped:
            if len(group) < 50:
                continue

            try:
                if PANDAS_TA_AVAILABLE:
                    # MACD
                    macd = pta.macd(group['close'])
                    if macd is not None and not macd.empty:
                        df.loc[group.index, 'macd'] = macd.iloc[:, 0]
                        df.loc[group.index, 'macd_signal'] = macd.iloc[:, 1]
                        df.loc[group.index, 'macd_hist'] = macd.iloc[:, 2]
                    # ADX
                    adx = pta.adx(group['high'], group['low'], group['close'], length=14)
                    if adx is not None and not adx.empty:
                        df.loc[group.index, 'adx'] = adx.iloc[:, 0]
                        if adx.shape[1] > 1:
                            df.loc[group.index, 'di_plus'] = adx.iloc[:, 1]
                            df.loc[group.index, 'di_minus'] = adx.iloc[:, 2]
                    # Aroon
                    aroon = pta.aroon(group['high'], group['low'], length=25)
                    if aroon is not None and not aroon.empty:
                        df.loc[group.index, 'aroon_up'] = aroon.iloc[:, 0]
                        df.loc[group.index, 'aroon_down'] = aroon.iloc[:, 1]
                else:
                    # Use ta library
                    from ta.trend import MACD, ADXIndicator, AroonIndicator
                    # MACD
                    macd = MACD(close=group['close'])
                    df.loc[group.index, 'macd'] = macd.macd()
                    df.loc[group.index, 'macd_signal'] = macd.macd_signal()
                    df.loc[group.index, 'macd_hist'] = macd.macd_diff()
                    # ADX
                    adx = ADXIndicator(high=group['high'], low=group['low'], close=group['close'], window=14)
                    df.loc[group.index, 'adx'] = adx.adx()
                    df.loc[group.index, 'di_plus'] = adx.adx_pos()
                    df.loc[group.index, 'di_minus'] = adx.adx_neg()
                    # Aroon
                    aroon = AroonIndicator(high=group['high'], low=group['low'], window=25)
                    df.loc[group.index, 'aroon_up'] = aroon.aroon_up()
                    df.loc[group.index, 'aroon_down'] = aroon.aroon_down()
            except Exception as e:
                self.logger.warning(f"Error adding trend indicators for {ticker}: {str(e)}")

        self.logger.info("Trend indicators added")
        return df

    def add_volatility_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add volatility indicators"""
        df = df.copy()

        grouped = df.groupby('ticker')

        for ticker, group in grouped:
            if len(group) < 50:
                continue

            try:
                if PANDAS_TA_AVAILABLE:
                    # Bollinger Bands
                    bbands = pta.bbands(group['close'], length=20, std=2)
                    if bbands is not None and not bbands.empty:
                        df.loc[group.index, 'bb_upper'] = bbands.iloc[:, 0]
                        df.loc[group.index, 'bb_middle'] = bbands.iloc[:, 1]
                        df.loc[group.index, 'bb_lower'] = bbands.iloc[:, 2]
                        df.loc[group.index, 'bb_width'] = (bbands.iloc[:, 0] - bbands.iloc[:, 2]) / bbands.iloc[:, 1]
                        df.loc[group.index, 'bb_position'] = (group['close'] - bbands.iloc[:, 2]) / (bbands.iloc[:, 0] - bbands.iloc[:, 2] + 1e-10)
                    # ATR
                    df.loc[group.index, 'atr_14'] = pta.atr(group['high'], group['low'], group['close'], length=14)
                    df.loc[group.index, 'atr_pct'] = df.loc[group.index, 'atr_14'] / group['close']
                    # Keltner Channels
                    kc = pta.kc(group['high'], group['low'], group['close'], length=20)
                    if kc is not None and not kc.empty:
                        df.loc[group.index, 'kc_upper'] = kc.iloc[:, 0]
                        df.loc[group.index, 'kc_middle'] = kc.iloc[:, 1]
                        df.loc[group.index, 'kc_lower'] = kc.iloc[:, 2]
                else:
                    # Use ta library
                    from ta.volatility import BollingerBands, AverageTrueRange, KeltnerChannel
                    # Bollinger Bands
                    bb = BollingerBands(close=group['close'], window=20, window_dev=2)
                    df.loc[group.index, 'bb_upper'] = bb.bollinger_hband()
                    df.loc[group.index, 'bb_middle'] = bb.bollinger_mavg()
                    df.loc[group.index, 'bb_lower'] = bb.bollinger_lband()
                    df.loc[group.index, 'bb_width'] = bb.bollinger_wband()
                    df.loc[group.index, 'bb_position'] = bb.bollinger_pband()
                    # ATR
                    atr = AverageTrueRange(high=group['high'], low=group['low'], close=group['close'], window=14)
                    df.loc[group.index, 'atr_14'] = atr.average_true_range()
                    df.loc[group.index, 'atr_pct'] = df.loc[group.index, 'atr_14'] / group['close']
                    # Keltner Channels
                    kc = KeltnerChannel(high=group['high'], low=group['low'], close=group['close'], window=20)
                    df.loc[group.index, 'kc_upper'] = kc.keltner_channel_hband()
                    df.loc[group.index, 'kc_middle'] = kc.keltner_channel_mband()
                    df.loc[group.index, 'kc_lower'] = kc.keltner_channel_lband()
            except Exception as e:
                self.logger.warning(f"Error adding volatility indicators for {ticker}: {str(e)}")

        self.logger.info("Volatility indicators added")
        return df

    def add_volume_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add volume indicators"""
        df = df.copy()

        grouped = df.groupby('ticker')

        # Volume changes and ratios
        df['volume_change'] = df.groupby('ticker')['volume'].pct_change()

        for window in [5, 10, 20, 50]:
            df[f'volume_ma_{window}'] = df.groupby('ticker')['volume'].rolling(window=window).mean().reset_index(0, drop=True)
            df[f'volume_ratio_{window}'] = df['volume'] / df[f'volume_ma_{window}']

        for ticker, group in grouped:
            if len(group) < 50:
                continue

            try:
                if PANDAS_TA_AVAILABLE:
                    # OBV
                    df.loc[group.index, 'obv'] = pta.obv(group['close'], group['volume'])
                    # VWAP
                    df.loc[group.index, 'vwap'] = pta.vwap(group['high'], group['low'], group['close'], group['volume'])
                    # MFI
                    df.loc[group.index, 'mfi_14'] = pta.mfi(group['high'], group['low'], group['close'], group['volume'], length=14)
                    # A/D
                    df.loc[group.index, 'ad'] = pta.ad(group['high'], group['low'], group['close'], group['volume'])
                else:
                    # Use ta library
                    from ta.volume import OnBalanceVolumeIndicator, VolumeWeightedAveragePrice, MFIIndicator, AccDistIndexIndicator
                    # OBV
                    obv = OnBalanceVolumeIndicator(close=group['close'], volume=group['volume'])
                    df.loc[group.index, 'obv'] = obv.on_balance_volume()
                    # VWAP
                    vwap = VolumeWeightedAveragePrice(high=group['high'], low=group['low'], close=group['close'], volume=group['volume'])
                    df.loc[group.index, 'vwap'] = vwap.volume_weighted_average_price()
                    # MFI
                    mfi = MFIIndicator(high=group['high'], low=group['low'], close=group['close'], volume=group['volume'], window=14)
                    df.loc[group.index, 'mfi_14'] = mfi.money_flow_index()
                    # A/D
                    ad = AccDistIndexIndicator(high=group['high'], low=group['low'], close=group['close'], volume=group['volume'])
                    df.loc[group.index, 'ad'] = ad.acc_dist_index()
            except Exception as e:
                self.logger.warning(f"Error adding volume indicators for {ticker}: {str(e)}")

        self.logger.info("Volume indicators added")
        return df

    def add_pattern_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add pattern recognition features"""
        df = df.copy()

        # Support and resistance levels (simplified)
        for window in [10, 20, 50]:
            df[f'resistance_{window}'] = df.groupby('ticker')['high'].rolling(window=window).max().reset_index(0, drop=True)
            df[f'support_{window}'] = df.groupby('ticker')['low'].rolling(window=window).min().reset_index(0, drop=True)
            df[f'dist_to_resistance_{window}'] = (df[f'resistance_{window}'] - df['close']) / df['close']
            df[f'dist_to_support_{window}'] = (df['close'] - df[f'support_{window}']) / df['close']

        # Trend detection (simple)
        for window in [10, 20, 50]:
            df[f'trend_{window}'] = df.groupby('ticker')['close'].rolling(window=window).apply(
                lambda x: 1 if x.iloc[-1] > x.iloc[0] else -1, raw=False
            ).reset_index(0, drop=True)

        self.logger.info("Pattern features added")
        return df

    def add_lag_features(self, df: pd.DataFrame, columns: List[str], lags: List[int]) -> pd.DataFrame:
        """Add lagged features"""
        df = df.copy()

        for col in columns:
            if col in df.columns:
                for lag in lags:
                    df[f'{col}_lag_{lag}'] = df.groupby('ticker')[col].shift(lag)

        self.logger.info(f"Lag features added for {len(columns)} columns")
        return df

    def add_rolling_statistics(self, df: pd.DataFrame, columns: List[str], windows: List[int]) -> pd.DataFrame:
        """Add rolling statistical features"""
        df = df.copy()

        for col in columns:
            if col in df.columns:
                for window in windows:
                    df[f'{col}_rolling_mean_{window}'] = df.groupby('ticker')[col].rolling(window=window).mean().reset_index(0, drop=True)
                    df[f'{col}_rolling_std_{window}'] = df.groupby('ticker')[col].rolling(window=window).std().reset_index(0, drop=True)
                    df[f'{col}_rolling_min_{window}'] = df.groupby('ticker')[col].rolling(window=window).min().reset_index(0, drop=True)
                    df[f'{col}_rolling_max_{window}'] = df.groupby('ticker')[col].rolling(window=window).max().reset_index(0, drop=True)

        self.logger.info(f"Rolling statistics added for {len(columns)} columns")
        return df

    def create_all_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create all features"""
        self.logger.info("Creating all features...")

        df = self.add_price_features(df)
        df = self.add_moving_averages(df)
        df = self.add_momentum_indicators(df)
        df = self.add_trend_indicators(df)
        df = self.add_volatility_indicators(df)
        df = self.add_volume_indicators(df)
        df = self.add_pattern_features(df)

        # Add lag features for key indicators
        lag_columns = ['close', 'volume', 'rsi_14', 'macd', 'atr_14']
        df = self.add_lag_features(df, lag_columns, lags=[1, 2, 3, 5])

        # Add rolling statistics for key features
        rolling_columns = ['return_1d', 'volume_change']
        df = self.add_rolling_statistics(df, rolling_columns, windows=[5, 10, 20])

        self.logger.info(f"Total features: {len(df.columns)}")

        return df

    def select_features(self, df: pd.DataFrame, exclude_cols: List[str] = None) -> List[str]:
        """Select feature columns for modeling"""
        if exclude_cols is None:
            exclude_cols = ['ticker', 'date', 'open', 'high', 'low', 'close', 'volume',
                           'dividends', 'stock_splits', 'capital_gains']

        # Add columns that start with 'future_' or 'surge_' to exclude list
        exclude_cols.extend([col for col in df.columns if col.startswith('future_') or col.startswith('surge_')])

        feature_cols = [col for col in df.columns if col not in exclude_cols]

        self.logger.info(f"Selected {len(feature_cols)} features for modeling")

        return feature_cols

    def handle_missing_values(self, df: pd.DataFrame, method: str = 'drop') -> pd.DataFrame:
        """Handle missing values"""
        df = df.copy()

        if method == 'drop':
            # Drop rows with any missing values
            before_count = len(df)
            df = df.dropna()
            after_count = len(df)
            self.logger.info(f"Dropped {before_count - after_count} rows with missing values")

        elif method == 'forward_fill':
            df = df.groupby('ticker').fillna(method='ffill')

        elif method == 'backward_fill':
            df = df.groupby('ticker').fillna(method='bfill')

        elif method == 'mean':
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            df[numeric_cols] = df.groupby('ticker')[numeric_cols].transform(lambda x: x.fillna(x.mean()))

        else:
            raise ValueError(f"Unknown method: {method}")

        return df

    def normalize_features(self, df: pd.DataFrame, feature_cols: List[str],
                          method: str = 'standard') -> pd.DataFrame:
        """Normalize features"""
        from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler

        df = df.copy()

        if method == 'standard':
            scaler = StandardScaler()
        elif method == 'minmax':
            scaler = MinMaxScaler()
        elif method == 'robust':
            scaler = RobustScaler()
        else:
            raise ValueError(f"Unknown normalization method: {method}")

        df[feature_cols] = scaler.fit_transform(df[feature_cols])

        self.logger.info(f"Features normalized using {method} scaler")

        return df, scaler
