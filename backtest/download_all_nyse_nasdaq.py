"""
Download ALL NYSE/NASDAQ Stocks - Complete Database Builder
Downloads 2-3 years of historical data for all actively traded stocks
Filters out delisted, sub-$1, and low-volume stocks
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web.polygon_service import PolygonService
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime, timedelta
import time


class ComprehensiveStockDownloader:
    """Download ALL NYSE/NASDAQ stocks"""

    def __init__(self):
        # Load API key
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env_path = os.path.join(parent_dir, '.env')
        load_dotenv(env_path)

        api_key = os.getenv('POLYGON_API_KEY')
        if not api_key:
            raise ValueError("POLYGON_API_KEY not found in .env file")

        self.polygon = PolygonService(api_key)
        print(f"[OK] Polygon API initialized")

    def get_all_tickers(self):
        """Get ALL NYSE and NASDAQ tickers from Polygon.io"""

        print(f"\n[1/6] Getting ALL NYSE/NASDAQ tickers from Polygon.io...")

        all_tickers = []

        # Use Polygon's ticker list endpoint
        # This gets ALL tickers (not just actives)
        try:
            # Get reference data for all US stocks
            # We'll use the tickers endpoint to get comprehensive list

            print("  Fetching ticker list from Polygon.io...")

            # Method 1: Use tickers endpoint with pagination
            url = "https://api.polygon.io/v3/reference/tickers"

            params = {
                'market': 'stocks',
                'exchange': 'XNYS,XNAS',  # NYSE and NASDAQ
                'active': 'true',  # Only currently active
                'limit': 1000,
                'apiKey': self.polygon.api_key
            }

            all_results = []
            next_url = None

            # Paginate through all results
            page = 1
            while True:
                if next_url:
                    response = self.polygon.session.get(next_url)
                else:
                    response = self.polygon.session.get(url, params=params)

                if response.status_code == 200:
                    data = response.json()
                    results = data.get('results', [])
                    all_results.extend(results)

                    print(f"  Page {page}: Found {len(results)} tickers (Total: {len(all_results)})")

                    # Check for next page
                    next_url = data.get('next_url')
                    if not next_url:
                        break

                    # Add API key to next URL
                    next_url += f"&apiKey={self.polygon.api_key}"
                    page += 1

                    # Rate limit
                    time.sleep(0.1)
                else:
                    print(f"  [ERROR] API request failed: {response.status_code}")
                    break

            # Extract tickers
            for ticker_data in all_results:
                ticker = ticker_data.get('ticker')
                name = ticker_data.get('name', '')
                ticker_type = ticker_data.get('type', '')

                # Filter for common stocks only (not warrants, units, etc.)
                if ticker_type in ['CS', 'ADRC', 'ETF']:  # Common Stock, ADR, ETFs
                    all_tickers.append({
                        'ticker': ticker,
                        'name': name,
                        'type': ticker_type
                    })

            print(f"\n  Total tickers found: {len(all_tickers)}")

        except Exception as e:
            print(f"  [ERROR] Failed to get tickers: {e}")
            return []

        return all_tickers

    def filter_tickers(self, all_tickers):
        """Filter tickers by checking current status"""

        print(f"\n[2/6] Filtering tickers (checking current trading status)...")

        valid_tickers = []
        checked = 0

        for ticker_info in all_tickers:
            ticker = ticker_info['ticker']
            checked += 1

            if checked % 100 == 0:
                print(f"  Checked {checked}/{len(all_tickers)} tickers...")

            try:
                # Get ticker details to verify it's tradeable
                ticker_details = self.polygon.get_ticker_details(ticker)

                if ticker_details:
                    # Check if active
                    active = ticker_details.get('active', False)
                    market = ticker_details.get('market', '')
                    primary_exchange = ticker_details.get('primary_exchange', '')

                    # Must be active and on NYSE/NASDAQ
                    if active and market == 'stocks':
                        if 'NYSE' in primary_exchange or 'NASDAQ' in primary_exchange or \
                           primary_exchange in ['XNYS', 'XNAS', 'NYS', 'NAS']:
                            valid_tickers.append(ticker)

                # Rate limit (5 calls per second on Starter plan)
                time.sleep(0.2)

            except Exception as e:
                # Skip tickers that cause errors
                continue

        print(f"\n  Valid NYSE/NASDAQ tickers: {len(valid_tickers)}")
        return valid_tickers

    def download_historical_data(self, tickers, years=2):
        """Download historical data for all tickers"""

        print(f"\n[3/6] Downloading {years}-year historical data...")

        # Date range (2 years back from today, adjusted for actual data)
        end_date = '2024-10-25'  # Latest reliable data
        start_date = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=years*365)).strftime('%Y-%m-%d')

        print(f"  Date range: {start_date} to {end_date}")
        print(f"  Total tickers: {len(tickers)}")

        all_data = []
        success_count = 0
        fail_count = 0

        for idx, ticker in enumerate(tickers, 1):
            try:
                # Download data
                data = self.polygon.get_aggregates(
                    ticker=ticker,
                    multiplier=1,
                    timespan='day',
                    from_date=start_date,
                    to_date=end_date,
                    limit=5000
                )

                if data and len(data) > 0:
                    # Convert to DataFrame
                    df = pd.DataFrame(data)
                    df['ticker'] = ticker

                    # Rename columns to match our format
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

                    # Convert timestamp to date
                    df['date'] = pd.to_datetime(df['timestamp'], unit='ms')

                    all_data.append(df)
                    success_count += 1

                    if idx % 50 == 0:
                        print(f"  [{idx}/{len(tickers)}] {ticker}... [OK] {len(df)} bars (Total: {success_count} stocks)")
                else:
                    fail_count += 1

                # Rate limit
                time.sleep(0.12)  # ~8 requests/second (safe for Starter plan)

            except Exception as e:
                fail_count += 1
                if idx % 50 == 0:
                    print(f"  [{idx}/{len(tickers)}] {ticker}... [X] Error")
                continue

        print(f"\n  Success: {success_count}, Failed: {fail_count}")

        if len(all_data) == 0:
            print("  [ERROR] No data downloaded!")
            return None

        # Combine all data
        combined_df = pd.concat(all_data, ignore_index=True)
        print(f"  Total rows: {len(combined_df):,}")

        return combined_df

    def filter_by_quality(self, df):
        """Filter stocks by price and volume quality"""

        print(f"\n[4/6] Filtering by quality criteria...")

        print(f"  Total rows before filter: {len(df):,}")
        print(f"  Total tickers before filter: {df['ticker'].nunique()}")

        # Calculate average price and volume per ticker
        ticker_stats = df.groupby('ticker').agg({
            'Close': ['min', 'max', 'mean'],
            'Volume': 'mean'
        }).reset_index()

        ticker_stats.columns = ['ticker', 'min_price', 'max_price', 'avg_price', 'avg_volume']

        # Filter criteria for QUALITY stocks:
        # 1. Min price >= $1 (Kiwoom restriction)
        # 2. Avg price <= $100 (penny/small cap focus)
        # 3. Avg volume >= 100,000 (liquidity requirement)
        # 4. Min price not too close to max (avoid extreme volatility/splits)

        quality_tickers = ticker_stats[
            (ticker_stats['min_price'] >= 1.0) &
            (ticker_stats['avg_price'] <= 100.0) &
            (ticker_stats['avg_volume'] >= 100000) &
            (ticker_stats['max_price'] / ticker_stats['min_price'] <= 50)  # No 50x moves (likely data errors)
        ]['ticker'].tolist()

        print(f"\n  Quality criteria:")
        print(f"    Min price >= $1: {len(ticker_stats[ticker_stats['min_price'] >= 1.0])}")
        print(f"    Avg price <= $100: {len(ticker_stats[ticker_stats['avg_price'] <= 100])}")
        print(f"    Avg volume >= 100k: {len(ticker_stats[ticker_stats['avg_volume'] >= 100000])}")
        print(f"    Price stability: {len(ticker_stats[ticker_stats['max_price'] / ticker_stats['min_price'] <= 50])}")

        # Filter dataframe
        filtered_df = df[df['ticker'].isin(quality_tickers)].copy()

        print(f"\n  Tickers after quality filter: {len(quality_tickers)}")
        print(f"  Rows after filter: {len(filtered_df):,}")

        return filtered_df

    def save_database(self, df):
        """Save to master database"""

        print(f"\n[5/6] Saving master database...")

        # Create database directory
        db_dir = 'backtest/database'
        os.makedirs(db_dir, exist_ok=True)

        # Save main CSV
        csv_file = os.path.join(db_dir, 'nyse_nasdaq_master.csv')
        df.to_csv(csv_file, index=False)
        print(f"  [SAVED] {csv_file}")
        print(f"  Rows: {len(df):,}")
        print(f"  Tickers: {df['ticker'].nunique()}")
        print(f"  Date range: {df['date'].min()} to {df['date'].max()}")

        # Save ticker list
        ticker_list = df['ticker'].unique().tolist()
        ticker_file = os.path.join(db_dir, 'ticker_list.txt')
        with open(ticker_file, 'w') as f:
            for ticker in sorted(ticker_list):
                f.write(f"{ticker}\n")
        print(f"  [SAVED] {ticker_file} ({len(ticker_list)} tickers)")

        # Save metadata
        metadata = {
            'download_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_tickers': df['ticker'].nunique(),
            'total_rows': len(df),
            'date_range': f"{df['date'].min()} to {df['date'].max()}",
            'exchanges': 'NYSE, NASDAQ',
            'filters_applied': [
                'Min price >= $1',
                'Avg price <= $100',
                'Avg volume >= 100k/day',
                'Price stability check',
                'Active trading only'
            ]
        }

        metadata_file = os.path.join(db_dir, 'metadata.txt')
        with open(metadata_file, 'w') as f:
            for key, value in metadata.items():
                f.write(f"{key}: {value}\n")
        print(f"  [SAVED] {metadata_file}")

        return csv_file

    def generate_statistics(self, df):
        """Generate database statistics"""

        print(f"\n[6/6] Database Statistics")
        print("=" * 80)

        print(f"\nOverview:")
        print(f"  Total tickers: {df['ticker'].nunique()}")
        print(f"  Total data points: {len(df):,}")
        print(f"  Date range: {df['date'].min().strftime('%Y-%m-%d')} to {df['date'].max().strftime('%Y-%m-%d')}")
        print(f"  Trading days: {df['date'].nunique()}")

        # Price statistics
        print(f"\nPrice Range:")
        print(f"  Min: ${df['Close'].min():.2f}")
        print(f"  Max: ${df['Close'].max():.2f}")
        print(f"  Median: ${df['Close'].median():.2f}")
        print(f"  Mean: ${df['Close'].mean():.2f}")

        # Volume statistics
        print(f"\nVolume Statistics:")
        print(f"  Median daily volume: {df['Volume'].median():,.0f}")
        print(f"  Mean daily volume: {df['Volume'].mean():,.0f}")

        # Top 10 most active stocks
        top_volume = df.groupby('ticker')['Volume'].mean().nlargest(10)
        print(f"\nTop 10 Most Active Stocks (by avg volume):")
        for ticker, vol in top_volume.items():
            print(f"  {ticker}: {vol:,.0f}/day")

        # Top 10 most volatile stocks
        df['daily_return'] = df.groupby('ticker')['Close'].pct_change()
        volatility = df.groupby('ticker')['daily_return'].std().nlargest(10)
        print(f"\nTop 10 Most Volatile Stocks (by daily return std):")
        for ticker, vol in volatility.items():
            print(f"  {ticker}: {vol*100:.2f}% daily std")


def main():
    """Main download process"""

    print("\n")
    print("#" * 80)
    print("COMPREHENSIVE NYSE/NASDAQ DATABASE BUILDER")
    print("Download ALL actively traded stocks (2-3 years)")
    print("#" * 80)

    downloader = ComprehensiveStockDownloader()

    # Step 1: Get all tickers
    all_tickers = downloader.get_all_tickers()

    if len(all_tickers) == 0:
        print("\n[ERROR] No tickers found!")
        return

    # Step 2: Filter tickers (this will take a while)
    print(f"\n[WARNING] This will check {len(all_tickers)} tickers")
    print(f"[WARNING] Estimated time: {len(all_tickers) * 0.2 / 60:.1f} minutes")

    valid_tickers = downloader.filter_tickers(all_tickers)

    if len(valid_tickers) == 0:
        print("\n[ERROR] No valid tickers after filtering!")
        return

    # Step 3: Download historical data
    print(f"\n[WARNING] Downloading data for {len(valid_tickers)} tickers")
    print(f"[WARNING] Estimated time: {len(valid_tickers) * 0.12 / 60:.1f} minutes")

    df = downloader.download_historical_data(valid_tickers, years=2)

    if df is None:
        print("\n[ERROR] Download failed!")
        return

    # Step 4: Filter by quality
    df_filtered = downloader.filter_by_quality(df)

    # Step 5: Save database
    db_file = downloader.save_database(df_filtered)

    # Step 6: Statistics
    downloader.generate_statistics(df_filtered)

    print("\n" + "=" * 80)
    print("DATABASE BUILD COMPLETE!")
    print("=" * 80)
    print(f"\nDatabase file: {db_file}")
    print(f"Ready for ML training and backtesting!")


if __name__ == '__main__':
    main()
