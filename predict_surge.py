"""
급등 예측 시스템 - 실시간 시장 스캔 및 종목 예측
"""

import sys
import argparse
import pandas as pd
import numpy as np
import pickle
import yfinance as yf
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class SurgePredictor:
    """급등 예측 시스템"""

    def __init__(self, model_name='XGBoost'):
        """
        Args:
            model_name: 사용할 모델 ('RandomForest', 'XGBoost', 'LightGBM')
        """
        self.model_name = model_name
        self.model = None
        self.features = None
        self.load_model()

    def load_model(self):
        """모델 로드"""
        try:
            # 모델 로드
            model_path = f'models/surge_predictor_{self.model_name}.pkl'
            with open(model_path, 'rb') as f:
                self.model = pickle.load(f)

            # 피처 리스트 로드
            with open('models/surge_predictor_features.pkl', 'rb') as f:
                self.features = pickle.load(f)

            print(f"모델 로드 완료: {self.model_name}")
            print(f"피처 수: {len(self.features)}개")

        except FileNotFoundError:
            print(f"ERROR: 모델 파일을 찾을 수 없습니다!")
            print("먼저 'python train_surge_predictor.py'를 실행하세요.")
            sys.exit(1)

    def calculate_features(self, df):
        """피처 계산"""
        df = df.copy()
        df = df.sort_values('date')

        # 일일 수익률
        df['daily_return'] = df['close'].pct_change()
        df['daily_return_pct'] = df['daily_return'] * 100

        # 거래량 변화
        df['volume_change'] = df['volume'].pct_change()
        df['volume_change_pct'] = df['volume_change'] * 100

        # 가격 변동성
        df['hl_range'] = (df['high'] - df['low']) / df['close']
        df['oc_range'] = abs(df['open'] - df['close']) / df['close']

        # 이동평균선
        for window in [5, 10, 20]:
            df[f'sma_{window}'] = df['close'].rolling(window).mean()
            df[f'price_to_sma_{window}'] = df['close'] / df[f'sma_{window}']

        # 거래량 이동평균
        for window in [5, 10, 20]:
            df[f'volume_ma_{window}'] = df['volume'].rolling(window).mean()
            df[f'volume_ratio_{window}'] = df['volume'] / df[f'volume_ma_{window}']

        # 과거 N일 수익률
        for n in [1, 2, 3, 5, 7, 10]:
            df[f'return_{n}d'] = df['close'].pct_change(n) * 100

        # 과거 N일 최고/최저가 대비
        for n in [5, 10, 20]:
            df[f'high_{n}d'] = df['high'].rolling(n).max()
            df[f'low_{n}d'] = df['low'].rolling(n).min()
            df[f'price_vs_high_{n}d'] = df['close'] / df[f'high_{n}d']
            df[f'price_vs_low_{n}d'] = df['close'] / df[f'low_{n}d']

        # RSI
        def calculate_rsi(series, period=14):
            delta = series.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi

        df['rsi_14'] = calculate_rsi(df['close'], 14)

        # 볼린저 밴드
        for window in [10, 20]:
            rolling_mean = df['close'].rolling(window).mean()
            rolling_std = df['close'].rolling(window).std()
            df[f'bb_upper_{window}'] = rolling_mean + (rolling_std * 2)
            df[f'bb_lower_{window}'] = rolling_mean - (rolling_std * 2)
            df[f'bb_position_{window}'] = (df['close'] - df[f'bb_lower_{window}']) / (df[f'bb_upper_{window}'] - df[f'bb_lower_{window}'])

        # 연속 상승/하락일
        df['price_direction'] = np.where(df['daily_return'] > 0, 1, np.where(df['daily_return'] < 0, -1, 0))
        df['consecutive_up'] = df['price_direction'].groupby((df['price_direction'] != df['price_direction'].shift()).cumsum()).cumsum().where(df['price_direction'] == 1, 0)
        df['consecutive_down'] = df['price_direction'].groupby((df['price_direction'] != df['price_direction'].shift()).cumsum()).cumsum().where(df['price_direction'] == -1, 0).abs()

        return df

    def predict_ticker(self, ticker, days=60):
        """
        특정 종목의 급등 확률 예측

        Args:
            ticker: 종목 심볼
            days: 과거 몇 일 데이터 사용

        Returns:
            dict: 예측 결과
        """
        try:
            # 데이터 다운로드
            print(f"\n{ticker} 데이터 다운로드 중...")
            stock = yf.Ticker(ticker)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            df = stock.history(start=start_date, end=end_date)

            if df.empty:
                return {'error': 'No data available'}

            df = df.reset_index()
            df.columns = df.columns.str.lower()

            # 피처 계산
            df = self.calculate_features(df)

            # 가장 최근 데이터 추출
            latest = df.iloc[-1]

            # 피처 벡터 생성
            X = pd.DataFrame([latest[self.features]])

            # 결측치 처리
            X = X.replace([np.inf, -np.inf], np.nan)
            if X.isnull().any().any():
                return {'error': 'Insufficient data for prediction'}

            # 예측
            surge_prob = self.model.predict_proba(X)[0][1]
            surge_pred = self.model.predict(X)[0]

            # 결과
            result = {
                'ticker': ticker,
                'date': latest['date'].strftime('%Y-%m-%d'),
                'close': latest['close'],
                'volume': latest['volume'],
                'surge_probability': surge_prob,
                'surge_prediction': bool(surge_pred),
                'volume_ratio_5d': latest.get('volume_ratio_5', None),
                'volume_ratio_10d': latest.get('volume_ratio_10', None),
                'price_vs_high_5d': latest.get('price_vs_high_5d', None),
                'rsi_14': latest.get('rsi_14', None),
                'return_1d': latest.get('return_1d', None),
            }

            return result

        except Exception as e:
            return {'error': str(e)}

    def scan_market(self, tickers, threshold=0.5, top_n=20):
        """
        시장 전체 스캔

        Args:
            tickers: 스캔할 종목 리스트
            threshold: 급등 확률 임계값
            top_n: 상위 몇 개 종목 반환

        Returns:
            DataFrame: 예측 결과
        """
        print(f"\n시장 스캔 시작: {len(tickers)}개 종목")
        print(f"급등 확률 임계값: {threshold:.0%}")
        print("=" * 80)

        results = []

        for i, ticker in enumerate(tickers, 1):
            print(f"[{i}/{len(tickers)}] {ticker}...", end=' ')

            result = self.predict_ticker(ticker, days=60)

            if 'error' in result:
                print(f"SKIP ({result['error']})")
                continue

            results.append(result)
            prob = result['surge_probability']

            if prob >= threshold:
                print(f"급등 가능성! (확률: {prob:.1%})")
            else:
                print(f"확률: {prob:.1%}")

        if not results:
            print("\n예측 가능한 종목이 없습니다.")
            return pd.DataFrame()

        # DataFrame 변환
        df_results = pd.DataFrame(results)

        # 정렬
        df_results = df_results.sort_values('surge_probability', ascending=False)

        # 상위 N개 반환
        top_results = df_results.head(top_n)

        return top_results


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='급등 예측 시스템')
    parser.add_argument('--model', type=str, default='XGBoost',
                        choices=['RandomForest', 'XGBoost', 'LightGBM'],
                        help='사용할 모델')
    parser.add_argument('--ticker', type=str, help='예측할 종목 심볼')
    parser.add_argument('--scan', action='store_true', help='전체 시장 스캔')
    parser.add_argument('--threshold', type=float, default=0.5,
                        help='급등 확률 임계값 (0.0-1.0)')
    parser.add_argument('--top', type=int, default=20,
                        help='상위 몇 개 종목 표시')

    args = parser.parse_args()

    # 예측기 초기화
    predictor = SurgePredictor(model_name=args.model)

    if args.ticker:
        # 특정 종목 예측
        print("=" * 80)
        print(f"급등 예측: {args.ticker}")
        print("=" * 80)

        result = predictor.predict_ticker(args.ticker)

        if 'error' in result:
            print(f"\nERROR: {result['error']}")
            return

        print(f"\n종목: {result['ticker']}")
        print(f"날짜: {result['date']}")
        print(f"종가: ${result['close']:.2f}")
        print(f"거래량: {result['volume']:,.0f}")
        print(f"\n급등 확률: {result['surge_probability']:.1%}")
        print(f"급등 예측: {'YES' if result['surge_prediction'] else 'NO'}")

        print(f"\n주요 지표:")
        print(f"  5일 거래량 비율: {result['volume_ratio_5d']:.2f}x")
        print(f"  10일 거래량 비율: {result['volume_ratio_10d']:.2f}x")
        print(f"  5일 최고가 대비: {result['price_vs_high_5d']:.1%}")
        print(f"  RSI(14): {result['rsi_14']:.1f}")
        print(f"  전날 수익률: {result['return_1d']:+.2f}%")

        if result['surge_probability'] >= args.threshold:
            print(f"\n⚠️  급등 가능성 높음! (임계값: {args.threshold:.0%})")
        else:
            print(f"\n   급등 가능성 낮음 (임계값: {args.threshold:.0%})")

    elif args.scan:
        # 전체 시장 스캔
        from src.data_collector import PennyStockCollector
        import yaml

        with open('config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        collector = PennyStockCollector(config)
        tickers = collector.get_penny_stock_universe()

        print("=" * 80)
        print("급등 예측 시장 스캔")
        print("=" * 80)

        top_stocks = predictor.scan_market(tickers, threshold=args.threshold, top_n=args.top)

        if top_stocks.empty:
            return

        print("\n" + "=" * 80)
        print(f"급등 가능성 높은 종목 TOP {len(top_stocks)}")
        print("=" * 80)

        print(f"\n{'순위':<5} {'종목':<8} {'종가':<10} {'급등확률':<12} {'5일거래량':<12} {'RSI':<8}")
        print("-" * 70)

        for i, row in top_stocks.iterrows():
            rank = list(top_stocks.index).index(i) + 1
            volume_ratio = row.get('volume_ratio_5d', 0)
            rsi = row.get('rsi_14', 0)

            print(f"{rank:<5} {row['ticker']:<8} ${row['close']:<9.2f} "
                  f"{row['surge_probability']:<11.1%} {volume_ratio:<11.2f}x {rsi:<8.1f}")

        # 결과 저장
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'results/surge_scan_{timestamp}.csv'
        top_stocks.to_csv(filename, index=False)
        print(f"\n결과 저장: {filename}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
