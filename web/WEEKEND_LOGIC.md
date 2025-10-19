# 주말 시그널 유지 로직

## 문제
- 금요일에 생성된 시그널이 다음날(토요일) 사라짐
- 실제로 거래는 월요일에 해야 하는데 시그널이 없음

## 해결 방법

### 1. Signal Generator - `get_next_trading_day()`

금요일 4:05 PM에 시그널 생성 시:
```python
def get_next_trading_day(self):
    """다음 거래일 계산 (주말 건너뛰기)"""
    today = datetime.now()
    next_day = today + timedelta(days=1)

    # 주말이면 월요일로
    while next_day.weekday() >= 5:  # 5=토, 6=일
        next_day += timedelta(days=1)

    return next_day.strftime('%Y-%m-%d')
```

**예시:**
- 금요일 (weekday=4) → 토요일(5) → 일요일(6) → **월요일(0)** ✓

### 2. Trade Date 설정

```python
signals_save['signal_date'] = today              # 금요일
signals_save['trade_date'] = next_trading_day    # 월요일!
```

### 3. 웹 대시보드 표시

`signals_today.csv`:
- 금요일 4:05 PM에 생성
- 토요일: signals_today.csv **그대로 유지**
- 일요일: signals_today.csv **그대로 유지**
- 월요일 4:05 PM: 새 시그널로 업데이트

### 4. 스케줄러 동작

```python
def is_market_day():
    today = datetime.now().weekday()
    return today < 5  # 월~금만 실행

# 토요일/일요일
if not is_market_day():
    logger.info("Weekend detected. Skipping daily process.")
    return  # 아무것도 안 함 → signals_today.csv 유지!
```

## 전체 타임라인

### 금요일 (10월 18일) 4:05 PM
```
✅ 시그널 생성
   signal_date: 2025-10-18
   trade_date: 2025-10-21 (월요일!)

✅ signals_today.csv 저장:
   RGTI, 97.2%, trade_date=2025-10-21
   IONQ, 96.8%, trade_date=2025-10-21
```

### 토요일 (10월 19일)
```
⏭️ 스케줄러: 주말 감지 → 스킵
📄 signals_today.csv: 그대로 유지
🌐 웹사이트: 금요일 시그널 계속 표시
```

### 일요일 (10월 20일)
```
⏭️ 스케줄러: 주말 감지 → 스킵
📄 signals_today.csv: 그대로 유지
🌐 웹사이트: 금요일 시그널 계속 표시
```

### 월요일 (10월 21일) 9:30 AM
```
💰 거래 실행!
   - RGTI 시가 매수
   - IONQ 시가 매수
```

### 월요일 (10월 21일) 4:00 PM
```
💰 거래 종료!
   - RGTI 종가 매도
   - IONQ 종가 매도
```

### 월요일 (10월 21일) 4:05 PM
```
✅ 1. 금요일 시그널 추적 → 결과 기록
✅ 2. 통계 업데이트
✅ 3. 화요일 시그널 생성
✅ 4. signals_today.csv 업데이트 (새 시그널)
```

## 핵심 포인트

1. **금요일 시그널 = 월요일 거래**
   - `trade_date`가 자동으로 월요일로 설정됨

2. **주말엔 아무것도 안 함**
   - 스케줄러 스킵
   - 파일 그대로 유지
   - 웹사이트는 금요일 시그널 계속 표시

3. **사용자 입장**
   - 금요일 오후: 시그널 확인
   - 주말: 시그널 유지 (언제 보든 표시됨)
   - 월요일 아침: 금요일 시그널로 거래
   - 월요일 저녁: 새 시그널 확인

## 코드 수정 완료 ✓

- ✅ `daily_signal_generator.py` - `get_next_trading_day()` 추가
- ✅ `scheduler.py` - `is_market_day()` 체크
- ✅ 금요일 → 월요일 자동 계산

## 테스트 방법

금요일에 수동 실행:
```bash
python web/daily_runner.py
```

출력 확인:
```
Signal date: 2025-10-18 (금요일)
Trade date: 2025-10-21 (월요일)  ← 확인!
```
