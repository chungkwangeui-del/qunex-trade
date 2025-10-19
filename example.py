"""
Example Usage Script
사용 예제 스크립트
"""

from src.trainer import PennyStockTrainer
from src.predictor import PennyStockPredictor


def example_1_simple_prediction():
    """예제 1: 간단한 종목 예측"""
    print("="*70)
    print("예제 1: 특정 종목의 급등 가능성 예측")
    print("="*70)

    # 예측기 초기화 및 모델 로드
    predictor = PennyStockPredictor()
    predictor.load_models(['XGBoost'])

    # 종목 예측
    tickers = ['SNDL', 'ATOS', 'GNUS']

    print(f"\n분석 대상: {', '.join(tickers)}\n")

    for ticker in tickers:
        result = predictor.predict_single_stock(ticker, model_name='XGBoost')

        if 'error' not in result:
            print(f"종목: {result['ticker']}")
            print(f"현재가: ${result['current_price']:.2f}")
            print(f"급등 예측: {'YES' if result['prediction'] == 1 else 'NO'}")
            print(f"급등 확률: {result['surge_probability']:.1%}")
            print("-"*70)
        else:
            print(f"종목: {ticker} - 오류: {result['error']}")
            print("-"*70)


def example_2_market_scan():
    """예제 2: 전체 시장 스캔"""
    print("\n\n")
    print("="*70)
    print("예제 2: 시장 스캔 - 급등 가능성 높은 종목 찾기")
    print("="*70)

    predictor = PennyStockPredictor()
    predictor.load_models(['XGBoost'])

    print("\n시장 스캔 시작...\n")

    # 시장 스캔
    top_stocks = predictor.scan_market(
        use_screening=True,
        model_name='XGBoost',
        top_n=10
    )

    if not top_stocks.empty:
        print(f"급등 가능성 높은 Top {len(top_stocks)} 종목:\n")

        for idx, row in top_stocks.iterrows():
            print(f"{idx+1}. {row['ticker']}")
            print(f"   현재가: ${row['current_price']:.2f}")
            print(f"   급등 확률: {row['surge_probability']:.1%}")
            print(f"   날짜: {row['date']}")
            print("-"*70)
    else:
        print("조건을 만족하는 종목이 없습니다.")


def example_3_ensemble_prediction():
    """예제 3: 앙상블 예측"""
    print("\n\n")
    print("="*70)
    print("예제 3: 앙상블 예측 (여러 모델의 평균)")
    print("="*70)

    predictor = PennyStockPredictor()
    predictor.load_models(['XGBoost', 'RandomForest', 'LightGBM'])

    ticker = 'SNDL'
    print(f"\n종목: {ticker}")
    print("\n개별 모델 예측:")

    # 각 모델 예측
    for model_name in ['XGBoost', 'RandomForest', 'LightGBM']:
        result = predictor.predict_single_stock(ticker, model_name)
        if 'error' not in result:
            print(f"  {model_name}: {result['surge_probability']:.1%}")

    # 앙상블 예측
    print("\n앙상블 예측:")
    ensemble_result = predictor.predict_ensemble(ticker)

    if 'error' not in ensemble_result:
        print(f"  평균 급등 확률: {ensemble_result['surge_probability']:.1%}")
        print(f"  최종 예측: {'급등 예상' if ensemble_result['prediction'] == 1 else '급등 예상 안 됨'}")
        print(f"  사용된 모델 수: {ensemble_result['num_models']}")


def example_4_custom_training():
    """예제 4: 커스텀 설정으로 학습"""
    print("\n\n")
    print("="*70)
    print("예제 4: 커스텀 설정으로 모델 학습")
    print("="*70)

    # 주의: 이 예제는 실제로 실행하면 시간이 오래 걸립니다
    print("\n주의: 실제 학습은 시간이 오래 걸립니다.")
    print("이 예제는 코드 구조만 보여줍니다.")
    print("\n실제로 실행하려면 아래 주석을 해제하세요.\n")

    """
    trainer = PennyStockTrainer()

    # 7일 후 급등 예측, 다중 클래스 분류
    results = trainer.train_all(
        force_collect=True,      # 새 데이터 수집
        target_window=7,         # 7일 후 예측
        label_type='multiclass', # 급등 정도 구분
        train_dl=False          # 머신러닝만 (빠른 학습)
    )

    # 결과 출력
    print("\n학습 결과:")
    for model_name, model_results in results['ML'].items():
        print(f"{model_name}:")
        print(f"  정확도: {model_results['accuracy']:.2%}")
        print(f"  ROC AUC: {model_results.get('roc_auc', 'N/A')}")
    """


def example_5_backtesting():
    """예제 5: 백테스팅"""
    print("\n\n")
    print("="*70)
    print("예제 5: 백테스팅 - 과거 데이터로 전략 검증")
    print("="*70)

    predictor = PennyStockPredictor()
    predictor.load_models(['XGBoost'])

    # 과거 데이터 로드
    print("\n과거 데이터 로딩...")
    df = predictor.data_collector.load_data()

    if not df.empty:
        print(f"데이터 로드 완료: {len(df)} 행")

        # 백테스팅
        print("\n백테스팅 시작...\n")
        results = predictor.backtest_predictions(df, model_name='XGBoost', window=5)

        if 'error' not in results:
            print("백테스트 결과:")
            print(f"  모델: {results['model']}")
            print(f"  총 급등 예측 수: {results['total_predictions']}")
            print(f"  평균 수익률: {results['average_return']:.2%}")
            print(f"  성공률 (30% 이상): {results['hit_rate']:.2%}")
        else:
            print(f"백테스팅 오류: {results['error']}")
    else:
        print("과거 데이터가 없습니다.")
        print("먼저 데이터를 수집하세요: python main.py --mode train --force-collect")


def main():
    """모든 예제 실행"""
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*20 + "페니스톡 급등 예측 시스템" + " "*21 + "║")
    print("║" + " "*15 + "Penny Stock Surge Prediction System" + " "*16 + "║")
    print("║" + " "*25 + "사용 예제 모음" + " "*27 + "║")
    print("╚" + "="*68 + "╝")

    try:
        # 예제 1: 간단한 예측
        example_1_simple_prediction()

        # 예제 2: 시장 스캔
        example_2_market_scan()

        # 예제 3: 앙상블 예측
        example_3_ensemble_prediction()

        # 예제 4: 커스텀 학습 (코드만)
        example_4_custom_training()

        # 예제 5: 백테스팅
        example_5_backtesting()

        print("\n\n")
        print("="*70)
        print("모든 예제 완료!")
        print("="*70)
        print("\n더 많은 정보는 README.md와 QUICKSTART_KR.md를 참조하세요.")
        print("\n")

    except Exception as e:
        print(f"\n오류 발생: {str(e)}")
        print("\n먼저 모델을 학습하세요: python main.py --mode train --force-collect")


if __name__ == '__main__':
    main()
