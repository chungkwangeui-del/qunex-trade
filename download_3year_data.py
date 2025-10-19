"""
3년치 페니스톡 데이터 다운로드 스크립트
2022-01-01부터 현재까지 급등 페니스톡 데이터 수집
"""

import sys
import yaml
import logging
from datetime import datetime, timedelta
from src.data_collector import PennyStockCollector

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/download_3year_data.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def main():
    """3년치 데이터 다운로드 메인 함수"""

    logger.info("=" * 80)
    logger.info("3년치 페니스톡 데이터 다운로드 시작")
    logger.info("=" * 80)

    # 설정 파일 로드
    with open('config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # 날짜 범위 설정 (2022-01-01 ~ 현재)
    start_date = datetime(2022, 1, 1)
    end_date = datetime.now()

    # lookback_days를 3년으로 강제 설정
    config['data']['lookback_days'] = (end_date - start_date).days

    logger.info(f"다운로드 기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    logger.info(f"총 {config['data']['lookback_days']}일 데이터 수집")

    # 데이터 수집기 초기화
    collector = PennyStockCollector(config)

    # 페니스톡 종목 리스트 가져오기
    tickers = collector.get_penny_stock_universe()
    logger.info(f"총 {len(tickers)}개 페니스톡 종목 발견")

    # 스크리닝 없이 모든 종목 데이터 수집 (use_screening=False)
    logger.info("스크리닝 없이 모든 종목 데이터 수집 시작...")
    logger.info("이 작업은 시간이 오래 걸릴 수 있습니다 (수십 분 ~ 수 시간)")

    # 데이터 다운로드
    start_time = datetime.now()

    try:
        # 직접 다운로드 (스크리닝 없이)
        df = collector.download_multiple_stocks(
            tickers=tickers,
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            max_workers=10  # 병렬 다운로드 워커 수
        )

        if df.empty:
            logger.error("다운로드된 데이터가 없습니다!")
            return

        # 데이터 정리
        logger.info("데이터 정리 중...")
        df = collector.clean_data(df)

        # 기술적 데이터 추가
        logger.info("기술적 지표 추가 중...")
        df = collector.add_technical_data(df)

        # 데이터 저장
        filename = f'penny_stocks_3year_{datetime.now().strftime("%Y%m%d")}.csv'
        collector.save_data(df, filename)

        # 통계 출력
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        logger.info("=" * 80)
        logger.info("데이터 다운로드 완료!")
        logger.info("=" * 80)
        logger.info(f"총 소요 시간: {duration:.2f}초 ({duration/60:.2f}분)")
        logger.info(f"총 데이터 행 수: {len(df):,}")
        logger.info(f"고유 종목 수: {df['ticker'].nunique()}")
        logger.info(f"날짜 범위: {df['date'].min()} ~ {df['date'].max()}")
        logger.info(f"저장 파일: data/{filename}")

        # 종목별 데이터 통계
        logger.info("\n=== 종목별 데이터 수 (상위 20개) ===")
        ticker_counts = df['ticker'].value_counts().head(20)
        for ticker, count in ticker_counts.items():
            logger.info(f"  {ticker}: {count:,} rows")

        # 기본 데이터로도 저장 (기존 파일명)
        logger.info("\n기본 파일명으로도 저장 중...")
        collector.save_data(df, 'penny_stocks_data.csv')
        logger.info("data/penny_stocks_data.csv 파일 업데이트 완료")

        logger.info("\n모든 작업 완료!")

    except Exception as e:
        logger.error(f"데이터 다운로드 중 오류 발생: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return

if __name__ == "__main__":
    main()
