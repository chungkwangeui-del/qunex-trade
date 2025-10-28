"""
Download Latest Data (2024-10-26 to 2025-10-27)
Append to existing CLEAN_STOCKS_2Y.csv
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web.polygon_service import PolygonService
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime
import time


def main():
    """Download latest year of data and append"""

    print("\n" + "=" * 80)
    print("DOWNLOAD LATEST DATA (2024-10-26 to 2025-10-27)")
    print("=" * 80)

    # Load API
    load_dotenv()
    api_key = os.getenv('POLYGON_API_KEY')
    polygon = PolygonService(api_key)
    print("[OK] Polygon API initialized")

    # Load existing clean tickers
    print("\n[1/4] Loading existing clean tickers...")
    with open('backtest/database/CLEAN_STOCKS_TICKERS.txt', 'r') as f:
        clean_tickers = [line.strip() for line in f.readlines()]

    print(f"  Found {len(clean_tickers)} clean tickers")

    # Download latest data
    print(f"\n[2/4] Downloading latest data (2024-10-26 to 2025-10-27)...")
    print(f"  [WARNING] This will take ~{len(clean_tickers) * 0.12 / 60:.0f} minutes")

    start_date = '2024-10-26'
    end_date = '2025-10-27'

    all_data = []
    success = 0
    failed = 0

    for idx, ticker in enumerate(clean_tickers, 1):
        try:
            data = polygon.get_aggregates(
                ticker=ticker,
                multiplier=1,
                timespan='day',
                from_date=start_date,
                to_date=end_date,
                limit=5000
            )

            if data and len(data) > 0:
                df = pd.DataFrame(data)
                df['ticker'] = ticker

                # Rename columns to match existing format
                df = df.rename(columns={
                    't': 'timestamp',
                    'o': 'open',
                    'h': 'high',
                    'l': 'low',
                    'c': 'close',
                    'v': 'volume',
                    'vw': 'vwap',
                    'n': 'transactions'
                })

                df['date'] = pd.to_datetime(df['timestamp'], unit='ms')

                # Select only columns that match existing data
                df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume',
                        'vwap', 'transactions', 'ticker', 'date']]

                all_data.append(df)
                success += 1
            else:
                failed += 1

            if idx % 100 == 0:
                print(f"  [{idx}/{len(clean_tickers)}] Progress: {success} success, {failed} failed")

            time.sleep(0.12)  # Rate limit

        except Exception as e:
            failed += 1
            if idx % 100 == 0:
                print(f"  Error on {ticker}: {str(e)}")
            continue

    print(f"\n  Download complete: {success} success, {failed} failed")

    if len(all_data) == 0:
        print("[ERROR] No new data downloaded!")
        return

    # Combine new data
    new_df = pd.concat(all_data, ignore_index=True)
    print(f"  New rows: {len(new_df):,}")
    print(f"  Date range: {new_df['date'].min()} to {new_df['date'].max()}")

    # Load existing data
    print(f"\n[3/4] Loading existing data...")
    existing_df = pd.read_csv('backtest/database/CLEAN_STOCKS_2Y.csv')
    existing_df['date'] = pd.to_datetime(existing_df['date'])

    print(f"  Existing rows: {len(existing_df):,}")
    print(f"  Existing date range: {existing_df['date'].min()} to {existing_df['date'].max()}")

    # Combine
    print(f"\n[4/4] Combining data...")
    combined_df = pd.concat([existing_df, new_df], ignore_index=True)

    # Remove duplicates (just in case)
    before_dedup = len(combined_df)
    combined_df = combined_df.drop_duplicates(subset=['ticker', 'date'], keep='last')
    after_dedup = len(combined_df)

    if before_dedup != after_dedup:
        print(f"  Removed {before_dedup - after_dedup} duplicate rows")

    # Sort by ticker and date
    combined_df = combined_df.sort_values(['ticker', 'date']).reset_index(drop=True)

    print(f"\n  Combined stats:")
    print(f"    Total rows: {len(combined_df):,}")
    print(f"    Tickers: {combined_df['ticker'].nunique()}")
    print(f"    Date range: {combined_df['date'].min().date()} to {combined_df['date'].max().date()}")
    print(f"    Trading days: {combined_df['date'].nunique()}")

    # Save
    combined_df.to_csv('backtest/database/CLEAN_STOCKS_3Y.csv', index=False)
    print(f"\n[SAVED] backtest/database/CLEAN_STOCKS_3Y.csv")

    # Backup old file
    import shutil
    shutil.copy('backtest/database/CLEAN_STOCKS_2Y.csv',
                'backtest/database/CLEAN_STOCKS_2Y_BACKUP.csv')
    print(f"[BACKUP] backtest/database/CLEAN_STOCKS_2Y_BACKUP.csv")

    # Statistics
    print("\n" + "=" * 80)
    print("DOWNLOAD COMPLETE!")
    print("=" * 80)
    print(f"\nNew data added:")
    print(f"  Before: {len(existing_df):,} rows")
    print(f"  After: {len(combined_df):,} rows")
    print(f"  Added: {len(combined_df) - len(existing_df):,} rows")
    print(f"\nDate coverage:")
    print(f"  Before: {existing_df['date'].max().date()}")
    print(f"  After: {combined_df['date'].max().date()}")
    print(f"  Gap filled: {(combined_df['date'].max() - existing_df['date'].max()).days} days")
    print("=" * 80)


if __name__ == '__main__':
    main()
