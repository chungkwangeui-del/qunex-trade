"""
Train model using existing training_data.csv
"""

import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "web"))
from ai_score_system import AIScoreModel

print("=" * 80)
print("QUNEX AI SCORE - TRAINING FROM EXISTING DATA")
print("=" * 80)

# Load training data
print("\nLoading training_data.csv...")
df = pd.read_csv("training_data.csv")
print(f"Loaded {len(df)} samples with {df.shape[1]} columns")

# Initialize model
model = AIScoreModel()

# Prepare features and labels
print("\nPreparing features and labels...")
X, y = model.prepare_features_and_labels(df)

print(f"Feature matrix: {X.shape}")
print(f"Label distribution:")
label_counts = np.bincount(y.astype(int))
label_names = ["Strong Sell", "Sell", "Hold", "Buy", "Strong Buy"]
for i, (name, count) in enumerate(zip(label_names, label_counts)):
    pct = (count / len(y)) * 100
    print(f"  {name:12} {count:6,} ({pct:5.1f}%)")

# Train model
print("\nTraining XGBoost model...")
model.train(X, y)

# Save model
print("\nSaving model...")
model.save("ai_score_model.pkl")
print("Model saved to models/ai_score_model.pkl")

print("\n" + "=" * 80)
print("TRAINING COMPLETE!")
print("=" * 80)
