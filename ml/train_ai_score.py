"""
Train Qunex AI Score Model with DVC and SHAP Explainability

This script:
1. Loads training data from DVC-tracked CSV
2. Prepares features and labels
3. Trains XGBoost model with SHAP explainer
4. Validates and saves metrics
5. Saves model and explainer for production

Run: dvc repro (recommended) or python train_ai_score.py
"""

import os
import sys
import logging
import json
import pickle
import yaml
from datetime import datetime
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, classification_report
import xgboost as xgb
import shap

# Add web directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "web"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("training.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def load_params():
    """Load training parameters from params.yaml."""
    params_path = os.path.join(os.path.dirname(__file__), "params.yaml")
    with open(params_path, "r") as f:
        params = yaml.safe_load(f)
    return params["train"]


def prepare_features_and_labels(df):
    """Prepare features (X) and labels (y) from training data."""
    # Feature columns
    feature_cols = [
        "price_change",
        "price_change_5d",
        "price_change_20d",
        "volume_ratio",
        "rsi",
        "price_to_ma5",
        "price_to_ma20",
        "price_to_ma50",
    ]

    # Ensure all feature columns exist
    missing_cols = [col for col in feature_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing feature columns: {missing_cols}")

    X = df[feature_cols].values
    y = df["target"].values

    # Convert continuous target to classification labels (0-4)
    # 0: Strong Sell (<-5%), 1: Sell (-5% to 0%), 2: Hold (0% to 5%), 3: Buy (5% to 10%), 4: Strong Buy (>10%)
    y_labels = np.zeros_like(y, dtype=int)
    y_labels[y < -0.05] = 0  # Strong Sell
    y_labels[(y >= -0.05) & (y < 0)] = 1  # Sell
    y_labels[(y >= 0) & (y < 0.05)] = 2  # Hold
    y_labels[(y >= 0.05) & (y < 0.10)] = 3  # Buy
    y_labels[y >= 0.10] = 4  # Strong Buy

    return X, y_labels, feature_cols


def main():
    """Train XGBoost model with SHAP explainer."""
    try:
        # Load parameters
        params = load_params()
        logger.info(f"Training parameters: {params}")

        # Load training data
        data_path = os.path.join(os.path.dirname(__file__), "data", "training_data.csv")
        logger.info(f"Loading training data from {data_path}")

        if not os.path.exists(data_path):
            raise FileNotFoundError(
                f"Training data not found at {data_path}. Run 'python ml/fetch_training_data.py' first."
            )

        df = pd.read_csv(data_path)
        logger.info(f"Loaded {len(df)} rows")

        # Prepare features and labels
        X, y, feature_cols = prepare_features_and_labels(df)
        logger.info(f"Features: {feature_cols}")
        logger.info(f"Training samples: {len(X)}")

        # Print label distribution
        label_counts = np.bincount(y)
        label_names = ["Strong Sell", "Sell", "Hold", "Buy", "Strong Buy"]
        logger.info("Label distribution:")
        for i, (name, count) in enumerate(zip(label_names, label_counts)):
            pct = (count / len(y)) * 100
            logger.info(f"  {name:12} {count:6,} ({pct:5.1f}%)")

        # Train/test split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=params["test_size"], random_state=params["random_state"]
        )

        logger.info(f"Train size: {len(X_train)}, Test size: {len(X_test)}")

        # Train XGBoost model
        logger.info("Training XGBoost classifier...")
        model = xgb.XGBClassifier(
            n_estimators=params["n_estimators"],
            max_depth=params["max_depth"],
            learning_rate=params["learning_rate"],
            random_state=params["random_state"],
            n_jobs=-1,
        )

        model.fit(X_train, y_train)
        logger.info("Model trained successfully")

        # Evaluate
        y_pred_train = model.predict(X_train)
        y_pred_test = model.predict(X_test)

        train_acc = accuracy_score(y_train, y_pred_train)
        test_acc = accuracy_score(y_test, y_pred_test)
        test_f1 = f1_score(y_test, y_pred_test, average="weighted")

        metrics = {
            "train_accuracy": float(train_acc),
            "test_accuracy": float(test_acc),
            "test_f1": float(test_f1),
            "timestamp": datetime.utcnow().isoformat(),
        }

        logger.info("\nModel Performance:")
        logger.info(f"  Train Accuracy: {train_acc:.4f}")
        logger.info(f"  Test Accuracy: {test_acc:.4f}")
        logger.info(f"  Test F1: {test_f1:.4f}")

        # Print classification report
        logger.info("\nClassification Report:")
        logger.info("\n" + classification_report(y_test, y_pred_test, target_names=label_names))

        # Save metrics
        metrics_path = os.path.join(os.path.dirname(__file__), "metrics.json")
        with open(metrics_path, "w") as f:
            json.dump(metrics, f, indent=2)
        logger.info(f"Metrics saved: {metrics_path}")

        # Save model
        model_path = os.path.join(os.path.dirname(__file__), "models", "model.pkl")
        with open(model_path, "wb") as f:
            pickle.dump({"model": model, "features": feature_cols}, f)
        logger.info(f"Model saved: {model_path}")

        # Train SHAP explainer
        logger.info("Creating SHAP explainer...")
        explainer = shap.TreeExplainer(model)

        # Save explainer
        explainer_path = os.path.join(os.path.dirname(__file__), "models", "explainer.pkl")
        with open(explainer_path, "wb") as f:
            pickle.dump(
                {
                    "explainer": explainer,
                    "features": feature_cols,
                    "base_value": explainer.expected_value,
                },
                f,
            )
        logger.info(f"Explainer saved: {explainer_path}")

        logger.info("\n✓ Training complete!")
        return True

    except Exception as e:
        logger.error(f"Training failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    main()
