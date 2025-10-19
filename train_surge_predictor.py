"""
급등 전 패턴 예측 모델 학습 스크립트
다음날 50%+ 급등을 사전에 예측하는 ML 모델
"""

import pandas as pd
import numpy as np
import pickle
import yaml
from datetime import datetime
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score, roc_curve
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

print("=" * 100)
print("급등 전 패턴 예측 모델 학습")
print("=" * 100)

# 설정 로드
with open('config.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

# 데이터 로드
print("\n데이터 로딩 중...")
df = pd.read_csv('data/penny_stocks_data.csv')
df['date'] = pd.to_datetime(df['date'], utc=True)
df = df.sort_values(['ticker', 'date'])

print(f"총 데이터: {len(df):,} rows, {df['ticker'].nunique()} tickers")

# ============================================================================
# 1. 피처 엔지니어링 (Feature Engineering)
# ============================================================================
print("\n" + "=" * 100)
print("1. 피처 엔지니어링")
print("=" * 100)

print("\n기본 피처 계산 중...")

# 일일 수익률
df['daily_return'] = df.groupby('ticker')['close'].pct_change()
df['daily_return_pct'] = df['daily_return'] * 100

# 거래량 변화
df['volume_change'] = df.groupby('ticker')['volume'].pct_change()
df['volume_change_pct'] = df['volume_change'] * 100

# 가격 변동성
df['hl_range'] = (df['high'] - df['low']) / df['close']
df['oc_range'] = abs(df['open'] - df['close']) / df['close']

# 이동평균선
for window in [5, 10, 20]:
    df[f'sma_{window}'] = df.groupby('ticker')['close'].rolling(window).mean().reset_index(0, drop=True)
    df[f'price_to_sma_{window}'] = df['close'] / df[f'sma_{window}']

# 거래량 이동평균
for window in [5, 10, 20]:
    df[f'volume_ma_{window}'] = df.groupby('ticker')['volume'].rolling(window).mean().reset_index(0, drop=True)
    df[f'volume_ratio_{window}'] = df['volume'] / df[f'volume_ma_{window}']

# 과거 N일 수익률
for n in [1, 2, 3, 5, 7, 10]:
    df[f'return_{n}d'] = df.groupby('ticker')['close'].pct_change(n) * 100

# 과거 N일 최고/최저가 대비
for n in [5, 10, 20]:
    df[f'high_{n}d'] = df.groupby('ticker')['high'].rolling(n).max().reset_index(0, drop=True)
    df[f'low_{n}d'] = df.groupby('ticker')['low'].rolling(n).min().reset_index(0, drop=True)
    df[f'price_vs_high_{n}d'] = df['close'] / df[f'high_{n}d']
    df[f'price_vs_low_{n}d'] = df['close'] / df[f'low_{n}d']

# RSI (Relative Strength Index)
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

df['rsi_14'] = df.groupby('ticker')['close'].apply(lambda x: calculate_rsi(x, 14)).reset_index(0, drop=True)

# 볼린저 밴드
for window in [10, 20]:
    rolling_mean = df.groupby('ticker')['close'].rolling(window).mean().reset_index(0, drop=True)
    rolling_std = df.groupby('ticker')['close'].rolling(window).std().reset_index(0, drop=True)
    df[f'bb_upper_{window}'] = rolling_mean + (rolling_std * 2)
    df[f'bb_lower_{window}'] = rolling_mean - (rolling_std * 2)
    df[f'bb_position_{window}'] = (df['close'] - df[f'bb_lower_{window}']) / (df[f'bb_upper_{window}'] - df[f'bb_lower_{window}'])

# 연속 상승/하락일
df['price_direction'] = np.where(df['daily_return'] > 0, 1, np.where(df['daily_return'] < 0, -1, 0))
df['consecutive_up'] = df.groupby('ticker')['price_direction'].apply(
    lambda x: x.groupby((x != x.shift()).cumsum()).cumsum().where(x == 1, 0)
).reset_index(0, drop=True)
df['consecutive_down'] = df.groupby('ticker')['price_direction'].apply(
    lambda x: x.groupby((x != x.shift()).cumsum()).cumsum().where(x == -1, 0).abs()
).reset_index(0, drop=True)

print(f"피처 생성 완료: {len(df.columns)}개 컬럼")

# ============================================================================
# 2. 라벨링 (Labeling) - 다음날 50%+ 급등 여부
# ============================================================================
print("\n" + "=" * 100)
print("2. 라벨링 (다음날 50%+ 급등 여부)")
print("=" * 100)

# 다음날 수익률 계산
df['next_day_return'] = df.groupby('ticker')['daily_return'].shift(-1)
df['next_day_return_pct'] = df['next_day_return'] * 100

# 라벨: 다음날 50% 이상 급등 = 1, 아니면 = 0
df['surge_label'] = (df['next_day_return_pct'] >= 50.0).astype(int)

print(f"\n총 샘플 수: {len(df):,}")
print(f"급등 케이스 (1): {df['surge_label'].sum():,} ({df['surge_label'].sum() / len(df) * 100:.2f}%)")
print(f"비급등 케이스 (0): {(df['surge_label'] == 0).sum():,} ({(df['surge_label'] == 0).sum() / len(df) * 100:.2f}%)")

# ============================================================================
# 3. 피처 선택 및 데이터 준비
# ============================================================================
print("\n" + "=" * 100)
print("3. 피처 선택 및 데이터 준비")
print("=" * 100)

# 예측에 사용할 피처 선택
feature_columns = [
    # 가격 관련
    'close', 'hl_range', 'oc_range',

    # 거래량 관련 (가장 중요!)
    'volume', 'volume_change_pct',
    'volume_ratio_5', 'volume_ratio_10', 'volume_ratio_20',

    # 과거 수익률
    'return_1d', 'return_2d', 'return_3d', 'return_5d', 'return_7d', 'return_10d',

    # 이동평균 대비 위치
    'price_to_sma_5', 'price_to_sma_10', 'price_to_sma_20',

    # 고점/저점 대비 위치
    'price_vs_high_5d', 'price_vs_high_10d', 'price_vs_high_20d',
    'price_vs_low_5d', 'price_vs_low_10d', 'price_vs_low_20d',

    # 기술적 지표
    'rsi_14',
    'bb_position_10', 'bb_position_20',

    # 추세
    'consecutive_up', 'consecutive_down',
]

print(f"\n선택된 피처: {len(feature_columns)}개")
for i, feat in enumerate(feature_columns, 1):
    print(f"  {i:2d}. {feat}")

# 결측치 제거
df_clean = df[feature_columns + ['surge_label']].copy()
df_clean = df_clean.replace([np.inf, -np.inf], np.nan)
df_clean = df_clean.dropna()

print(f"\n결측치 제거 후: {len(df_clean):,} rows")
print(f"급등 케이스: {df_clean['surge_label'].sum():,} ({df_clean['surge_label'].sum() / len(df_clean) * 100:.2f}%)")

# X, y 분리
X = df_clean[feature_columns]
y = df_clean['surge_label']

# 학습/테스트 분리 (시간 순서 보존)
split_idx = int(len(X) * 0.8)
X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

print(f"\n학습 데이터: {len(X_train):,} samples")
print(f"  급등: {y_train.sum():,} ({y_train.sum() / len(y_train) * 100:.2f}%)")
print(f"테스트 데이터: {len(X_test):,} samples")
print(f"  급등: {y_test.sum():,} ({y_test.sum() / len(y_test) * 100:.2f}%)")

# ============================================================================
# 4. 모델 학습
# ============================================================================
print("\n" + "=" * 100)
print("4. 모델 학습")
print("=" * 100)

# 클래스 불균형 처리를 위한 가중치 계산
scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()
print(f"\n클래스 불균형 비율: {scale_pos_weight:.1f}:1 (비급등:급등)")

models = {}
results = []

# Random Forest
print("\n[1/3] Random Forest 학습 중...")
rf_model = RandomForestClassifier(
    n_estimators=200,
    max_depth=15,
    min_samples_split=20,
    min_samples_leaf=10,
    class_weight='balanced',
    random_state=42,
    n_jobs=-1,
    verbose=0
)
rf_model.fit(X_train, y_train)
models['RandomForest'] = rf_model

# 예측 및 평가
y_pred_rf = rf_model.predict(X_test)
y_pred_proba_rf = rf_model.predict_proba(X_test)[:, 1]

print("\n  성능 평가:")
print(classification_report(y_test, y_pred_rf, target_names=['비급등', '급등']))

# XGBoost
print("\n[2/3] XGBoost 학습 중...")
xgb_model = XGBClassifier(
    n_estimators=300,
    max_depth=8,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    scale_pos_weight=scale_pos_weight,
    random_state=42,
    n_jobs=-1,
    verbosity=0
)
xgb_model.fit(X_train, y_train)
models['XGBoost'] = xgb_model

y_pred_xgb = xgb_model.predict(X_test)
y_pred_proba_xgb = xgb_model.predict_proba(X_test)[:, 1]

print("\n  성능 평가:")
print(classification_report(y_test, y_pred_xgb, target_names=['비급등', '급등']))

# LightGBM
print("\n[3/3] LightGBM 학습 중...")
lgb_model = LGBMClassifier(
    n_estimators=300,
    max_depth=10,
    learning_rate=0.05,
    num_leaves=50,
    subsample=0.8,
    colsample_bytree=0.8,
    scale_pos_weight=scale_pos_weight,
    random_state=42,
    n_jobs=-1,
    verbose=-1
)
lgb_model.fit(X_train, y_train)
models['LightGBM'] = lgb_model

y_pred_lgb = lgb_model.predict(X_test)
y_pred_proba_lgb = lgb_model.predict_proba(X_test)[:, 1]

print("\n  성능 평가:")
print(classification_report(y_test, y_pred_lgb, target_names=['비급등', '급등']))

# ============================================================================
# 5. 모델 비교 및 평가
# ============================================================================
print("\n" + "=" * 100)
print("5. 모델 성능 비교")
print("=" * 100)

model_predictions = {
    'RandomForest': (y_pred_rf, y_pred_proba_rf),
    'XGBoost': (y_pred_xgb, y_pred_proba_xgb),
    'LightGBM': (y_pred_lgb, y_pred_proba_lgb),
}

print(f"\n{'Model':<15} {'ROC-AUC':<10} {'Precision':<12} {'Recall':<10} {'F1-Score':<10}")
print("-" * 60)

for model_name, (y_pred, y_pred_proba) in model_predictions.items():
    from sklearn.metrics import precision_score, recall_score, f1_score

    roc_auc = roc_auc_score(y_test, y_pred_proba)
    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)

    print(f"{model_name:<15} {roc_auc:<10.4f} {precision:<12.4f} {recall:<10.4f} {f1:<10.4f}")

    results.append({
        'model': model_name,
        'roc_auc': roc_auc,
        'precision': precision,
        'recall': recall,
        'f1': f1
    })

# ============================================================================
# 6. 피처 중요도 분석
# ============================================================================
print("\n" + "=" * 100)
print("6. 피처 중요도 분석 (XGBoost)")
print("=" * 100)

feature_importance = pd.DataFrame({
    'feature': feature_columns,
    'importance': xgb_model.feature_importances_
}).sort_values('importance', ascending=False)

print("\nTOP 15 중요 피처:")
for i, row in feature_importance.head(15).iterrows():
    print(f"  {row['feature']:<25s}: {row['importance']:.4f}")

# ============================================================================
# 7. 실전 예측 성능 분석
# ============================================================================
print("\n" + "=" * 100)
print("7. 실전 예측 성능 분석")
print("=" * 100)

# XGBoost 사용 (보통 가장 좋은 성능)
best_model = xgb_model
y_pred_proba_best = y_pred_proba_xgb

# 다양한 확률 임계값으로 테스트
print("\n신뢰도 임계값별 성능:")
print(f"\n{'임계값':<10} {'예측 수':<10} {'급등 건수':<12} {'정확도':<10} {'실제 수익':<12}")
print("-" * 70)

for threshold in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
    y_pred_threshold = (y_pred_proba_best >= threshold).astype(int)

    # 예측한 급등 케이스
    predicted_surge_indices = y_test.index[y_pred_threshold == 1]

    if len(predicted_surge_indices) > 0:
        actual_surges = y_test[predicted_surge_indices].sum()
        accuracy = actual_surges / len(predicted_surge_indices)

        # 실제 수익률 계산 (급등 예측한 종목에 투자했다면?)
        # 다음날 수익률 데이터 필요

        print(f"{threshold:<10.1f} {len(predicted_surge_indices):<10} {actual_surges:<12} {accuracy:<10.2%}")
    else:
        print(f"{threshold:<10.1f} {'0':<10} {'-':<12} {'-':<10}")

# ============================================================================
# 8. 모델 저장
# ============================================================================
print("\n" + "=" * 100)
print("8. 모델 저장")
print("=" * 100)

import os
os.makedirs('models', exist_ok=True)

# 모델 저장
for model_name, model in models.items():
    filename = f'models/surge_predictor_{model_name}.pkl'
    with open(filename, 'wb') as f:
        pickle.dump(model, f)
    print(f"  저장: {filename}")

# 피처 리스트 저장
with open('models/surge_predictor_features.pkl', 'wb') as f:
    pickle.dump(feature_columns, f)
print(f"  저장: models/surge_predictor_features.pkl")

# 학습 결과 저장
results_df = pd.DataFrame(results)
results_df.to_csv('results/surge_predictor_performance.csv', index=False)
print(f"  저장: results/surge_predictor_performance.csv")

# 피처 중요도 저장
feature_importance.to_csv('results/surge_predictor_feature_importance.csv', index=False)
print(f"  저장: results/surge_predictor_feature_importance.csv")

print("\n" + "=" * 100)
print("학습 완료!")
print("=" * 100)

print(f"\n학습 모델: {len(models)}개")
print(f"사용 피처: {len(feature_columns)}개")
print(f"학습 샘플: {len(X_train):,}개")
print(f"테스트 샘플: {len(X_test):,}개")
print(f"\n최고 성능 모델: XGBoost")
print(f"  ROC-AUC: {results[1]['roc_auc']:.4f}")
print(f"  Precision: {results[1]['precision']:.4f}")
print(f"  Recall: {results[1]['recall']:.4f}")
print(f"  F1-Score: {results[1]['f1']:.4f}")

print("\n다음 단계:")
print("  1. python predict_surge.py --scan  # 현재 시장 스캔")
print("  2. python predict_surge.py --ticker AAPL  # 특정 종목 예측")
