"""
다운로드한 3년치 데이터 통계 확인 스크립트
"""

import pandas as pd
import numpy as np
from datetime import datetime

# 데이터 로드
print("=" * 80)
print("3년치 페니스톡 데이터 통계 확인")
print("=" * 80)

df = pd.read_csv('data/penny_stocks_data.csv')
df['date'] = pd.to_datetime(df['date'])

print(f"\n총 데이터 행 수: {len(df):,}")
print(f"고유 종목 수: {df['ticker'].nunique()}")
print(f"날짜 범위: {df['date'].min()} ~ {df['date'].max()}")
print(f"데이터 기간: {(df['date'].max() - df['date'].min()).days}일")

print("\n" + "=" * 80)
print("종목별 데이터 수 (상위 30개)")
print("=" * 80)
ticker_counts = df['ticker'].value_counts().head(30)
for i, (ticker, count) in enumerate(ticker_counts.items(), 1):
    print(f"{i:2d}. {ticker:6s}: {count:4d} rows")

print("\n" + "=" * 80)
print("2022-2025 급등 실적 종목 데이터 확인")
print("=" * 80)

# 2022-2025 급등주 체크
surge_stocks = {
    'AI/퀀텀 컴퓨팅': ['RGTI', 'IREN', 'SOUN', 'RR', 'IONQ', 'QUBT'],
    '바이오테크': ['NVAX', 'MRNA', 'BNTX', 'ARDX', 'SAVA'],
    'EV/자동차': ['CVNA', 'BLNK', 'PSNY', 'LCID', 'RIVN'],
    '대마초': ['CGC', 'TLRY', 'SNDL', 'ACB', 'CRON'],
    '에너지': ['INDO', 'TALO', 'REI', 'VTLE'],
    'AI/테크': ['AMST', 'BBAI', 'AI', 'PLTR'],
}

for category, tickers in surge_stocks.items():
    print(f"\n{category}:")
    for ticker in tickers:
        count = len(df[df['ticker'] == ticker])
        if count > 0:
            ticker_data = df[df['ticker'] == ticker].sort_values('date')
            first_date = ticker_data['date'].iloc[0].strftime('%Y-%m-%d')
            last_date = ticker_data['date'].iloc[-1].strftime('%Y-%m-%d')
            first_price = ticker_data['close'].iloc[0]
            last_price = ticker_data['close'].iloc[-1]
            total_return = ((last_price / first_price) - 1) * 100

            print(f"  {ticker:6s}: {count:4d} rows | {first_date} ~ {last_date} | "
                  f"${first_price:7.2f} → ${last_price:7.2f} ({total_return:+7.1f}%)")
        else:
            print(f"  {ticker:6s}: 데이터 없음 (상장폐지 또는 오류)")

print("\n" + "=" * 80)
print("급등 패턴 분석 (50% 이상 급등한 사례)")
print("=" * 80)

# 각 종목별로 50% 이상 급등한 케이스 찾기
surge_count = 0
for ticker in df['ticker'].unique()[:10]:  # 상위 10개 종목만 확인
    ticker_data = df[df['ticker'] == ticker].sort_values('date')
    ticker_data['future_10d_return'] = ticker_data['close'].shift(-10) / ticker_data['close'] - 1

    surges = ticker_data[ticker_data['future_10d_return'] >= 0.50]

    if len(surges) > 0:
        surge_count += len(surges)
        print(f"\n{ticker}: {len(surges)}회 급등 (50%+)")
        for idx, row in surges.head(3).iterrows():
            print(f"  {row['date'].strftime('%Y-%m-%d')}: "
                  f"${row['close']:.2f} → 10일 후 +{row['future_10d_return']*100:.1f}%")

print(f"\n총 50% 이상 급등 케이스: {surge_count}개 (상위 10개 종목)")

print("\n" + "=" * 80)
print("데이터 품질 확인")
print("=" * 80)
print(f"결측치 (close): {df['close'].isna().sum()}")
print(f"결측치 (volume): {df['volume'].isna().sum()}")
print(f"0 이하 가격: {(df['close'] <= 0).sum()}")
print(f"0 거래량: {(df['volume'] == 0).sum()}")

print("\n" + "=" * 80)
print("완료!")
print("=" * 80)
