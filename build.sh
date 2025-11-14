#!/usr/bin/env bash
# Render Master Build Script
# Installs all requirements for web, ml, and cron jobs

set -o errexit

echo "================================"
echo "QUNEX TRADE - Master Build"
echo "================================"

# 1. Root requirements
echo "📦 Installing root requirements..."
pip install -r requirements.txt

# 2. Web requirements (if exists)
if [ -f web/requirements.txt ]; then
    echo "🌐 Installing web requirements..."
    pip install -r web/requirements.txt
else
    echo "⚠️  web/requirements.txt not found, skipping"
fi

# 3. ML requirements (if exists)
if [ -f ml/requirements.txt ]; then
    echo "🤖 Installing ML requirements..."
    pip install -r ml/requirements.txt
else
    echo "⚠️  ml/requirements.txt not found, skipping"
fi

echo "================================"
echo "✓ Build completed successfully!"
echo "================================"

# 4. Initialize database (create tables if they don't exist)
if [ -f init_db.py ]; then
    echo "🗄️  Initializing database..."
    python init_db.py
else
    echo "⚠️  init_db.py not found, skipping database initialization"
fi

echo "================================"
echo "✅ All setup complete!"
echo "================================"
