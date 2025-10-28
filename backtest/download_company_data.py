"""
Download Company Information & Splits for All Tickers
Real data from Polygon.io API
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web.polygon_service import PolygonService
from dotenv import load_dotenv
import pandas as pd
import time


def main():
    """Download company info and splits for all clean tickers"""

    print("\n" + "=" * 80)
    print("DOWNLOAD COMPANY DATA & SPLITS")
    print("100% Real Data from Polygon.io")
    print("=" * 80)

    # Load API
    load_dotenv()
    api_key = os.getenv('POLYGON_API_KEY')
    polygon = PolygonService(api_key)
    print("[OK] Polygon API initialized")

    # Load clean tickers
    print("\n[1/3] Loading clean tickers...")
    with open('backtest/database/CLEAN_STOCKS_TICKERS.txt', 'r') as f:
        tickers = [line.strip() for line in f.readlines()]

    print(f"  Found {len(tickers)} tickers")

    # Download Ticker Details (Company Info)
    print(f"\n[2/3] Downloading company information...")
    print(f"  [WARNING] This will take ~{len(tickers) * 0.12 / 60:.0f} minutes")

    company_data = []
    success = 0
    failed = 0

    for idx, ticker in enumerate(tickers, 1):
        try:
            url = f'https://api.polygon.io/v3/reference/tickers/{ticker}'
            params = {'apiKey': api_key}

            response = polygon.session.get(url, params=params)

            if response.status_code == 200:
                data = response.json()
                results = data.get('results', {})

                company_data.append({
                    'ticker': ticker,
                    'name': results.get('name', ''),
                    'market_cap': results.get('market_cap', 0),
                    'sector': results.get('sic_description', ''),
                    'exchange': results.get('primary_exchange', ''),
                    'type': results.get('type', ''),
                    'locale': results.get('locale', ''),
                    'currency': results.get('currency_name', ''),
                    'total_employees': results.get('total_employees', 0),
                    'list_date': results.get('list_date', ''),
                    'description': results.get('description', '')[:200] if results.get('description') else ''
                })
                success += 1
            else:
                # If ticker not found, add minimal info
                company_data.append({
                    'ticker': ticker,
                    'name': '',
                    'market_cap': 0,
                    'sector': '',
                    'exchange': '',
                    'type': '',
                    'locale': '',
                    'currency': '',
                    'total_employees': 0,
                    'list_date': '',
                    'description': ''
                })
                failed += 1

            if idx % 100 == 0:
                print(f"  [{idx}/{len(tickers)}] Progress: {success} success, {failed} failed")

            time.sleep(0.13)  # Rate limit (slightly slower to be safe)

        except Exception as e:
            failed += 1
            company_data.append({
                'ticker': ticker,
                'name': '',
                'market_cap': 0,
                'sector': '',
                'exchange': '',
                'type': '',
                'locale': '',
                'currency': '',
                'total_employees': 0,
                'list_date': '',
                'description': ''
            })
            continue

    print(f"\n  Download complete: {success} success, {failed} failed")

    # Save company data
    company_df = pd.DataFrame(company_data)
    company_df.to_csv('backtest/database/COMPANY_INFO.csv', index=False)
    print(f"  [SAVED] backtest/database/COMPANY_INFO.csv")

    # Download Splits
    print(f"\n[3/3] Downloading stock splits information...")
    print(f"  [WARNING] This will take ~{len(tickers) * 0.12 / 60:.0f} minutes")

    all_splits = []
    success = 0
    failed = 0

    for idx, ticker in enumerate(tickers, 1):
        try:
            url = f'https://api.polygon.io/v3/reference/splits'
            params = {
                'ticker': ticker,
                'limit': 100,
                'apiKey': api_key
            }

            response = polygon.session.get(url, params=params)

            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])

                for split in results:
                    all_splits.append({
                        'ticker': ticker,
                        'execution_date': split.get('execution_date'),
                        'split_from': split.get('split_from'),
                        'split_to': split.get('split_to'),
                        'ratio': split.get('split_to', 1) / split.get('split_from', 1)
                    })

                if len(results) > 0:
                    success += 1
            else:
                failed += 1

            if idx % 100 == 0:
                print(f"  [{idx}/{len(tickers)}] Progress: {success} with splits, {failed} failed")

            time.sleep(0.13)  # Rate limit

        except Exception as e:
            failed += 1
            continue

    print(f"\n  Download complete: {success} tickers with splits, {len(all_splits)} total splits")

    # Save splits data
    if len(all_splits) > 0:
        splits_df = pd.DataFrame(all_splits)
        splits_df.to_csv('backtest/database/STOCK_SPLITS.csv', index=False)
        print(f"  [SAVED] backtest/database/STOCK_SPLITS.csv")
    else:
        print(f"  [INFO] No splits found")

    # Statistics
    print("\n" + "=" * 80)
    print("DOWNLOAD COMPLETE!")
    print("=" * 80)

    print(f"\n[COMPANY INFO]")
    print(f"  Total tickers: {len(company_df)}")
    print(f"  With market cap: {len(company_df[company_df['market_cap'] > 0])}")
    print(f"  With sector: {len(company_df[company_df['sector'] != ''])}")
    print(f"  With name: {len(company_df[company_df['name'] != ''])}")

    if len(all_splits) > 0:
        print(f"\n[SPLITS INFO]")
        print(f"  Total splits: {len(splits_df)}")
        print(f"  Tickers with splits: {splits_df['ticker'].nunique()}")

        # Reverse splits (ratio < 1)
        reverse = splits_df[splits_df['ratio'] < 1]
        print(f"  Reverse splits: {len(reverse)}")
        if len(reverse) > 0:
            print(f"    Top 5 reverse splits:")
            for _, row in reverse.nsmallest(5, 'ratio').iterrows():
                print(f"      {row['ticker']}: {row['split_from']}:{row['split_to']} ({row['execution_date']})")

        # Forward splits (ratio > 1)
        forward = splits_df[splits_df['ratio'] > 1]
        print(f"  Forward splits: {len(forward)}")

    print("\n" + "=" * 80)
    print("Real data from Polygon.io - Ready for ML!")
    print("=" * 80)


if __name__ == '__main__':
    main()
