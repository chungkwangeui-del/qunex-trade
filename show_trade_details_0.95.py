"""
임계값 0.95 - 모든 거래 상세 내용
"""

import pandas as pd
import numpy as np
from datetime import datetime

print("=" * 120)
print("임계값 0.95 - 전체 거래 상세 내역 (136건)")
print("=" * 120)

# 백테스트 데이터 로드
bt = pd.read_csv('results/backtest_threshold_0.95.csv')
bt['date'] = pd.to_datetime(bt['date'])
bt['trade_date'] = pd.to_datetime(bt['trade_date'])

# 정렬 (거래일 기준)
bt = bt.sort_values('trade_date')

print(f"\n백테스트 기간: {bt['trade_date'].min().date()} ~ {bt['trade_date'].max().date()}")
print(f"총 거래 건수: {len(bt)}건")
print(f"총 성공 건수: {(bt['is_surge'] == True).sum()}건 ({(bt['is_surge'] == True).sum() / len(bt) * 100:.1f}%)")
print(f"총 수익 건수: {(bt['net_return'] > 0).sum()}건 ({(bt['net_return'] > 0).sum() / len(bt) * 100:.1f}%)")

print("\n" + "=" * 120)
print("전체 거래 내역")
print("=" * 120)

print(f"\n{'#':<4} {'예측일':<12} {'거래일':<12} {'티커':<8} {'확률':<8} "
      f"{'매수가':<12} {'매도가':<12} {'수익률':<10} {'급등':<6} {'요일':<8}")
print("-" * 120)

# 누적 수익 계산
cumulative_return = 1.0
cumulative_returns = []

for idx, (i, row) in enumerate(bt.iterrows(), 1):
    date_str = row['date'].strftime('%Y-%m-%d')
    trade_date_str = row['trade_date'].strftime('%Y-%m-%d')
    ticker = row['ticker']
    prob = row['predicted_prob']
    buy = row['buy_price']
    sell = row['sell_price']
    ret = row['net_return'] * 100
    surge = 'O' if row['is_surge'] else 'X'
    weekday = row['trade_date'].strftime('%a')

    # 누적 수익 계산
    cumulative_return *= (1 + row['net_return'])
    cumulative_returns.append(cumulative_return)

    # 수익률 표시 색상 (텍스트)
    ret_str = f"{ret:>9.1f}%"

    print(f"{idx:<4} {date_str:<12} {trade_date_str:<12} {ticker:<8} {prob:<7.1%} "
          f"${buy:<11.6f} ${sell:<11.6f} {ret_str:<10} {surge:<6} {weekday:<8}")

# 통계 요약
print("\n" + "=" * 120)
print("구간별 통계")
print("=" * 120)

# 월별 통계
bt['year_month'] = bt['trade_date'].dt.to_period('M')
monthly = bt.groupby('year_month').agg({
    'ticker': 'count',
    'is_surge': 'sum',
    'net_return': ['mean', 'sum', 'min', 'max']
}).reset_index()

monthly.columns = ['월', '거래수', '급등성공', '평균수익률', '누적수익률', '최소수익률', '최대수익률']
monthly['성공률'] = (monthly['급등성공'] / monthly['거래수'] * 100).round(1)

print(f"\n{'월':<12} {'거래수':<8} {'급등성공':<10} {'성공률':<10} "
      f"{'평균수익':<12} {'누적수익':<12} {'최소수익':<12} {'최대수익':<12}")
print("-" * 120)

for _, row in monthly.iterrows():
    print(f"{str(row['월']):<12} {row['거래수']:<8} {row['급등성공']:<10} {row['성공률']:<9.1f}% "
          f"{row['평균수익률']*100:<11.1f}% {row['누적수익률']*100:<11.1f}% "
          f"{row['최소수익률']*100:<11.1f}% {row['최대수익률']*100:<11.1f}%")

# 티커별 통계
print("\n" + "=" * 120)
print("티커별 성과")
print("=" * 120)

ticker_stats = bt.groupby('ticker').agg({
    'trade_date': 'count',
    'is_surge': 'sum',
    'net_return': ['mean', 'sum', 'min', 'max'],
    'predicted_prob': 'mean'
}).reset_index()

ticker_stats.columns = ['티커', '거래수', '급등성공', '평균수익률', '누적수익률', '최소수익률', '최대수익률', '평균확률']
ticker_stats['성공률'] = (ticker_stats['급등성공'] / ticker_stats['거래수'] * 100).round(1)
ticker_stats = ticker_stats.sort_values('누적수익률', ascending=False)

print(f"\n{'티커':<8} {'거래수':<8} {'급등성공':<10} {'성공률':<10} "
      f"{'평균수익':<12} {'누적수익':<12} {'평균확률':<10}")
print("-" * 120)

for _, row in ticker_stats.iterrows():
    print(f"{row['티커']:<8} {row['거래수']:<8} {row['급등성공']:<10} {row['성공률']:<9.1f}% "
          f"{row['평균수익률']*100:<11.1f}% {row['누적수익률']*100:<11.1f}% {row['평균확률']:<9.1%}")

# 요일별 통계
print("\n" + "=" * 120)
print("요일별 성과")
print("=" * 120)

bt['weekday'] = bt['trade_date'].dt.day_name()
weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']

weekday_stats = bt.groupby('weekday').agg({
    'ticker': 'count',
    'is_surge': 'sum',
    'net_return': ['mean', 'sum']
}).reindex(weekday_order)

weekday_stats.columns = ['거래수', '급등성공', '평균수익률', '누적수익률']
weekday_stats['성공률'] = (weekday_stats['급등성공'] / weekday_stats['거래수'] * 100).round(1)
weekday_stats = weekday_stats.reset_index()

print(f"\n{'요일':<12} {'거래수':<8} {'급등성공':<10} {'성공률':<10} {'평균수익':<12} {'누적수익':<12}")
print("-" * 120)

for _, row in weekday_stats.iterrows():
    print(f"{row['weekday']:<12} {row['거래수']:<8} {row['급등성공']:<10} {row['성공률']:<9.1f}% "
          f"{row['평균수익률']*100:<11.1f}% {row['누적수익률']*100:<11.1f}%")

# 확률 구간별 성과
print("\n" + "=" * 120)
print("확률 구간별 성과")
print("=" * 120)

prob_bins = [0.95, 0.96, 0.97, 0.98, 0.99, 1.0]
prob_labels = ['95-96%', '96-97%', '97-98%', '98-99%', '99-100%']

bt['prob_bin'] = pd.cut(bt['predicted_prob'], bins=prob_bins, labels=prob_labels, include_lowest=True)

prob_stats = bt.groupby('prob_bin', observed=True).agg({
    'ticker': 'count',
    'is_surge': 'sum',
    'net_return': ['mean', 'sum']
})

prob_stats.columns = ['거래수', '급등성공', '평균수익률', '누적수익률']
prob_stats['성공률'] = (prob_stats['급등성공'] / prob_stats['거래수'] * 100).round(1)
prob_stats = prob_stats.reset_index()

print(f"\n{'확률구간':<12} {'거래수':<8} {'급등성공':<10} {'성공률':<10} {'평균수익':<12} {'누적수익':<12}")
print("-" * 120)

for _, row in prob_stats.iterrows():
    print(f"{row['prob_bin']:<12} {row['거래수']:<8} {row['급등성공']:<10} {row['성공률']:<9.1f}% "
          f"{row['평균수익률']*100:<11.1f}% {row['누적수익률']*100:<11.1f}%")

# 수익률 분포 상세
print("\n" + "=" * 120)
print("수익률 분포 상세")
print("=" * 120)

return_bins = [-100, -50, -20, -10, 0, 10, 20, 50, 100, 500, 1000, 5000, 100000]
return_labels = ['< -50%', '-50~-20%', '-20~-10%', '-10~0%', '0~10%', '10~20%',
                 '20~50%', '50~100%', '100~500%', '500~1000%', '1000~5000%', '> 5000%']

bt['return_bin'] = pd.cut(bt['net_return'] * 100, bins=return_bins, labels=return_labels, include_lowest=True)

return_dist = bt.groupby('return_bin', observed=True).agg({
    'ticker': 'count',
    'net_return': ['mean', 'sum']
})

return_dist.columns = ['거래수', '평균수익률', '누적수익률']
return_dist = return_dist.reset_index()

print(f"\n{'수익률구간':<15} {'거래수':<8} {'비율':<8} {'평균수익':<12} {'누적수익':<12}")
print("-" * 120)

for _, row in return_dist.iterrows():
    pct = row['거래수'] / len(bt) * 100
    print(f"{row['return_bin']:<15} {row['거래수']:<8} {pct:<7.1f}% "
          f"{row['평균수익률']*100:<11.1f}% {row['누적수익률']*100:<11.1f}%")

# 누적 수익 추이
print("\n" + "=" * 120)
print("누적 수익 추이 (주요 시점)")
print("=" * 120)

bt['cumulative_return'] = cumulative_returns
milestones = [0, 9, 19, 29, 39, 49, 59, 69, 79, 89, 99, 109, 119, 129, 135]

print(f"\n{'거래번호':<10} {'날짜':<12} {'티커':<8} {'수익률':<10} {'누적수익':<12} {'배수':<8}")
print("-" * 120)

for milestone in milestones:
    if milestone < len(bt):
        row = bt.iloc[milestone]
        print(f"{milestone+1:<10} {row['trade_date'].strftime('%Y-%m-%d'):<12} {row['ticker']:<8} "
              f"{row['net_return']*100:<9.1f}% {(row['cumulative_return']-1)*100:<11.1f}% "
              f"{row['cumulative_return']:<7.2f}x")

# 최종 요약
print("\n" + "=" * 120)
print("최종 요약")
print("=" * 120)

final_cumulative = cumulative_returns[-1]
total_return = (final_cumulative - 1) * 100
cagr = (final_cumulative ** (12 / 19) - 1) * 100  # 연환산

print(f"""
총 거래 건수: {len(bt)}건
거래 기간: {bt['trade_date'].min().date()} ~ {bt['trade_date'].max().date()} (19개월)

성공률:
- 50% 급등 성공: {(bt['is_surge'] == True).sum()}건 / {len(bt)}건 = {(bt['is_surge'] == True).sum() / len(bt) * 100:.1f}%
- 수익 거래: {(bt['net_return'] > 0).sum()}건 / {len(bt)}건 = {(bt['net_return'] > 0).sum() / len(bt) * 100:.1f}%
- 손실 거래: {(bt['net_return'] <= 0).sum()}건 / {len(bt)}건 = {(bt['net_return'] <= 0).sum() / len(bt) * 100:.1f}%

수익률:
- 평균 거래당 수익률: {bt['net_return'].mean() * 100:.1f}%
- 중간값 수익률: {bt['net_return'].median() * 100:.1f}%
- 최대 수익률: {bt['net_return'].max() * 100:.1f}%
- 최대 손실률: {bt['net_return'].min() * 100:.1f}%

누적 성과:
- 총 누적 수익률: {total_return:.1f}%
- 최종 배수: {final_cumulative:.2f}x
- 연환산 수익률 (CAGR): {cagr:.1f}%

리스크:
- 최대 낙폭 (MDD): {bt.groupby(bt.index // 1).apply(lambda x: ((1 + x['net_return']).cumprod() / (1 + x['net_return']).cumprod().cummax() - 1).min()).min() * 100:.1f}%
- 샤프 비율 (추정): {bt['net_return'].mean() / bt['net_return'].std():.2f}

거래 빈도:
- 월평균: {len(bt) / 19:.1f}건
- 주평균: {len(bt) / (19 * 4):.1f}건
""")

print("=" * 120)
print("분석 완료")
print("=" * 120)

# CSV 저장 옵션
save_option = input("\n상세 내역을 CSV로 저장하시겠습니까? (y/n): ")
if save_option.lower() == 'y':
    output_file = 'results/trade_details_0.95_full.csv'
    bt_export = bt[['date', 'trade_date', 'ticker', 'predicted_prob', 'buy_price',
                     'sell_price', 'net_return', 'is_surge', 'cumulative_return']].copy()
    bt_export.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n파일 저장 완료: {output_file}")
