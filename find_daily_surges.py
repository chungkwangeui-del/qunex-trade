"""
하루에 50% 이상 급등한 페니스톡 찾기 스크립트
실제 다운로드된 데이터에서 일일 급등 종목 분석
"""

import pandas as pd
import numpy as np
from collections import defaultdict

print("=" * 80)
print("하루 50% 이상 급등한 페니스톡 분석")
print("=" * 80)

# 데이터 로드
df = pd.read_csv('data/penny_stocks_data.csv')
df['date'] = pd.to_datetime(df['date'])

# 각 종목별로 일일 변동률 계산
print("\n데이터 로딩 완료. 일일 변동률 계산 중...")
df = df.sort_values(['ticker', 'date'])
df['daily_return'] = df.groupby('ticker')['close'].pct_change()
df['daily_return_pct'] = df['daily_return'] * 100

# 50% 이상 급등한 케이스 찾기
surges_50 = df[df['daily_return_pct'] >= 50.0].copy()
surges_100 = df[df['daily_return_pct'] >= 100.0].copy()
surges_200 = df[df['daily_return_pct'] >= 200.0].copy()

print(f"\n총 50%+ 급등 케이스: {len(surges_50):,}개")
print(f"총 100%+ 급등 케이스: {len(surges_100):,}개")
print(f"총 200%+ 급등 케이스: {len(surges_200):,}개")

# 종목별 급등 횟수 집계
surge_counts = surges_50.groupby('ticker').size().sort_values(ascending=False)

print("\n" + "=" * 80)
print("하루 50%+ 급등 횟수 TOP 50 종목")
print("=" * 80)

top_surge_stocks = []
for i, (ticker, count) in enumerate(surge_counts.head(50).items(), 1):
    ticker_surges = surges_50[surges_50['ticker'] == ticker].sort_values('daily_return_pct', ascending=False)

    max_surge = ticker_surges['daily_return_pct'].max()
    avg_surge = ticker_surges['daily_return_pct'].mean()
    surge_100_count = len(ticker_surges[ticker_surges['daily_return_pct'] >= 100])

    print(f"{i:2d}. {ticker:6s}: {count:3d}회 급등 | "
          f"최대 +{max_surge:6.1f}% | 평균 +{avg_surge:5.1f}% | "
          f"100%+ {surge_100_count}회")

    top_surge_stocks.append(ticker)

print("\n" + "=" * 80)
print("하루 100% 이상 급등 종목 (TOP 30)")
print("=" * 80)

surge_100_counts = surges_100.groupby('ticker').size().sort_values(ascending=False)
for i, (ticker, count) in enumerate(surge_100_counts.head(30).items(), 1):
    ticker_surges = surges_100[surges_100['ticker'] == ticker].sort_values('daily_return_pct', ascending=False)
    max_surge = ticker_surges['daily_return_pct'].max()

    # 가장 큰 급등 케이스 3개
    top_3_surges = ticker_surges.head(3)

    print(f"\n{i:2d}. {ticker}: {count}회 100%+ 급등, 최대 +{max_surge:.1f}%")
    for idx, row in top_3_surges.iterrows():
        print(f"    {row['date'].strftime('%Y-%m-%d')}: "
              f"${row['close']:.2f} (+{row['daily_return_pct']:.1f}%, "
              f"거래량: {row['volume']:,.0f})")

print("\n" + "=" * 80)
print("하루 200% 이상 급등 케이스 (전체)")
print("=" * 80)

if len(surges_200) > 0:
    surges_200_sorted = surges_200.sort_values('daily_return_pct', ascending=False)
    for idx, row in surges_200_sorted.head(50).iterrows():
        print(f"{row['ticker']:6s} | {row['date'].strftime('%Y-%m-%d')} | "
              f"${row['close']:7.2f} | +{row['daily_return_pct']:6.1f}% | "
              f"거래량: {row['volume']:>12,.0f}")
else:
    print("200% 이상 급등 케이스 없음")

# 추가할 종목 추천
print("\n" + "=" * 80)
print("데이터에서 추출한 고변동성 페니스톡 (일일 급등 상위 50개)")
print("=" * 80)
print("이미 data_collector.py에 추가할 추천 종목:")
print(", ".join(f"'{t}'" for t in top_surge_stocks))

# 월별/연도별 급등 패턴
print("\n" + "=" * 80)
print("연도별 50%+ 급등 케이스 분포")
print("=" * 80)
surges_50['year'] = surges_50['date'].dt.year
yearly_surges = surges_50.groupby('year').size()
for year, count in yearly_surges.items():
    unique_tickers = surges_50[surges_50['year'] == year]['ticker'].nunique()
    print(f"{year}: {count:4d}회 급등 ({unique_tickers}개 종목)")

# 가격대별 분석
print("\n" + "=" * 80)
print("급등 시 가격대 분석")
print("=" * 80)
price_ranges = [
    ('$0.01 이하', 0, 0.01),
    ('$0.01 - $0.10', 0.01, 0.10),
    ('$0.10 - $0.50', 0.10, 0.50),
    ('$0.50 - $1.00', 0.50, 1.00),
    ('$1.00 - $2.00', 1.00, 2.00),
    ('$2.00 - $5.00', 2.00, 5.00),
    ('$5.00 이상', 5.00, float('inf'))
]

for label, low, high in price_ranges:
    count = len(surges_50[(surges_50['close'] >= low) & (surges_50['close'] < high)])
    pct = (count / len(surges_50) * 100) if len(surges_50) > 0 else 0
    print(f"{label:15s}: {count:5d}회 ({pct:5.1f}%)")

print("\n" + "=" * 80)
print("분석 완료!")
print("=" * 80)
