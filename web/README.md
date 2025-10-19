# God Model Web Dashboard

매일 자동으로 페니스톡 급등 시그널을 생성하고 추적하는 웹 대시보드입니다.

## 기능

### 1. 매일 4:05 PM 자동 실행 (한 번에 모두!)
- **시간**: 매일 오후 4:05 PM (미국 동부 시간) - 장 마감 후 5분
- **동작**:
  1. **어제 시그널 추적**: 실제 매매 결과 확인 (시가 매수, 종가 매도)
  2. **성공/실패 판정**:
     - SUCCESS: 50% 이상 급등
     - PARTIAL: 0-50% 수익
     - FAILED: 마이너스 수익
  3. **통계 자동 업데이트**: 성공률, 평균 수익률 계산
  4. **오늘 시그널 생성**: God 모델로 내일 급등주 예측 (임계값 0.95)
  5. **데이터베이스 저장**: 모든 결과 누적 저장

- **파일**:
  - `web/data/signals_today.csv` (오늘 시그널)
  - `web/data/signals_history.csv` (전체 히스토리 - 계속 쌓임)

### 2. 웹 대시보드
- **URL**: http://localhost:5000
- **표시 정보**:
  - 오늘의 시그널 (다음 거래일 예측)
  - 전체 통계 (성공률, 평균 수익률 등)
  - 최근 30일 성과
  - 실시간 업데이트 (5분마다 자동 새로고침)

## 설치 방법

1. 필요한 패키지 설치:
```bash
pip install -r web/requirements.txt
```

2. 데이터 폴더 생성:
```bash
mkdir web/data
mkdir web/logs
```

## 실행 방법

### 옵션 1: 수동 실행 (테스트용)

1. 시그널 생성:
```bash
python web/daily_signal_generator.py
```

2. 시그널 추적:
```bash
python web/signal_tracker.py
```

3. 웹 대시보드 실행:
```bash
python web/app.py
```

브라우저에서 http://localhost:5000 접속

### 옵션 2: 자동 스케줄러 (실전용)

1. 스케줄러 시작 (백그라운드):
```bash
python web/scheduler.py
```

2. 웹 대시보드 시작 (별도 터미널):
```bash
python web/app.py
```

스케줄러가 자동으로:
- 매일 오후 4:05 PM: 시그널 생성
- 매일 오전 9:00 AM: 시그널 추적

### 옵션 3: 윈도우 작업 스케줄러 (권장)

1. 작업 스케줄러 열기
2. "기본 작업 만들기" 클릭
3. 이름: "God Model Signal Generator"
4. 트리거: 매일 오후 4:05 PM
5. 작업: `python web/daily_signal_generator.py`
6. 완료

동일하게 "Signal Tracker" 작업도 생성 (오전 9:00 AM)

## 파일 구조

```
web/
├── daily_signal_generator.py  # 매일 시그널 생성
├── signal_tracker.py          # 시그널 추적 및 성과 기록
├── app.py                     # Flask 웹 애플리케이션
├── scheduler.py               # 자동 스케줄러
├── requirements.txt           # 필요한 패키지 목록
├── templates/
│   └── index.html            # 대시보드 HTML
├── data/
│   ├── signals_today.csv     # 오늘 시그널
│   └── signals_history.csv   # 전체 히스토리
└── logs/
    └── scheduler.log          # 스케줄러 로그
```

## 데이터 형식

### signals_history.csv
| 컬럼 | 설명 |
|------|------|
| ticker | 종목 티커 |
| predicted_probability | 예측 확률 (0.95~1.0) |
| signal_date | 시그널 생성 날짜 |
| trade_date | 거래 날짜 (다음 날) |
| status | pending/success/partial/failed |
| buy_price | 매수가 (시가) |
| sell_price | 매도가 (종가) |
| actual_return | 실제 수익률 (%) |
| Close | 시그널 생성 시점 종가 |

## API 엔드포인트

- `GET /` - 메인 대시보드
- `GET /api/signals/today` - 오늘 시그널 (JSON)
- `GET /api/signals/history` - 전체 히스토리 (JSON)
- `GET /api/statistics` - 통계 정보 (JSON)
- `GET /api/chart/daily_performance` - 일별 성과 차트 데이터

## 성능 지표

- **ROC-AUC**: 0.9789
- **성공률 (50%+ 급등)**: 70%+
- **전체 승률**: 72%+
- **평균 수익률**: 1,366%
- **중앙값 수익률**: 48.31%

## 주의사항

1. **시장 휴장일**: 주말과 공휴일에는 자동으로 스킵됩니다
2. **타임존**: 미국 동부 시간(ET) 기준으로 작동
3. **데이터 제한**: yfinance API 제한 주의 (1분당 2000 요청)
4. **백업**: signals_history.csv는 정기적으로 백업 권장

## 트러블슈팅

### 시그널이 생성 안 됨
- God 모델 파일 확인: `models/god_model_*.pkl`
- 피처 파일 확인: `models/god_model_features.pkl`
- 로그 확인: `web/logs/scheduler.log`

### 추적이 안 됨
- 인터넷 연결 확인
- yfinance 정상 작동 확인
- trade_date가 과거인지 확인

### 웹 대시보드 안 뜸
- Flask 설치 확인: `pip install flask`
- 포트 5000 사용 중인지 확인
- 방화벽 설정 확인

## 향후 개선 사항

- [ ] 이메일/SMS 알림 기능
- [ ] 브로커 API 연동 (자동 매매)
- [ ] 실시간 가격 업데이트
- [ ] 섹터별 분석 페이지
- [ ] 백테스트 시뮬레이터
- [ ] 포트폴리오 관리 기능
