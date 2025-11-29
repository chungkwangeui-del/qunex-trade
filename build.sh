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
echo "✅ Build completed successfully!"
echo "================================"
echo "Note: Database tables will be created automatically when the app starts."
