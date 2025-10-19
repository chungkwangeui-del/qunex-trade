"""
급등주 예측의 신(神) 모델 - Ultimate ML/DL System
최고 성능을 위한 모든 기법 총동원
"""

import pandas as pd
import numpy as np
import pickle
import yaml
from datetime import datetime
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import classification_report, roc_auc_score, precision_recall_curve
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
# from catboost import CatBoostClassifier  # 설치 실패 시 주석 처리
import warnings
warnings.filterwarnings('ignore')

print("=" * 100)
print("급등주 예측의 신(神) 모델 - Ultimate Training")
print("=" * 100)

# 설정
with open('config.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

# 데이터 로드
print("\n데이터 로딩 중...")
df = pd.read_csv('data/penny_stocks_data.csv')
df['date'] = pd.to_datetime(df['date'], utc=True)
df = df.sort_values(['ticker', 'date'])

print(f"총 데이터: {len(df):,} rows, {df['ticker'].nunique()} tickers")

# ============================================================================
# 1. 고급 피처 엔지니어링 (Advanced Feature Engineering)
# ============================================================================
print("\n" + "=" * 100)
print("1. 고급 피처 엔지니어링 (100+ 피처)")
print("=" * 100)

print("\n[1/8] 기본 피처 계산...")
# 기본 수익률 및 거래량
df['daily_return'] = df.groupby('ticker')['close'].pct_change()
df['daily_return_pct'] = df['daily_return'] * 100
df['volume_change'] = df.groupby('ticker')['volume'].pct_change()
df['volume_change_pct'] = df['volume_change'] * 100

# 가격 변동성
df['hl_range'] = (df['high'] - df['low']) / df['close']
df['oc_range'] = abs(df['open'] - df['close']) / df['close']

print("[2/8] 이동평균 및 비율 계산...")
# 다양한 이동평균
for window in [3, 5, 7, 10, 15, 20, 30, 50]:
    df[f'sma_{window}'] = df.groupby('ticker')['close'].rolling(window).mean().reset_index(0, drop=True)
    df[f'price_to_sma_{window}'] = df['close'] / df[f'sma_{window}']

    # EMA (지수이동평균)
    df[f'ema_{window}'] = df.groupby('ticker')['close'].ewm(span=window, adjust=False).mean().reset_index(0, drop=True)
    df[f'price_to_ema_{window}'] = df['close'] / df[f'ema_{window}']

# 거래량 이동평균
for window in [3, 5, 10, 20, 30]:
    df[f'volume_ma_{window}'] = df.groupby('ticker')['volume'].rolling(window).mean().reset_index(0, drop=True)
    df[f'volume_ratio_{window}'] = df['volume'] / df[f'volume_ma_{window}']

print("[3/8] 과거 수익률 및 변동성...")
# 과거 N일 수익률
for n in [1, 2, 3, 5, 7, 10, 15, 20, 30]:
    df[f'return_{n}d'] = df.groupby('ticker')['close'].pct_change(n) * 100

# 롤링 변동성 (표준편차)
for window in [5, 10, 20, 30]:
    df[f'volatility_{window}d'] = df.groupby('ticker')['daily_return'].rolling(window).std().reset_index(0, drop=True)

# 롤링 최대/최소 수익률
for window in [5, 10, 20]:
    df[f'max_return_{window}d'] = df.groupby('ticker')['daily_return_pct'].rolling(window).max().reset_index(0, drop=True)
    df[f'min_return_{window}d'] = df.groupby('ticker')['daily_return_pct'].rolling(window).min().reset_index(0, drop=True)

print("[4/8] 고점/저점 분석...")
# 고점/저점 대비
for n in [5, 10, 15, 20, 30, 60]:
    df[f'high_{n}d'] = df.groupby('ticker')['high'].rolling(n).max().reset_index(0, drop=True)
    df[f'low_{n}d'] = df.groupby('ticker')['low'].rolling(n).min().reset_index(0, drop=True)
    df[f'price_vs_high_{n}d'] = df['close'] / df[f'high_{n}d']
    df[f'price_vs_low_{n}d'] = df['close'] / df[f'low_{n}d']

    # 고점/저점으로부터의 거리
    df[f'dist_from_high_{n}d'] = (df[f'high_{n}d'] - df['close']) / df[f'high_{n}d']
    df[f'dist_from_low_{n}d'] = (df['close'] - df[f'low_{n}d']) / df['close']

print("[5/8] 기술적 지표 (RSI, MACD, BB)...")
# RSI (다양한 기간)
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

for period in [7, 14, 21, 30]:
    df[f'rsi_{period}'] = df.groupby('ticker')['close'].apply(lambda x: calculate_rsi(x, period)).reset_index(0, drop=True)

# MACD
exp1 = df.groupby('ticker')['close'].ewm(span=12, adjust=False).mean().reset_index(0, drop=True)
exp2 = df.groupby('ticker')['close'].ewm(span=26, adjust=False).mean().reset_index(0, drop=True)
df['macd'] = exp1 - exp2
df['macd_signal'] = df.groupby('ticker')['macd'].ewm(span=9, adjust=False).mean().reset_index(0, drop=True)
df['macd_diff'] = df['macd'] - df['macd_signal']

# 볼린저 밴드 (다양한 기간)
for window in [10, 20, 30]:
    rolling_mean = df.groupby('ticker')['close'].rolling(window).mean().reset_index(0, drop=True)
    rolling_std = df.groupby('ticker')['close'].rolling(window).std().reset_index(0, drop=True)
    df[f'bb_upper_{window}'] = rolling_mean + (rolling_std * 2)
    df[f'bb_lower_{window}'] = rolling_mean - (rolling_std * 2)
    df[f'bb_middle_{window}'] = rolling_mean
    df[f'bb_position_{window}'] = (df['close'] - df[f'bb_lower_{window}']) / (df[f'bb_upper_{window}'] - df[f'bb_lower_{window}'])
    df[f'bb_width_{window}'] = (df[f'bb_upper_{window}'] - df[f'bb_lower_{window}']) / rolling_mean

print("[6/8] 추세 및 모멘텀 지표...")
# 추세 지표
df['price_direction'] = np.where(df['daily_return'] > 0, 1, np.where(df['daily_return'] < 0, -1, 0))

# 연속 상승/하락일
df['consecutive_up'] = df.groupby('ticker')['price_direction'].apply(
    lambda x: x.groupby((x != x.shift()).cumsum()).cumsum().where(x == 1, 0)
).reset_index(0, drop=True)
df['consecutive_down'] = df.groupby('ticker')['price_direction'].apply(
    lambda x: x.groupby((x != x.shift()).cumsum()).cumsum().where(x == -1, 0).abs()
).reset_index(0, drop=True)

# 승률 (최근 N일 중 상승일 비율)
for window in [5, 10, 20]:
    df[f'win_rate_{window}d'] = df.groupby('ticker')['price_direction'].rolling(window).apply(
        lambda x: (x > 0).sum() / len(x)
    ).reset_index(0, drop=True)

print("[7/8] 거래량 패턴...")
# 거래량 급증 감지
for window in [5, 10, 20]:
    df[f'volume_spike_{window}d'] = (
        df['volume'] > df[f'volume_ma_{window}'] * 2
    ).astype(int)

# 거래량 추세
for window in [5, 10]:
    df[f'volume_trend_{window}d'] = df.groupby('ticker')['volume'].rolling(window).apply(
        lambda x: 1 if x.iloc[-1] > x.iloc[0] else 0
    ).reset_index(0, drop=True)

# 가격-거래량 상관관계 (수정)
for window in [5, 10, 20]:
    def calc_corr(group):
        return group['daily_return'].rolling(window).corr(group['volume_change'])

    df[f'price_volume_corr_{window}d'] = df.groupby('ticker').apply(calc_corr).reset_index(0, drop=True)

print("[8/8] 시간 피처...")
# 시간 관련 피처
df['day_of_week'] = df['date'].dt.dayofweek  # 0=Monday, 4=Friday
df['month'] = df['date'].dt.month
df['quarter'] = df['date'].dt.quarter
df['is_month_start'] = df['date'].dt.is_month_start.astype(int)
df['is_month_end'] = df['date'].dt.is_month_end.astype(int)
df['is_quarter_start'] = df['date'].dt.is_quarter_start.astype(int)
df['is_quarter_end'] = df['date'].dt.is_quarter_end.astype(int)

# 가격대 (로그 스케일)
df['log_price'] = np.log(df['close'] + 1)
df['log_volume'] = np.log(df['volume'] + 1)

print(f"\n총 피처 생성 완료: {len(df.columns)}개 컬럼")

# ============================================================================
# 2. 라벨링 - 다음날 50%+ 급등 여부
# ============================================================================
print("\n" + "=" * 100)
print("2. 타겟 라벨링")
print("=" * 100)

df['next_day_return'] = df.groupby('ticker')['daily_return'].shift(-1)
df['next_day_return_pct'] = df['next_day_return'] * 100
df['surge_label'] = (df['next_day_return_pct'] >= 50.0).astype(int)

print(f"총 샘플: {len(df):,}")
print(f"급등 케이스: {df['surge_label'].sum():,} ({df['surge_label'].sum() / len(df) * 100:.2f}%)")

# ============================================================================
# 3. 피처 선택 및 데이터 준비
# ============================================================================
print("\n" + "=" * 100)
print("3. 피처 선택 및 데이터 준비")
print("=" * 100)

# 제외할 컬럼
exclude_cols = [
    'date', 'ticker', 'next_day_return', 'next_day_return_pct', 'surge_label',
    'daily_return', 'volume_change', 'price_direction'
]

# 피처 선택
feature_columns = [col for col in df.columns if col not in exclude_cols
                   and not col.startswith('sma_') and not col.startswith('ema_')
                   and not col.startswith('volume_ma_') and not col.startswith('high_')
                   and not col.startswith('low_') and not col.startswith('bb_upper')
                   and not col.startswith('bb_lower') and not col.startswith('bb_middle')]

print(f"\n선택된 피처: {len(feature_columns)}개")

# 데이터 정제
df_clean = df[feature_columns + ['surge_label']].copy()

# 진단: NaN 및 Inf 분석
print(f"\n진단 - 정제 전 데이터: {len(df_clean):,} rows")

df_clean = df_clean.replace([np.inf, -np.inf], np.nan)

print("\n=== NaN 분석 (TOP 20) ===")
nan_counts = df_clean.isnull().sum()
nan_counts_filtered = nan_counts[nan_counts > 0].sort_values(ascending=False)
if len(nan_counts_filtered) > 0:
    print(f"NaN이 있는 컬럼 수: {len(nan_counts_filtered)}개")
    print(f"\nTOP 20 NaN 컬럼:")
    for col, count in nan_counts_filtered.head(20).items():
        pct = count / len(df_clean) * 100
        print(f"  {col:<40s}: {count:>8,} ({pct:>6.2f}%)")
else:
    print("NaN이 없습니다.")

print(f"\n각 행의 NaN 개수 분포:")
nan_per_row = df_clean.isnull().sum(axis=1)
print(f"  NaN 0개인 행: {(nan_per_row == 0).sum():,} ({(nan_per_row == 0).sum() / len(df_clean) * 100:.2f}%)")
print(f"  NaN 1-10개인 행: {((nan_per_row > 0) & (nan_per_row <= 10)).sum():,}")
print(f"  NaN 11-30개인 행: {((nan_per_row > 10) & (nan_per_row <= 30)).sum():,}")
print(f"  NaN 31-60개인 행: {((nan_per_row > 30) & (nan_per_row <= 60)).sum():,}")
print(f"  NaN 60개 이상인 행: {(nan_per_row > 60).sum():,}")

# 결측치 제거 대신 임계값 기반 제거 (60d 롤링을 고려하여 최소 70행 이상 필요)
min_valid_features = len(feature_columns) * 0.7  # 70% 이상의 피처가 있어야 함
df_clean = df_clean[nan_per_row <= (len(feature_columns) - min_valid_features)]

print(f"\n임계값 기반 필터링 후: {len(df_clean):,} rows")
print(f"급등 케이스: {df_clean['surge_label'].sum():,} ({df_clean['surge_label'].sum() / len(df_clean) * 100:.2f}%)")

# 남은 NaN은 평균값으로 채움 (피처별)
if df_clean.isnull().any().any():
    print("\n남은 NaN을 평균값으로 채우는 중...")
    for col in feature_columns:
        if df_clean[col].isnull().any():
            mean_val = df_clean[col].mean()
            if pd.isna(mean_val):
                df_clean[col].fillna(0, inplace=True)
            else:
                df_clean[col].fillna(mean_val, inplace=True)
    print("완료!")

print(f"\n최종 데이터: {len(df_clean):,} rows")
print(f"급등 케이스: {df_clean['surge_label'].sum():,} ({df_clean['surge_label'].sum() / len(df_clean) * 100:.2f}%)")

# X, y 분리
X = df_clean[feature_columns]
y = df_clean['surge_label']

# 시간순 분할
split_idx = int(len(X) * 0.8)
X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

print(f"\n학습 데이터: {len(X_train):,} ({y_train.sum()} 급등)")
print(f"테스트 데이터: {len(X_test):,} ({y_test.sum()} 급등)")

# 클래스 가중치
scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()
print(f"클래스 불균형: {scale_pos_weight:.1f}:1")

# ============================================================================
# 4. 고급 ML 모델 학습
# ============================================================================
print("\n" + "=" * 100)
print("4. 고급 ML 모델 학습")
print("=" * 100)

models = {}

# XGBoost (최적화)
print("\n[1/5] XGBoost (최적화)...")
xgb_model = XGBClassifier(
    n_estimators=500,
    max_depth=10,
    learning_rate=0.03,
    subsample=0.8,
    colsample_bytree=0.8,
    scale_pos_weight=scale_pos_weight,
    min_child_weight=3,
    gamma=0.1,
    reg_alpha=0.1,
    reg_lambda=1.0,
    random_state=42,
    n_jobs=-1,
    verbosity=0
)
xgb_model.fit(X_train, y_train)
models['XGBoost_Advanced'] = xgb_model

# LightGBM (최적화)
print("[2/5] LightGBM (최적화)...")
lgb_model = LGBMClassifier(
    n_estimators=500,
    max_depth=12,
    learning_rate=0.03,
    num_leaves=64,
    subsample=0.8,
    colsample_bytree=0.8,
    scale_pos_weight=scale_pos_weight,
    min_child_samples=20,
    reg_alpha=0.1,
    reg_lambda=1.0,
    random_state=42,
    n_jobs=-1,
    verbose=-1
)
lgb_model.fit(X_train, y_train)
models['LightGBM_Advanced'] = lgb_model

# CatBoost (새로운 모델!) - 설치 불가능 시 스킵
# print("[3/5] CatBoost...")
# cat_model = CatBoostClassifier(
#     iterations=500,
#     depth=10,
#     learning_rate=0.03,
#     l2_leaf_reg=3.0,
#     scale_pos_weight=scale_pos_weight,
#     random_state=42,
#     verbose=0
# )
# cat_model.fit(X_train, y_train)
# models['CatBoost'] = cat_model
print("[3/5] CatBoost 스킵 (설치 불가)")

# RandomForest (최적화)
print("[4/5] RandomForest (최적화)...")
rf_model = RandomForestClassifier(
    n_estimators=300,
    max_depth=20,
    min_samples_split=10,
    min_samples_leaf=5,
    max_features='sqrt',
    class_weight='balanced',
    random_state=42,
    n_jobs=-1,
    verbose=0
)
rf_model.fit(X_train, y_train)
models['RandomForest_Advanced'] = rf_model

# GradientBoosting
print("[5/5] GradientBoosting...")
gb_model = GradientBoostingClassifier(
    n_estimators=300,
    max_depth=8,
    learning_rate=0.05,
    subsample=0.8,
    min_samples_split=20,
    random_state=42,
    verbose=0
)
gb_model.fit(X_train, y_train)
models['GradientBoosting'] = gb_model

# ============================================================================
# 5. 앙상블 모델 (Voting)
# ============================================================================
print("\n" + "=" * 100)
print("5. 앙상블 모델 구축")
print("=" * 100)

# 각 모델의 예측 확률
ensemble_probs = []
for name, model in models.items():
    probs = model.predict_proba(X_test)[:, 1]
    ensemble_probs.append(probs)
    print(f"{name}: {roc_auc_score(y_test, probs):.4f}")

# 평균 앙상블
ensemble_avg = np.mean(ensemble_probs, axis=0)
print(f"\n앙상블 (평균): {roc_auc_score(y_test, ensemble_avg):.4f}")

# 가중 평균 (성능에 따라)
weights = np.array([0.30, 0.30, 0.25, 0.15])  # XGB, LGB, RF, GB (CatBoost 제외)
ensemble_weighted = np.average(ensemble_probs, axis=0, weights=weights)
print(f"앙상블 (가중): {roc_auc_score(y_test, ensemble_weighted):.4f}")

# ============================================================================
# 6. 모델 평가
# ============================================================================
print("\n" + "=" * 100)
print("6. 최종 모델 평가")
print("=" * 100)

print(f"\n{'Model':<25} {'ROC-AUC':<10} {'Precision@0.7':<15} {'Recall@0.7':<12}")
print("-" * 70)

best_auc = 0
best_model_name = None

for name, model in models.items():
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    y_pred_07 = (y_pred_proba >= 0.7).astype(int)

    auc = roc_auc_score(y_test, y_pred_proba)

    if y_pred_07.sum() > 0:
        precision = (y_test[y_pred_07 == 1] == 1).sum() / y_pred_07.sum()
        recall = (y_test[y_pred_07 == 1] == 1).sum() / y_test.sum()
    else:
        precision = recall = 0

    print(f"{name:<25} {auc:<10.4f} {precision:<15.4f} {recall:<12.4f}")

    if auc > best_auc:
        best_auc = auc
        best_model_name = name

print(f"\n최고 성능 모델: {best_model_name} (ROC-AUC: {best_auc:.4f})")

# 앙상블 평가
y_pred_ensemble = (ensemble_weighted >= 0.7).astype(int)
if y_pred_ensemble.sum() > 0:
    precision_ens = (y_test[y_pred_ensemble == 1] == 1).sum() / y_pred_ensemble.sum()
    recall_ens = (y_test[y_pred_ensemble == 1] == 1).sum() / y_test.sum()
    auc_ens = roc_auc_score(y_test, ensemble_weighted)
    print(f"{'Ensemble (Weighted)':<25} {auc_ens:<10.4f} {precision_ens:<15.4f} {recall_ens:<12.4f}")

# ============================================================================
# 7. 피처 중요도 (TOP 30)
# ============================================================================
print("\n" + "=" * 100)
print("7. 피처 중요도 분석 (TOP 30)")
print("=" * 100)

best_model = models[best_model_name]
feature_importance = pd.DataFrame({
    'feature': feature_columns,
    'importance': best_model.feature_importances_ if hasattr(best_model, 'feature_importances_') else [0] * len(feature_columns)
}).sort_values('importance', ascending=False)

print(f"\n{best_model_name} TOP 30 중요 피처:")
for i, row in feature_importance.head(30).iterrows():
    print(f"  {row['feature']:<35s}: {row['importance']:.6f}")

# ============================================================================
# 8. 임계값별 성능
# ============================================================================
print("\n" + "=" * 100)
print("8. 임계값별 실전 성능 (앙상블)")
print("=" * 100)

print(f"\n{'임계값':<10} {'예측 수':<10} {'실제 급등':<12} {'정확도':<12} {'Recall':<10}")
print("-" * 60)

for threshold in [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95]:
    y_pred_threshold = (ensemble_weighted >= threshold).astype(int)

    if y_pred_threshold.sum() > 0:
        actual = (y_test[y_pred_threshold == 1] == 1).sum()
        precision = actual / y_pred_threshold.sum()
        recall = actual / y_test.sum()

        print(f"{threshold:<10.2f} {y_pred_threshold.sum():<10} {actual:<12} {precision:<12.2%} {recall:<10.2%}")

# ============================================================================
# 9. 모델 저장
# ============================================================================
print("\n" + "=" * 100)
print("9. 신(神) 모델 저장")
print("=" * 100)

import os
os.makedirs('models', exist_ok=True)

# 모든 모델 저장
for name, model in models.items():
    filename = f'models/god_model_{name}.pkl'
    with open(filename, 'wb') as f:
        pickle.dump(model, f)
    print(f"  저장: {filename}")

# 앙상블 가중치 저장
with open('models/god_model_ensemble_weights.pkl', 'wb') as f:
    pickle.dump(weights, f)
print(f"  저장: models/god_model_ensemble_weights.pkl")

# 피처 리스트 저장
with open('models/god_model_features.pkl', 'wb') as f:
    pickle.dump(feature_columns, f)
print(f"  저장: models/god_model_features.pkl")

# 피처 중요도 저장
feature_importance.to_csv('results/god_model_feature_importance.csv', index=False)
print(f"  저장: results/god_model_feature_importance.csv")

print("\n" + "=" * 100)
print("신(神) 모델 학습 완료!")
print("=" * 100)

print(f"\n학습 모델: {len(models)}개 + 앙상블")
print(f"사용 피처: {len(feature_columns)}개")
print(f"최고 ROC-AUC: {best_auc:.4f} ({best_model_name})")
print(f"앙상블 ROC-AUC: {auc_ens:.4f}")
print(f"\n다음 단계: python predict_god.py --scan")
