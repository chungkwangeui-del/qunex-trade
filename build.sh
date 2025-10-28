#!/usr/bin/env bash
# Render build script

set -o errexit

# Install dependencies
pip install -r requirements.txt

echo "Build completed successfully!"
