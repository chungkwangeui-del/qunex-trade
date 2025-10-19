# Qunex Trade - Deployment Guide

## 배포 방법 (Public Website 만들기)

### 옵션 1: Render (추천 - 무료, 가장 쉬움)

**장점:**
- 완전 무료 (Free tier)
- 설정 간단
- GitHub 연동 자동 배포
- HTTPS 자동 제공

**단계:**

1. **GitHub에 코드 업로드**
   ```bash
   cd "c:\Users\chung\OneDrive\바탕 화면\PENNY STOCK TRADE"
   git init
   git add .
   git commit -m "Initial commit - Qunex Trade"

   # GitHub에서 새 repository 만들기 (qunex-trade)
   git remote add origin https://github.com/YOUR_USERNAME/qunex-trade.git
   git push -u origin main
   ```

2. **Render 계정 만들기**
   - https://render.com 접속
   - GitHub 계정으로 로그인

3. **새 Web Service 만들기**
   - Dashboard → "New +" → "Web Service"
   - GitHub repository 연결 (qunex-trade)
   - 설정:
     - **Name**: qunex-trade
     - **Environment**: Python 3
     - **Build Command**: `pip install -r web/requirements.txt`
     - **Start Command**: `cd web && gunicorn app:app`
     - **Plan**: Free

4. **배포 완료!**
   - 자동으로 빌드 & 배포
   - URL: `https://qunex-trade.onrender.com`

---

### 옵션 2: Railway (무료, 쉬움)

**장점:**
- 무료 $5 credit/month
- 빠른 배포
- 자동 HTTPS

**단계:**

1. GitHub에 코드 업로드 (위와 동일)

2. **Railway 계정 만들기**
   - https://railway.app 접속
   - GitHub 로그인

3. **New Project**
   - "Deploy from GitHub repo"
   - qunex-trade 선택
   - 자동으로 Python 감지 & 배포

4. **URL**: `https://qunex-trade.up.railway.app`

---

### 옵션 3: PythonAnywhere (무료, 쉬움)

**장점:**
- 완전 무료 플랜
- Python 전문 호스팅
- 간단한 설정

**단계:**

1. **계정 만들기**: https://www.pythonanywhere.com

2. **Files 탭에서 코드 업로드**
   - Zip 파일로 압축 후 업로드
   - 또는 GitHub에서 clone

3. **Web 탭에서 Flask 앱 설정**
   - Add a new web app
   - Flask 선택
   - Python 3.11 선택
   - WSGI 파일 설정

4. **URL**: `https://YOUR_USERNAME.pythonanywhere.com`

---

### 옵션 4: Heroku (유료, 가장 안정적)

**참고**: Heroku는 무료 플랜이 종료되어 월 $5부터 시작합니다.

**단계:**

1. GitHub에 코드 업로드

2. **Heroku 계정 & CLI 설치**
   - https://heroku.com
   - Heroku CLI 설치

3. **배포**
   ```bash
   heroku login
   heroku create qunex-trade
   git push heroku main
   ```

4. **URL**: `https://qunex-trade.herokuapp.com`

---

## 추천 배포 플랫폼

### 🏆 1위: Render
- 완전 무료
- 가장 쉬움
- 안정적
- **추천!**

### 🥈 2위: Railway
- 무료 크레딧
- 매우 빠름
- 좋은 UI

### 🥉 3위: PythonAnywhere
- 완전 무료
- Python 전문
- 약간 느림

---

## 배포 후 확인사항

1. **모델 파일 크기**
   - `models/` 폴더가 너무 크면 Git LFS 사용
   - 또는 배포 시 모델 다시 학습

2. **환경변수 설정** (필요시)
   - API keys
   - Secret keys

3. **도메인 연결** (선택)
   - Render에서 커스텀 도메인 연결 가능
   - 예: www.qunextrade.com

---

## 파일 설명

- **render.yaml**: Render 배포 설정
- **Procfile**: Heroku/Railway 배포 설정
- **web/requirements.txt**: Python 패키지 목록
- **web/app.py**: Flask 웹 애플리케이션

---

## 문제 해결

### 배포 후 500 에러
- 로그 확인: Render Dashboard → Logs
- 모델 파일 경로 확인
- 환경변수 확인

### 모델 로드 실패
- 모델 파일 크기가 너무 큼
- Git LFS 사용하거나 S3/클라우드 스토리지 사용

### 무료 플랜 제한
- Render Free: 15분 inactivity 후 sleep
- Railway: $5/month 크레딧 소진 시 중단
- PythonAnywhere: CPU/메모리 제한

---

## 다음 단계

1. GitHub repository 만들기
2. Render 계정 만들기
3. Repository 연결 & 배포
4. URL 공유하기!

**예상 소요 시간**: 15-30분
**비용**: $0 (무료)
