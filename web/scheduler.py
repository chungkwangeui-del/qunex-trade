"""
자동 스케줄러 - 매일 오후 4:05 PM 통합 실행
- 어제 시그널 추적
- 통계 업데이트
- 오늘 시그널 생성
"""

import schedule
import time
from datetime import datetime
import subprocess
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('web/logs/scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def is_market_day():
    """
    시장 개장일 체크 (주말 + 휴장일 제외)
    """
    today = datetime.now()

    # 주말 체크
    if today.weekday() >= 5:  # 토, 일
        return False

    # 2025년 미국 주식시장 휴장일
    us_holidays_2025 = [
        datetime(2025, 1, 1),   # New Year's Day
        datetime(2025, 1, 20),  # Martin Luther King Jr. Day
        datetime(2025, 2, 17),  # Presidents' Day
        datetime(2025, 4, 18),  # Good Friday
        datetime(2025, 5, 26),  # Memorial Day
        datetime(2025, 6, 19),  # Juneteenth
        datetime(2025, 7, 4),   # Independence Day
        datetime(2025, 9, 1),   # Labor Day
        datetime(2025, 11, 27), # Thanksgiving
        datetime(2025, 12, 25), # Christmas
    ]

    # 날짜만 비교
    today_date = datetime(today.year, today.month, today.day)
    if today_date in us_holidays_2025:
        return False

    return True

def run_daily_process():
    """매일 4:05 PM 통합 실행"""
    if not is_market_day():
        logger.info("Non-trading day detected (weekend or holiday). Skipping daily process.")
        logger.info("Signals from previous trading day will remain active.")
        return

    logger.info("=" * 100)
    logger.info("Starting daily process (tracking + generation)...")
    logger.info(f"Time: {datetime.now()}")
    logger.info("=" * 100)

    try:
        result = subprocess.run(
            ['python', 'web/daily_runner.py'],
            capture_output=True,
            text=True,
            timeout=1200,  # 20분 타임아웃
            cwd=r'c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE'
        )

        if result.returncode == 0:
            logger.info("Daily process completed successfully!")
            logger.info(result.stdout)
        else:
            logger.error("Daily process failed!")
            logger.error(result.stderr)

    except subprocess.TimeoutExpired:
        logger.error("Daily process timed out (20 minutes exceeded)")
    except Exception as e:
        logger.error(f"Error during daily process: {e}")

def schedule_jobs():
    """스케줄 설정"""

    # 매일 오후 4:05 PM (미국 동부 시간 기준)
    # 장 마감 후 5분 뒤 - 모든 작업 한 번에 실행
    schedule.every().day.at("16:05").do(run_daily_process)

    logger.info("=" * 100)
    logger.info("God Model Scheduler Started!")
    logger.info("=" * 100)
    logger.info("Schedule: Every day at 4:05 PM ET")
    logger.info("")
    logger.info("Daily Process:")
    logger.info("  1. Track yesterday's signals (success/failed)")
    logger.info("  2. Update statistics")
    logger.info("  3. Generate today's signals")
    logger.info("  4. Verify data integrity")
    logger.info("=" * 100)

    # 즉시 한 번 실행 (테스트용 - 주석 해제하면 바로 실행)
    # logger.info("\nRunning initial test...")
    # run_daily_process()

    # 스케줄 루프
    while True:
        schedule.run_pending()
        time.sleep(60)  # 1분마다 체크

if __name__ == '__main__':
    import os
    os.makedirs('web/logs', exist_ok=True)

    logger.info("=" * 80)
    logger.info("God Model Scheduler Starting...")
    logger.info(f"Current time: {datetime.now()}")
    logger.info("=" * 80)

    schedule_jobs()
