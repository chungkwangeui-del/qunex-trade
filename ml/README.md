# Qunex AI Score - Machine Learning System

## Overview

The Qunex AI Score is an ML-based stock scoring system (0-100) that predicts stock performance using real historical data.

## How It Works

### 1. Data Collection
- Downloads 8+ years of historical price data for 100 S&P 500 stocks from Polygon.io API
- Date range: 2016-01-01 to 2023-12-31 (training data)
- Validation data: 2024 (holdout set, never seen during training)

### 2. Feature Engineering (25+ Technical Indicators)

**Price & Moving Averages:**
- MA 20, 50, 200
- Price position relative to MAs
- MA slope/trend

**Momentum Indicators:**
- RSI (14-day)
- MACD + Signal + Histogram
- Price returns (1d, 5d, 20d, 60d)

**Volatility:**
- Bollinger Bands position & width
- ATR (Average True Range)
- 20-day volatility (annualized)

**Volume:**
- Volume MA (20-day)
- Volume ratio (current vs average)

### 3. Label Generation

Based on **forward 20-day returns**, stocks are classified into 5 categories:

| Label | Forward Return | AI Score Range |
|-------|---------------|----------------|
| Strong Buy | > +10% | 75-100 |
| Buy | +5% to +10% | 60-74 |
| Hold | -5% to +5% | 40-59 |
| Sell | -10% to -5% | 25-39 |
| Strong Sell | < -10% | 0-24 |

### 4. Model Training

**Algorithm:** XGBoost Classifier
- 200 trees
- Max depth: 6
- Learning rate: 0.1
- Multi-class classification (5 classes)

**Training Split:**
- 80% training
- 20% validation
- Stratified by label to ensure balanced classes

### 5. Prediction

For a given stock, the model:
1. Calculates all 25+ technical features from recent price data
2. Feeds features into trained XGBoost model
3. Gets probability distribution across 5 classes
4. Converts to 0-100 score using weighted average:
   - Score = (P_strong_sell × 0) + (P_sell × 25) + (P_hold × 50) + (P_buy × 75) + (P_strong_buy × 100)

## Training the Model

### Prerequisites

```bash
# Install dependencies
cd ml
pip install -r requirements.txt
```

### Run Training

```bash
# Full training (100 stocks, 8 years of data)
python train_ai_score.py

# Custom date range
python train_ai_score.py --start-date 2015-01-01 --end-date 2023-12-31

# Specific symbols
python train_ai_score.py --symbols AAPL MSFT NVDA TSLA
```

### What Happens During Training

1. **Data Download** (~30-60 minutes)
   - Downloads historical daily OHLCV data from Polygon.io
   - Processes ~100 stocks × ~2000 trading days = 200,000+ samples

2. **Feature Calculation** (~10 minutes)
   - For each trading day, calculates 25+ technical indicators
   - Creates training samples with features + labels

3. **Model Training** (~5 minutes)
   - Trains XGBoost on prepared dataset
   - Validates on holdout set
   - Prints accuracy metrics

4. **Model Saving**
   - Saves trained model to `models/ai_score_model.pkl`
   - Includes model, scaler, and feature names

### Expected Output

```
================================================================================
QUNEX AI SCORE MODEL TRAINING
================================================================================

STEP 1: COLLECTING HISTORICAL DATA
Downloading data: 100%|██████████| 100/100 [45:23<00:00, 27.23s/it]
Total samples: 187,432

STEP 2: PREPARING FEATURES AND LABELS
Feature matrix shape: (187432, 25)
Label distribution:
  Strong Sell    8,234 ( 4.4%)
  Sell          22,156 (11.8%)
  Hold         127,845 (68.2%)
  Buy           24,891 (13.3%)
  Strong Buy     4,306 ( 2.3%)

STEP 3: TRAINING MODEL
Model accuracy: 0.7234

Classification Report:
              precision    recall  f1-score   support
Strong Sell       0.68      0.45      0.54      1647
Sell              0.70      0.58      0.63      4431
Hold              0.73      0.84      0.78     25569
Buy               0.71      0.62      0.66      4978
Strong Buy        0.69      0.41      0.51       861

STEP 4: SAVING MODEL
✓ Model saved to models/ai_score_model.pkl

STEP 5: VALIDATION ON RECENT DATA (2024)
✓ AAPL    AI Score:  78/100  |  Actual 20-day return: +12.34%
✓ MSFT    AI Score:  65/100  |  Actual 20-day return:  +8.21%
✓ NVDA    AI Score:  82/100  |  Actual 20-day return: +15.67%
✓ TSLA    AI Score:  45/100  |  Actual 20-day return:  -2.11%
✓ META    AI Score:  71/100  |  Actual 20-day return:  +9.88%

================================================================================
TRAINING COMPLETE!
================================================================================
```

## Using the Trained Model

### In Python

```python
from ai_score_system import AIScoreModel, FeatureEngineer
from polygon_service import PolygonService
import pandas as pd

# Load trained model
model = AIScoreModel()
model.load('ai_score_model.pkl')

# Get recent price data
polygon = PolygonService()
price_data = polygon._fetch_historical_prices('AAPL', '2023-01-01', '2024-11-11', polygon)

# Calculate features
features = FeatureEngineer.calculate_technical_features(price_data)

# Predict AI score
score = model.predict_score(features)
print(f"AAPL AI Score: {score}/100")
```

### Integration with Web App

The model will be integrated into [polygon_service.py](../web/polygon_service.py) to provide real-time AI scores for the stock screener.

## Model Performance Metrics

### Accuracy Goals

- **Overall Accuracy:** >70%
- **Buy/Strong Buy Precision:** >65% (minimize false positives)
- **Sell/Strong Sell Recall:** >60% (catch actual losers)

### Validation Strategy

1. **Time-based split:** Train on 2016-2023, validate on 2024
2. **Walk-forward validation:** Continuously retrain on new data
3. **Real-world backtest:** Track actual vs predicted returns

## Future Improvements

### Phase 2: Add Fundamental Features
- P/E, P/B, P/S ratios
- EPS growth, revenue growth
- Debt/Equity, profit margins

### Phase 3: Sentiment Analysis
- News sentiment scores
- Social media mentions
- Analyst rating changes

### Phase 4: Advanced Models
- LSTM/Transformer for time series
- Ensemble methods (XGBoost + RandomForest + Neural Network)
- Multi-timeframe prediction (1-day, 1-week, 1-month)

## File Structure

```
ml/
├── README.md                 # This file
├── requirements.txt          # Python dependencies
├── ai_score_system.py        # Core ML system
├── train_ai_score.py         # Training script
├── test_ai_score.py          # Testing script (to be created)
├── training.log              # Training logs
├── training_data.csv         # Raw training data
└── models/
    └── ai_score_model.pkl    # Trained model
```

## Notes

- **API Rate Limits:** Polygon.io free tier has rate limits. Training may take 1-2 hours.
- **Data Quality:** Model accuracy depends on data quality. More stocks + longer history = better model.
- **Retraining:** Retrain monthly with latest data to maintain accuracy.
- **Disclaimer:** AI Score is for informational purposes only. Not financial advice.

## Contact

For questions about the AI Score system, see project documentation.
