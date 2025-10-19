"""
새로 추가된 고변동성 종목 데이터 다운로드 스크립트
"""

import sys
import yaml
import logging
import pandas as pd
from datetime import datetime
from src.data_collector import PennyStockCollector

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/download_new_tickers.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# 새로 추가된 종목 리스트
NEW_TICKERS = [
    # 고변동성 2024 종목
    'MTTR', 'EDBL', 'PEGY', 'ONFO', 'SPRC', 'AUUD', 'BMR',

    # 바이오테크 고변동성
    'PBLA', 'KTRA', 'BXRX', 'OCEA',

    # OTC/Pink Sheet 고변동성
    'GOFF', 'SNGX',

    # 추가 뉴스 기반 급등 종목들
    'REED', 'BKTI', 'DPLS', 'LQDA', 'HSTO', 'DRUG',
    'DRMA', 'TPST', 'EVAX', 'CDTX',
]

def main():
    """새 종목 데이터 다운로드 및 통합"""

    logger.info("=" * 80)
    logger.info(f"새로 추가된 {len(NEW_TICKERS)}개 종목 데이터 다운로드 시작")
    logger.info("=" * 80)

    # 설정 파일 로드
    with open('config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # 데이터 수집기 초기화
    collector = PennyStockCollector(config)

    # 3년치 데이터 다운로드
    start_date = '2022-01-01'
    end_date = datetime.now().strftime('%Y-%m-%d')

    logger.info(f"다운로드 기간: {start_date} ~ {end_date}")
    logger.info(f"종목 리스트: {', '.join(NEW_TICKERS)}")

    # 새 데이터 다운로드
    start_time = datetime.now()

    try:
        new_df = collector.download_multiple_stocks(
            tickers=NEW_TICKERS,
            start_date=start_date,
            end_date=end_date,
            max_workers=10
        )

        if new_df.empty:
            logger.error("다운로드된 데이터가 없습니다!")
            return

        # 데이터 정리
        logger.info("데이터 정리 중...")
        new_df = collector.clean_data(new_df)

        # 기술적 데이터 추가
        logger.info("기술적 지표 추가 중...")
        new_df = collector.add_technical_data(new_df)

        # 기존 데이터 로드
        logger.info("기존 데이터 로드 중...")
        try:
            existing_df = pd.read_csv('data/penny_stocks_data.csv')
            logger.info(f"기존 데이터: {len(existing_df):,} rows, {existing_df['ticker'].nunique()} tickers")

            # 새 종목만 추가 (기존에 있는 종목 제외)
            new_tickers_only = set(new_df['ticker'].unique()) - set(existing_df['ticker'].unique())
            logger.info(f"새로 추가될 종목: {len(new_tickers_only)}개 - {', '.join(sorted(new_tickers_only))}")

            # 데이터 병합
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            combined_df = collector.clean_data(combined_df)

            logger.info(f"병합 후 데이터: {len(combined_df):,} rows, {combined_df['ticker'].nunique()} tickers")

        except FileNotFoundError:
            logger.warning("기존 데이터 파일 없음. 새 데이터만 저장합니다.")
            combined_df = new_df

        # 저장
        collector.save_data(combined_df, 'penny_stocks_data.csv')

        # 백업 저장
        backup_filename = f'penny_stocks_updated_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        collector.save_data(combined_df, backup_filename)

        # 통계 출력
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        logger.info("=" * 80)
        logger.info("데이터 업데이트 완료!")
        logger.info("=" * 80)
        logger.info(f"소요 시간: {duration:.2f}초")
        logger.info(f"새 데이터: {len(new_df):,} rows")
        logger.info(f"최종 데이터: {len(combined_df):,} rows")
        logger.info(f"총 종목 수: {combined_df['ticker'].nunique()}")
        logger.info(f"저장 파일: data/penny_stocks_data.csv")
        logger.info(f"백업 파일: data/{backup_filename}")

        # 새 종목별 데이터 수
        logger.info("\n=== 새 종목 데이터 수 ===")
        for ticker in sorted(new_df['ticker'].unique()):
            count = len(new_df[new_df['ticker'] == ticker])
            logger.info(f"  {ticker}: {count:,} rows")

        # 일일 급등 체크
        logger.info("\n=== 새 종목 50%+ 급등 케이스 ===")
        new_df['daily_return_pct'] = new_df.groupby('ticker')['close'].pct_change() * 100
        surge_50 = new_df[new_df['daily_return_pct'] >= 50.0]

        if len(surge_50) > 0:
            surge_counts = surge_50.groupby('ticker').size().sort_values(ascending=False)
            for ticker, count in surge_counts.items():
                max_surge = surge_50[surge_50['ticker'] == ticker]['daily_return_pct'].max()
                logger.info(f"  {ticker}: {count}회 급등, 최대 +{max_surge:.1f}%")
        else:
            logger.info("  50%+ 급등 케이스 없음")

        logger.info("\n모든 작업 완료!")

    except Exception as e:
        logger.error(f"오류 발생: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return

if __name__ == "__main__":
    main()
