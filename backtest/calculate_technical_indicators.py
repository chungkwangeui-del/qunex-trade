"""
Calculate Technical Indicators for ML Model
Focus on penny stock surge prediction
"""

import pandas as pd
import numpy as np
from datetime import datetime


def calculate_technical_indicators(df):
    """
    Calculate technical indicators optimized for penny stock surge prediction

    Key indicators:
    1. Price momentum (ROC, RSI)
    2. Volatility (ATR, Bollinger Bands)
    3. Volume patterns (Volume MA, Volume ratio)
    4. Trend (SMA, EMA)
    5. Gap detection
    """

    # Sort by ticker and date
    df = df.sort_values(['ticker', 'date']).copy()

    print("Calculating technical indicators...")

    # 1. Price-based indicators
    print("  [1/6] Price momentum indicators...")

    # Daily returns
    df['returns'] = df.groupby('ticker')['close'].pct_change()

    # Rate of Change (ROC) - 5, 10, 20 days
    df['roc_5'] = df.groupby('ticker')['close'].pct_change(5)
    df['roc_10'] = df.groupby('ticker')['close'].pct_change(10)
    df['roc_20'] = df.groupby('ticker')['close'].pct_change(20)

    # Intraday range
    df['intraday_range'] = (df['high'] - df['low']) / df['low'] * 100

    # Gap (open vs previous close)
    df['prev_close'] = df.groupby('ticker')['close'].shift(1)
    df['gap'] = (df['open'] - df['prev_close']) / df['prev_close'] * 100

    # 2. Moving Averages
    print("  [2/6] Moving averages...")

    for period in [5, 10, 20, 50]:
        df[f'sma_{period}'] = df.groupby('ticker')['close'].transform(
            lambda x: x.rolling(period, min_periods=1).mean()
        )
        df[f'ema_{period}'] = df.groupby('ticker')['close'].transform(
            lambda x: x.ewm(span=period, min_periods=1).mean()
        )

    # Price distance from MA
    df['dist_sma_20'] = (df['close'] - df['sma_20']) / df['sma_20'] * 100

    # 3. RSI (Relative Strength Index)
    print("  [3/6] RSI...")

    def calculate_rsi(series, period=14):
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period, min_periods=1).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period, min_periods=1).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    df['rsi_14'] = df.groupby('ticker')['close'].transform(
        lambda x: calculate_rsi(x, 14)
    )

    # 4. Bollinger Bands
    print("  [4/6] Bollinger Bands...")

    # Calculate SMA for BB
    df['bb_sma'] = df.groupby('ticker')['close'].transform(
        lambda x: x.rolling(20, min_periods=1).mean()
    )

    # Calculate standard deviation for BB
    df['bb_std'] = df.groupby('ticker')['close'].transform(
        lambda x: x.rolling(20, min_periods=1).std()
    )

    # Upper and lower bands
    df['bb_upper'] = df['bb_sma'] + (df['bb_std'] * 2)
    df['bb_lower'] = df['bb_sma'] - (df['bb_std'] * 2)

    # BB position (where price is within the bands)
    df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower']) * 100

    # Drop temporary columns
    df = df.drop(['bb_sma', 'bb_std'], axis=1)

    # 5. Volume indicators
    print("  [5/6] Volume indicators...")

    for period in [5, 10, 20]:
        df[f'volume_ma_{period}'] = df.groupby('ticker')['volume'].transform(
            lambda x: x.rolling(period, min_periods=1).mean()
        )

    df['volume_ratio'] = df['volume'] / df['volume_ma_20']

    # Volume trend
    df['volume_trend'] = df.groupby('ticker')['volume'].transform(
        lambda x: x.rolling(5, min_periods=1).mean() / x.rolling(20, min_periods=1).mean()
    )

    # 6. Volatility indicators
    print("  [6/6] Volatility indicators...")

    # ATR (Average True Range)
    df['tr'] = df[['high', 'low', 'prev_close']].apply(
        lambda x: max(x['high'] - x['low'],
                     abs(x['high'] - x['prev_close']),
                     abs(x['low'] - x['prev_close'])),
        axis=1
    )
    df['atr_14'] = df.groupby('ticker')['tr'].transform(
        lambda x: x.rolling(14, min_periods=1).mean()
    )
    df['atr_ratio'] = df['atr_14'] / df['close'] * 100

    # Price volatility (standard deviation)
    df['price_std_20'] = df.groupby('ticker')['close'].transform(
        lambda x: x.rolling(20, min_periods=1).std()
    )
    df['price_volatility'] = df['price_std_20'] / df['close'] * 100

    # Historical volatility
    df['hist_vol_20'] = df.groupby('ticker')['returns'].transform(
        lambda x: x.rolling(20, min_periods=1).std() * np.sqrt(252) * 100
    )

    print("  [DONE] All indicators calculated!")

    return df


def main():
    """Calculate technical indicators and save"""

    print("\n" + "=" * 80)
    print("TECHNICAL INDICATORS CALCULATION")
    print("=" * 80)

    # Load price data
    print("\n[1/3] Loading price data...")
    df = pd.read_csv('backtest/database/CLEAN_STOCKS_3Y.csv')
    df['date'] = pd.to_datetime(df['date'])

    print(f"  Loaded: {len(df):,} rows, {df['ticker'].nunique()} tickers")
    print(f"  Date range: {df['date'].min().date()} to {df['date'].max().date()}")

    # Calculate indicators
    print("\n[2/3] Calculating technical indicators...")
    df_with_indicators = calculate_technical_indicators(df)

    # Save
    print("\n[3/3] Saving enhanced dataset...")
    output_file = 'backtest/database/STOCKS_WITH_INDICATORS.csv'
    df_with_indicators.to_csv(output_file, index=False)
    print(f"  [SAVED] {output_file}")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    # Count new columns
    original_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume',
                    'vwap', 'transactions', 'ticker', 'date']
    new_cols = [col for col in df_with_indicators.columns if col not in original_cols]

    print(f"\nOriginal columns: {len(original_cols)}")
    print(f"New indicator columns: {len(new_cols)}")
    print(f"Total columns: {len(df_with_indicators.columns)}")

    print(f"\nNew indicators added:")
    for i, col in enumerate(new_cols, 1):
        print(f"  {i:2d}. {col}")

    print(f"\nFile size:")
    import os
    file_size = os.path.getsize(output_file) / (1024 * 1024)
    print(f"  {file_size:.1f} MB")

    print("\n" + "=" * 80)
    print("READY FOR ML TRAINING!")
    print("=" * 80)


if __name__ == '__main__':
    main()
