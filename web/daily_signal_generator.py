"""
매일 시그널 자동 생성 스크립트
- 주식시장 마감 후 (오후 4시) 실행
- 다음 날 거래 시그널 생성
- 데이터베이스에 저장
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import pickle
from datetime import datetime, timedelta
import yfinance as yf
import logging
from src.data_collector import PennyStockCollector

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DailySignalGenerator:
    def __init__(self):
        self.models = self.load_models()
        self.features = self.load_features()
        self.threshold = 0.90

    def load_models(self):
        """God 모델 로드"""
        models = {}
        model_names = ['XGBoost_Advanced', 'LightGBM_Advanced',
                      'RandomForest_Advanced', 'GradientBoosting']

        for name in model_names:
            path = f'models/god_model_{name}.pkl'
            if os.path.exists(path):
                with open(path, 'rb') as f:
                    models[name] = pickle.load(f)
                logger.info(f"Loaded model: {name}")

        # 앙상블 가중치 로드
        with open('models/god_model_ensemble_weights.pkl', 'rb') as f:
            models['weights'] = pickle.load(f)

        return models

    def load_features(self):
        """피처 리스트 로드"""
        with open('models/god_model_features.pkl', 'rb') as f:
            features = pickle.load(f)
        return features

    def get_all_tickers(self):
        """모든 티커 가져오기"""
        from src.data_collector import PennyStockCollector
        from src.config import Config

        config = Config()
        collector = PennyStockCollector(config)
        return collector.get_all_tickers()

    def download_latest_data(self):
        """최신 데이터 다운로드 (오늘 종가)"""
        logger.info("Downloading latest market data...")

        tickers = self.get_all_tickers()
        today = datetime.now().strftime('%Y-%m-%d')

        all_data = []
        for ticker in tickers:
            try:
                df = yf.download(ticker, start=today, end=today, progress=False)
                if not df.empty:
                    df['ticker'] = ticker
                    df['date'] = df.index
                    all_data.append(df)
            except Exception as e:
                logger.warning(f"Failed to download {ticker}: {e}")

        if all_data:
            df_today = pd.concat(all_data, ignore_index=True)
            logger.info(f"Downloaded data for {len(all_data)} tickers")
            return df_today
        else:
            logger.error("No data downloaded!")
            return None

    def calculate_features(self, df):
        """피처 계산"""
        logger.info("Calculating features...")

        # 기본 피처
        df['return'] = df.groupby('ticker')['Close'].pct_change()
        df['volatility_20d'] = df.groupby('ticker')['return'].rolling(20).std().reset_index(0, drop=True)
        df['volatility_10d'] = df.groupby('ticker')['return'].rolling(10).std().reset_index(0, drop=True)
        df['volume_ratio_20'] = df['Volume'] / df.groupby('ticker')['Volume'].rolling(20).mean().reset_index(0, drop=True)

        # 가격 관련
        df['high_20d'] = df.groupby('ticker')['High'].rolling(20).max().reset_index(0, drop=True)
        df['low_20d'] = df.groupby('ticker')['Low'].rolling(20).min().reset_index(0, drop=True)
        df['dist_from_high_20d'] = (df['high_20d'] - df['Close']) / df['high_20d']
        df['dist_from_low_20d'] = (df['Close'] - df['low_20d']) / df['low_20d']

        # 기술적 지표
        df['rsi_14'] = self.calculate_rsi(df, 14)
        df['macd'], df['macd_signal'] = self.calculate_macd(df)

        # 갭
        df['prev_close'] = df.groupby('ticker')['Close'].shift(1)
        df['gap'] = (df['Open'] - df['prev_close']) / df['prev_close']

        return df

    def calculate_rsi(self, df, period=14):
        """RSI 계산"""
        delta = df.groupby('ticker')['Close'].diff()
        gain = delta.where(delta > 0, 0).rolling(window=period).mean()
        loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def calculate_macd(self, df):
        """MACD 계산"""
        ema12 = df.groupby('ticker')['Close'].ewm(span=12).mean()
        ema26 = df.groupby('ticker')['Close'].ewm(span=26).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9).mean()
        return macd, signal

    def predict_signals(self, df):
        """시그널 예측"""
        logger.info("Generating predictions...")

        # 피처만 선택
        X = df[self.features].copy()

        # NaN 처리
        X = X.fillna(X.median())
        X = X.replace([np.inf, -np.inf], 0)

        # 각 모델 예측
        predictions = {}
        for name, model in self.models.items():
            if name != 'weights':
                pred_proba = model.predict_proba(X)[:, 1]
                predictions[name] = pred_proba

        # 앙상블
        weights = self.models['weights']
        ensemble_pred = np.zeros(len(X))
        for name, weight in weights.items():
            if name in predictions:
                ensemble_pred += predictions[name] * weight

        df['predicted_probability'] = ensemble_pred

        # 임계값 필터링
        signals = df[df['predicted_probability'] >= self.threshold].copy()
        signals = signals.sort_values('predicted_probability', ascending=False)

        logger.info(f"Generated {len(signals)} signals (threshold >= {self.threshold})")

        return signals

    def is_market_open(self, date):
        """
        해당 날짜가 시장 개장일인지 확인
        - 주말 제외
        - 미국 주요 공휴일 제외
        """
        # 주말 체크
        if date.weekday() >= 5:  # 토, 일
            return False

        # 2025년 미국 주식시장 휴장일 (주요 공휴일)
        us_holidays_2025 = [
            datetime(2025, 1, 1),   # New Year's Day
            datetime(2025, 1, 20),  # Martin Luther King Jr. Day
            datetime(2025, 2, 17),  # Presidents' Day
            datetime(2025, 4, 18),  # Good Friday
            datetime(2025, 5, 26),  # Memorial Day
            datetime(2025, 6, 19),  # Juneteenth
            datetime(2025, 7, 4),   # Independence Day
            datetime(2025, 9, 1),   # Labor Day
            datetime(2025, 11, 27), # Thanksgiving
            datetime(2025, 12, 25), # Christmas
        ]

        # 날짜만 비교 (시간 제외)
        date_only = datetime(date.year, date.month, date.day)
        if date_only in us_holidays_2025:
            return False

        return True

    def get_next_trading_day(self):
        """다음 거래일 계산 (주말 + 휴장일 건너뛰기)"""
        today = datetime.now()
        next_day = today + timedelta(days=1)

        # 주말이거나 휴장일이면 다음 거래일로
        while not self.is_market_open(next_day):
            next_day += timedelta(days=1)

            # 무한루프 방지 (최대 10일)
            if (next_day - today).days > 10:
                logger.warning("Could not find trading day within 10 days!")
                break

        logger.info(f"Next trading day calculated: {next_day.strftime('%Y-%m-%d')} ({next_day.strftime('%A')})")
        return next_day.strftime('%Y-%m-%d')

    def save_signals(self, signals):
        """시그널 저장"""
        if signals.empty:
            logger.warning("No signals to save!")
            return None

        # 오늘 날짜
        today = datetime.now().strftime('%Y-%m-%d')

        # 다음 거래일 (금요일이면 월요일로)
        next_trading_day = self.get_next_trading_day()

        logger.info(f"Signal date: {today}, Trade date: {next_trading_day}")

        # 저장할 데이터 선택
        save_columns = ['ticker', 'predicted_probability', 'Close',
                       'Volume', 'volatility_20d', 'rsi_14']

        signals_save = signals[save_columns].copy()
        signals_save['signal_date'] = today
        signals_save['trade_date'] = next_trading_day  # 주말 고려!
        signals_save['signal_generated_at'] = datetime.now()
        signals_save['status'] = 'pending'  # pending, success, failed
        signals_save['buy_price'] = None
        signals_save['sell_price'] = None
        signals_save['actual_return'] = None

        # CSV 저장 (매일 누적)
        csv_path = f'web/data/signals_history.csv'

        if os.path.exists(csv_path):
            # 기존 데이터에 추가
            existing = pd.read_csv(csv_path)
            combined = pd.concat([existing, signals_save], ignore_index=True)
            combined.to_csv(csv_path, index=False)
        else:
            # 새로 생성
            os.makedirs('web/data', exist_ok=True)
            signals_save.to_csv(csv_path, index=False)

        # 오늘 시그널만 따로 저장
        today_path = f'web/data/signals_today.csv'
        signals_save.to_csv(today_path, index=False)

        logger.info(f"Signals saved: {csv_path}")
        logger.info(f"Today's signals: {today_path}")

        return signals_save

    def run(self):
        """전체 프로세스 실행"""
        logger.info("=" * 80)
        logger.info("Daily Signal Generator - Starting")
        logger.info(f"Time: {datetime.now()}")
        logger.info("=" * 80)

        try:
            # 1. 최신 데이터 다운로드
            df_today = self.download_latest_data()
            if df_today is None:
                logger.error("Failed to download data. Exiting.")
                return None

            # 2. 피처 계산
            df_features = self.calculate_features(df_today)

            # 3. 시그널 예측
            signals = self.predict_signals(df_features)

            # 4. 시그널 저장
            saved_signals = self.save_signals(signals)

            logger.info("=" * 80)
            logger.info("Daily Signal Generator - Completed")
            logger.info(f"Total signals: {len(signals) if signals is not None else 0}")
            logger.info("=" * 80)

            return saved_signals

        except Exception as e:
            logger.error(f"Error in signal generation: {e}")
            import traceback
            traceback.print_exc()
            return None

if __name__ == '__main__':
    generator = DailySignalGenerator()
    signals = generator.run()

    if signals is not None and not signals.empty:
        print("\n" + "=" * 80)
        print("TODAY'S SIGNALS")
        print("=" * 80)
        print(signals[['ticker', 'predicted_probability', 'Close']].to_string(index=False))
        print("=" * 80)
