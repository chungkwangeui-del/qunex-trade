#!/usr/bin/env bash
# Render build script

set -o errexit

# Install dependencies
pip install -r requirements.txt

# Initialize database
cd web
python create_db.py
cd ..

echo "Build completed successfully!"
