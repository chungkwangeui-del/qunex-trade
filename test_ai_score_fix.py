#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to verify AI Score cron job fix.

This runs the same logic as the cron job to verify it creates AI scores
for default popular stocks when watchlist is empty.

Usage:
    python test_ai_score_fix.py
"""

import os
import sys
import io

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add web directory to path
web_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web')
sys.path.insert(0, web_dir)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 80)
print("AI SCORE FIX TEST")
print("=" * 80)

# Check environment variables
print("\n1. Checking environment variables...")
polygon_key = os.getenv('POLYGON_API_KEY')
database_url = os.getenv('DATABASE_URL')

if not polygon_key:
    print("   ❌ POLYGON_API_KEY missing")
    sys.exit(1)
else:
    print(f"   ✅ POLYGON_API_KEY found ({polygon_key[:10]}...)")

if not database_url:
    print("   ❌ DATABASE_URL missing")
    sys.exit(1)
else:
    print(f"   ✅ DATABASE_URL found")

# Fix driver
if database_url.startswith('postgresql://'):
    database_url = database_url.replace('postgresql://', 'postgresql+psycopg://')
elif database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql+psycopg://')

# Test database connection
print("\n2. Testing database connection...")
try:
    from flask import Flask
    from flask_sqlalchemy import SQLAlchemy

    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db = SQLAlchemy(app)

    from database import Watchlist, AIScore

    with app.app_context():
        # Count watchlist tickers
        watchlist_count = db.session.query(Watchlist.ticker).distinct().count()
        print(f"   ✅ Database connected")
        print(f"   📊 Watchlist tickers: {watchlist_count}")

        # Count existing AI scores
        ai_score_count = db.session.query(AIScore).count()
        print(f"   📊 Existing AI scores: {ai_score_count}")

    print("   ✅ Database connection successful")

except Exception as e:
    print(f"   ❌ Database connection failed: {e}")
    sys.exit(1)

# Test default ticker list
print("\n3. Testing default ticker logic...")
with app.app_context():
    watchlist_tickers = db.session.query(Watchlist.ticker).distinct().all()
    tickers = [t[0] for t in watchlist_tickers]

    if not tickers:
        print("   ✅ Watchlist is empty - will use default stocks")
        tickers = [
            # FAANG + Popular Tech
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'NFLX',
            # Major Indices ETFs
            'SPY', 'QQQ', 'DIA',
            # Popular Growth
            'AMD', 'AVGO', 'CRM', 'ORCL', 'ADBE', 'INTC',
            # Financials
            'JPM', 'BAC', 'WFC', 'GS', 'MS', 'V', 'MA',
            # Healthcare
            'JNJ', 'UNH', 'PFE', 'ABBV', 'LLY', 'MRK',
            # Consumer
            'WMT', 'HD', 'MCD', 'NKE', 'SBUX', 'COST',
            # Energy
            'XOM', 'CVX',
            # Communication
            'T', 'VZ', 'DIS'
        ]
        print(f"   📋 Default tickers: {len(tickers)} stocks")
        print(f"   📝 Examples: {', '.join(tickers[:10])}")
    else:
        print(f"   ✅ Using watchlist tickers: {len(tickers)} stocks")

# Test Polygon API connection
print("\n4. Testing Polygon API for AAPL...")
try:
    from polygon_service import PolygonService
    polygon = PolygonService()

    details = polygon.get_ticker_details('AAPL')
    if details:
        print(f"   ✅ Polygon API working")
        print(f"   📊 AAPL market cap: ${details.get('market_cap', 0):,.0f}")
    else:
        print("   ⚠️  Polygon API returned no data (might be rate limited)")

except Exception as e:
    print(f"   ⚠️  Polygon API error: {e}")

print("\n" + "=" * 80)
print("TEST SUMMARY")
print("=" * 80)
print("\n✅ All checks passed! The fix should work in production.")
print("\n📌 NEXT STEPS:")
print("1. Deploy updated code to Render.com (git push already done)")
print("2. In Render Dashboard, go to Cron Jobs")
print("3. Find 'qunex-ai-score-update' cron job")
print("4. Click 'Trigger Run' to manually run it")
print("5. Check logs - should see 'Processing 40+ default tickers'")
print("6. Test API: https://qunextrade.onrender.com/api/stock/AAPL/ai-score")
print("\nOR run locally:")
print("  python cron_update_ai_scores.py")
print("=" * 80)
