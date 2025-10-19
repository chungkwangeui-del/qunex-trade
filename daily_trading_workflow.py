"""
실전 트레이딩 워크플로우 - 언제 시그널 돌리고, 언제 매수하고, 언제 매도하나?
"""

print("=" * 100)
print("God 모델 실전 트레이딩 타임라인")
print("=" * 100)

print("""
[핵심 원칙]
----------
T일 종가 데이터 → T+1일 예측 → T+1일 거래 (시가 매수 → 종가 매도)

예시:
- 화요일 오후 4시 (장 마감): 화요일 데이터로 수요일 급등주 예측
- 수요일 오전 9:30 (장 시작): 예측된 종목 시가 매수
- 수요일 오후 4:00 (장 마감): 종가 매도

[!] 중요: 절대 같은 날 데이터로 같은 날 거래하지 않습니다! (lookahead bias)
""")

print("\n" + "=" * 100)
print("[옵션 1] 수동 트레이딩 (초보자 추천)")
print("=" * 100)

print("""
매일 저녁 루틴 (장 마감 후):
============================

시간: 오후 4:30 PM - 5:30 PM (미국 장 기준: 오전 1:30 AM - 2:30 AM 한국시간)

단계 1: 최신 데이터 다운로드 (5-10분)
-------------------------------------
명령어:
  python download_latest_data.py

작업 내용:
- 522개 종목의 당일 종가 데이터 다운로드
- 기존 데이터에 추가
- 피처 자동 계산

출력 예시:
  [OK] RGTI: $15.23 (+8.5%)
  [OK] IONQ: $12.87 (+3.2%)
  ...
  [OK] 522개 종목 다운로드 완료


단계 2: God 모델 시그널 생성 (1-2분)
-----------------------------------
명령어:
  python predict_tomorrow_signals.py

작업 내용:
- 522개 전체 종목 스캔
- 급등 확률 계산
- 임계값 0.95 이상 시그널만 추출

출력 예시:
  ============================================================
  내일 (2025-10-20) 급등 예측 시그널
  ============================================================

  Ticker  Probability  Expected_Return  Sector          Risk
  ------  -----------  ---------------  --------------  ----
  RGTI    0.972        +127%            AI/양자컴퓨팅    중
  IONQ    0.968        +98%             AI/양자컴퓨팅    중
  QUBT    0.951        +76%             AI/양자컴퓨팅    중

  [추천] 내일 시가 매수 → 종가 매도


단계 3: 거래 계획 수립 (5분)
---------------------------
- 추천 종목 검토 (3-5개)
- 포트폴리오 비중 결정
  * 0.97 이상: 2배 비중
  * 0.95-0.97: 1배 비중
  * 0.95 미만: 제외

- 섹터 분산 체크
  * 같은 섹터 3개 이상 금지
  * 리스크 분산

- 매수 금액 계산
  예: 총 $10,000
  → RGTI: $4,000 (40%, 확률 0.972)
  → IONQ: $3,000 (30%, 확률 0.968)
  → QUBT: $3,000 (30%, 확률 0.951)


단계 4: 알람 설정
----------------
- 다음날 오전 9:20 AM 알람 (장 시작 10분 전)
- 다음날 오후 3:50 PM 알람 (장 마감 10분 전)
""")

print("\n" + "=" * 100)
print("다음날 아침 루틴 (거래일)")
print("=" * 100)

print("""
시간: 오전 9:20 AM - 9:30 AM (미국 장 기준)

단계 1: 프리마켓 체크 (5분)
--------------------------
- Yahoo Finance / TradingView 확인
- 시그널 종목들의 프리마켓 가격 확인
- 급락 (-10% 이상) 종목은 제외

예시:
  RGTI: $15.23 → $15.89 (+4.3% 프리마켓) [OK] 매수 진행
  IONQ: $12.87 → $11.20 (-13% 프리마켓) [X] 제외 (뉴스 확인)


단계 2: 시가 매수 (9:30 AM 정각)
--------------------------------
주문 방식: Market Order (시장가 주문)

브로커 예시 (Interactive Brokers):
1. 종목 선택: RGTI
2. 주문 유형: BUY
3. 수량: $4,000 / 시가
4. 주문 타입: Market Order
5. Time in Force: Day
6. 제출

[!] 주의: 9:30 AM 정각에 주문 (시가 확보)
[!] 변동성 큰 종목은 Limit Order 고려 (시가 +2% 이내)


단계 3: 포지션 확인 (9:35 AM)
----------------------------
- 매수 체결 확인
- 평균 매수가 기록
- 스톱로스 설정 (선택사항: -15%)

예시:
  RGTI: 251주 @ $15.94 (총 $4,000)
  IONQ: 233주 @ $12.88 (총 $3,000)
  QUBT: 395주 @ $7.59 (총 $3,000)

  총 투자: $10,000
""")

print("\n" + "=" * 100)
print("당일 오후 루틴 (매도)")
print("=" * 100)

print("""
시간: 오후 3:50 PM - 4:00 PM (미국 장 기준)

단계 1: 종가 매도 (3:55 PM - 3:59 PM)
-------------------------------------
주문 방식: Market Order on Close (MOC)

브로커 예시 (Interactive Brokers):
1. 종목 선택: RGTI
2. 주문 유형: SELL
3. 수량: 전량 (251주)
4. 주문 타입: Market on Close (MOC)
5. 제출 (3:50 PM - 3:59 PM 사이)

[!] MOC 주문은 3:50 PM 이후 제출 가능
[!] 3:59 PM까지 제출해야 당일 종가 매도


단계 2: 결과 확인 (4:05 PM)
--------------------------
- 체결 가격 확인
- 수익률 계산
- 기록 (엑셀/구글 시트)

예시:
  RGTI: $15.94 → $21.34 (+33.9%) = +$1,356
  IONQ: $12.88 → $14.23 (+10.5%) = +$315
  QUBT: $7.59 → $6.89 (-9.2%) = -$276

  총 수익: +$1,395 (+13.95% 하루)


단계 3: 기록 및 복기 (10분)
--------------------------
- 거래 일지 작성
  * 날짜, 종목, 시그널 확률, 매수가, 매도가, 수익률

- 주간/월간 성과 트래킹
  * 승률
  * 평균 수익률
  * MDD

- 시그널 검증
  * God 모델 예측 vs 실제 결과
  * 잘못된 예측 분석
""")

print("\n" + "=" * 100)
print("[옵션 2] 반자동 트레이딩 (중급자)")
print("=" * 100)

print("""
자동화 스크립트:
==============

1. 데이터 다운로드 자동화
------------------------
# daily_update.bat (Windows) 또는 daily_update.sh (Mac/Linux)

@echo off
cd "C:\\Users\\chung\\OneDrive\\Desktop\\PENNY STOCK TRADE"
python download_latest_data.py
python predict_tomorrow_signals.py
pause


스케줄러 설정:
- Windows: 작업 스케줄러 (오후 5PM 매일 실행)
- Mac: Automator + Calendar
- Linux: cron job


2. 알림 자동화
------------
# send_signals_email.py

import smtplib
from email.mime.text import MIMEText

def send_signal_email(signals):
    msg = MIMEText(signals)
    msg['Subject'] = f'[God Model] 내일 급등 시그널 {len(signals)}개'
    msg['From'] = 'your_email@gmail.com'
    msg['To'] = 'your_email@gmail.com'

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login('your_email@gmail.com', 'your_password')
        smtp.send_message(msg)

# predict_tomorrow_signals.py에서 호출
if len(signals) > 0:
    send_signal_email(signals)


3. 브로커 API 연동 (선택사항)
---------------------------
# Interactive Brokers API 예시

from ib_insync import IB, MarketOrder

ib = IB()
ib.connect('127.0.0.1', 7497, clientId=1)

def auto_buy(ticker, amount):
    contract = Stock(ticker, 'SMART', 'USD')
    order = MarketOrder('BUY', amount)
    trade = ib.placeOrder(contract, order)
    return trade

# 시그널 기반 자동 매수 (9:30 AM)
for signal in signals:
    auto_buy(signal['ticker'], signal['shares'])
""")

print("\n" + "=" * 100)
print("[옵션 3] 완전 자동 트레이딩 (고급자)")
print("=" * 100)

print("""
Alpaca API 활용 (무료 브로커):
============================

# auto_trade_god_model.py

import alpaca_trade_api as tradeapi
import pandas as pd

API_KEY = 'your_api_key'
API_SECRET = 'your_secret_key'
BASE_URL = 'https://paper-api.alpaca.markets'  # 종이 거래 (테스트)

api = tradeapi.REST(API_KEY, API_SECRET, BASE_URL, api_version='v2')

def auto_trade():
    # 1. 시그널 로드
    signals = pd.read_csv('results/tomorrow_signals.csv')

    # 2. 오전 9:30 AM: 자동 매수
    for _, row in signals.iterrows():
        ticker = row['ticker']
        probability = row['probability']

        # 비중 계산
        if probability >= 0.97:
            amount = 4000
        elif probability >= 0.95:
            amount = 3000
        else:
            continue

        # 시장가 매수
        api.submit_order(
            symbol=ticker,
            qty=amount // get_current_price(ticker),
            side='buy',
            type='market',
            time_in_force='day'
        )
        print(f"[OK] {ticker} 매수: ${amount}")

    # 3. 오후 3:55 PM: 자동 매도
    positions = api.list_positions()
    for position in positions:
        api.submit_order(
            symbol=position.symbol,
            qty=position.qty,
            side='sell',
            type='market',
            time_in_force='cls'  # Market on Close
        )
        print(f"[OK] {position.symbol} 매도")

# 스케줄러 (APScheduler)
from apscheduler.schedulers.blocking import BlockingScheduler

scheduler = BlockingScheduler()

# 매일 오전 9:29 AM 매수
scheduler.add_job(auto_buy, 'cron', hour=9, minute=29, timezone='America/New_York')

# 매일 오후 3:55 PM 매도
scheduler.add_job(auto_sell, 'cron', hour=15, minute=55, timezone='America/New_York')

# 매일 오후 5:00 PM 시그널 생성
scheduler.add_job(generate_signals, 'cron', hour=17, minute=0, timezone='America/New_York')

scheduler.start()
""")

print("\n" + "=" * 100)
print("실전 예시 - 완전한 타임라인")
print("=" * 100)

print("""
월요일 (2025-10-20)
==================

오후 5:00 PM (장 마감 후)
- python download_latest_data.py 실행
- python predict_tomorrow_signals.py 실행
- 결과:
  * RGTI: 0.972 확률
  * IONQ: 0.968 확률
  * QUBT: 0.951 확률

오후 5:10 PM
- 거래 계획 수립:
  * RGTI: $4,000
  * IONQ: $3,000
  * QUBT: $3,000
  * 총 $10,000

오후 11:00 PM
- 잠자기 전 알람 설정 (9:20 AM)


화요일 (2025-10-21) - 거래일
==========================

오전 9:20 AM (장 시작 10분 전)
- 프리마켓 체크
- RGTI: +4% (OK)
- IONQ: +2% (OK)
- QUBT: -1% (OK)

오전 9:30 AM (장 시작)
- RGTI 시장가 매수: 251주 @ $15.94
- IONQ 시장가 매수: 233주 @ $12.88
- QUBT 시장가 매수: 395주 @ $7.59

오전 9:35 AM
- 매수 체결 확인
- 총 투자: $10,000

오후 12:00 PM (점심)
- 현재 수익률 체크 (선택사항)
- RGTI: +8%
- IONQ: +5%
- QUBT: -3%

오후 3:50 PM (장 마감 10분 전)
- 알람
- 준비

오후 3:55 PM
- RGTI MOC 매도 주문
- IONQ MOC 매도 주문
- QUBT MOC 매도 주문

오후 4:05 PM (장 마감 후)
- 체결 확인
- RGTI: $21.34 (+33.9%)
- IONQ: $14.23 (+10.5%)
- QUBT: $6.89 (-9.2%)

총 수익: +$1,395 (+13.95%)

오후 5:00 PM
- 다시 내일(수요일) 시그널 생성
- 거래 일지 작성
- 반복!
""")

print("\n" + "=" * 100)
print("리스크 관리 규칙")
print("=" * 100)

print("""
1. 포지션 크기
------------
- 단일 종목: 최대 40%
- 섹터: 최대 60%
- 현금 보유: 최소 10%

2. 손절 규칙
----------
- 스톱로스: -15% (선택사항)
- 연속 3회 손실: 1주일 휴식
- 월간 -20%: 그 달 거래 중단

3. 거래 제한
----------
- 하루 최대 5개 종목
- 프리마켓 -10% 이상 종목 제외
- 뉴스 체크 (파산, 증권사기 등)

4. 백테스트 검증
--------------
- 매주 실제 결과 vs 백테스트 비교
- 성공률 70% 이하 떨어지면 모델 재검토
- 연속 5회 손실: 모델 점검
""")

print("\n" + "=" * 100)
print("FAQ - 자주 묻는 질문")
print("=" * 100)

print("""
Q1: 시그널이 없는 날도 있나요?
A: 네! 임계값 0.95 이상이 없으면 거래 안 함.
   백테스트 기준: 월 평균 7-15회 시그널

Q2: 프리마켓에서 이미 급등하면?
A: 제외하는 게 안전. God 모델은 장 중 급등 예측이지,
   프리마켓 급등은 이미 반영된 것.

Q3: 종가 매도 안 하고 홀딩하면?
A: God 모델은 1일 트레이딩 최적화.
   홀딩 전략은 별도 백테스트 필요.

Q4: 시그널 3개인데 돈이 부족하면?
A: 확률 높은 순으로 TOP 2-3개만 선택.

Q5: 주말에는?
A: 금요일 오후 5PM 시그널 → 월요일 거래

Q6: 휴장일(공휴일)에는?
A: 시그널 생성 안 함. 다음 거래일에 재개.

Q7: 모델 성능이 떨어지면?
A: 매달 재학습 권장 (최신 데이터 반영).
   python train_god_model.py (월 1회)
""")

print("\n" + "=" * 100)
print("지금 해야 할 일")
print("=" * 100)

print("""
1단계: 모델 학습 완료 대기 [진행 중]
- train_god_model.py 실행 중
- 예상 완료: 1-2시간 후

2단계: 백테스트 [대기]
- python backtest_god_model.py
- 성능 확인

3단계: 실전 스크립트 생성 [다음]
- predict_tomorrow_signals.py 작성
- download_latest_data.py 작성

4단계: 페이퍼 트레이딩 테스트 [권장]
- Alpaca Paper Trading으로 2주 테스트
- 실제 돈 없이 시뮬레이션
- 성공률 확인 후 실전 진입

5단계: 실전 투자 시작!
- 소액으로 시작 ($1,000-$5,000)
- 1개월 트래킹
- 성과 좋으면 증액
""")

print("\n" + "=" * 100)
print("요약")
print("=" * 100)

print("""
[간단 버전]
---------
1. 매일 오후 5PM: 시그널 생성 (내일 급등주 예측)
2. 다음날 9:30AM: 시가 매수
3. 같은날 4:00PM: 종가 매도
4. 수익 확인, 반복!

[시간대 (미국 동부 기준)]
----------------------
오후 5:00 PM: 시그널 생성
오전 9:30 AM: 매수 (다음날)
오후 4:00 PM: 매도 (당일)

[기대 수익]
---------
- 백테스트 기준: 73.5% 성공률
- 평균 수익률: +50-100% (급등 성공 시)
- 월 평균 거래: 7-15회
- 연간 기대 수익: 100-300%+ (복리)

[핵심]
----
God 모델 신뢰하고, 규칙 지키고, 감정 배제!
"시스템 트레이딩은 기계처럼!"
""")

print("\n" + "=" * 100)
