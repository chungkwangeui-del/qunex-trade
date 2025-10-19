"""
시그널 성공/실패 추적 시스템
- 다음 날 실제 가격 데이터 다운로드
- 시그널 성공 여부 판정 (50% 이상 급등)
- 데이터베이스 업데이트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SignalTracker:
    def __init__(self):
        self.history_path = 'web/data/signals_history.csv'
        self.surge_threshold = 0.5  # 50% 급등 기준

    def load_pending_signals(self):
        """아직 추적 안 된 시그널 로드"""
        if not os.path.exists(self.history_path):
            logger.warning("No signal history found!")
            return pd.DataFrame()

        df = pd.read_csv(self.history_path)

        # pending 상태만 필터링
        pending = df[df['status'] == 'pending'].copy()

        # trade_date가 오늘 또는 과거인 것만
        today = datetime.now().date()
        pending['trade_date'] = pd.to_datetime(pending['trade_date']).dt.date
        pending = pending[pending['trade_date'] <= today]

        logger.info(f"Found {len(pending)} pending signals to track")

        return pending

    def download_actual_prices(self, ticker, trade_date):
        """실제 거래 가격 다운로드"""
        try:
            # trade_date 당일 데이터
            start_date = trade_date
            end_date = trade_date + timedelta(days=1)

            df = yf.download(ticker, start=start_date, end=end_date, progress=False)

            if df.empty:
                logger.warning(f"{ticker} - No data for {trade_date}")
                return None, None

            # 시가 (매수가), 종가 (매도가)
            buy_price = df['Open'].iloc[0]
            sell_price = df['Close'].iloc[0]

            return buy_price, sell_price

        except Exception as e:
            logger.error(f"Error downloading {ticker}: {e}")
            return None, None

    def calculate_return(self, buy_price, sell_price):
        """수익률 계산"""
        if buy_price is None or sell_price is None:
            return None

        return_pct = ((sell_price - buy_price) / buy_price) * 100
        return return_pct

    def determine_status(self, actual_return):
        """성공/실패 판정"""
        if actual_return is None:
            return 'no_data'

        if actual_return >= (self.surge_threshold * 100):
            return 'success'
        elif actual_return >= 0:
            return 'partial'  # 플러스지만 50% 미만
        else:
            return 'failed'

    def update_signal(self, idx, buy_price, sell_price, actual_return, status):
        """시그널 상태 업데이트"""
        df = pd.read_csv(self.history_path)

        df.loc[idx, 'buy_price'] = buy_price
        df.loc[idx, 'sell_price'] = sell_price
        df.loc[idx, 'actual_return'] = actual_return
        df.loc[idx, 'status'] = status
        df.loc[idx, 'tracked_at'] = datetime.now()

        df.to_csv(self.history_path, index=False)

    def track_signals(self):
        """모든 pending 시그널 추적"""
        pending = self.load_pending_signals()

        if pending.empty:
            logger.info("No signals to track.")
            return

        logger.info("=" * 80)
        logger.info("Signal Tracking - Starting")
        logger.info("=" * 80)

        tracked_count = 0
        success_count = 0
        partial_count = 0
        failed_count = 0

        for idx, row in pending.iterrows():
            ticker = row['ticker']
            trade_date = row['trade_date']
            predicted_prob = row['predicted_probability']

            logger.info(f"\nTracking: {ticker} (trade_date: {trade_date}, prob: {predicted_prob:.3f})")

            # 실제 가격 다운로드
            buy_price, sell_price = self.download_actual_prices(ticker, trade_date)

            if buy_price is None or sell_price is None:
                # 데이터 없음 (휴장일, 상장폐지 등)
                self.update_signal(idx, None, None, None, 'no_data')
                logger.warning(f"  -> No data available")
                continue

            # 수익률 계산
            actual_return = self.calculate_return(buy_price, sell_price)

            # 성공/실패 판정
            status = self.determine_status(actual_return)

            # 업데이트
            self.update_signal(idx, buy_price, sell_price, actual_return, status)

            # 카운트
            tracked_count += 1
            if status == 'success':
                success_count += 1
                logger.info(f"  -> SUCCESS: {actual_return:.2f}% (${buy_price:.4f} -> ${sell_price:.4f})")
            elif status == 'partial':
                partial_count += 1
                logger.info(f"  -> PARTIAL: {actual_return:.2f}% (${buy_price:.4f} -> ${sell_price:.4f})")
            elif status == 'failed':
                failed_count += 1
                logger.info(f"  -> FAILED: {actual_return:.2f}% (${buy_price:.4f} -> ${sell_price:.4f})")

        logger.info("\n" + "=" * 80)
        logger.info("Signal Tracking - Completed")
        logger.info("=" * 80)
        logger.info(f"Total tracked: {tracked_count}")
        logger.info(f"Success (50%+): {success_count} ({success_count/tracked_count*100:.1f}%)" if tracked_count > 0 else "No signals tracked")
        logger.info(f"Partial (0-50%): {partial_count}")
        logger.info(f"Failed (<0%): {failed_count}")
        logger.info("=" * 80)

    def get_statistics(self):
        """전체 통계 계산"""
        if not os.path.exists(self.history_path):
            return None

        df = pd.read_csv(self.history_path)

        # 추적 완료된 시그널만
        tracked = df[df['status'].isin(['success', 'partial', 'failed'])].copy()

        if tracked.empty:
            return None

        stats = {
            'total_signals': len(tracked),
            'success_count': len(tracked[tracked['status'] == 'success']),
            'partial_count': len(tracked[tracked['status'] == 'partial']),
            'failed_count': len(tracked[tracked['status'] == 'failed']),
            'success_rate': len(tracked[tracked['status'] == 'success']) / len(tracked) * 100,
            'win_rate': len(tracked[tracked['actual_return'] >= 0]) / len(tracked) * 100,
            'avg_return': tracked['actual_return'].mean(),
            'median_return': tracked['actual_return'].median(),
            'max_return': tracked['actual_return'].max(),
            'min_return': tracked['actual_return'].min()
        }

        return stats

    def print_statistics(self):
        """통계 출력"""
        stats = self.get_statistics()

        if stats is None:
            print("No tracked signals yet.")
            return

        print("\n" + "=" * 80)
        print("OVERALL STATISTICS")
        print("=" * 80)
        print(f"Total Signals Tracked: {stats['total_signals']}")
        print(f"Success (50%+): {stats['success_count']} ({stats['success_rate']:.1f}%)")
        print(f"Partial (0-50%): {stats['partial_count']}")
        print(f"Failed (<0%): {stats['failed_count']}")
        print(f"Overall Win Rate: {stats['win_rate']:.1f}%")
        print(f"Average Return: {stats['avg_return']:.2f}%")
        print(f"Median Return: {stats['median_return']:.2f}%")
        print(f"Max Return: {stats['max_return']:.2f}%")
        print(f"Min Return: {stats['min_return']:.2f}%")
        print("=" * 80)

if __name__ == '__main__':
    tracker = SignalTracker()

    # 추적 실행
    tracker.track_signals()

    # 전체 통계 출력
    tracker.print_statistics()
