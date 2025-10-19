"""
일일 50%+ 급등 패턴 상세 분석 스크립트
급등 전 신호, 급등 후 움직임, 기술적 지표 패턴 분석
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# 한글 폰트 설정
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

print("=" * 100)
print("일일 50%+ 급등 패턴 상세 분석")
print("=" * 100)

# 데이터 로드
print("\n데이터 로딩 중...")
df = pd.read_csv('data/penny_stocks_data.csv')
df['date'] = pd.to_datetime(df['date'], utc=True)
df = df.sort_values(['ticker', 'date'])

print(f"총 데이터: {len(df):,} rows, {df['ticker'].nunique()} tickers")

# 일일 변동률 계산
print("\n일일 변동률 및 지표 계산 중...")
df['daily_return'] = df.groupby('ticker')['close'].pct_change()
df['daily_return_pct'] = df['daily_return'] * 100
df['volume_change'] = df.groupby('ticker')['volume'].pct_change()
df['volume_change_pct'] = df['volume_change'] * 100

# 이전 N일 평균 계산 (급등 전 신호)
for n in [1, 2, 3, 5, 10]:
    df[f'prev_{n}d_return'] = df.groupby('ticker')['daily_return_pct'].shift(n)
    df[f'prev_{n}d_volume_change'] = df.groupby('ticker')['volume_change_pct'].shift(n)
    df[f'prev_{n}d_avg_volume'] = df.groupby('ticker')['volume'].rolling(n).mean().shift(1).reset_index(0, drop=True)

# 급등 후 N일 수익률
for n in [1, 2, 3, 5, 10]:
    df[f'next_{n}d_return'] = df.groupby('ticker')['close'].shift(-n) / df['close'] - 1
    df[f'next_{n}d_return_pct'] = df[f'next_{n}d_return'] * 100

# 50% 이상 급등 케이스 추출
surges_50 = df[df['daily_return_pct'] >= 50.0].copy()
surges_100 = df[df['daily_return_pct'] >= 100.0].copy()

print(f"\n총 50%+ 급등 케이스: {len(surges_50):,}개")
print(f"총 100%+ 급등 케이스: {len(surges_100):,}개")

# ============================================================================
# 1. 급등 전 패턴 분석 (Pre-Surge Signals)
# ============================================================================
print("\n" + "=" * 100)
print("1. 급등 전 신호 분석 (Pre-Surge Patterns)")
print("=" * 100)

# 급등 전 1일 수익률 분석
print("\n[급등 전 1일 가격 움직임]")
prev_1d_stats = surges_50['prev_1d_return'].describe()
print(prev_1d_stats)
print(f"\n전날 상승한 케이스: {(surges_50['prev_1d_return'] > 0).sum()} ({(surges_50['prev_1d_return'] > 0).sum() / len(surges_50) * 100:.1f}%)")
print(f"전날 10%+ 상승: {(surges_50['prev_1d_return'] > 10).sum()} ({(surges_50['prev_1d_return'] > 10).sum() / len(surges_50) * 100:.1f}%)")
print(f"전날 하락한 케이스: {(surges_50['prev_1d_return'] < 0).sum()} ({(surges_50['prev_1d_return'] < 0).sum() / len(surges_50) * 100:.1f}%)")

# 급등 전 거래량 분석
print("\n[급등 전 거래량 패턴]")
print(f"\n급등 전날 거래량 증가: {(surges_50['prev_1d_volume_change'] > 0).sum()} ({(surges_50['prev_1d_volume_change'] > 0).sum() / len(surges_50) * 100:.1f}%)")
print(f"급등 전날 거래량 50%+ 증가: {(surges_50['prev_1d_volume_change'] > 50).sum()} ({(surges_50['prev_1d_volume_change'] > 50).sum() / len(surges_50) * 100:.1f}%)")
print(f"급등 전날 거래량 100%+ 증가: {(surges_50['prev_1d_volume_change'] > 100).sum()} ({(surges_50['prev_1d_volume_change'] > 100).sum() / len(surges_50) * 100:.1f}%)")

# 급등일 거래량 vs 평균 거래량
surges_50['volume_vs_avg_5d'] = surges_50['volume'] / surges_50['prev_5d_avg_volume']
print(f"\n급등일 거래량 / 5일 평균:")
print(f"  평균 배수: {surges_50['volume_vs_avg_5d'].mean():.1f}x")
print(f"  중앙값: {surges_50['volume_vs_avg_5d'].median():.1f}x")
print(f"  2배 이상: {(surges_50['volume_vs_avg_5d'] > 2).sum()} ({(surges_50['volume_vs_avg_5d'] > 2).sum() / len(surges_50) * 100:.1f}%)")
print(f"  5배 이상: {(surges_50['volume_vs_avg_5d'] > 5).sum()} ({(surges_50['volume_vs_avg_5d'] > 5).sum() / len(surges_50) * 100:.1f}%)")
print(f"  10배 이상: {(surges_50['volume_vs_avg_5d'] > 10).sum()} ({(surges_50['volume_vs_avg_5d'] > 10).sum() / len(surges_50) * 100:.1f}%)")

# 급등 전 3일 연속 패턴
print("\n[급등 전 3일 연속 패턴]")
three_day_up = ((surges_50['prev_1d_return'] > 0) &
                (surges_50['prev_2d_return'] > 0) &
                (surges_50['prev_3d_return'] > 0))
print(f"3일 연속 상승 후 급등: {three_day_up.sum()} ({three_day_up.sum() / len(surges_50) * 100:.1f}%)")

three_day_down = ((surges_50['prev_1d_return'] < 0) &
                  (surges_50['prev_2d_return'] < 0) &
                  (surges_50['prev_3d_return'] < 0))
print(f"3일 연속 하락 후 급등: {three_day_down.sum()} ({three_day_down.sum() / len(surges_50) * 100:.1f}%)")

# ============================================================================
# 2. 급등일 가격대 분석
# ============================================================================
print("\n" + "=" * 100)
print("2. 급등일 가격대 분석")
print("=" * 100)

price_ranges = [
    ('$0.01 이하', 0, 0.01),
    ('$0.01 - $0.10', 0.01, 0.10),
    ('$0.10 - $0.50', 0.10, 0.50),
    ('$0.50 - $1.00', 0.50, 1.00),
    ('$1.00 - $2.00', 1.00, 2.00),
    ('$2.00 - $5.00', 2.00, 5.00),
    ('$5.00 이상', 5.00, float('inf'))
]

print("\n[가격대별 50%+ 급등 분포]")
for label, low, high in price_ranges:
    count = len(surges_50[(surges_50['close'] >= low) & (surges_50['close'] < high)])
    pct = (count / len(surges_50) * 100) if len(surges_50) > 0 else 0
    avg_surge = surges_50[(surges_50['close'] >= low) & (surges_50['close'] < high)]['daily_return_pct'].mean()
    print(f"{label:15s}: {count:5d}회 ({pct:5.1f}%) | 평균 급등률: {avg_surge:6.1f}%")

# ============================================================================
# 3. 급등 후 가격 움직임 분석 (Post-Surge Behavior)
# ============================================================================
print("\n" + "=" * 100)
print("3. 급등 후 가격 움직임 분석 (Post-Surge Performance)")
print("=" * 100)

print("\n[급등 후 평균 수익률]")
for n in [1, 2, 3, 5, 10]:
    avg_return = surges_50[f'next_{n}d_return_pct'].mean()
    median_return = surges_50[f'next_{n}d_return_pct'].median()
    positive_pct = (surges_50[f'next_{n}d_return_pct'] > 0).sum() / len(surges_50) * 100

    print(f"{n}일 후: 평균 {avg_return:+6.1f}% | 중앙값 {median_return:+6.1f}% | 상승 {positive_pct:.1f}%")

print("\n[급등 후 추가 상승 확률]")
for threshold in [10, 20, 50]:
    for n in [1, 3, 5, 10]:
        count = (surges_50[f'next_{n}d_return_pct'] >= threshold).sum()
        pct = count / len(surges_50) * 100
        print(f"{n}일 내 +{threshold}% 이상 추가 상승: {count:4d}회 ({pct:5.1f}%)")

print("\n[급등 후 하락 리스크]")
for threshold in [-20, -30, -50]:
    for n in [1, 3, 5, 10]:
        count = (surges_50[f'next_{n}d_return_pct'] <= threshold).sum()
        pct = count / len(surges_50) * 100
        print(f"{n}일 내 {threshold}% 이상 하락: {count:4d}회 ({pct:5.1f}%)")

# ============================================================================
# 4. 급등 강도별 분석
# ============================================================================
print("\n" + "=" * 100)
print("4. 급등 강도별 후속 패턴 비교")
print("=" * 100)

surge_categories = [
    ('50-100%', 50, 100),
    ('100-200%', 100, 200),
    ('200-500%', 200, 500),
    ('500%+', 500, float('inf'))
]

print("\n[급등 강도별 다음날 수익률]")
for label, low, high in surge_categories:
    subset = surges_50[(surges_50['daily_return_pct'] >= low) & (surges_50['daily_return_pct'] < high)]
    if len(subset) > 0:
        next_1d_avg = subset['next_1d_return_pct'].mean()
        next_1d_positive = (subset['next_1d_return_pct'] > 0).sum() / len(subset) * 100
        print(f"{label:12s}: {len(subset):4d}회 | 다음날 평균 {next_1d_avg:+6.1f}% | 상승 확률 {next_1d_positive:.1f}%")

# ============================================================================
# 5. 시간대별 패턴 (요일, 월별)
# ============================================================================
print("\n" + "=" * 100)
print("5. 시간대별 급등 패턴")
print("=" * 100)

surges_50['weekday'] = surges_50['date'].dt.day_name()
surges_50['month'] = surges_50['date'].dt.month
surges_50['year'] = surges_50['date'].dt.year

print("\n[요일별 급등 분포]")
weekday_counts = surges_50['weekday'].value_counts()
weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
for day in weekday_order:
    count = weekday_counts.get(day, 0)
    pct = count / len(surges_50) * 100
    print(f"{day:10s}: {count:4d}회 ({pct:5.1f}%)")

print("\n[월별 급등 분포]")
monthly_counts = surges_50['month'].value_counts().sort_index()
month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
for month, name in enumerate(month_names, 1):
    count = monthly_counts.get(month, 0)
    pct = count / len(surges_50) * 100
    print(f"{name:3s}: {count:4d}회 ({pct:5.1f}%)")

# ============================================================================
# 6. TOP 급등 케이스 분석
# ============================================================================
print("\n" + "=" * 100)
print("6. 극단적 급등 케이스 분석 (TOP 20)")
print("=" * 100)

top_surges = surges_50.nlargest(20, 'daily_return_pct')
print(f"\n{'Rank':<5} {'Ticker':<8} {'Date':<12} {'가격':<10} {'급등률':<12} {'거래량':<15} {'다음날':<10}")
print("-" * 80)

for i, (idx, row) in enumerate(top_surges.iterrows(), 1):
    next_day = row['next_1d_return_pct']
    next_day_str = f"{next_day:+.1f}%" if pd.notna(next_day) else "N/A"

    print(f"{i:<5} {row['ticker']:<8} {row['date'].strftime('%Y-%m-%d'):<12} "
          f"${row['close']:<9.2f} {row['daily_return_pct']:>+10.1f}% "
          f"{row['volume']:>14,.0f} {next_day_str:<10}")

# ============================================================================
# 7. 핵심 패턴 요약
# ============================================================================
print("\n" + "=" * 100)
print("7. 급등 패턴 핵심 요약 (Key Insights)")
print("=" * 100)

# 가장 유망한 패턴 찾기
print("\n[고수익 확률이 높은 패턴]")

# 패턴 1: 급등 + 거래량 폭증 + 다음날 추가 상승
pattern1 = surges_50[
    (surges_50['volume_vs_avg_5d'] > 5) &
    (surges_50['next_1d_return_pct'] > 10)
]
print(f"\n패턴 1: 거래량 5배+ 폭증 후 급등")
print(f"  발생 횟수: {len(pattern1)}회")
print(f"  다음날 평균 수익률: {pattern1['next_1d_return_pct'].mean():+.1f}%")
print(f"  5일 평균 수익률: {pattern1['next_5d_return_pct'].mean():+.1f}%")

# 패턴 2: 저가주 급등
pattern2 = surges_50[
    (surges_50['close'] < 0.50) &
    (surges_50['daily_return_pct'] >= 100)
]
print(f"\n패턴 2: $0.50 이하 저가주 100%+ 급등")
print(f"  발생 횟수: {len(pattern2)}회")
print(f"  평균 급등률: {pattern2['daily_return_pct'].mean():.1f}%")
print(f"  다음날 평균 수익률: {pattern2['next_1d_return_pct'].mean():+.1f}%")

# 패턴 3: 연속 상승 후 급등
pattern3 = surges_50[three_day_up]
print(f"\n패턴 3: 3일 연속 상승 후 급등")
print(f"  발생 횟수: {len(pattern3)}회")
print(f"  다음날 평균 수익률: {pattern3['next_1d_return_pct'].mean():+.1f}%")
print(f"  5일 평균 수익률: {pattern3['next_5d_return_pct'].mean():+.1f}%")

print("\n[위험 신호 (급등 후 급락 패턴)]")

# 다음날 30% 이상 급락한 케이스
crash_pattern = surges_50[surges_50['next_1d_return_pct'] < -30]
print(f"\n급등 후 다음날 30%+ 급락: {len(crash_pattern)}회 ({len(crash_pattern) / len(surges_50) * 100:.1f}%)")
if len(crash_pattern) > 0:
    print(f"  평균 급등률: {crash_pattern['daily_return_pct'].mean():.1f}%")
    print(f"  평균 급락률: {crash_pattern['next_1d_return_pct'].mean():.1f}%")
    print(f"  평균 가격대: ${crash_pattern['close'].mean():.2f}")

print("\n" + "=" * 100)
print("분석 완료! 시각화 생성 중...")
print("=" * 100)

# ============================================================================
# 8. 시각화 생성
# ============================================================================

# 플롯 디렉토리 확인
import os
os.makedirs('plots', exist_ok=True)

# 그래프 1: 급등 전 거래량 vs 급등률
plt.figure(figsize=(12, 6))
valid_data = surges_50[
    (surges_50['volume_vs_avg_5d'].notna()) &
    (surges_50['volume_vs_avg_5d'] < 50)  # 이상치 제거
].copy()

plt.scatter(valid_data['volume_vs_avg_5d'], valid_data['daily_return_pct'],
            alpha=0.3, s=20)
plt.xlabel('거래량 / 5일 평균 (배수)', fontsize=12)
plt.ylabel('일일 급등률 (%)', fontsize=12)
plt.title('급등일 거래량 vs 급등률', fontsize=14, fontweight='bold')
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('plots/surge_volume_vs_return.png', dpi=150, bbox_inches='tight')
print("\n✓ 저장: plots/surge_volume_vs_return.png")
plt.close()

# 그래프 2: 급등 후 수익률 분포
plt.figure(figsize=(14, 8))
for i, n in enumerate([1, 3, 5, 10], 1):
    plt.subplot(2, 2, i)
    data = surges_50[f'next_{n}d_return_pct'].dropna()
    data = data[(data > -100) & (data < 200)]  # 이상치 제거
    plt.hist(data, bins=50, alpha=0.7, edgecolor='black')
    plt.axvline(x=0, color='red', linestyle='--', linewidth=2, label='손익분기점')
    plt.xlabel(f'{n}일 후 수익률 (%)', fontsize=10)
    plt.ylabel('빈도', fontsize=10)
    plt.title(f'급등 후 {n}일 수익률 분포', fontsize=12, fontweight='bold')
    plt.legend()
    plt.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('plots/post_surge_returns_distribution.png', dpi=150, bbox_inches='tight')
print("✓ 저장: plots/post_surge_returns_distribution.png")
plt.close()

# 그래프 3: 가격대별 급등 분포
plt.figure(figsize=(12, 6))
price_data = []
labels_kr = []
for label, low, high in price_ranges:
    count = len(surges_50[(surges_50['close'] >= low) & (surges_50['close'] < high)])
    price_data.append(count)
    labels_kr.append(label)

plt.bar(range(len(price_data)), price_data, edgecolor='black', alpha=0.7)
plt.xticks(range(len(labels_kr)), labels_kr, rotation=45, ha='right')
plt.xlabel('가격대', fontsize=12)
plt.ylabel('급등 횟수', fontsize=12)
plt.title('가격대별 50%+ 급등 분포', fontsize=14, fontweight='bold')
plt.grid(True, axis='y', alpha=0.3)
plt.tight_layout()
plt.savefig('plots/surge_by_price_range.png', dpi=150, bbox_inches='tight')
print("✓ 저장: plots/surge_by_price_range.png")
plt.close()

# 그래프 4: 요일별/월별 급등 패턴
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

# 요일별
weekday_data = [weekday_counts.get(day, 0) for day in weekday_order]
weekday_labels_kr = ['월', '화', '수', '목', '금']
ax1.bar(weekday_labels_kr, weekday_data, edgecolor='black', alpha=0.7, color='skyblue')
ax1.set_xlabel('요일', fontsize=12)
ax1.set_ylabel('급등 횟수', fontsize=12)
ax1.set_title('요일별 급등 분포', fontsize=12, fontweight='bold')
ax1.grid(True, axis='y', alpha=0.3)

# 월별
monthly_data = [monthly_counts.get(m, 0) for m in range(1, 13)]
ax2.bar(month_names, monthly_data, edgecolor='black', alpha=0.7, color='lightcoral')
ax2.set_xlabel('월', fontsize=12)
ax2.set_ylabel('급등 횟수', fontsize=12)
ax2.set_title('월별 급등 분포', fontsize=12, fontweight='bold')
ax2.grid(True, axis='y', alpha=0.3)
ax2.tick_params(axis='x', rotation=45)

plt.tight_layout()
plt.savefig('plots/surge_by_time.png', dpi=150, bbox_inches='tight')
print("✓ 저장: plots/surge_by_time.png")
plt.close()

print("\n" + "=" * 100)
print("분석 및 시각화 완료!")
print("=" * 100)
print(f"\n총 {len(surges_50):,}개의 50%+ 급등 케이스 분석 완료")
print(f"시각화 파일 4개 생성: plots/ 디렉토리 확인")
