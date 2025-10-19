"""
God 모델 백테스트 시스템
실제 거래 조건을 반영한 백테스트
"""

import pandas as pd
import numpy as np
import pickle
import yaml
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("=" * 100)
print("God 모델 백테스트 시스템")
print("=" * 100)

# 설정
with open('config.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

# 거래 설정
TRANSACTION_FEE = 0.001  # 0.1% 수수료 (편도)
SLIPPAGE = 0.005  # 0.5% 슬리피지 (페니스톡은 슬리피지 큼)
MIN_VOLUME = 10000  # 최소 거래량 (유동성 확인)

# ============================================================================
# 1. 데이터 및 모델 로드
# ============================================================================
print("\n[1/6] 데이터 및 모델 로딩...")

# 데이터 로드
df = pd.read_csv('data/penny_stocks_data.csv')
df['date'] = pd.to_datetime(df['date'], utc=True)
df = df.sort_values(['ticker', 'date'])

print(f"총 데이터: {len(df):,} rows, {df['ticker'].nunique()} tickers")

# God 모델 로드
models = {}
model_names = ['XGBoost_Advanced', 'LightGBM_Advanced', 'RandomForest_Advanced', 'GradientBoosting']

for name in model_names:
    with open(f'models/god_model_{name}.pkl', 'rb') as f:
        models[name] = pickle.load(f)
print(f"모델 로드 완료: {len(models)}개")

# 앙상블 가중치 로드
with open('models/god_model_ensemble_weights.pkl', 'rb') as f:
    ensemble_weights = pickle.load(f)

# 피처 리스트 로드
with open('models/god_model_features.pkl', 'rb') as f:
    feature_columns = pickle.load(f)

print(f"피처 개수: {len(feature_columns)}개")

# ============================================================================
# 2. 피처 생성 (train_god_model.py와 동일)
# ============================================================================
print("\n[2/6] 피처 생성 중...")

# 기본 피처
df['daily_return'] = df.groupby('ticker')['close'].pct_change()
df['daily_return_pct'] = df['daily_return'] * 100
df['volume_change'] = df.groupby('ticker')['volume'].pct_change()
df['volume_change_pct'] = df['volume_change'] * 100
df['hl_range'] = (df['high'] - df['low']) / df['close']
df['oc_range'] = abs(df['open'] - df['close']) / df['close']
df['gap'] = (df['open'] - df.groupby('ticker')['close'].shift(1)) / df.groupby('ticker')['close'].shift(1)

# 이동평균
for window in [3, 5, 7, 10, 15, 20, 30, 50]:
    df[f'sma_{window}'] = df.groupby('ticker')['close'].rolling(window).mean().reset_index(0, drop=True)
    df[f'price_to_sma_{window}'] = df['close'] / df[f'sma_{window}']
    df[f'ema_{window}'] = df.groupby('ticker')['close'].ewm(span=window, adjust=False).mean().reset_index(0, drop=True)
    df[f'price_to_ema_{window}'] = df['close'] / df[f'ema_{window}']

# 거래량 이동평균
for window in [3, 5, 10, 20, 30]:
    df[f'volume_ma_{window}'] = df.groupby('ticker')['volume'].rolling(window).mean().reset_index(0, drop=True)
    df[f'volume_ratio_{window}'] = df['volume'] / df[f'volume_ma_{window}']

# 과거 수익률
for n in [1, 2, 3, 5, 7, 10, 15, 20, 30]:
    df[f'return_{n}d'] = df.groupby('ticker')['close'].pct_change(n) * 100

# 변동성
for window in [5, 10, 20, 30]:
    df[f'volatility_{window}d'] = df.groupby('ticker')['daily_return'].rolling(window).std().reset_index(0, drop=True)

# 롤링 최대/최소 수익률
for window in [5, 10, 20]:
    df[f'max_return_{window}d'] = df.groupby('ticker')['daily_return_pct'].rolling(window).max().reset_index(0, drop=True)
    df[f'min_return_{window}d'] = df.groupby('ticker')['daily_return_pct'].rolling(window).min().reset_index(0, drop=True)

# 고점/저점 분석
for n in [5, 10, 15, 20, 30, 60]:
    df[f'high_{n}d'] = df.groupby('ticker')['high'].rolling(n).max().reset_index(0, drop=True)
    df[f'low_{n}d'] = df.groupby('ticker')['low'].rolling(n).min().reset_index(0, drop=True)
    df[f'price_vs_high_{n}d'] = df['close'] / df[f'high_{n}d']
    df[f'price_vs_low_{n}d'] = df['close'] / df[f'low_{n}d']
    df[f'dist_from_high_{n}d'] = (df[f'high_{n}d'] - df['close']) / df[f'high_{n}d']
    df[f'dist_from_low_{n}d'] = (df['close'] - df[f'low_{n}d']) / df['close']

# RSI
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

# 볼린저 밴드
for window in [10, 20, 30]:
    rolling_mean = df.groupby('ticker')['close'].rolling(window).mean().reset_index(0, drop=True)
    rolling_std = df.groupby('ticker')['close'].rolling(window).std().reset_index(0, drop=True)
    df[f'bb_upper_{window}'] = rolling_mean + (rolling_std * 2)
    df[f'bb_lower_{window}'] = rolling_mean - (rolling_std * 2)
    df[f'bb_middle_{window}'] = rolling_mean
    df[f'bb_position_{window}'] = (df['close'] - df[f'bb_lower_{window}']) / (df[f'bb_upper_{window}'] - df[f'bb_lower_{window}'])
    df[f'bb_width_{window}'] = (df[f'bb_upper_{window}'] - df[f'bb_lower_{window}']) / rolling_mean

# 추세 지표
df['price_direction'] = np.where(df['daily_return'] > 0, 1, np.where(df['daily_return'] < 0, -1, 0))
df['consecutive_up'] = df.groupby('ticker')['price_direction'].apply(
    lambda x: x.groupby((x != x.shift()).cumsum()).cumsum().where(x == 1, 0)
).reset_index(0, drop=True)
df['consecutive_down'] = df.groupby('ticker')['price_direction'].apply(
    lambda x: x.groupby((x != x.shift()).cumsum()).cumsum().where(x == -1, 0).abs()
).reset_index(0, drop=True)

# 승률
for window in [5, 10, 20]:
    df[f'win_rate_{window}d'] = df.groupby('ticker')['price_direction'].rolling(window).apply(
        lambda x: (x > 0).sum() / len(x)
    ).reset_index(0, drop=True)

# 거래량 패턴
for window in [5, 10, 20]:
    df[f'volume_spike_{window}d'] = (df['volume'] > df[f'volume_ma_{window}'] * 2).astype(int)

for window in [5, 10]:
    df[f'volume_trend_{window}d'] = df.groupby('ticker')['volume'].rolling(window).apply(
        lambda x: 1 if x.iloc[-1] > x.iloc[0] else 0
    ).reset_index(0, drop=True)

# 가격-거래량 상관관계
for window in [5, 10, 20]:
    def calc_corr(group):
        return group['daily_return'].rolling(window).corr(group['volume_change'])
    df[f'price_volume_corr_{window}d'] = df.groupby('ticker').apply(calc_corr).reset_index(0, drop=True)

# 시간 피처
df['day_of_week'] = df['date'].dt.dayofweek
df['month'] = df['date'].dt.month
df['quarter'] = df['date'].dt.quarter
df['is_month_start'] = df['date'].dt.is_month_start.astype(int)
df['is_month_end'] = df['date'].dt.is_month_end.astype(int)
df['is_quarter_start'] = df['date'].dt.is_quarter_start.astype(int)
df['is_quarter_end'] = df['date'].dt.is_quarter_end.astype(int)

# 로그 스케일
df['log_price'] = np.log(df['close'] + 1)
df['log_volume'] = np.log(df['volume'] + 1)

# 다음날 수익률 (타겟)
df['next_day_return'] = df.groupby('ticker')['daily_return'].shift(-1)
df['next_day_return_pct'] = df['next_day_return'] * 100

print("피처 생성 완료")

# ============================================================================
# 3. 백테스트 기간 설정
# ============================================================================
print("\n[3/6] 백테스트 기간 설정...")

# 학습 기간: 2022-01-01 ~ 2024-03-31 (80%)
# 테스트 기간: 2024-04-01 ~ 2025-10-17 (20%)
train_end = pd.Timestamp('2024-03-31', tz='UTC')
test_start = pd.Timestamp('2024-04-01', tz='UTC')

# 전체 데이터에서 백테스트 기간만 필터링 (피처는 이미 계산됨)
df_backtest = df[df['date'] >= test_start].copy()

# NaN 처리 (train_god_model.py와 동일)
df_backtest_clean = df_backtest[feature_columns + ['next_day_return_pct']].copy()
df_backtest_clean = df_backtest_clean.replace([np.inf, -np.inf], np.nan)

# 임계값 기반 필터링 (70% 이상의 피처가 있어야 함)
nan_per_row = df_backtest_clean[feature_columns].isnull().sum(axis=1)
min_valid_features = len(feature_columns) * 0.7
df_backtest = df_backtest[nan_per_row <= (len(feature_columns) - min_valid_features)].copy()

# 남은 NaN은 평균값으로 채움
for col in feature_columns:
    if df_backtest[col].isnull().any():
        mean_val = df_backtest[col].mean()
        if pd.isna(mean_val):
            df_backtest[col].fillna(0, inplace=True)
        else:
            df_backtest[col].fillna(mean_val, inplace=True)

print(f"백테스트 기간: {test_start.date()} ~ {df_backtest['date'].max().date()}")
print(f"백테스트 데이터: {len(df_backtest):,} rows (NaN 처리 후)")

# ============================================================================
# 4. 백테스트 실행
# ============================================================================
print("\n[4/6] 백테스트 실행 중...")

# 임계값별 백테스트
thresholds = [0.95, 0.90, 0.85, 0.80, 0.75, 0.70, 0.60, 0.50]

backtest_results = {}

debug_stats = {
    'total_dates': 0,
    'dates_with_data': 0,
    'dates_with_valid_features': 0,
    'total_candidates': 0,
    'candidates_above_threshold': 0,
    'candidates_with_volume': 0
}

for threshold in thresholds:
    print(f"\n임계값 {threshold:.2f} 백테스트 중...")

    trades = []

    # 각 날짜별로 예측
    unique_dates = df_backtest['date'].unique()
    debug_stats['total_dates'] = len(unique_dates) - 1

    for i, current_date in enumerate(unique_dates[:-1]):  # 마지막 날 제외 (다음날 데이터 필요)
        # 현재 날짜 데이터
        df_today = df_backtest[df_backtest['date'] == current_date].copy()

        if len(df_today) > 0:
            debug_stats['dates_with_data'] += 1

        # 피처 준비
        df_today_clean = df_today[feature_columns].copy()
        df_today_clean = df_today_clean.replace([np.inf, -np.inf], np.nan)

        # NaN 있는 행 제거
        valid_rows = df_today_clean.dropna().index
        df_today_valid = df_today.loc[valid_rows]

        if len(df_today_valid) == 0:
            continue

        debug_stats['dates_with_valid_features'] += 1
        debug_stats['total_candidates'] += len(df_today_valid)

        X_today = df_today_clean.loc[valid_rows]

        # 앙상블 예측
        ensemble_probs = []
        for name, model in models.items():
            probs = model.predict_proba(X_today)[:, 1]
            ensemble_probs.append(probs)

        # 가중 평균
        predictions = np.average(ensemble_probs, axis=0, weights=ensemble_weights)

        # 임계값 이상인 종목들
        buy_signals = predictions >= threshold

        if buy_signals.sum() == 0:
            continue

        debug_stats['candidates_above_threshold'] += buy_signals.sum()

        # 매수 종목
        buy_candidates = df_today_valid[buy_signals].copy()
        buy_candidates['predicted_prob'] = predictions[buy_signals]

        # 유동성 필터링 (거래량 체크)
        buy_candidates = buy_candidates[buy_candidates['volume'] >= MIN_VOLUME]

        if len(buy_candidates) == 0:
            continue

        debug_stats['candidates_with_volume'] += len(buy_candidates)

        # 다음날 데이터 가져오기
        next_date = unique_dates[i + 1]
        df_next = df_backtest[df_backtest['date'] == next_date]

        for idx, row in buy_candidates.iterrows():
            ticker = row['ticker']

            # 다음날 해당 종목 데이터
            next_day_data = df_next[df_next['ticker'] == ticker]

            if len(next_day_data) == 0:
                continue

            next_day_data = next_day_data.iloc[0]

            # 매수: 다음날 시가 (+ 슬리피지)
            buy_price = next_day_data['open'] * (1 + SLIPPAGE)

            # 매도: 다음날 종가 (- 슬리피지)
            sell_price = next_day_data['close'] * (1 - SLIPPAGE)

            # 수익률 계산 (수수료 포함)
            gross_return = (sell_price - buy_price) / buy_price
            net_return = gross_return - (TRANSACTION_FEE * 2)  # 매수/매도 수수료

            # 실제 다음날 수익률 (시가 → 종가)
            actual_return = (next_day_data['close'] - next_day_data['open']) / next_day_data['open']

            # 50% 급등 여부
            is_surge = actual_return >= 0.50

            trades.append({
                'date': current_date,
                'trade_date': next_date,
                'ticker': ticker,
                'predicted_prob': row['predicted_prob'],
                'buy_price': buy_price,
                'sell_price': sell_price,
                'gross_return': gross_return,
                'net_return': net_return,
                'actual_return': actual_return,
                'is_surge': is_surge,
                'volume': row['volume']
            })

    if len(trades) == 0:
        print(f"  거래 없음")
        print(f"  디버그: 총 {debug_stats['total_dates']}일 중 데이터 있는 날: {debug_stats['dates_with_data']}일")
        print(f"  디버그: 유효한 피처 있는 날: {debug_stats['dates_with_valid_features']}일")
        print(f"  디버그: 총 후보 종목: {debug_stats['total_candidates']}개")
        print(f"  디버그: 임계값 이상: {debug_stats['candidates_above_threshold']}개")
        print(f"  디버그: 거래량 조건 충족: {debug_stats['candidates_with_volume']}개")
        continue

    # 결과 정리
    trades_df = pd.DataFrame(trades)

    # 성과 지표 계산
    total_trades = len(trades_df)
    surge_count = trades_df['is_surge'].sum()
    surge_rate = surge_count / total_trades * 100 if total_trades > 0 else 0

    win_count = (trades_df['net_return'] > 0).sum()
    win_rate = win_count / total_trades * 100 if total_trades > 0 else 0

    avg_return = trades_df['net_return'].mean() * 100
    median_return = trades_df['net_return'].median() * 100
    total_return = trades_df['net_return'].sum() * 100

    max_win = trades_df['net_return'].max() * 100
    max_loss = trades_df['net_return'].min() * 100

    # 누적 수익률 계산
    trades_df['cumulative_return'] = (1 + trades_df['net_return']).cumprod() - 1
    final_return = trades_df['cumulative_return'].iloc[-1] * 100

    # MDD 계산
    cumulative = (1 + trades_df['net_return']).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max
    mdd = drawdown.min() * 100

    backtest_results[threshold] = {
        'total_trades': total_trades,
        'surge_count': surge_count,
        'surge_rate': surge_rate,
        'win_count': win_count,
        'win_rate': win_rate,
        'avg_return': avg_return,
        'median_return': median_return,
        'total_return': total_return,
        'final_return': final_return,
        'max_win': max_win,
        'max_loss': max_loss,
        'mdd': mdd,
        'trades': trades_df
    }

    print(f"  거래 횟수: {total_trades}")
    print(f"  50% 급등 성공: {surge_count} ({surge_rate:.1f}%)")
    print(f"  수익 거래: {win_count} ({win_rate:.1f}%)")
    print(f"  평균 수익률: {avg_return:.2f}%")

# ============================================================================
# 5. 결과 출력
# ============================================================================
print("\n" + "=" * 100)
print("백테스트 결과 요약")
print("=" * 100)

print(f"\n백테스트 조건:")
print(f"  기간: {test_start.date()} ~ {df_backtest['date'].max().date()}")
print(f"  수수료: {TRANSACTION_FEE*100:.1f}% (편도)")
print(f"  슬리피지: {SLIPPAGE*100:.1f}%")
print(f"  최소 거래량: {MIN_VOLUME:,}")

print(f"\n{'임계값':<10} {'거래수':<10} {'50%급등':<12} {'승률':<12} {'평균수익':<12} {'누적수익':<12} {'MDD':<10}")
print("-" * 100)

for threshold in thresholds:
    if threshold not in backtest_results:
        continue

    res = backtest_results[threshold]
    print(f"{threshold:<10.2f} {res['total_trades']:<10} "
          f"{res['surge_count']}/{res['total_trades']} ({res['surge_rate']:>5.1f}%)  "
          f"{res['win_count']}/{res['total_trades']} ({res['win_rate']:>5.1f}%)  "
          f"{res['avg_return']:>10.2f}%  "
          f"{res['final_return']:>10.1f}%  "
          f"{res['mdd']:>8.1f}%")

# ============================================================================
# 6. 최고 성과 전략 상세 분석
# ============================================================================
print("\n" + "=" * 100)
print("전략별 상세 분석")
print("=" * 100)

for threshold in [0.95, 0.90, 0.80, 0.70]:
    if threshold not in backtest_results:
        continue

    res = backtest_results[threshold]
    trades_df = res['trades']

    print(f"\n{'='*50}")
    print(f"임계값: {threshold:.2f}")
    print(f"{'='*50}")
    print(f"총 거래 횟수: {res['total_trades']}")
    print(f"50% 급등 성공: {res['surge_count']} / {res['total_trades']} ({res['surge_rate']:.1f}%)")
    print(f"수익 거래: {res['win_count']} / {res['total_trades']} ({res['win_rate']:.1f}%)")
    print(f"")
    print(f"평균 수익률: {res['avg_return']:.2f}%")
    print(f"중앙 수익률: {res['median_return']:.2f}%")
    print(f"누적 수익률: {res['final_return']:.1f}%")
    print(f"최대 수익: {res['max_win']:.1f}%")
    print(f"최대 손실: {res['max_loss']:.1f}%")
    print(f"MDD: {res['mdd']:.1f}%")

    # 수익률 분포
    print(f"\n수익률 분포:")
    print(f"  50% 이상: {(trades_df['net_return'] >= 0.50).sum()}")
    print(f"  30-50%: {((trades_df['net_return'] >= 0.30) & (trades_df['net_return'] < 0.50)).sum()}")
    print(f"  10-30%: {((trades_df['net_return'] >= 0.10) & (trades_df['net_return'] < 0.30)).sum()}")
    print(f"  0-10%: {((trades_df['net_return'] >= 0.0) & (trades_df['net_return'] < 0.10)).sum()}")
    print(f"  손실: {(trades_df['net_return'] < 0.0).sum()}")

# ============================================================================
# 7. 결과 저장
# ============================================================================
print("\n" + "=" * 100)
print("결과 저장")
print("=" * 100)

import os
os.makedirs('results', exist_ok=True)

# 각 임계값별 거래 내역 저장
for threshold, res in backtest_results.items():
    trades_df = res['trades']
    filename = f'results/backtest_threshold_{threshold:.2f}.csv'
    trades_df.to_csv(filename, index=False, encoding='utf-8-sig')
    print(f"저장: {filename}")

# 요약 결과 저장
summary = []
for threshold, res in backtest_results.items():
    summary.append({
        'threshold': threshold,
        'total_trades': res['total_trades'],
        'surge_count': res['surge_count'],
        'surge_rate': res['surge_rate'],
        'win_count': res['win_count'],
        'win_rate': res['win_rate'],
        'avg_return': res['avg_return'],
        'median_return': res['median_return'],
        'final_return': res['final_return'],
        'max_win': res['max_win'],
        'max_loss': res['max_loss'],
        'mdd': res['mdd']
    })

summary_df = pd.DataFrame(summary)
summary_df.to_csv('results/backtest_summary.csv', index=False, encoding='utf-8-sig')
print(f"저장: results/backtest_summary.csv")

print("\n" + "=" * 100)
print("백테스트 완료!")
print("=" * 100)
