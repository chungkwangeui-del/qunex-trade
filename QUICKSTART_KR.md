# 빠른 시작 가이드 (Quick Start Guide)

## 5분 만에 시작하기

### 1단계: 패키지 설치
```bash
pip install -r requirements.txt
```

### 2단계: 모델 학습하기
```bash
# 기본 학습 (머신러닝 모델만, 약 10-30분 소요)
python main.py --mode train --force-collect

# 딥러닝 포함 (약 1-2시간 소요)
python main.py --mode train --force-collect --train-dl
```

### 3단계: 급등주 찾기
```bash
# 시장 전체 스캔하여 급등 가능성 높은 종목 찾기
python main.py --mode scan --top-n 20
```

---

## 자주 하는 작업들

### 특정 종목 급등 가능성 확인
```bash
python main.py --mode predict --tickers SNDL,ATOS,GNUS,ZOM,BNGO
```

### 시장에서 가장 유망한 종목 찾기
```bash
python main.py --mode scan --top-n 50 --model XGBoost
```

### 백테스팅으로 전략 검증
```bash
python main.py --mode backtest --model XGBoost --window 5
```

### 다른 급등 기준으로 학습
```bash
# 10일 내 급등 예측
python main.py --mode train --window 10

# 3일 내 급등 예측
python main.py --mode train --window 3
```

---

## 설정 커스터마이징

`config.yaml` 파일에서 중요한 설정들:

### 페니스톡 기준 변경
```yaml
data:
  penny_stock_max_price: 5.0  # 최대 가격 ($5 이하)
  min_volume: 100000          # 최소 거래량
  min_market_cap: 1000000     # 최소 시가총액
```

### 급등 기준 변경
```yaml
surge:
  default_threshold: 0.30  # 30% 상승을 급등으로 정의
  # 0.15 = 15%, 0.50 = 50%, 1.00 = 100%
```

### 예측 신뢰도 기준 변경
```yaml
prediction:
  confidence_threshold: 0.7  # 70% 이상 확률만 표시
  top_n_stocks: 20          # 상위 20개 종목만 반환
```

---

## Python 코드로 직접 사용하기

### 예제 1: 간단한 예측
```python
from src.predictor import PennyStockPredictor

# 예측기 초기화
predictor = PennyStockPredictor()
predictor.load_models(['XGBoost'])

# 특정 종목 예측
result = predictor.predict_single_stock('SNDL', model_name='XGBoost')
print(f"급등 확률: {result['surge_probability']:.1%}")
```

### 예제 2: 시장 스캔
```python
from src.predictor import PennyStockPredictor

predictor = PennyStockPredictor()
predictor.load_models(['XGBoost', 'RandomForest', 'LightGBM'])

# 시장 스캔
top_stocks = predictor.scan_market(use_screening=True, top_n=20)
print(top_stocks[['ticker', 'current_price', 'surge_probability']])
```

### 예제 3: 앙상블 예측
```python
from src.predictor import PennyStockPredictor

predictor = PennyStockPredictor()
predictor.load_models(['XGBoost', 'RandomForest', 'LightGBM'])

# 여러 모델의 평균으로 예측
result = predictor.predict_ensemble('ATOS')
print(f"앙상블 예측 급등 확률: {result['surge_probability']:.1%}")
```

### 예제 4: 커스텀 학습
```python
from src.trainer import PennyStockTrainer

trainer = PennyStockTrainer()

# 특정 설정으로 학습
results = trainer.train_all(
    force_collect=True,      # 새 데이터 수집
    target_window=7,         # 7일 후 급등 예측
    label_type='multiclass', # 다중 클래스 (급등 정도 구분)
    train_dl=True           # 딥러닝 모델도 학습
)

# 결과 확인
for model_name, model_results in results['ML'].items():
    print(f"{model_name}: {model_results['accuracy']:.2%}")
```

---

## 일반적인 워크플로우

### 초기 설정 (한 번만)
1. 패키지 설치
2. config.yaml 설정 확인/수정
3. 첫 모델 학습

### 매일 사용
1. 시장 스캔하여 급등 가능성 종목 찾기
2. 관심 종목 개별 예측
3. 백테스팅으로 전략 검증

### 주기적 업데이트 (주 1회 권장)
1. 새 데이터로 모델 재학습
2. 성능 비교 및 최적 모델 선택

---

## 결과 파일 확인

### 학습 결과
```
results/training_summary.csv
```
- 각 모델의 정확도, ROC AUC 등 성능 지표

### 시장 스캔 결과
```
results/market_scan_YYYYMMDD_HHMMSS.csv
```
- 급등 가능성 높은 종목 리스트
- 현재가, 급등 확률 등 상세 정보

### 로그 파일
```
logs/pennystock_ml.log
```
- 모든 작업 로그 기록

---

## 팁과 트릭

### 1. 여러 모델 비교
```bash
# XGBoost로 스캔
python main.py --mode scan --model XGBoost > xgb_results.txt

# RandomForest로 스캔
python main.py --mode scan --model RandomForest > rf_results.txt

# 결과 비교
```

### 2. 급등 기준별 학습
```bash
# 15% 급등 (보수적)
# config.yaml에서 default_threshold: 0.15로 변경 후
python main.py --mode train

# 50% 급등 (공격적)
# config.yaml에서 default_threshold: 0.50로 변경 후
python main.py --mode train
```

### 3. 특정 섹터만 분석
`src/data_collector.py`의 `get_penny_stock_universe()` 함수에서 원하는 종목만 포함:
```python
def get_penny_stock_universe(self):
    # 바이오텍 페니스톡만
    penny_stocks = ['ATOS', 'OCGN', 'BNGO', 'JAGX', ...]
    return penny_stocks
```

### 4. 실시간 모니터링 (고급)
```python
import time
from src.predictor import PennyStockPredictor

predictor = PennyStockPredictor()
predictor.load_models(['XGBoost'])

# 1시간마다 스캔
while True:
    top_stocks = predictor.scan_market(top_n=10)
    print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}]")
    print(top_stocks[['ticker', 'surge_probability']])
    time.sleep(3600)  # 1시간 대기
```

---

## 문제 해결

### "No data available"
- 인터넷 연결 확인
- 티커 심볼이 올바른지 확인
- yfinance 업데이트: `pip install -U yfinance`

### 학습 시간이 너무 오래 걸림
- `config.yaml`에서 `lookback_days` 줄이기 (365 → 180)
- 종목 수 줄이기
- `--train-dl` 옵션 제거 (머신러닝만)

### 예측 결과가 없음
- `config.yaml`의 `confidence_threshold` 낮추기 (0.7 → 0.5)
- 더 많은 종목 스캔 (`--top-n` 늘리기)

---

## 다음 단계

1. 자신만의 페니스톡 리스트 만들기
2. 새로운 기술적 지표 추가해보기
3. 모델 하이퍼파라미터 튜닝
4. 실제 거래 전략 개발 및 백테스팅

---

**중요**: 이 시스템은 투자 조언이 아닙니다. 반드시 본인의 판단으로 투자하세요!
