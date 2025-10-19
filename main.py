"""
Main Script for Penny Stock Surge Prediction
미국 페니스톡 급등주 예측 시스템

Usage:
    python main.py --mode train              # Train models
    python main.py --mode predict            # Make predictions
    python main.py --mode scan               # Scan market for opportunities
    python main.py --mode backtest           # Backtest strategy
"""

import argparse
import sys
from src.trainer import PennyStockTrainer
from src.predictor import PennyStockPredictor
from src.backtester import WalkForwardBacktester
from src.utils import load_config


def train_models(args):
    """Train all models"""
    print("="*70)
    print("페니스톡 급등주 예측 모델 학습 시작")
    print("Starting Penny Stock Surge Prediction Model Training")
    print("="*70)

    trainer = PennyStockTrainer(args.config)

    results = trainer.train_all(
        force_collect=args.force_collect,
        target_window=args.window,
        label_type=args.label_type,
        train_dl=args.train_dl
    )

    print("\n학습 완료! Training Complete!")
    print(f"결과가 저장되었습니다: {trainer.config['output']['results_dir']}/training_summary.csv")


def predict_stocks(args):
    """Make predictions on specific stocks"""
    print("="*70)
    print("페니스톡 급등주 예측")
    print("Penny Stock Surge Prediction")
    print("="*70)

    predictor = PennyStockPredictor(args.config)

    # Load models
    print("\n모델 로딩 중... Loading models...")
    predictor.load_models(['RandomForest', 'XGBoost', 'LightGBM'])

    if args.tickers:
        # Predict specific tickers
        tickers = args.tickers.split(',')
        print(f"\n예측 대상 종목: {tickers}")

        results = predictor.predict_multiple_stocks(
            tickers,
            model_name=args.model,
            top_n=args.top_n
        )

        print("\n예측 결과:")
        print(results.to_string())

    else:
        print("사용법: --tickers TICKER1,TICKER2,TICKER3")
        print("예시: python main.py --mode predict --tickers SNDL,ATOS,GNUS")


def scan_market(args):
    """Scan entire market for surge opportunities"""
    print("="*70)
    print("시장 스캔 - 급등 가능성 높은 종목 탐색")
    print("Market Scan - Finding High Surge Probability Stocks")
    print("="*70)

    predictor = PennyStockPredictor(args.config)

    # Load models
    print("\n모델 로딩 중... Loading models...")
    predictor.load_models(['RandomForest', 'XGBoost', 'LightGBM'])

    # Scan market
    print(f"\n시장 스캔 시작... (Top {args.top_n} 종목)")
    results = predictor.scan_market(
        use_screening=not args.no_screening,
        model_name=args.model,
        top_n=args.top_n
    )

    if not results.empty:
        print(f"\n급등 가능성 높은 Top {len(results)} 종목:")
        print("="*70)
        for idx, row in results.iterrows():
            print(f"{idx+1}. {row['ticker']}")
            print(f"   현재가: ${row['current_price']:.2f}")
            print(f"   급등 확률: {row['surge_probability']:.1%}")
            print(f"   날짜: {row['date']}")
            print("-"*70)

        print(f"\n상세 결과가 저장되었습니다.")
    else:
        print("\n예측 임계값을 넘는 종목이 없습니다.")


def backtest_strategy(args):
    """Backtest prediction strategy with walk-forward validation (NO LOOKAHEAD BIAS)"""
    print("="*70)
    print("Walk-Forward 백테스팅 (Lookahead Bias 없음)")
    print("Walk-Forward Backtesting (No Lookahead Bias)")
    print("="*70)

    backtester = WalkForwardBacktester(args.config)

    # Load historical data
    print("\n과거 데이터 로딩 중...")
    df = backtester.data_collector.load_data()

    if df.empty:
        print("과거 데이터가 없습니다. 먼저 데이터를 수집해주세요.")
        print("사용법: python main.py --mode train --force-collect")
        return

    print(f"\n총 데이터: {len(df):,} 행")
    print(f"기간: {df['date'].min()} ~ {df['date'].max()}")
    print(f"종목 수: {df['ticker'].nunique()}")

    # Run walk-forward backtest
    print(f"\nWalk-Forward 백테스팅 시작...")
    print(f"- 학습 기간: {args.train_days}일")
    print(f"- 리밸런싱 주기: {args.rebalance_days}일")
    print(f"- 포지션 보유 기간: {args.window}일")
    print("")

    results = backtester.walk_forward_backtest(
        df,
        train_period_days=args.train_days,
        rebalance_frequency_days=args.rebalance_days,
        prediction_window=args.window
    )

    if 'error' not in results:
        print("\n" + "="*70)
        print("최종 백테스트 결과")
        print("="*70)
        print(f"총 거래 수: {results['total_trades']}")
        print(f"승률: {results['win_rate']*100:.2f}%")
        print(f"평균 거래당 수익률: {results['avg_return_per_trade']*100:.2f}%")
        print(f"총 포트폴리오 수익률: {results['total_return']*100:.2f}%")
        print(f"샤프 비율: {results['sharpe_ratio']:.2f}")
        print(f"최대 낙폭 (Max Drawdown): {results['max_drawdown']*100:.2f}%")
        print(f"최종 포트폴리오 가치: ${results['final_portfolio']:,.2f}")
        print("="*70)


def main():
    parser = argparse.ArgumentParser(
        description='미국 페니스톡 급등주 예측 시스템 / Penny Stock Surge Prediction System'
    )

    parser.add_argument(
        '--mode',
        type=str,
        required=True,
        choices=['train', 'predict', 'scan', 'backtest'],
        help='실행 모드 / Execution mode'
    )

    parser.add_argument(
        '--config',
        type=str,
        default='config.yaml',
        help='설정 파일 경로 / Config file path'
    )

    parser.add_argument(
        '--model',
        type=str,
        default='XGBoost',
        choices=['RandomForest', 'XGBoost', 'LightGBM', 'LSTM', 'GRU', 'Transformer'],
        help='사용할 모델 / Model to use'
    )

    parser.add_argument(
        '--tickers',
        type=str,
        help='예측할 종목 티커 (쉼표로 구분) / Stock tickers to predict (comma-separated)'
    )

    parser.add_argument(
        '--top-n',
        type=int,
        default=20,
        help='상위 N개 종목 반환 / Return top N stocks'
    )

    parser.add_argument(
        '--window',
        type=int,
        default=5,
        help='예측 윈도우 (일) / Prediction window (days)'
    )

    parser.add_argument(
        '--label-type',
        type=str,
        default='binary',
        choices=['binary', 'multiclass'],
        help='라벨 타입 / Label type'
    )

    parser.add_argument(
        '--force-collect',
        action='store_true',
        help='강제로 새 데이터 수집 / Force collect new data'
    )

    parser.add_argument(
        '--no-screening',
        action='store_true',
        help='종목 스크리닝 건너뛰기 / Skip stock screening'
    )

    parser.add_argument(
        '--train-dl',
        action='store_true',
        default=False,
        help='딥러닝 모델도 학습 / Also train deep learning models'
    )

    parser.add_argument(
        '--train-days',
        type=int,
        default=365,
        help='백테스팅 학습 기간 (일) / Backtest training period (days)'
    )

    parser.add_argument(
        '--rebalance-days',
        type=int,
        default=30,
        help='백테스팅 리밸런싱 주기 (일) / Backtest rebalancing frequency (days)'
    )

    args = parser.parse_args()

    # Route to appropriate function
    if args.mode == 'train':
        train_models(args)
    elif args.mode == 'predict':
        predict_stocks(args)
    elif args.mode == 'scan':
        scan_market(args)
    elif args.mode == 'backtest':
        backtest_strategy(args)


if __name__ == '__main__':
    main()
