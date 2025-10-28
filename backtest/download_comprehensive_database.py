"""
Download Comprehensive Stock Database
Uses Polygon's grouped daily API to get ALL actively traded stocks
Then downloads 2 years of historical data for quality stocks
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web.polygon_service import PolygonService
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime, timedelta
import time


def main():
    """Download comprehensive database"""

    print("\n")
    print("#" * 80)
    print("COMPREHENSIVE STOCK DATABASE DOWNLOADER")
    print("Get ALL actively traded US stocks + 2 years history")
    print("#" * 80)

    # Load API
    load_dotenv()
    api_key = os.getenv('POLYGON_API_KEY')
    polygon = PolygonService(api_key)
    print("[OK] Polygon API initialized")

    # Step 1: Get all actively traded tickers from grouped daily
    print("\n[1/5] Getting all actively traded tickers...")

    url = 'https://api.polygon.io/v2/aggs/grouped/locale/us/market/stocks/2024-10-25'
    params = {'adjusted': 'true', 'apiKey': api_key}

    response = polygon.session.get(url, params=params)

    if response.status_code != 200:
        print(f"[ERROR] API request failed: {response.status_code}")
        return

    data = response.json()
    results = data.get('results', [])

    print(f"  Total stocks found: {len(results)}")

    # Extract ticker info
    all_tickers = []
    for result in results:
        ticker = result.get('T')
        close = result.get('c', 0)
        volume = result.get('v', 0)

        all_tickers.append({
            'ticker': ticker,
            'last_close': close,
            'last_volume': volume
        })

    tickers_df = pd.DataFrame(all_tickers)

    # Step 2: Filter by basic criteria
    print("\n[2/5] Filtering tickers...")

    # Filter out:
    # - ETFs, warrants, units (anything with ., -, special chars)
    # - Price < $1 or > $200
    # - Volume < 50k

    filtered = tickers_df[
        (~tickers_df['ticker'].str.contains(r'[.\-\^]', regex=True)) &  # No special chars
        (tickers_df['ticker'].str.len() <= 5) &  # Max 5 letters
        (tickers_df['last_close'] >= 1.0) &
        (tickers_df['last_close'] <= 200.0) &
        (tickers_df['last_volume'] >= 50000)
    ].copy()

    print(f"  After filtering: {len(filtered)} tickers")
    print(f"    Removed warrants/ETFs: {len(tickers_df) - len(tickers_df[~tickers_df['ticker'].str.contains(r'[.\-\^]', regex=True)])}")
    print(f"    Price $1-$200: {len(filtered[filtered['last_close'].between(1, 200)])}")
    print(f"    Volume >= 50k: {len(filtered[filtered['last_volume'] >= 50000])}")

    ticker_list = filtered['ticker'].tolist()

    # Step 3: Download historical data
    print(f"\n[3/5] Downloading 2-year historical data for {len(ticker_list)} stocks...")
    print(f"  [WARNING] This will take ~{len(ticker_list) * 0.12 / 60:.0f} minutes")

    start_date = '2022-10-26'
    end_date = '2024-10-25'

    all_data = []
    success = 0
    failed = 0

    for idx, ticker in enumerate(ticker_list, 1):
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

                # Rename columns
                df = df.rename(columns={
                    't': 'timestamp',
                    'o': 'Open',
                    'h': 'High',
                    'l': 'Low',
                    'c': 'Close',
                    'v': 'Volume',
                    'vw': 'VWAP',
                    'n': 'Transactions'
                })

                df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
                all_data.append(df)
                success += 1
            else:
                failed += 1

            if idx % 100 == 0:
                print(f"  [{idx}/{len(ticker_list)}] Progress: {success} success, {failed} failed")

            time.sleep(0.12)  # Rate limit

        except Exception as e:
            failed += 1
            continue

    print(f"\n  Download complete: {success} success, {failed} failed")

    if len(all_data) == 0:
        print("[ERROR] No data downloaded!")
        return

    # Combine
    combined_df = pd.concat(all_data, ignore_index=True)
    print(f"  Total rows: {len(combined_df):,}")

    # Step 4: Quality filter
    print(f"\n[4/5] Final quality filtering...")

    # Remove stocks with:
    # - < 400 days of data (should have ~504 days)
    # - Min price ever < $1
    # - Extreme volatility (50x price change = likely data error)

    ticker_quality = combined_df.groupby('ticker').agg({
        'date': 'count',
        'Close': ['min', 'max', 'mean'],
        'Volume': 'mean'
    }).reset_index()

    ticker_quality.columns = ['ticker', 'days', 'min_price', 'max_price', 'avg_price', 'avg_volume']

    quality_tickers = ticker_quality[
        (ticker_quality['days'] >= 400) &
        (ticker_quality['min_price'] >= 1.0) &
        (ticker_quality['max_price'] / ticker_quality['min_price'] <= 20) &  # No 20x moves
        (ticker_quality['avg_volume'] >= 100000)
    ]['ticker'].tolist()

    final_df = combined_df[combined_df['ticker'].isin(quality_tickers)].copy()

    print(f"  Quality tickers: {len(quality_tickers)}")
    print(f"  Final rows: {len(final_df):,}")

    # Step 5: Save
    print(f"\n[5/5] Saving master database...")

    os.makedirs('backtest/database', exist_ok=True)

    # Save main CSV
    csv_file = 'backtest/database/master_stocks_2y.csv'
    final_df.to_csv(csv_file, index=False)
    print(f"  [SAVED] {csv_file}")

    # Save ticker list
    ticker_file = 'backtest/database/ticker_list.txt'
    with open(ticker_file, 'w') as f:
        for t in sorted(quality_tickers):
            f.write(f"{t}\n")
    print(f"  [SAVED] {ticker_file}")

    # Statistics
    print("\n" + "=" * 80)
    print("DATABASE STATISTICS")
    print("=" * 80)
    print(f"\nOverview:")
    print(f"  Total tickers: {len(quality_tickers)}")
    print(f"  Total data points: {len(final_df):,}")
    print(f"  Date range: {final_df['date'].min().strftime('%Y-%m-%d')} to {final_df['date'].max().strftime('%Y-%m-%d')}")
    print(f"  Trading days: {final_df['date'].nunique()}")

    print(f"\nPrice Range:")
    print(f"  Min: ${final_df['Close'].min():.2f}")
    print(f"  Max: ${final_df['Close'].max():.2f}")
    print(f"  Median: ${final_df['Close'].median():.2f}")

    print(f"\nVolume:")
    print(f"  Median: {final_df['Volume'].median():,.0f}")
    print(f"  Mean: {final_df['Volume'].mean():,.0f}")

    print("\n" + "=" * 80)
    print("DOWNLOAD COMPLETE!")
    print("=" * 80)
    print(f"\nDatabase ready for ML training!")
    print(f"File: {csv_file}")


if __name__ == '__main__':
    main()
