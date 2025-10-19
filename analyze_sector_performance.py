"""
섹터별 성능 분석 - 어떤 섹터가 잘 예측되고 어떤 섹터가 약한지 확인
"""

import pandas as pd
import numpy as np
from datetime import datetime

print("=" * 100)
print("섹터별 성능 분석 - God 모델 강점/약점 파악")
print("=" * 100)

# 섹터 정의
SECTORS = {
    'AI/양자컴퓨팅': ['RGTI', 'IONQ', 'QUBT', 'SOUN', 'IREN', 'BBAI', 'AI', 'PLTR', 'QBTS', 'DTST', 'CXAI', 'LUNR'],

    '바이오테크': ['NVAX', 'MRNA', 'BNTX', 'SAVA', 'OCGN', 'INO', 'VXRT', 'TNXP', 'SRNE', 'ATOS',
                  'ABVC', 'NLSP', 'SKIN', 'MBRX', 'AQST', 'SENS', 'NRXP', 'VKTX', 'KPTI', 'TGTX'],

    '전기차/EV': ['LCID', 'RIVN', 'PSNY', 'BLNK', 'CVNA', 'CHPT', 'EVGO', 'GOEV', 'WKHS', 'GEVO',
                 'AYRO', 'HYLN', 'QS', 'STEM'],

    '크립토/마이닝': ['RIOT', 'MARA', 'CLSK', 'COIN', 'CIFR', 'HUT', 'ANY', 'BITF', 'BTBT', 'ARBK',
                    'EBON', 'MIGI', 'CAN', 'XNET', 'SOS', 'CNET', 'APLD', 'WULF', 'CORZ'],

    '대마초': ['CGC', 'TLRY', 'SNDL', 'ACB', 'CRON', 'GRWG', 'IIPR', 'CURLF', 'GTBIF', 'TCNNF',
             'CRLBF', 'HEXO', 'OGI'],

    '밈주식': ['GME', 'AMC', 'BBBY', 'KOSS', 'NOK', 'BB', 'CLOV', 'MVIS', 'ATER', 'BBIG', 'PHUN'],

    '해운/물류': ['ZIM', 'TOPS', 'SHIP', 'CTRM', 'SBLK', 'GLBS', 'EDRY', 'ESEA', 'CMRE', 'NMM',
                'GSL', 'MATX', 'GOGL', 'HSHP'],

    '에너지/원자재': ['INDO', 'TALO', 'REI', 'VTLE', 'AR', 'GTE', 'CLF', 'FCX', 'NEM', 'VALE', 'MT'],

    '통신': ['SIRI', 'T', 'VZ', 'TMUS', 'LUMN', 'VEON', 'S', 'VOD'],

    'OTC 저가주': ['HMBL', 'SRMX', 'IGEX', 'OPTI', 'VYST', 'AITX', 'PHIL', 'GTEH', 'ENZC', 'PCTL',
                 'USMJ', 'ALPP', 'AMLH', 'AZFL', 'BIEL', 'BLSP', 'BOTY', 'CBDL', 'OZSC']
}

def get_sector(ticker):
    """티커의 섹터 반환"""
    for sector, tickers in SECTORS.items():
        if ticker in tickers:
            return sector
    return '기타'

def analyze_sector_performance():
    """섹터별 백테스트 성능 분석"""

    print("\n[1] 백테스트 데이터 로드")
    print("-" * 100)

    # 백테스트 결과 로드
    bt = pd.read_csv('results/backtest_threshold_0.95.csv')
    bt['date'] = pd.to_datetime(bt['date'])
    bt['trade_date'] = pd.to_datetime(bt['trade_date'])

    print(f"총 거래: {len(bt)}건")
    print(f"기간: {bt['trade_date'].min().date()} ~ {bt['trade_date'].max().date()}")

    # 섹터 추가
    bt['sector'] = bt['ticker'].apply(get_sector)

    print("\n[2] 섹터별 성과 분석")
    print("-" * 100)

    sector_stats = bt.groupby('sector').agg({
        'ticker': 'count',
        'is_surge': 'sum',
        'net_return': ['mean', 'median', 'std', 'min', 'max']
    }).round(4)

    sector_stats.columns = ['거래수', '급등성공', '평균수익률', '중간수익률', '수익률표준편차', '최소수익률', '최대수익률']
    sector_stats['성공률'] = (sector_stats['급등성공'] / sector_stats['거래수'] * 100).round(1)
    sector_stats = sector_stats.sort_values('성공률', ascending=False)

    print(f"\n{'섹터':<20} {'거래수':<8} {'성공률':<10} {'평균수익':<12} {'중간수익':<12} {'표준편차':<10}")
    print("-" * 100)

    for sector, row in sector_stats.iterrows():
        print(f"{sector:<20} {int(row['거래수']):<8} {row['성공률']:<9.1f}% "
              f"{row['평균수익률']*100:<11.1f}% {row['중간수익률']*100:<11.1f}% {row['수익률표준편차']*100:<9.1f}%")

    print("\n[3] 섹터별 상세 분석")
    print("-" * 100)

    print("\n[최고 성능 섹터 TOP 3]")
    top3_sectors = sector_stats.head(3)

    for i, (sector, row) in enumerate(top3_sectors.iterrows(), 1):
        print(f"\n{i}. {sector}")
        print(f"   - 성공률: {row['성공률']:.1f}%")
        print(f"   - 평균 수익률: {row['평균수익률']*100:.1f}%")
        print(f"   - 거래 수: {int(row['거래수'])}건")
        print(f"   - 평가: ★★★ 매우 강함 (뉴스 피처 불필요)")

    print("\n[최저 성능 섹터 TOP 3]")
    bottom3_sectors = sector_stats.tail(3)

    for i, (sector, row) in enumerate(bottom3_sectors.iloc[::-1].iterrows(), 1):
        print(f"\n{i}. {sector}")
        print(f"   - 성공률: {row['성공률']:.1f}%")
        print(f"   - 평균 수익률: {row['평균수익률']*100:.1f}%")
        print(f"   - 거래 수: {int(row['거래수'])}건")
        print(f"   - 평가: ⚠️ 약함 (뉴스 피처 추가 필요!)")

    print("\n[4] 뉴스 피처 추가 우선순위")
    print("-" * 100)

    # 거래수가 5건 이상이면서 성공률이 70% 미만인 섹터
    weak_sectors = sector_stats[(sector_stats['거래수'] >= 5) & (sector_stats['성공률'] < 70.0)]

    if len(weak_sectors) > 0:
        print("\n뉴스 피처 추가가 필요한 섹터:")
        print("\n우선순위  섹터               현재성공률  목표성공률  추가할 뉴스 피처")
        print("-" * 100)

        news_features = {
            'AI/양자컴퓨팅': 'Google/Microsoft AI 발표, Nvidia 실적',
            '바이오테크': 'FDA 승인, 임상시험 결과',
            '전기차/EV': '테슬라 실적, 정부 보조금',
            '크립토/마이닝': '비트코인 가격, SEC 규제',
            '대마초': '합법화 법안, FDA 치료제 승인',
            '밈주식': 'Reddit 트렌딩, Twitter 센티먼트',
            '해운/물류': '운임료, 수에즈 운하 뉴스',
            '에너지/원자재': '원유/금 가격, OPEC 발표',
            '통신': '5G 정책, 합병 뉴스',
            'OTC 저가주': 'Reddit 센티먼트, 거래량 급증'
        }

        for i, (sector, row) in enumerate(weak_sectors.iterrows(), 1):
            current_rate = row['성공률']
            target_rate = current_rate + 10  # 목표: +10%
            news_feature = news_features.get(sector, '일반 뉴스 센티먼트')

            print(f"{i:<10}  {sector:<20} {current_rate:<11.1f}% {target_rate:<11.1f}% {news_feature}")
    else:
        print("\n모든 섹터가 70% 이상 성공률! 뉴스 피처 추가 필요 없음!")

    print("\n[5] 월별 섹터 성과 추이")
    print("-" * 100)

    bt['year_month'] = bt['trade_date'].dt.to_period('M')

    # 최근 3개월
    recent_months = bt['year_month'].unique()[-3:]

    print(f"\n최근 3개월 섹터별 성과:")
    for month in recent_months:
        print(f"\n{month}:")
        month_data = bt[bt['year_month'] == month]

        sector_month = month_data.groupby('sector').agg({
            'ticker': 'count',
            'is_surge': 'sum'
        })
        sector_month['성공률'] = (sector_month['is_surge'] / sector_month['ticker'] * 100).round(1)
        sector_month = sector_month[sector_month['ticker'] >= 2]  # 2건 이상만
        sector_month = sector_month.sort_values('성공률', ascending=False)

        for sector, row in sector_month.iterrows():
            print(f"  {sector:<20}: {row['성공률']:.1f}% ({int(row['is_surge'])}/{int(row['ticker'])})")

    print("\n[6] 티커별 성과 (섹터 내)")
    print("-" * 100)

    print("\n각 섹터에서 가장 잘 예측되는 종목:")

    for sector in ['AI/양자컴퓨팅', '바이오테크', '크립토/마이닝', 'OTC 저가주']:
        sector_data = bt[bt['sector'] == sector]

        if len(sector_data) > 0:
            ticker_perf = sector_data.groupby('ticker').agg({
                'trade_date': 'count',
                'is_surge': 'sum',
                'net_return': 'mean'
            })
            ticker_perf.columns = ['거래수', '성공', '평균수익률']
            ticker_perf['성공률'] = (ticker_perf['성공'] / ticker_perf['거래수'] * 100).round(1)
            ticker_perf = ticker_perf[ticker_perf['거래수'] >= 3]  # 3건 이상
            ticker_perf = ticker_perf.sort_values('성공률', ascending=False).head(5)

            print(f"\n{sector}:")
            for ticker, row in ticker_perf.iterrows():
                print(f"  {ticker:<8}: {row['성공률']:.1f}% ({int(row['성공'])}/{int(row['거래수'])}건) "
                      f"평균 {row['평균수익률']*100:.1f}%")

    print("\n" + "=" * 100)
    print("[7] 최종 권장사항")
    print("=" * 100)

    # 전체 성공률
    overall_success = (bt['is_surge'].sum() / len(bt) * 100)

    print(f"\n현재 전체 성공률: {overall_success:.1f}%")

    # 섹터별 비교
    strong_sectors = sector_stats[sector_stats['성공률'] > overall_success]
    weak_sectors = sector_stats[sector_stats['성공률'] < overall_success]

    print(f"\n강한 섹터 ({len(strong_sectors)}개):")
    for sector in strong_sectors.head(5).index:
        rate = strong_sectors.loc[sector, '성공률']
        print(f"  - {sector}: {rate:.1f}% (평균 대비 +{rate - overall_success:.1f}%)")

    print(f"\n약한 섹터 ({len(weak_sectors)}개):")
    for sector in weak_sectors.tail(5).index:
        rate = weak_sectors.loc[sector, '성공률']
        print(f"  - {sector}: {rate:.1f}% (평균 대비 {rate - overall_success:.1f}%)")

    print("\n[권장사항]")
    print("-" * 100)

    if len(weak_sectors) > 0:
        print("""
1단계: 약한 섹터 파악 완료 ✓
   → 위에서 확인한 약한 섹터들

2단계: 뉴스 피처 추가 (우선순위)
   a) 비트코인 가격 → 크립토/마이닝 개선
   b) Reddit 센티먼트 → 밈주식 개선
   c) FDA RSS → 바이오테크 개선

3단계: 재학습 및 비교
   - 기존 모델 성능: {:.1f}%
   - 목표 성능: {:.1f}%+ (뉴스 추가 후)

4단계: 백테스트 재실행
   - 섹터별 개선도 측정
   - 전체 성능 향상 확인
        """.format(overall_success, overall_success + 5))
    else:
        print("""
현재 모델이 모든 섹터에서 우수한 성능!
뉴스 피처 추가는 선택사항입니다.

옵션:
1. 현재 모델로 실전 투자 시작
2. 뉴스 피처 추가로 더 높은 성능 추구 (75% → 80%+)
        """)

    print("\n" + "=" * 100)

    return sector_stats, weak_sectors

if __name__ == '__main__':
    try:
        sector_stats, weak_sectors = analyze_sector_performance()

        # 결과 저장
        sector_stats.to_csv('results/sector_performance.csv')
        print("\n결과 저장: results/sector_performance.csv")

    except FileNotFoundError:
        print("\n오류: 백테스트 파일이 없습니다.")
        print("먼저 백테스트를 실행해주세요:")
        print("  python backtest_god_model.py")
    except Exception as e:
        print(f"\n오류 발생: {str(e)}")
