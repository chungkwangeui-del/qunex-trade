"""
매일 4:05 PM 통합 실행 스크립트
1. 어제 시그널 추적 (실제 결과 확인)
2. 통계 업데이트
3. 오늘 새 시그널 생성
4. 데이터베이스 정리
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from datetime import datetime
from signal_tracker import SignalTracker
from daily_signal_generator import DailySignalGenerator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DailyRunner:
    def __init__(self):
        self.tracker = SignalTracker()
        self.generator = DailySignalGenerator()

    def run_daily_process(self):
        """매일 4:05 PM 실행 프로세스"""
        logger.info("=" * 100)
        logger.info("GOD MODEL DAILY PROCESS - STARTING")
        logger.info(f"Time: {datetime.now()}")
        logger.info("=" * 100)

        # STEP 1: 어제 시그널 추적 및 성공/실패 판정
        logger.info("\n[STEP 1/4] Tracking yesterday's signals...")
        logger.info("-" * 100)
        try:
            self.tracker.track_signals()
            logger.info("[STEP 1/4] COMPLETED - Signal tracking finished")
        except Exception as e:
            logger.error(f"[STEP 1/4] FAILED - Error in tracking: {e}")

        # STEP 2: 통계 업데이트 및 출력
        logger.info("\n[STEP 2/4] Calculating statistics...")
        logger.info("-" * 100)
        try:
            self.tracker.print_statistics()
            logger.info("[STEP 2/4] COMPLETED - Statistics calculated")
        except Exception as e:
            logger.error(f"[STEP 2/4] FAILED - Error in statistics: {e}")

        # STEP 3: 오늘 새로운 시그널 생성
        logger.info("\n[STEP 3/4] Generating today's signals...")
        logger.info("-" * 100)
        try:
            signals = self.generator.run()

            if signals is not None and not signals.empty:
                logger.info(f"[STEP 3/4] COMPLETED - Generated {len(signals)} signals")
                logger.info("\nTODAY'S SIGNALS:")
                logger.info("-" * 100)
                for idx, row in signals.iterrows():
                    logger.info(f"  {row['ticker']}: {row['predicted_probability']:.3f} probability, "
                              f"Price: ${row['Close']:.4f}, Volume: {row['Volume']:,.0f}")
            else:
                logger.warning("[STEP 3/4] No signals generated (no stocks above threshold)")

        except Exception as e:
            logger.error(f"[STEP 3/4] FAILED - Error in signal generation: {e}")

        # STEP 4: 데이터 정리 및 최종 확인
        logger.info("\n[STEP 4/4] Final verification...")
        logger.info("-" * 100)
        try:
            # signals_today.csv 존재 확인
            today_path = 'web/data/signals_today.csv'
            history_path = 'web/data/signals_history.csv'

            today_exists = os.path.exists(today_path)
            history_exists = os.path.exists(history_path)

            logger.info(f"  Today's signals file: {'EXISTS' if today_exists else 'MISSING'}")
            logger.info(f"  History file: {'EXISTS' if history_exists else 'MISSING'}")

            if history_exists:
                import pandas as pd
                df = pd.read_csv(history_path)
                logger.info(f"  Total signals in history: {len(df)}")
                logger.info(f"  Pending signals: {len(df[df['status'] == 'pending'])}")
                logger.info(f"  Tracked signals: {len(df[df['status'] != 'pending'])}")

            logger.info("[STEP 4/4] COMPLETED - Verification finished")

        except Exception as e:
            logger.error(f"[STEP 4/4] FAILED - Error in verification: {e}")

        # 최종 요약
        logger.info("\n" + "=" * 100)
        logger.info("GOD MODEL DAILY PROCESS - COMPLETED")
        logger.info(f"Time: {datetime.now()}")
        logger.info("=" * 100)
        logger.info("\nNext run: Tomorrow at 4:05 PM ET")
        logger.info("Web dashboard: http://localhost:5000")
        logger.info("=" * 100 + "\n")

if __name__ == '__main__':
    runner = DailyRunner()
    runner.run_daily_process()
