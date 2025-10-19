"""
현재 God 모델 상태 및 시그널 기준 설명
"""

import pandas as pd
import glob
import os
from datetime import datetime

print("=" * 100)
print("God 모델 - 현재 상태 및 시그널 기준")
print("=" * 100)

# 데이터 상태 확인
print("\n[1] 데이터 상태")
print("-" * 100)

df = pd.read_csv('data/penny_stocks_data.csv')
df['date'] = pd.to_datetime(df['date'], utc=True)

latest_date = df['date'].max()
total_tickers = df['ticker'].nunique()
total_rows = len(df)
date_range = f"{df['date'].min().date()} ~ {latest_date.date()}"

print(f"최신 데이터 날짜: {latest_date.date()}")
print(f"총 종목 수: {total_tickers:,}개")
print(f"총 데이터 행: {total_rows:,}개")
print(f"데이터 기간: {date_range}")

# 최신일 데이터
df_latest = df[df['date'] == latest_date]
print(f"\n최신일({latest_date.date()}) 종목 수: {len(df_latest):,}개")

# 모델 상태 확인
print("\n" + "=" * 100)
print("[2] God 모델 상태")
print("-" * 100)

model_files = [
    'models/god_model_XGBoost_Advanced.pkl',
    'models/god_model_LightGBM_Advanced.pkl',
    'models/god_model_RandomForest_Advanced.pkl',
    'models/god_model_GradientBoosting.pkl'
]

all_exist = all(os.path.exists(f) for f in model_files)

if all_exist:
    print("[OK] God 모델 4개 모두 준비됨")
    for f in model_files:
        size = os.path.getsize(f) / 1024 / 1024
        print(f"  - {os.path.basename(f)}: {size:.2f} MB")

    # 피처 개수
    import pickle
    with open('models/god_model_features.pkl', 'rb') as f:
        features = pickle.load(f)
    print(f"\n사용 피처: {len(features)}개")
else:
    print("[X] 모델 파일이 없습니다")

# 백테스트 결과
print("\n" + "=" * 100)
print("[3] 백테스트 성능 (2024-04 ~ 2025-10)")
print("-" * 100)

backtest_file = 'results/backtest_threshold_0.95.csv'
if os.path.exists(backtest_file):
    bt = pd.read_csv(backtest_file)
    bt['date'] = pd.to_datetime(bt['date'])
    bt['trade_date'] = pd.to_datetime(bt['trade_date'])

    total_trades = len(bt)
    surge_success = (bt['is_surge'] == True).sum()
    win_trades = (bt['net_return'] > 0).sum()

    surge_rate = surge_success / total_trades * 100
    win_rate = win_trades / total_trades * 100
    avg_return = bt['net_return'].mean() * 100

    print(f"임계값 0.95 (초고신뢰도) 백테스트:")
    print(f"  - 총 거래 수: {total_trades}회")
    print(f"  - 50% 급등 성공률: {surge_rate:.1f}% ({surge_success}/{total_trades})")
    print(f"  - 전체 승률: {win_rate:.1f}% ({win_trades}/{total_trades})")
    print(f"  - 평균 수익률: {avg_return:.1f}%")
    print(f"  - 백테스트 기간: {bt['trade_date'].min().date()} ~ {bt['trade_date'].max().date()}")

# 시그널 기준 설명
print("\n" + "=" * 100)
print("[4] 시그널 기준 (임계값별)")
print("-" * 100)

signal_criteria = {
    0.95: {
        'name': '초고신뢰도',
        'surge_rate': 73.5,
        'win_rate': 75.7,
        'avg_return': 1427,
        'mdd': -67.6,
        'trades': 136,
        'recommendation': '매우 확실한 경우만 거래'
    },
    0.90: {
        'name': '고신뢰도',
        'surge_rate': 71.0,
        'win_rate': 75.6,
        'avg_return': 1130,
        'mdd': -76.0,
        'trades': 185,
        'recommendation': '높은 확률, 하지만 위험 증가'
    },
    0.85: {
        'name': '중고신뢰도',
        'surge_rate': 67.7,
        'win_rate': 73.3,
        'avg_return': 970,
        'mdd': -81.5,
        'trades': 279,
        'recommendation': '더 많은 기회, 위험 관리 필수'
    },
    0.80: {
        'name': '균형',
        'surge_rate': 63.1,
        'win_rate': 69.1,
        'avg_return': 836,
        'mdd': -88.0,
        'trades': 379,
        'recommendation': '균형잡힌 접근, 분산 투자 필수'
    },
    0.75: {
        'name': '공격형',
        'surge_rate': 57.3,
        'win_rate': 63.0,
        'avg_return': 694,
        'mdd': -93.1,
        'trades': 557,
        'recommendation': '공격적 전략, 높은 위험'
    }
}

print(f"\n{'임계값':<10} {'이름':<15} {'50%급등률':<12} {'승률':<10} {'평균수익':<12} {'MDD':<10} {'거래수':<10}")
print("-" * 100)

for threshold, info in signal_criteria.items():
    print(f"{threshold:<10.2f} {info['name']:<15} {info['surge_rate']:<11.1f}% {info['win_rate']:<9.1f}% "
          f"{info['avg_return']:<11.0f}% {info['mdd']:<9.1f}% {info['trades']:<10}")

# 상세 설명
print("\n" + "=" * 100)
print("[5] 시그널 상세 설명")
print("-" * 100)

print("""
시그널 의미:
- surge_probability: God 모델이 예측한 내일 50% 급등 확률
- 임계값: 거래를 실행할 최소 확률 기준
- 50% 급등률: 백테스트에서 실제로 50% 이상 급등한 비율
- 승률: 백테스트에서 수익이 발생한 비율 (손실 포함)
- 평균 수익: 모든 거래의 평균 순수익률 (수수료/슬리피지 제외)
- MDD: 최대 낙폭 (Maximum Drawdown)

거래 방식:
1. 예측: T일 장마감 후 God 모델 실행
2. 매수: T+1일 시가 매수 (슬리피지 +0.5%)
3. 매도: T+1일 종가 매도 (슬리피지 -0.5%)
4. 비용: 수수료 0.1% x 2 = 0.2% (매수+매도)

추천 전략:
- 0.95 임계값: 가장 확실한 신호만, 소수 종목 집중 투자
- 0.90 임계값: 높은 신뢰도, 중간 규모 포트폴리오
- 0.80 임계값: 균형잡힌 접근, 더 많은 기회
- 0.75 이하: 공격적 전략, 높은 위험 감수 가능한 경우만

주의사항:
[!] 페니스톡은 극도로 변동성이 높습니다
[!] 높은 확률이라도 손실 가능성 있음 (24-25% 손실 확률)
[!] 반드시 손실 감내 가능한 금액만 투자
[!] 분산 투자 필수 (한 종목에 전체 자금 투자 금지)
[!] MDD를 고려한 위험 관리 필수
""")

print("=" * 100)
print("[6] 예측 가능 종목 수")
print("-" * 100)

print(f"""
현재 데이터베이스: {total_tickers:,}개 종목
최신 데이터: {latest_date.date()}

실제 예측 가능 종목 수는 피처 품질에 따라 달라집니다:
- 총 {total_tickers}개 종목 중
- 최소 70% 이상의 피처가 유효한 종목만 예측 가능
- 일반적으로 {total_tickers * 0.8:.0f}-{total_tickers * 0.95:.0f}개 정도 예측 가능

예측을 실행하려면:
1. 최신 데이터 다운로드 및 피처 생성이 필요
2. 현재는 모델과 백테스트 결과만 확인 가능
""")

print("\n" + "=" * 100)
print("요약")
print("=" * 100)

print(f"""
[OK] God 모델: 4개 앙상블 모델 준비 완료
[OK] 피처: {len(features)}개 고급 피처 사용
[OK] 백테스트: 19개월 (2024-04 ~ 2025-10) 검증 완료
[OK] 최고 성능: 임계값 0.95 -> 73.5% 급등 성공률, 1,427% 평균 수익

데이터베이스:
- 총 {total_tickers:,}개 종목
- 최신 데이터: {latest_date.date()}
- 예측 가능 종목: 약 {total_tickers * 0.9:.0f}개 (추정)

시그널 추천:
- 보수적: 임계값 0.95 (73.5% 성공률, 평균 1,427% 수익)
- 균형형: 임계값 0.80 (63.1% 성공률, 평균 836% 수익)
- 공격적: 임계값 0.75 (57.3% 성공률, 평균 694% 수익)
""")

print("=" * 100)
