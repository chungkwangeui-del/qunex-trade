# Qunex Trade - Kiwoom API Integration

## 시스템 리셋 완료 (2025-10-20)

모든 기존 데이터와 모델을 삭제하고 키움증권 Open API 통합을 위한 새로운 시작점입니다.

## 삭제된 항목

### 모델 파일
- ✅ God Model 관련 파일 전체 삭제
- ✅ Qunex Model 구버전 삭제
- ✅ Surge Predictor 구버전 삭제

### 데이터 파일
- ✅ penny_stocks_data.csv (모든 주식 데이터)
- ✅ 백테스트 결과 파일 전체
- ✅ 웹 시그널 데이터 (signals_today.csv, signals_history.csv)
- ✅ Korean tradeable tickers CSV

### 스크립트 파일
- ✅ 분석 스크립트 20+ 개 삭제
- ✅ train_god_model.py, backtest_god_model.py 삭제

## 유지된 항목

### 웹 애플리케이션
- ✅ web/ 디렉토리 전체 (Flask 앱)
- ✅ 유저 데이터베이스 및 인증 시스템
- ✅ 결제 시스템 (Stripe)
- ✅ 템플릿 및 UI

### 기타
- ✅ config.yaml
- ✅ main.py (core script)
- ✅ src/ 디렉토리 (필요시 수정 예정)

## 다음 단계: 키움 API 통합

### 1. 키움증권 Open API 신청
- [ ] 키움증권 HTS(영웅문) 설치
- [ ] Open API 신청 및 승인
- [ ] KOA Studio 설치

### 2. 개발 환경 설정
- [ ] Python 32-bit 설치 확인
- [ ] 필요한 라이브러리 설치
  ```bash
  pip install pywin32
  pip install pywinauto
  ```

### 3. 키움 API 연동 코드 작성
- [ ] 로그인 자동화
- [ ] 미국 주식 급등 랭킹 데이터 수집
- [ ] NASDAQ/NYSE 거래 가능 종목 필터링
- [ ] 실시간 데이터 수집 스크립트

### 4. 새로운 ML 모델 개발
- [ ] 키움 데이터 기반 피처 엔지니어링
- [ ] 새로운 급등주 예측 모델 학습
- [ ] 백테스트 시스템 재구축
- [ ] 웹 대시보드 연동

### 5. 웹사이트 재개
- [ ] 새 모델로 시그널 생성 테스트
- [ ] Maintenance 모드 해제
- [ ] 유저 알림 발송

## 현재 상태

- 🔧 **웹사이트**: Maintenance 모드 활성화
- 🗑️ **데이터**: 전체 삭제 완료
- 📁 **폴더 구조**: 클린 상태 (data/, models/, results/ 빈 폴더)
- ⏳ **다음 작업**: 키움 API 승인 대기 중

## 참고

- 기존 God Model은 완전히 삭제됨
- 키움 API 기반 새로운 모델로 완전 교체 예정
- 웹사이트 유저 데이터는 보존됨 (database.db)
