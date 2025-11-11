# Qunex Trade - Cloud-Native Deployment Guide

**Date:** 2025-11-11
**Platform:** Render.com (100% Free Tier)

---

## 🎯 Architecture Overview

### Stateless Cloud-Native Design

```
┌─────────────────────────────────────────────┐
│          Render.com (Free Tier)             │
├─────────────────────────────────────────────┤
│                                             │
│  Web Service (Flask + Gunicorn)            │
│  ├─ Auto-scaling                           │
│  ├─ Zero downtime deploys                  │
│  └─ Connected to PostgreSQL + Redis        │
│                                             │
│  Cron Job (Data Refresh)                   │
│  ├─ Runs every hour                        │
│  ├─ Fetches news from APIs                 │
│  ├─ Analyzes with Claude AI                │
│  └─ Stores in PostgreSQL                   │
│                                             │
│  (No database - uses external Supabase)    │
│                                             │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│          External Services (Free)           │
├─────────────────────────────────────────────┤
│                                             │
│  Supabase PostgreSQL (Permanent Free)     │
│  ├─ Users, payments, watchlists            │
│  ├─ News articles with AI analysis         │
│  └─ Economic calendar events               │
│                                             │
│  Upstash Redis (Free)                      │
│  └─ Distributed rate limiting              │
│                                             │
│  Polygon.io API                            │
│  └─ Real-time market data                  │
│                                             │
│  Anthropic Claude API                      │
│  └─ News analysis                          │
│                                             │
└─────────────────────────────────────────────┘
```

---

## 📋 Prerequisites

### 1. Render.com Account
- Sign up at https://render.com (free)
- Connect your GitHub account

### 2. Supabase Account (Permanent Free PostgreSQL)
- Sign up at https://supabase.com (free)
- Create a new project
- Go to Project Settings → Database → Connection string
- Copy the **URI** (starts with `postgres://` or `postgresql://`)
- This is your `DATABASE_URL`

### 3. Upstash Redis (Free)
- Sign up at https://upstash.com
- Create a Redis database
- Copy the Redis URL

### 4. API Keys
- **Polygon.io:** https://polygon.io (get API key)
- **Anthropic:** https://console.anthropic.com (get API key)
- **NewsAPI:** https://newsapi.org (get API key)

---

## 🚀 Step-by-Step Deployment

### Step 1: Push Code to GitHub

```bash
git add -A
git commit -m "Cloud-native refactoring complete"
git push origin main
```

### Step 2: Create Render Services

#### A. Create Web Service

1. Go to https://dashboard.render.com
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Configuration:
   - **Name:** qunex-trade
   - **Region:** Oregon (US West)
   - **Branch:** main
   - **Runtime:** Python 3
   - **Build Command:** `bash build.sh`
   - **Start Command:** `cd web && gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`
   - **Plan:** Free

#### B. Create Cron Job

1. Click "New +" → "Cron Job"
2. Configuration:
   - **Name:** qunex-data-refresh
   - **Region:** Oregon
   - **Branch:** main
   - **Schedule:** `0 * * * *` (every hour)
   - **Build Command:** `pip install -r requirements.txt && pip install -r web/requirements.txt`
   - **Start Command:** `python scripts/refresh_data_cron.py`
   - **Plan:** Free

### Step 3: Configure Environment Variables

In Render Dashboard → Web Service → Environment:

```bash
# Database (from Supabase - see Prerequisites step 2)
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@[YOUR-PROJECT].supabase.co:5432/postgres

# Redis (from Upstash)
REDIS_URL=rediss://default:password@hostname:port

# API Keys
POLYGON_API_KEY=your_polygon_api_key
NEWSAPI_KEY=your_newsapi_key
ANTHROPIC_API_KEY=your_anthropic_api_key

# Email (Gmail)
MAIL_USERNAME=your_gmail@gmail.com
MAIL_PASSWORD=your_gmail_app_password

# reCAPTCHA
RECAPTCHA_SECRET_KEY=your_recaptcha_secret

# Google OAuth (optional)
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# Stripe (optional)
STRIPE_SECRET_KEY=your_stripe_secret_key
STRIPE_PUBLISHABLE_KEY=your_stripe_publishable_key

# Flask
SECRET_KEY=auto-generated-by-render

# Background threads (must be false for stateless)
ENABLE_BACKGROUND_THREAD=false
```

### Step 4: Initialize Database

After first deployment, run once:

```bash
# SSH into Render shell or use Render Console
python scripts/init_database.py
```

This creates all database tables.

### Step 5: Test Cron Job

Manually trigger the cron job once:

```bash
python scripts/refresh_data_cron.py
```

Verify news and calendar data appear in database.

---

## 🔄 How It Works

### 1. Web Service (Stateless)

- **No local files:** All data in PostgreSQL
- **No threading:** Background tasks handled by Cron Job
- **Distributed rate limiting:** Uses Redis (Upstash)
- **Auto-scaling:** Render can spawn multiple instances

### 2. Cron Job (Scheduled Tasks)

- **Runs every hour**
- **Fetches news** from NewsAPI
- **Analyzes news** with Claude AI
- **Updates database** with latest data
- **Cleans old data** (keeps last 30 days)

### 3. PostgreSQL Database

#### Tables:
- `user` - User accounts
- `payment` - Payment history
- `watchlist` - User watchlists
- `saved_screener` - Saved screener criteria
- `news_articles` - News with AI analysis
- `economic_events` - Economic calendar

### 4. Redis (Upstash)

- **Rate limiting** storage
- **Session management** (optional)
- **Distributed across** multiple web instances

---

## 📊 Monitoring

### Render Dashboard

- **Logs:** Real-time application logs
- **Metrics:** CPU, memory, request count
- **Events:** Deployment history
- **Health Checks:** Auto-restart on failure

### Cron Job Logs

Check cron job execution:
```
Render Dashboard → Cron Job → Logs
```

Expected output:
```
================================================================================
RENDER CRON JOB: Data Refresh Started
================================================================================
2025-11-11 12:00:00 - INFO - Starting news refresh...
2025-11-11 12:00:05 - INFO - Collected 25 articles
2025-11-11 12:00:30 - INFO - Saved 10 new articles to database
2025-11-11 12:00:30 - INFO - Deleted 5 old articles
================================================================================
CRON JOB COMPLETED in 30.45 seconds
News: ✓ SUCCESS
Calendar: ✓ SUCCESS
================================================================================
```

---

## 🛠️ Local Development

### Run with SQLite (Development)

```bash
# Don't set DATABASE_URL - uses SQLite automatically
python web/app.py
```

### Run with PostgreSQL (Production-like)

```bash
# Set DATABASE_URL in .env
DATABASE_URL=postgresql://localhost/qunex_trade_dev
python web/app.py
```

### Test Cron Job Locally

```bash
python scripts/refresh_data_cron.py
```

---

## 🔐 Security Checklist

- ✅ PostgreSQL password auto-generated by Render
- ✅ Redis password required (Upstash)
- ✅ All API keys in environment variables
- ✅ .env file in .gitignore
- ✅ HTTPS enforced by Render
- ✅ CSRF protection enabled
- ✅ Rate limiting with Redis
- ✅ Session cookies secure (HTTPS-only)

---

## 💰 Cost Breakdown

### 100% Free Tier (Permanent!)

| Service | Plan | Cost | Limit |
|---------|------|------|-------|
| Render Web Service | Free | $0/month | 750 hrs/month |
| Render Cron Job | Free | $0/month | Unlimited |
| Supabase PostgreSQL | Free | $0/month | **Permanent** ✓ |
| Upstash Redis | Free | $0/month | 10K cmds/day |
| **Total** | | **$0/month** | **Forever** |

### Why This Stack?

- ✅ **Permanent Free Database:** Supabase PostgreSQL (no 90-day limit)
- ✅ **Unlimited Cron Jobs:** Render free tier
- ✅ **Auto-scaling:** Render web service
- ✅ **No credit card required:** For all services

---

## 🐛 Troubleshooting

### Issue: App not starting

**Check:**
1. Build logs for errors
2. Environment variables set correctly
3. DATABASE_URL format correct

### Issue: Rate limiting not working

**Check:**
1. REDIS_URL set in environment
2. Upstash Redis accessible
3. Logs show "Rate limiting using Redis"

### Issue: News not updating

**Check:**
1. Cron job running (check logs)
2. API keys valid (NEWSAPI, ANTHROPIC)
3. Database tables created

### Issue: Database connection errors

**Check:**
1. PostgreSQL service running
2. DATABASE_URL starts with `postgresql://` (not `postgres://`)
3. Database tables initialized

---

## 📚 Additional Resources

- **Render Docs:** https://render.com/docs
- **Upstash Docs:** https://docs.upstash.com
- **Flask Docs:** https://flask.palletsprojects.com
- **PostgreSQL Docs:** https://www.postgresql.org/docs

---

## 🔄 Updates & Maintenance

### Deploy Updates

```bash
git add -A
git commit -m "Your changes"
git push origin main
```

Render automatically deploys on push to `main` branch.

### Database Migrations

If you add new models:

1. Update `web/database.py`
2. Run migration script:
```bash
python scripts/init_database.py
```

### Scale Up (Optional)

If traffic increases:
- Upgrade to Render Standard ($7/month)
- Increase Gunicorn workers
- Add more Render instances

---

**Status:** ✅ Production-Ready
**Last Updated:** 2025-11-11
**Deployment:** Render.com Free Tier
