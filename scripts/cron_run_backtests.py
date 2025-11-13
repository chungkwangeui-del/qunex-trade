"""
Run Pending Backtests Cron Job

Processes pending backtest jobs and calculates strategy performance.
Schedule: Every minute (* * * * *)
"""

import os
import sys
import json
from datetime import datetime, timedelta
from decimal import Decimal

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()


def run_backtests():
    """Process pending backtest jobs"""
    try:
        # Import within function to avoid circular imports
        from web.app import app
        from web.database import db, BacktestJob
        from src.polygon_service import PolygonService

        with app.app_context():
            # Get pending jobs
            pending_jobs = BacktestJob.query.filter_by(status='pending').limit(5).all()

            if not pending_jobs:
                print("No pending backtest jobs")
                return True

            print(f"Processing {len(pending_jobs)} backtest jobs...")

            polygon = PolygonService()

            for job in pending_jobs:
                try:
                    # Update status to running
                    job.status = 'running'
                    db.session.commit()

                    print(f"Running backtest {job.id}: {job.ticker} from {job.start_date} to {job.end_date}")

                    # Fetch historical data
                    start_str = job.start_date.strftime('%Y-%m-%d')
                    end_str = job.end_date.strftime('%Y-%m-%d')

                    bars = polygon.get_aggregates(
                        ticker=job.ticker,
                        multiplier=1,
                        timespan='day',
                        from_date=start_str,
                        to_date=end_str
                    )

                    if not bars or len(bars) < 10:
                        raise ValueError("Insufficient data for backtest")

                    # Simple backtest strategy: Buy and Hold
                    initial_capital = float(job.initial_capital)
                    entry_price = bars[0].get('c', 0)  # First close price
                    exit_price = bars[-1].get('c', 0)  # Last close price

                    if entry_price == 0 or exit_price == 0:
                        raise ValueError("Invalid price data")

                    shares = initial_capital / entry_price
                    final_value = shares * exit_price
                    profit = final_value - initial_capital
                    profit_pct = (profit / initial_capital) * 100

                    # Calculate daily returns for charting
                    daily_values = []
                    for bar in bars:
                        day_price = bar.get('c', 0)
                        day_value = shares * day_price
                        daily_values.append({
                            'date': datetime.fromtimestamp(bar['t'] / 1000).strftime('%Y-%m-%d'),
                            'value': round(day_value, 2)
                        })

                    # Build result
                    result = {
                        'ticker': job.ticker,
                        'strategy': 'Buy and Hold',
                        'initial_capital': initial_capital,
                        'final_value': round(final_value, 2),
                        'profit': round(profit, 2),
                        'profit_pct': round(profit_pct, 2),
                        'entry_price': round(entry_price, 2),
                        'exit_price': round(exit_price, 2),
                        'shares': round(shares, 4),
                        'num_days': len(bars),
                        'daily_values': daily_values
                    }

                    # Save result
                    job.result_json = json.dumps(result)
                    job.status = 'completed'
                    job.completed_at = datetime.utcnow()
                    job.error_message = None

                    db.session.commit()

                    print(f"✓ Backtest {job.id} completed: {profit_pct:+.2f}% return")

                except Exception as e:
                    # Mark as failed
                    job.status = 'failed'
                    job.error_message = str(e)
                    job.completed_at = datetime.utcnow()
                    db.session.commit()

                    print(f"✗ Backtest {job.id} failed: {e}")

            return True

    except Exception as e:
        print(f"✗ Error processing backtests: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_backtests()
    sys.exit(0 if success else 1)
