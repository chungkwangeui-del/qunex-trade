"""
현재 시그널 확인 - God 모델로 최신 예측
"""

import pandas as pd
import numpy as np
import pickle
import yaml
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

print("=" * 100)
print("God 모델 - 현재 시그널 확인")
print("=" * 100)

# 설정
with open('config.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

# God 모델 로드
print("\n모델 로딩 중...")
models = {}
model_names = ['XGBoost_Advanced', 'LightGBM_Advanced', 'RandomForest_Advanced', 'GradientBoosting']

for name in model_names:
    with open(f'models/god_model_{name}.pkl', 'rb') as f:
        models[name] = pickle.load(f)

# 앙상블 가중치 로드
with open('models/god_model_ensemble_weights.pkl', 'rb') as f:
    ensemble_weights = pickle.load(f)

# 피처 리스트 로드
with open('models/god_model_features.pkl', 'rb') as f:
    feature_columns = pickle.load(f)

print(f"모델 로드 완료: {len(models)}개")
print(f"피처 개수: {len(feature_columns)}개")

# 데이터 로드
print("\n데이터 로딩 중...")
df = pd.read_csv('data/penny_stocks_data.csv')
df['date'] = pd.to_datetime(df['date'], utc=True)
df = df.sort_values(['ticker', 'date'])

# 최신 날짜
latest_date = df['date'].max()
print(f"최신 데이터 날짜: {latest_date.date()}")

# 최신 데이터만 필터링 (이미 모든 피처가 계산되어 있음)
df_latest = df[df['date'] == latest_date].copy()

print(f"최신일 종목 수: {len(df_latest)}")

# 피처가 있는지 확인
if not all(col in df_latest.columns for col in feature_columns):
    print("\n피처가 없습니다. 먼저 download_3year_data.py를 실행하세요.")
    exit(1)

# 피처 준비
df_features = df_latest[feature_columns].copy()
df_features = df_features.replace([np.inf, -np.inf], np.nan)

# NaN 처리 (임계값 기반)
nan_per_row = df_features.isnull().sum(axis=1)
min_valid_features = len(feature_columns) * 0.7

valid_mask = nan_per_row <= (len(feature_columns) - min_valid_features)
df_valid = df_latest[valid_mask].copy()
df_features_valid = df_features[valid_mask].copy()

print(f"유효한 피처를 가진 종목: {len(df_valid)}개")

# 남은 NaN 평균값으로 채우기
for col in feature_columns:
    if df_features_valid[col].isnull().any():
        mean_val = df_features_valid[col].mean()
        if pd.isna(mean_val):
            df_features_valid[col].fillna(0, inplace=True)
        else:
            df_features_valid[col].fillna(mean_val, inplace=True)

# 예측
print("\n예측 중...")
ensemble_probs = []
for name, model in models.items():
    probs = model.predict_proba(df_features_valid)[:, 1]
    ensemble_probs.append(probs)

# 가중 평균
predictions = np.average(ensemble_probs, axis=0, weights=ensemble_weights)

# 결과 저장
df_valid['surge_probability'] = predictions

# 정렬
df_valid = df_valid.sort_values('surge_probability', ascending=False)

print("\n" + "=" * 100)
print("시그널 분석 결과")
print("=" * 100)

# 임계값별 시그널 개수
thresholds = [0.95, 0.90, 0.85, 0.80, 0.75, 0.70, 0.60, 0.50]

print("\n임계값별 시그널 개수:")
print(f"{'임계값':<10} {'시그널 개수':<15} {'백테스트 성공률':<20}")
print("-" * 50)

backtest_success_rates = {
    0.95: 73.5,
    0.90: 71.0,
    0.85: 67.7,
    0.80: 63.1,
    0.75: 57.3,
    0.70: 54.6,
    0.60: 47.9,
    0.50: 41.9
}

for threshold in thresholds:
    count = (df_valid['surge_probability'] >= threshold).sum()
    success_rate = backtest_success_rates[threshold]
    print(f"{threshold:<10.2f} {count:<15} {success_rate:.1f}%")

print("\n" + "=" * 100)
print("추천 시그널 (임계값 0.95 - 초고신뢰도)")
print("=" * 100)

# 0.95 이상 시그널
high_confidence = df_valid[df_valid['surge_probability'] >= 0.95].copy()

if len(high_confidence) == 0:
    print("\n현재 0.95 이상 시그널 없음")
else:
    print(f"\n총 {len(high_confidence)}개 시그널")
    print(f"백테스트 성공률: 73.5% (136번 중 100번 50% 급등)")
    print(f"평균 수익률: 1,427%")
    print(f"\n{'순위':<6} {'티커':<10} {'확률':<12} {'현재가':<12} {'거래량':<15}")
    print("-" * 60)

    for i, (idx, row) in enumerate(high_confidence.iterrows(), 1):
        print(f"{i:<6} {row['ticker']:<10} {row['surge_probability']:<12.2%} ${row['close']:<11.6f} {row['volume']:>12,.0f}")

print("\n" + "=" * 100)
print("중간 신뢰도 시그널 (임계값 0.80 - 균형)")
print("=" * 100)

# 0.80 이상 시그널
medium_confidence = df_valid[(df_valid['surge_probability'] >= 0.80) & (df_valid['surge_probability'] < 0.95)].copy()

if len(medium_confidence) == 0:
    print("\n현재 0.80-0.95 시그널 없음")
else:
    print(f"\n총 {len(medium_confidence)}개 시그널")
    print(f"백테스트 성공률: 63.1% (379번 중 239번 50% 급등)")
    print(f"평균 수익률: 836%")
    print(f"\n{'순위':<6} {'티커':<10} {'확률':<12} {'현재가':<12} {'거래량':<15}")
    print("-" * 60)

    for i, (idx, row) in enumerate(medium_confidence.iterrows(), 1):
        if i > 10:  # 최대 10개만 표시
            break
        print(f"{i:<6} {row['ticker']:<10} {row['surge_probability']:<12.2%} ${row['close']:<11.6f} {row['volume']:>12,.0f}")

print("\n" + "=" * 100)
print("시그널 기준 설명")
print("=" * 100)

print(f"""
현재 예측 가능한 종목: {len(df_valid)}개
최신 데이터 날짜: {latest_date.date()}

시그널 기준:
1. 임계값 0.95 (초고신뢰도)
   - 백테스트 성공률: 73.5%
   - 평균 수익률: 1,427%
   - 승률: 75.7%
   - 위험: 높음 (MDD -67.6%)
   - 추천: 매우 확실한 경우만 거래

2. 임계값 0.90 (고신뢰도)
   - 백테스트 성공률: 71.0%
   - 평균 수익률: 1,130%
   - 승률: 75.6%
   - 위험: 높음 (MDD -76.0%)

3. 임계값 0.80 (균형)
   - 백테스트 성공률: 63.1%
   - 평균 수익률: 836%
   - 승률: 69.1%
   - 위험: 매우 높음 (MDD -88.0%)
   - 추천: 더 많은 기회, 하지만 위험 증가

예측 내용:
- 내일 (다음 거래일) 50% 이상 급등 확률
- 시가 매수 → 종가 매도 전략
- 슬리피지 0.5% + 수수료 0.1% 양방향 반영됨

주의사항:
⚠️ 페니스톡은 극도로 변동성이 높습니다
⚠️ 높은 확률에도 손실 가능성 있음 (24.3% 손실 비율)
⚠️ 반드시 손실 감내 가능한 금액만 투자
⚠️ 분산 투자 필수
""")

print("=" * 100)

# 결과 저장
output_file = f'results/current_signals_{latest_date.strftime("%Y%m%d")}.csv'
df_valid[['ticker', 'surge_probability', 'close', 'volume', 'high', 'low', 'open']].to_csv(
    output_file,
    index=False,
    encoding='utf-8-sig'
)
print(f"\n결과 저장: {output_file}")
