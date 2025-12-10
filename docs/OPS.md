# Ops & QA Checklist

Quick checklist to keep the app healthy and avoid surprises in prod.

## Required environment variables
- `SECRET_KEY`
- `DATABASE_URL` (PostgreSQL in prod)
- `POLYGON_API_KEY`
- `FINNHUB_API_KEY`
- `ALPHA_VANTAGE_API_KEY` (optional)
- `GEMINI_API_KEY` (optional, for offline news/QA jobs)
- `MAIL_USERNAME`, `MAIL_PASSWORD`
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` (optional)
- `RECAPTCHA_SECRET_KEY` (optional, enables reCAPTCHA)
- `ADMIN_PASSWORD` (must be non-default)
- `REDIS_URL` (optional; falls back to in-memory cache)

## Running tests on Windows + OneDrive desktop
PowerShell handles the localized Desktop path better via .NET:
```
Set-Location -LiteralPath ([Environment]::GetFolderPath('Desktop'))
Set-Location -LiteralPath 'PENNY STOCK TRADE'
python -m pytest
```

## CSP sanity check
Current CSP allows: `accounts.google.com`, `cdn.jsdelivr.net`, `fonts.googleapis.com`, `fonts.gstatic.com`, `unpkg.com`, `s3.tradingview.com`. If you add new external scripts/fonts, update `web/app.py` accordingly.

## DB schema changes
Set `AUTO_CREATE_TABLES=false` in prod and run migrations (Alembic recommended) instead of `db.create_all()`.

## Health/status check
- Start server and call `/api/status` to verify API keys, Redis, mail, DB:
  ```
  curl -s http://localhost:5000/api/status | jq .
  ```
- Confirm `ADMIN_PASSWORD` is set (non-default) and `POLYGON_API_KEY`/`FINNHUB_API_KEY` respond OK.

## Alembic quick-start (suggested)
- Install: `pip install alembic`.
- Init: `alembic init migrations`.
- In `alembic.ini`, set `sqlalchemy.url` or use env `DATABASE_URL`.
- In `migrations/env.py`, import models from `web.database`.
- Create migration: `alembic revision --autogenerate -m "describe change"`.
- Apply: `alembic upgrade head`.

## Offline ML/ETL pipeline
- Training/inference lives in `ml/` + `scripts/`.
- Cron/batch jobs write AI scores into the `ai_scores` table; web reads from DB only.
- Keep model artifacts in `ml/models/` and retrain via `scripts/train_multiframe_models.py` or `scripts/retrain_ml_model.py`.

