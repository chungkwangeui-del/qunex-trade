# Qunex Trade - Monetization Implementation Guide

## 🎉 수익화 시스템 구축 완료!

이 가이드는 Qunex Trade의 수익화 시스템을 설정하고 활성화하는 방법을 설명합니다.

---

## 📋 구현된 기능

### ✅ 1. 사용자 인증 시스템
- **Flask-Login** 기반 인증
- 회원가입/로그인/로그아웃
- 데이터베이스: SQLite (qunextrade.db)
- 비밀번호 암호화 (Werkzeug)

### ✅ 2. Freemium 모델
**무료 (Free) 티어:**
- 하루 3개 시그널만 표시
- 7일 히스토리
- 기본 통계
- 광고 표시 (AdSense)

**Pro 티어 ($19.99/월):**
- 무제한 시그널
- 30일 히스토리
- 이메일 알림
- CSV 다운로드
- 우선 지원

**Premium 티어 ($49.99/월):**
- Pro 기능 전체
- API 접근
- 텔레그램 봇
- 실시간 알림
- 커스텀 임계값

### ✅ 3. Stripe 결제 통합
- 구독 관리
- 자동 청구
- 취소 기능
- Webhook 지원

### ✅ 4. 새로운 페이지
- `/pricing` - 가격 페이지
- `/auth/login` - 로그인
- `/auth/signup` - 회원가입
- `/auth/account` - 계정 관리
- `/payments/subscribe/<tier>` - 구독
- `/terms` - 이용약관 (TODO)
- `/privacy` - 개인정보처리방침 (TODO)

---

## 🚀 활성화 방법

### Step 1: 기존 Flask 앱 백업

```bash
# 현재 app.py를 백업
mv web/app.py web/app_original.py

# 수익화 버전으로 교체
mv web/app_monetized.py web/app.py
```

### Step 2: 필요한 패키지 설치

```bash
cd web
pip install -r requirements.txt
```

**새로 추가된 패키지:**
- flask-login==0.6.3
- flask-sqlalchemy==3.1.1
- werkzeug==3.0.0
- stripe==7.0.0

### Step 3: 환경 변수 설정

`.env` 파일 생성:

```bash
# Flask 비밀 키 (보안!)
SECRET_KEY=your-super-secret-key-change-this

# Stripe 키 (나중에 설정)
STRIPE_PUBLIC_KEY=pk_test_YOUR_KEY_HERE
STRIPE_SECRET_KEY=sk_test_YOUR_KEY_HERE
```

**비밀 키 생성:**
```python
import secrets
print(secrets.token_hex(32))
```

### Step 4: 데이터베이스 초기화

```bash
cd web
python -c "from app_monetized import app, db; app.app_context().push(); db.create_all(); print('Database created!')"
```

### Step 5: 테스트 실행

```bash
cd web
python app.py
```

브라우저에서 접속:
```
http://localhost:5000
```

---

## 💳 Stripe 설정 (나중에)

### 1. Stripe 계정 만들기
- https://stripe.com
- 회원가입
- Dashboard 접속

### 2. API 키 받기
- Dashboard → Developers → API keys
- **Publishable key** (pk_test_...) 복사
- **Secret key** (sk_test_...) 복사

### 3. 환경 변수 설정
```bash
STRIPE_PUBLIC_KEY=pk_test_실제키로변경
STRIPE_SECRET_KEY=sk_test_실제키로변경
```

### 4. Webhook 설정
- Dashboard → Developers → Webhooks
- Endpoint URL: `https://qunextrade.com/payments/webhook`
- Events: `customer.subscription.created`, `customer.subscription.deleted`

---

## 📊 제휴 마케팅 설정

### 1. Robinhood 제휴
- https://robinhood.com/us/en/about/affiliates/
- 신청 후 제휴 링크 받기

### 2. Webull 제휴
- https://www.webull.com/activity
- 제휴 프로그램 가입

### 3. 링크 추가
템플릿에 제휴 링크 추가:
```html
<a href="제휴링크" target="_blank">
    Open Trading Account (Get $10 Free)
</a>
```

---

## 🎯 Google AdSense 설정

### 1. AdSense 계정
- https://www.google.com/adsense
- 신청 (승인까지 1-2주)

### 2. 광고 코드 추가
템플릿 `<head>` 태그에:
```html
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-YOUR-ID"
     crossorigin="anonymous"></script>
```

### 3. 광고 단위 삽입
```html
<ins class="adsbygoogle"
     style="display:block"
     data-ad-client="ca-pub-YOUR-ID"
     data-ad-slot="YOUR-SLOT-ID"
     data-ad-format="auto"></ins>
<script>
     (adsbygoogle = window.adsbygoogle || []).push({});
</script>
```

---

## 📈 예상 수익 (12개월)

### 보수적 추정:
```
Month 1-3:
- 100 무료 사용자
- 광고 수익: $50-100/월

Month 4-6:
- 500 무료 사용자
- 10명 Pro 구독 × $19.99 = $199.90/월
- 광고: $200/월
- 제휴: $300/월
- 총: $700/월

Month 7-12:
- 1,000 무료 사용자
- 30명 Pro × $19.99 = $599.70/월
- 5명 Premium × $49.99 = $249.95/월
- 광고: $500/월
- 제휴: $700/월
- 총: $2,050/월

Year 1 총 수익: $12,000-18,000
```

### 공격적 추정:
```
- 5,000 무료 사용자
- 100명 Pro = $1,999/월
- 20명 Premium = $999/월
- 광고 + 제휴: $2,000/월
- 총: $5,000/월 ($60,000/년)
```

---

## 🔒 보안 체크리스트

- [ ] SECRET_KEY 환경 변수 설정
- [ ] Stripe 키 환경 변수로 관리
- [ ] HTTPS 필수 (Render 자동 제공)
- [ ] SQL Injection 방지 (SQLAlchemy 사용)
- [ ] XSS 방지 (Flask 기본 제공)
- [ ] CSRF 보호 (Flask-WTF 추천)
- [ ] 비밀번호 암호화 (Werkzeug 사용)
- [ ] 환경 변수 .gitignore에 추가

---

## 📝 법적 문서 (필수!)

### 이용약관 (Terms of Service)
- 템플릿: `web/templates/terms.html` (TODO)
- 내용: 서비스 사용 조건, 책임 한계

### 개인정보처리방침 (Privacy Policy)
- 템플릿: `web/templates/privacy.html` (TODO)
- 내용: 데이터 수집, 사용, 보관 정책

### 면책조항 (Disclaimer)
- 이미 About 페이지에 포함됨 ✅
- "투자 조언이 아님" 명시

---

## 🌐 배포 (Render)

### 1. .gitignore 업데이트
```
*.db
*.sqlite
.env
web/qunextrade.db
```

### 2. GitHub 푸시
```bash
git add .
git commit -m "Add monetization features"
git push origin main
```

### 3. Render 환경 변수 설정
Dashboard → Environment → Add Environment Variable:
```
SECRET_KEY=실제비밀키
STRIPE_PUBLIC_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
```

### 4. 자동 재배포
- Render가 자동으로 재배포
- 5-10분 소요

---

## 🎉 완료 후 확인사항

✅ 회원가입 작동
✅ 로그인 작동
✅ 무료 사용자는 3개 시그널만 표시
✅ Pricing 페이지 표시
✅ Pro 구독 시뮬레이션 작동
✅ 업그레이드 배너 표시

---

## 💰 다음 단계 (우선순위)

1. **즉시 (이번 주):**
   - [ ] Terms of Service 페이지 작성
   - [ ] Privacy Policy 페이지 작성
   - [ ] Google AdSense 신청
   - [ ] Robinhood/Webull 제휴 신청

2. **단기 (이번 달):**
   - [ ] Stripe 실제 키로 교체
   - [ ] 결제 테스트
   - [ ] 이메일 알림 구현
   - [ ] CSV 다운로드 기능

3. **중기 (3개월):**
   - [ ] API 엔드포인트 개발
   - [ ] 텔레그램 봇 연동
   - [ ] 실시간 알림
   - [ ] 분석 대시보드

4. **장기 (6개월):**
   - [ ] 모바일 앱
   - [ ] 교육 콘텐츠 판매
   - [ ] Enterprise 플랜
   - [ ] 화이트라벨 솔루션

---

## 🆘 문제 해결

### Q: 데이터베이스 에러
```bash
rm web/qunextrade.db
python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

### Q: Stripe 테스트 카드
```
카드 번호: 4242 4242 4242 4242
만료일: 미래 날짜
CVC: 아무 3자리
ZIP: 아무 5자리
```

### Q: 로그인 안 됨
- 비밀번호 최소 6자 이상
- 이메일 형식 확인
- 브라우저 캐시 삭제

---

## 📧 지원

문제가 있으면:
1. 로그 확인: Render Dashboard → Logs
2. 로컬 테스트: `python web/app.py`
3. 데이터베이스 확인: `sqlite3 web/qunextrade.db`

---

**축하합니다! 수익화 시스템 구축 완료!** 🎉

이제 사용자를 모으고 수익을 창출할 준비가 되었습니다!
