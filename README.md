# 미국 페니스톡 급등주 예측 시스템
# US Penny Stock Surge Prediction System

머신러닝(ML)과 딥러닝(DL)을 활용하여 미국 페니스톡의 급등을 사전에 예측하는 시스템입니다.

This system predicts US penny stock surges before they happen using Machine Learning and Deep Learning.

---

## 주요 기능 (Key Features)

### 1. 데이터 수집 (Data Collection)
- yfinance를 통한 실시간 주가 데이터 수집
- 페니스톡 자동 스크리닝 (가격, 거래량, 시가총액 기준)
- 과거 데이터 자동 업데이트

### 2. 급등주 패턴 학습 (Surge Pattern Learning)
- 다양한 시간 윈도우(1일, 3일, 5일, 7일, 10일) 급등 패턴 분석
- 급등 기준: 15%, 30%, 50%, 100% 상승
- 거래량 급증 패턴 감지
- 갭 상승 패턴 인식

### 3. 기술적 지표 (Technical Indicators)
- **추세 지표**: MACD, ADX, Aroon, 이동평균선
- **모멘텀 지표**: RSI, Stochastic, CCI, Williams %R, ROC
- **변동성 지표**: Bollinger Bands, ATR, Keltner Channels
- **거래량 지표**: OBV, VWAP, MFI, A/D Line
- **가격 패턴**: 지지/저항선, 추세 감지, 캔들 패턴

### 4. 머신러닝 모델 (ML Models)
- **Random Forest**: 앙상블 학습
- **XGBoost**: 그래디언트 부스팅
- **LightGBM**: 고속 그래디언트 부스팅
- **Ensemble**: 모든 모델의 예측 결합

### 5. 딥러닝 모델 (DL Models)
- **LSTM**: 장단기 메모리 네트워크
- **GRU**: Gated Recurrent Unit
- **Transformer**: 어텐션 메커니즘 기반 모델

### 6. 실시간 예측 (Real-time Prediction)
- 개별 종목 급등 확률 예측
- 전체 시장 스캔
- 앙상블 예측
- 신뢰도 기반 필터링

### 7. 백테스팅 (Backtesting)
- 과거 데이터 기반 전략 검증
- 수익률 및 성공률 계산
- 모델 성능 비교

---

## 설치 방법 (Installation)

### 1. Python 환경 준비
```bash
# Python 3.8 이상 필요
python --version
```

### 2. 패키지 설치
```bash
pip install -r requirements.txt
```

### 3. TA-Lib 설치 (선택사항, 고급 기술적 지표용)
Windows:
```bash
# https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib
# 에서 본인 Python 버전에 맞는 .whl 파일 다운로드 후
pip install TA_Lib-0.4.XX-cpXX-cpXX-win_amd64.whl
```

---

## 사용 방법 (Usage)

### 1. 설정 파일 수정
`config.yaml` 파일을 열어 원하는 설정을 변경하세요:
- 페니스톡 기준 (최대 가격, 최소 거래량)
- 급등 임계값
- 모델 하이퍼파라미터
- 예측 신뢰도 기준

### 2. 모델 학습 (Model Training)

#### 기본 학습 (머신러닝만)
```bash
python main.py --mode train
```

#### 새 데이터 수집 후 학습
```bash
python main.py --mode train --force-collect
```

#### 딥러닝 모델 포함 학습
```bash
python main.py --mode train --train-dl
```

#### 다른 예측 윈도우로 학습
```bash
python main.py --mode train --window 10
```

### 3. 종목 예측 (Stock Prediction)

#### 특정 종목 예측
```bash
python main.py --mode predict --tickers SNDL,ATOS,GNUS
```

#### 다른 모델 사용
```bash
python main.py --mode predict --tickers SNDL,ATOS --model RandomForest
```

### 4. 시장 스캔 (Market Scan)

#### 급등 가능성 높은 종목 찾기
```bash
python main.py --mode scan
```

#### 상위 50개 종목 스캔
```bash
python main.py --mode scan --top-n 50
```

#### 특정 모델로 스캔
```bash
python main.py --mode scan --model LightGBM
```

### 5. 백테스팅 (Backtesting)

#### 전략 성과 검증
```bash
python main.py --mode backtest
```

#### 다른 예측 윈도우로 백테스팅
```bash
python main.py --mode backtest --window 7
```

---

## 프로젝트 구조 (Project Structure)

```
PENNY STOCK TRADE/
│
├── config.yaml                 # 설정 파일
├── requirements.txt            # 필요한 패키지
├── main.py                     # 메인 실행 스크립트
├── README.md                   # 이 문서
│
├── src/                        # 소스 코드
│   ├── __init__.py
│   ├── data_collector.py       # 데이터 수집
│   ├── labeling.py             # 급등주 라벨링
│   ├── feature_engineering.py  # 피처 엔지니어링
│   ├── ml_models.py            # 머신러닝 모델
│   ├── dl_models.py            # 딥러닝 모델
│   ├── trainer.py              # 학습 파이프라인
│   ├── predictor.py            # 예측 시스템
│   └── utils.py                # 유틸리티 함수
│
├── data/                       # 데이터 저장
│   └── penny_stocks_data.csv
│
├── models/                     # 학습된 모델
│   ├── RandomForest.pkl
│   ├── XGBoost.pkl
│   ├── LightGBM.pkl
│   ├── lstm_best.h5
│   ├── gru_best.h5
│   └── transformer_best.h5
│
├── results/                    # 결과 저장
│   ├── training_summary.csv
│   └── market_scan_*.csv
│
├── plots/                      # 시각화 저장
│
└── logs/                       # 로그 파일
    └── pennystock_ml.log
```

---

## 급등주 판단 기준 (Surge Criteria)

시스템은 다음 기준으로 급등주를 정의합니다:

1. **Mild (경미)**: 15% 이상 상승
2. **Moderate (보통)**: 30% 이상 상승 ⭐ (기본값)
3. **Strong (강함)**: 50% 이상 상승
4. **Extreme (극단)**: 100% 이상 상승

`config.yaml`에서 기준을 변경할 수 있습니다.

---

## 모델 성능 비교 (Model Performance)

학습 후 `results/training_summary.csv` 파일에서 각 모델의 성능을 확인할 수 있습니다:

- Accuracy (정확도)
- ROC AUC (ROC 곡선 아래 면적)
- Precision (정밀도)
- Recall (재현율)
- F1-Score

일반적으로:
- **XGBoost**: 가장 균형잡힌 성능
- **LightGBM**: 가장 빠른 학습 속도
- **Random Forest**: 안정적인 성능
- **Ensemble**: 최고 정확도
- **LSTM/GRU**: 시계열 패턴 포착에 강함
- **Transformer**: 복잡한 패턴 학습 가능

---

## 주의사항 (Important Notes)

### ⚠️ 투자 유의사항
1. **이 시스템은 투자 조언이 아닙니다**
2. 페니스톡은 **매우 높은 변동성과 위험**을 가집니다
3. 과거 성과가 미래 수익을 보장하지 않습니다
4. 반드시 본인의 판단으로 투자하세요
5. 손실 감당 가능한 금액만 투자하세요

### 🔧 기술적 고려사항
1. 데이터 품질이 예측 정확도에 큰 영향을 미칩니다
2. 시장 상황 변화에 따라 모델 재학습이 필요합니다
3. yfinance 데이터는 15-20분 지연될 수 있습니다
4. 일부 페니스톡은 데이터가 불완전할 수 있습니다

---

## 고급 사용법 (Advanced Usage)

### 1. 커스텀 페니스톡 리스트 사용
`src/data_collector.py`의 `get_penny_stock_universe()` 함수를 수정하여 원하는 종목 리스트를 사용할 수 있습니다.

### 2. 새로운 기술적 지표 추가
`src/feature_engineering.py`에 새로운 기술적 지표를 추가할 수 있습니다.

### 3. 모델 하이퍼파라미터 튜닝
`config.yaml`의 `ml_models` 및 `dl_models` 섹션에서 하이퍼파라미터를 조정할 수 있습니다.

### 4. Python 코드로 직접 사용
```python
from src.trainer import PennyStockTrainer
from src.predictor import PennyStockPredictor

# 학습
trainer = PennyStockTrainer()
results = trainer.train_all()

# 예측
predictor = PennyStockPredictor()
predictor.load_models(['XGBoost'])
top_stocks = predictor.scan_market()
```

---

## 문제 해결 (Troubleshooting)

### 데이터 수집 오류
```
Error downloading ticker: ...
```
- 인터넷 연결 확인
- 티커 심볼이 정확한지 확인
- yfinance 버전 업데이트: `pip install -U yfinance`

### 메모리 부족
```
MemoryError
```
- `config.yaml`에서 `lookback_days` 감소
- 더 적은 종목으로 학습
- 시스템 메모리 증설 고려

### TA-Lib 설치 오류
- pandas-ta를 대신 사용 (자동으로 전환됨)
- 또는 위 설치 가이드 참조

---

## 기여 (Contributing)

개선 사항이나 버그 발견 시 이슈를 등록해주세요.

---

## 라이선스 (License)

이 프로젝트는 교육 및 연구 목적으로 제공됩니다.

---

## 면책 조항 (Disclaimer)

이 소프트웨어는 "있는 그대로" 제공되며, 어떠한 보증도 하지 않습니다.
투자 손실에 대해 개발자는 책임을 지지 않습니다.

This software is provided "as is" without any warranties.
The developer is not responsible for any investment losses.

---

**Happy Trading! 행운을 빕니다!** 🚀📈
