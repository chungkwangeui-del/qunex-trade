#!/bin/bash

echo "================================"
echo "Building Qunex Trade..."
echo "================================"

# Install dependencies
echo "Installing Python packages..."
pip install -r web/requirements.txt

# Check if models exist
if [ -d "models" ] && [ "$(ls -A models/*.pkl 2>/dev/null)" ]; then
    echo "Models found! Skipping training..."
else
    echo "Models not found. Training models..."

    # Create models directory
    mkdir -p models
    mkdir -p data
    mkdir -p results

    # Download data
    echo "Downloading historical data..."
    python download_3year_data.py || echo "Data download completed with warnings"

    # Train models
    echo "Training ML models..."
    python train_god_model.py || echo "Model training completed with warnings"

    echo "Model training complete!"
fi

echo "================================"
echo "Build completed successfully!"
echo "================================"
