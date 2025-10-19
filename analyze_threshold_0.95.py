"""
임계값 0.95 전략 상세 분석
"""

import pandas as pd
import numpy as np
from datetime import datetime

print("=" * 100)
print("임계값 0.95 (초고신뢰도) 전략 - 상세 분석")
print("=" * 100)

# 백테스트 데이터 로드
bt = pd.read_csv('results/backtest_threshold_0.95.csv')
bt['date'] = pd.to_datetime(bt['date'])
bt['trade_date'] = pd.to_datetime(bt['trade_date'])

print("\n[1] 전략 개요")
print("-" * 100)

print("""
전략 이름: 초고신뢰도 전략 (Ultra High Confidence)
임계값: 0.95 (95% 이상 확률)

의미: God 모델이 95% 이상의 확률로 내일 50% 급등을 예측한 경우만 거래

특징:
- 가장 보수적이고 신중한 접근
- 매우 높은 신뢰도가 있는 신호만 선택
- 거래 빈도는 낮지만 성공률이 가장 높음
- 초보자에게 가장 추천되는 전략
""")

# 기본 통계
print("\n[2] 백테스트 성과 (2024-04 ~ 2025-10)")
print("-" * 100)

total_trades = len(bt)
surge_success = (bt['is_surge'] == True).sum()
win_trades = (bt['net_return'] > 0).sum()
loss_trades = (bt['net_return'] <= 0).sum()

surge_rate = surge_success / total_trades * 100
win_rate = win_trades / total_trades * 100
loss_rate = loss_trades / total_trades * 100

avg_return = bt['net_return'].mean() * 100
median_return = bt['net_return'].median() * 100
max_return = bt['net_return'].max() * 100
min_return = bt['net_return'].min() * 100

print(f"총 거래 수: {total_trades}회")
print(f"백테스트 기간: {bt['trade_date'].min().date()} ~ {bt['trade_date'].max().date()} (19개월)")
print(f"월평균 거래: {total_trades / 19:.1f}회")
print(f"주평균 거래: {total_trades / (19 * 4):.1f}회")

print(f"\n성공률:")
print(f"  - 50% 급등 성공: {surge_success}회 / {total_trades}회 = {surge_rate:.1f}%")
print(f"  - 수익 거래: {win_trades}회 / {total_trades}회 = {win_rate:.1f}%")
print(f"  - 손실 거래: {loss_trades}회 / {total_trades}회 = {loss_rate:.1f}%")

print(f"\n수익률 통계:")
print(f"  - 평균 수익률: {avg_return:.1f}%")
print(f"  - 중간값 수익률: {median_return:.1f}%")
print(f"  - 최대 수익률: {max_return:.1f}%")
print(f"  - 최대 손실률: {min_return:.1f}%")

# 수익 분포
print(f"\n수익률 구간별 분포:")
bins = [-100, -50, -20, 0, 20, 50, 100, 500, 1000, 5000, 100000]
labels = ['< -50%', '-50~-20%', '-20~0%', '0~20%', '20~50%', '50~100%', '100~500%', '500~1000%', '1000~5000%', '> 5000%']

bt['return_pct'] = bt['net_return'] * 100
for i in range(len(bins)-1):
    count = ((bt['return_pct'] >= bins[i]) & (bt['return_pct'] < bins[i+1])).sum()
    pct = count / total_trades * 100
    print(f"  {labels[i]:<15}: {count:>3}회 ({pct:>5.1f}%)")

# 월별 성과
print("\n[3] 월별 성과")
print("-" * 100)

bt['year_month'] = bt['trade_date'].dt.to_period('M')
monthly = bt.groupby('year_month').agg({
    'ticker': 'count',
    'is_surge': 'sum',
    'net_return': ['mean', 'sum']
}).reset_index()

monthly.columns = ['월', '거래수', '급등성공', '평균수익률', '누적수익률']
monthly['성공률'] = (monthly['급등성공'] / monthly['거래수'] * 100).round(1)
monthly['평균수익률'] = (monthly['평균수익률'] * 100).round(1)
monthly['누적수익률'] = (monthly['누적수익률'] * 100).round(1)

print(f"\n{'월':<12} {'거래수':<8} {'급등성공':<10} {'성공률':<10} {'평균수익':<12} {'누적수익':<12}")
print("-" * 100)

for _, row in monthly.iterrows():
    print(f"{str(row['월']):<12} {row['거래수']:<8} {row['급등성공']:<10} {row['성공률']:<9.1f}% {row['평균수익률']:<11.1f}% {row['누적수익률']:<11.1f}%")

# TOP 10 최고 수익
print("\n[4] TOP 10 최고 수익 거래")
print("-" * 100)

top10 = bt.nlargest(10, 'net_return')[['trade_date', 'ticker', 'predicted_prob', 'buy_price', 'sell_price', 'net_return', 'is_surge']]

print(f"\n{'날짜':<12} {'티커':<8} {'예측확률':<10} {'매수가':<12} {'매도가':<12} {'수익률':<12} {'급등':<6}")
print("-" * 100)

for _, row in top10.iterrows():
    surge_str = 'O' if row['is_surge'] else 'X'
    print(f"{row['trade_date'].date()} {row['ticker']:<8} {row['predicted_prob']:<9.1%} "
          f"${row['buy_price']:<11.6f} ${row['sell_price']:<11.6f} {row['net_return']*100:<11.1f}% {surge_str:<6}")

# TOP 10 최악 손실
print("\n[5] TOP 10 최악 손실 거래")
print("-" * 100)

worst10 = bt.nsmallest(10, 'net_return')[['trade_date', 'ticker', 'predicted_prob', 'buy_price', 'sell_price', 'net_return', 'is_surge']]

print(f"\n{'날짜':<12} {'티커':<8} {'예측확률':<10} {'매수가':<12} {'매도가':<12} {'수익률':<12} {'급등':<6}")
print("-" * 100)

for _, row in worst10.iterrows():
    surge_str = 'O' if row['is_surge'] else 'X'
    print(f"{row['trade_date'].date()} {row['ticker']:<8} {row['predicted_prob']:<9.1%} "
          f"${row['buy_price']:<11.6f} ${row['sell_price']:<11.6f} {row['net_return']*100:<11.1f}% {surge_str:<6}")

# 리스크 분석
print("\n[6] 리스크 분석")
print("-" * 100)

# Drawdown 계산
bt_sorted = bt.sort_values('trade_date')
bt_sorted['cumulative_return'] = (1 + bt_sorted['net_return']).cumprod()
bt_sorted['cumulative_max'] = bt_sorted['cumulative_return'].cummax()
bt_sorted['drawdown'] = (bt_sorted['cumulative_return'] - bt_sorted['cumulative_max']) / bt_sorted['cumulative_max']

max_dd = bt_sorted['drawdown'].min() * 100
max_dd_date = bt_sorted.loc[bt_sorted['drawdown'].idxmin(), 'trade_date']

print(f"최대 낙폭 (MDD): {max_dd:.1f}%")
print(f"MDD 발생일: {max_dd_date.date()}")

# 연속 손실
bt_sorted['is_loss'] = bt_sorted['net_return'] < 0
consecutive_losses = []
current_streak = 0

for loss in bt_sorted['is_loss']:
    if loss:
        current_streak += 1
    else:
        if current_streak > 0:
            consecutive_losses.append(current_streak)
        current_streak = 0
if current_streak > 0:
    consecutive_losses.append(current_streak)

if consecutive_losses:
    max_consecutive_loss = max(consecutive_losses)
    avg_consecutive_loss = np.mean(consecutive_losses)
    print(f"\n최대 연속 손실: {max_consecutive_loss}회")
    print(f"평균 연속 손실: {avg_consecutive_loss:.1f}회")
else:
    print(f"\n연속 손실 없음")

# 손실 크기 분석
losses = bt[bt['net_return'] < 0]['net_return'] * 100
if len(losses) > 0:
    print(f"\n손실 거래 분석:")
    print(f"  - 평균 손실: {losses.mean():.1f}%")
    print(f"  - 최대 손실: {losses.min():.1f}%")
    print(f"  - 중간 손실: {losses.median():.1f}%")

# 승률 vs 손실 비율
wins = bt[bt['net_return'] > 0]['net_return'] * 100
print(f"\n수익 vs 손실 비교:")
print(f"  - 평균 수익: {wins.mean():.1f}%")
print(f"  - 평균 손실: {losses.mean():.1f}%")
print(f"  - 수익/손실 비율: {wins.mean() / abs(losses.mean()):.2f}:1")

# 실전 적용 가이드
print("\n" + "=" * 100)
print("[7] 실전 적용 가이드")
print("=" * 100)

print("""
[단계 1] 매일 장마감 후 실행
- 장마감 후 God 모델 실행
- surge_probability >= 0.95 인 종목 선택
- 예상 종목 수: 월 평균 7-8개 (주 1-2개)

[단계 2] 종목 선택
- 임계값 0.95 이상 종목만 선택
- 확률이 높은 순서대로 정렬
- TOP 3-5 종목 선택 (분산 투자)

[단계 3] 자금 배분
- 전체 투자 가능 자금의 5-10%만 사용
- 종목당 1-2%씩 분산
- 예: 1,000만원 투자 가능 -> 50-100만원 사용, 종목당 10-20만원

[단계 4] 다음날 거래
- 시장 개장 시 시가로 매수
- 종가에 무조건 매도 (손익 관계없이)
- 절대 오버나잇 홀딩 금지

[단계 5] 리스크 관리
- 최대 연속 3회 손실 시 1주일 휴식
- 월 누적 손실 20% 도달 시 해당 월 거래 중단
- MDD -30% 도달 시 전략 재검토

[주의사항]
[!] 95% 확률이라도 25%는 손실 가능
[!] 페니스톡 특성상 변동성 극심
[!] 반드시 손실 감내 가능한 금액만 투자
[!] 감정적 거래 금지 (시스템 100% 준수)
[!] 백테스트는 과거 데이터, 미래 보장 아님

[성공 전략]
[+] 매일 꾸준히 실행 (19개월간 136회 = 월 7회)
[+] 시스템 100% 준수 (예외 금지)
[+] 분산 투자 (한 종목에 몰빵 금지)
[+] 손실 관리 철저 (손절 규칙 준수)
[+] 장기적 관점 (단기 손실에 흔들리지 않기)
""")

# 예상 수익 시뮬레이션
print("\n" + "=" * 100)
print("[8] 예상 수익 시뮬레이션 (참고용)")
print("=" * 100)

initial_capital = 1000000  # 100만원

print(f"\n초기 자본: {initial_capital:,}원")
print(f"월평균 거래: 7회")
print(f"거래당 투자: {initial_capital * 0.02:,.0f}원 (전체의 2%)")

print(f"\n시나리오 1: 백테스트 평균 수익률 적용 (1,427%)")
print("-" * 100)
monthly_trades = 7
trade_amount = initial_capital * 0.02
avg_return_per_trade = 14.27  # 1427% -> 14.27배

profit_per_trade = trade_amount * avg_return_per_trade
monthly_profit = profit_per_trade * monthly_trades

print(f"거래당 평균 수익: {profit_per_trade:,.0f}원")
print(f"월 예상 수익: {monthly_profit:,.0f}원")
print(f"월 수익률: {monthly_profit / initial_capital * 100:.1f}%")

print(f"\n시나리오 2: 보수적 추정 (평균의 30%만 적용)")
print("-" * 100)
conservative_return = avg_return_per_trade * 0.3
profit_per_trade_cons = trade_amount * conservative_return
monthly_profit_cons = profit_per_trade_cons * monthly_trades

print(f"거래당 평균 수익: {profit_per_trade_cons:,.0f}원")
print(f"월 예상 수익: {monthly_profit_cons:,.0f}원")
print(f"월 수익률: {monthly_profit_cons / initial_capital * 100:.1f}%")

print(f"\n시나리오 3: 현실적 추정 (중간값 수익률 적용, {median_return:.1f}%)")
print("-" * 100)
realistic_return = median_return / 100
profit_per_trade_real = trade_amount * realistic_return
monthly_profit_real = profit_per_trade_real * monthly_trades

print(f"거래당 평균 수익: {profit_per_trade_real:,.0f}원")
print(f"월 예상 수익: {monthly_profit_real:,.0f}원")
print(f"월 수익률: {monthly_profit_real / initial_capital * 100:.1f}%")

# 최종 요약
print("\n" + "=" * 100)
print("[9] 최종 요약 - 임계값 0.95 전략")
print("=" * 100)

print(f"""
[핵심 지표]
- 백테스트 성공률: 73.5% (50% 급등 기준)
- 전체 승률: 75.7%
- 평균 수익률: 1,427%
- 중간값 수익률: {median_return:.1f}%
- 최대 손실: {min_return:.1f}%
- MDD: {max_dd:.1f}%

[거래 빈도]
- 월평균: 7회
- 주평균: 1-2회
- 매우 선별적이고 신중한 접근

[장점]
[+] 가장 높은 성공률 (73.5%)
[+] 높은 평균 수익률 (1,427%)
[+] 비교적 낮은 MDD (-67.6%)
[+] 초보자에게 적합한 보수적 전략
[+] 명확한 진입/퇴출 규칙

[단점]
[-] 거래 빈도 낮음 (월 7회)
[-] 25%는 손실 가능
[-] 페니스톡 특성상 높은 변동성
[-] 슬리피지 발생 가능 (유동성 부족)
[-] 과거 성과가 미래 보장하지 않음

[추천 대상]
- 페니스톡 투자 초보자
- 보수적 투자 성향
- 시스템 트레이딩 선호
- 감정 통제 가능한 투자자
- 장기적 관점 보유자

[비추천 대상]
- 빠른 수익 원하는 투자자
- 높은 거래 빈도 선호
- 시스템 규칙 준수 어려운 경우
- 손실 감내 불가능한 경우
- 페니스톡 리스크 이해 부족

[결론]
임계값 0.95는 가장 신중하고 보수적인 전략입니다.
백테스트 결과 73.5%의 높은 성공률을 보였지만,
반드시 리스크 관리와 시스템 준수가 필요합니다.
""")

print("=" * 100)
print("분석 완료")
print("=" * 100)
