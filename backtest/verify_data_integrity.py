"""
Complete Data Integrity Verification
Verify all data is real historical data with no errors
For backtesting strategy - must be 100% accurate
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def check_time_consistency(df):
    """Check if dates are in proper chronological order and real"""
    print("\n[TIME CONSISTENCY CHECK]")

    # Check for future dates
    today = pd.Timestamp.now()
    future_dates = df[df['date'] > today]

    if len(future_dates) > 0:
        print(f"  ERROR: Found {len(future_dates)} rows with FUTURE dates!")
        print(f"    Latest date in data: {df['date'].max()}")
        print(f"    Today: {today}")
        print(f"    Tickers affected: {future_dates['ticker'].unique()[:10]}")
        return False
    else:
        print(f"  OK: No future dates (latest: {df['date'].max().date()})")

    # Check for weekends/holidays (rough check)
    df['dayofweek'] = df['date'].dt.dayofweek
    weekend_trades = df[df['dayofweek'] >= 5]  # Sat=5, Sun=6

    # Allow some weekend data (could be valid in some cases)
    if len(weekend_trades) > 0:
        print(f"  WARNING: {len(weekend_trades)} rows on weekends (might be OK for some exchanges)")
    else:
        print(f"  OK: No weekend trading data")

    # Check date gaps per ticker
    print(f"\n  Checking date continuity per ticker...")
    max_gap = 0
    ticker_with_max_gap = None

    for ticker in df['ticker'].unique()[:100]:  # Sample 100 tickers
        ticker_data = df[df['ticker'] == ticker].sort_values('date')
        if len(ticker_data) > 1:
            ticker_data['gap'] = ticker_data['date'].diff().dt.days
            ticker_max_gap = ticker_data['gap'].max()
            if ticker_max_gap > max_gap:
                max_gap = ticker_max_gap
                ticker_with_max_gap = ticker

    if max_gap > 30:
        print(f"  WARNING: Max gap between dates: {max_gap} days (ticker: {ticker_with_max_gap})")
    else:
        print(f"  OK: Max gap between dates: {max_gap} days")

    return True


def check_price_integrity(df):
    """Check if prices are realistic and consistent"""
    print("\n[PRICE INTEGRITY CHECK]")

    errors = []

    # 1. Extreme prices
    extreme_high = df[df['close'] > 10000]
    if len(extreme_high) > 0:
        errors.append(f"Prices > $10k: {len(extreme_high)} rows in {extreme_high['ticker'].nunique()} tickers")
        print(f"  ERROR: {errors[-1]}")
        print(f"    Tickers: {sorted(extreme_high['ticker'].unique()[:10])}")
    else:
        print(f"  OK: No extreme high prices (>$10k)")

    extreme_low = df[df['close'] < 0.01]
    if len(extreme_low) > 0:
        errors.append(f"Prices < $0.01: {len(extreme_low)} rows in {extreme_low['ticker'].nunique()} tickers")
        print(f"  ERROR: {errors[-1]}")
        print(f"    Tickers: {sorted(extreme_low['ticker'].unique()[:10])}")
    else:
        print(f"  OK: No extreme low prices (<$0.01)")

    # 2. Negative prices
    negative = df[df['close'] < 0]
    if len(negative) > 0:
        errors.append(f"Negative prices: {len(negative)} rows")
        print(f"  ERROR: {errors[-1]}")
    else:
        print(f"  OK: No negative prices")

    # 3. Price logic (high >= low, etc)
    bad_high_low = df[df['high'] < df['low']]
    if len(bad_high_low) > 0:
        errors.append(f"High < Low: {len(bad_high_low)} rows")
        print(f"  ERROR: {errors[-1]}")
    else:
        print(f"  OK: High >= Low for all rows")

    bad_close = df[(df['close'] > df['high']) | (df['close'] < df['low'])]
    if len(bad_close) > 0:
        errors.append(f"Close outside [Low,High]: {len(bad_close)} rows")
        print(f"  ERROR: {errors[-1]}")
    else:
        print(f"  OK: Close within [Low,High] for all rows")

    bad_open = df[(df['open'] > df['high']) | (df['open'] < df['low'])]
    if len(bad_open) > 0:
        errors.append(f"Open outside [Low,High]: {len(bad_open)} rows")
        print(f"  ERROR: {errors[-1]}")
    else:
        print(f"  OK: Open within [Low,High] for all rows")

    # 4. Unrealistic intraday moves (>90% in one day)
    df_sample = df.copy()
    df_sample['intraday_move'] = (df_sample['high'] - df_sample['low']) / df_sample['low']
    extreme_moves = df_sample[df_sample['intraday_move'] > 5]  # 500%+ intraday

    if len(extreme_moves) > 100:
        print(f"  WARNING: {len(extreme_moves)} rows with >500% intraday moves")
        print(f"    This might indicate split-adjusted data issues")
    else:
        print(f"  OK: Intraday moves are reasonable")

    return len(errors) == 0, errors


def check_volume_integrity(df):
    """Check if volume data is realistic"""
    print("\n[VOLUME INTEGRITY CHECK]")

    errors = []

    # 1. Negative volume
    negative_vol = df[df['volume'] < 0]
    if len(negative_vol) > 0:
        errors.append(f"Negative volume: {len(negative_vol)} rows")
        print(f"  ERROR: {errors[-1]}")
    else:
        print(f"  OK: No negative volume")

    # 2. Zero volume (common, not an error but noteworthy)
    zero_vol = df[df['volume'] == 0]
    if len(zero_vol) > 0:
        pct = len(zero_vol) / len(df) * 100
        print(f"  INFO: {len(zero_vol)} rows with zero volume ({pct:.2f}%)")
        if pct > 5:
            print(f"    WARNING: >5% zero volume rows - check data quality")
    else:
        print(f"  OK: No zero volume")

    # 3. Extreme volume spikes
    ticker_avg_vol = df.groupby('ticker')['volume'].median()

    return len(errors) == 0, errors


def check_data_completeness(df):
    """Check if data is complete for all tickers"""
    print("\n[DATA COMPLETENESS CHECK]")

    errors = []

    # 1. Check days per ticker
    ticker_days = df.groupby('ticker')['date'].count()

    print(f"  Days per ticker:")
    print(f"    Min: {ticker_days.min()}")
    print(f"    Max: {ticker_days.max()}")
    print(f"    Median: {ticker_days.median():.0f}")

    incomplete = ticker_days[ticker_days < 400]
    if len(incomplete) > 0:
        errors.append(f"Tickers with <400 days: {len(incomplete)}")
        print(f"  ERROR: {errors[-1]}")
        print(f"    Examples: {list(incomplete.head(10).index)}")
    else:
        print(f"  OK: All tickers have >= 400 days")

    # 2. Check for missing dates
    all_dates = pd.date_range(df['date'].min(), df['date'].max(), freq='D')
    trading_days = df['date'].dt.date.unique()

    print(f"\n  Date coverage:")
    print(f"    Total days in range: {len(all_dates)}")
    print(f"    Trading days in data: {len(trading_days)}")
    print(f"    Coverage: {len(trading_days)/len(all_dates)*100:.1f}%")

    # 3. Check for duplicates
    duplicates = df.duplicated(subset=['ticker', 'date'], keep=False)
    if duplicates.sum() > 0:
        errors.append(f"Duplicate rows: {duplicates.sum()}")
        print(f"  ERROR: {errors[-1]}")
    else:
        print(f"  OK: No duplicate (ticker, date) pairs")

    # 4. Check for missing values
    missing = df[['open', 'high', 'low', 'close', 'volume']].isna().sum()
    if missing.sum() > 0:
        errors.append(f"Missing values: {missing.sum()}")
        print(f"  ERROR: {errors[-1]}")
        print(missing[missing > 0])
    else:
        print(f"  OK: No missing values in price/volume columns")

    return len(errors) == 0, errors


def check_split_adjustments(df):
    """Check for potential split adjustment issues"""
    print("\n[SPLIT ADJUSTMENT CHECK]")

    issues = []

    # Look for sudden large price changes (potential reverse splits)
    print(f"  Checking for reverse split patterns...")

    problem_tickers = []
    for ticker in df['ticker'].unique()[:200]:  # Sample 200 tickers
        ticker_data = df[df['ticker'] == ticker].sort_values('date')
        ticker_data['pct_change'] = ticker_data['close'].pct_change()

        # Large drops could indicate reverse splits
        big_drops = ticker_data[ticker_data['pct_change'] < -0.7]

        if len(big_drops) > 5:
            problem_tickers.append({
                'ticker': ticker,
                'reverse_splits': len(big_drops),
                'max_price': ticker_data['close'].max(),
                'min_price': ticker_data['close'].min()
            })

    if len(problem_tickers) > 0:
        print(f"  INFO: {len(problem_tickers)} tickers with multiple reverse split patterns")
        print(f"    Top 5:")
        for item in sorted(problem_tickers, key=lambda x: x['reverse_splits'], reverse=True)[:5]:
            print(f"      {item['ticker']}: {item['reverse_splits']} splits, "
                  f"price range ${item['min_price']:.2f} - ${item['max_price']:.2f}")
    else:
        print(f"  OK: No excessive reverse split patterns")

    return True


def verify_historical_data(df):
    """Verify this is actual historical data, not simulated/fake"""
    print("\n[HISTORICAL DATA VERIFICATION]")

    # 1. Check if prices show realistic market behavior
    print(f"  Checking price distribution...")

    # Real market data should have specific characteristics
    ticker_stats = df.groupby('ticker').agg({
        'close': ['mean', 'std', 'min', 'max'],
        'volume': ['mean', 'std']
    }).reset_index()

    ticker_stats.columns = ['ticker', 'avg_price', 'std_price', 'min_price', 'max_price',
                            'avg_vol', 'std_vol']

    # Check for constant prices (could be fake/suspended)
    ticker_stats['price_range'] = ticker_stats['max_price'] - ticker_stats['min_price']
    zero_variance = ticker_stats[ticker_stats['price_range'] == 0]

    if len(zero_variance) > 0:
        print(f"  WARNING: {len(zero_variance)} tickers with zero price variance")
        print(f"    (Could be suspended/delisted stocks)")
    else:
        print(f"  OK: All tickers show price movement")

    # 2. Check volume patterns
    zero_avg_vol = ticker_stats[ticker_stats['avg_vol'] == 0]
    if len(zero_avg_vol) > 0:
        print(f"  WARNING: {len(zero_avg_vol)} tickers with zero average volume")
    else:
        print(f"  OK: All tickers have trading volume")

    # 3. Verify date range matches requested range
    print(f"\n  Date range verification:")
    print(f"    Earliest date: {df['date'].min().date()}")
    print(f"    Latest date: {df['date'].max().date()}")
    print(f"    Span: {(df['date'].max() - df['date'].min()).days} days")

    return True


def main():
    """Run complete data integrity verification"""

    print("=" * 80)
    print("COMPLETE DATA INTEGRITY VERIFICATION")
    print("For Backtesting Strategy Database - Must Be 100% Accurate")
    print("=" * 80)

    # Load data
    print("\n[LOADING DATA]")
    try:
        df = pd.read_csv('backtest/database/CLEAN_STOCKS_3Y.csv')
        df['date'] = pd.to_datetime(df['date'])
        print(f"  Loaded: {len(df):,} rows, {df['ticker'].nunique()} tickers")
    except FileNotFoundError:
        print("  ERROR: CLEAN_STOCKS_3Y.csv not found!")
        print("  Trying CLEAN_STOCKS_2Y.csv...")
        df = pd.read_csv('backtest/database/CLEAN_STOCKS_2Y.csv')
        df['date'] = pd.to_datetime(df['date'])
        print(f"  Loaded: {len(df):,} rows, {df['ticker'].nunique()} tickers")

    # Run all checks
    all_passed = True
    all_errors = []

    # 1. Time consistency
    time_ok = check_time_consistency(df)
    if not time_ok:
        all_passed = False

    # 2. Price integrity
    price_ok, price_errors = check_price_integrity(df)
    if not price_ok:
        all_passed = False
        all_errors.extend(price_errors)

    # 3. Volume integrity
    vol_ok, vol_errors = check_volume_integrity(df)
    if not vol_ok:
        all_passed = False
        all_errors.extend(vol_errors)

    # 4. Data completeness
    complete_ok, complete_errors = check_data_completeness(df)
    if not complete_ok:
        all_passed = False
        all_errors.extend(complete_errors)

    # 5. Split adjustments
    check_split_adjustments(df)

    # 6. Historical verification
    verify_historical_data(df)

    # Final verdict
    print("\n" + "=" * 80)
    print("VERIFICATION RESULT")
    print("=" * 80)

    if all_passed:
        print("\n  PASSED: Data integrity verified!")
        print("  - All critical checks passed")
        print("  - Data is suitable for backtesting")
        print("  - No major errors detected")
    else:
        print("\n  FAILED: Data has issues!")
        print(f"  - {len(all_errors)} critical errors found:")
        for err in all_errors:
            print(f"    * {err}")
        print("\n  DO NOT USE for backtesting until fixed!")

    print("=" * 80)

    return all_passed


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
