"""
Evaluate trained model performance.
"""

import os
import sys
import json
import pickle
import pandas as pd
import numpy as np
from sklearn.metrics import accuracy_score, f1_score, classification_report
from sklearn.model_selection import train_test_split
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_params():
    """Load training parameters."""
    params_path = os.path.join(os.path.dirname(__file__), "params.yaml")
    with open(params_path, "r") as f:
        params = yaml.safe_load(f)
    return params["train"]


def main():
    try:
        params = load_params()

        # Load model
        model_path = os.path.join(os.path.dirname(__file__), "models", "model.pkl")
        with open(model_path, "rb") as f:
            model_data = pickle.load(f)
        model = model_data["model"]
        feature_cols = model_data["features"]

        # Load training data
        data_path = os.path.join(os.path.dirname(__file__), "data", "training_data.csv")
        df = pd.read_csv(data_path)

        # Prepare features
        X = df[feature_cols].values
        y_target = df["target"].values

        # Convert to labels
        y = np.zeros_like(y_target, dtype=int)
        y[y_target < -0.05] = 0
        y[(y_target >= -0.05) & (y_target < 0)] = 1
        y[(y_target >= 0) & (y_target < 0.05)] = 2
        y[(y_target >= 0.05) & (y_target < 0.10)] = 3
        y[y_target >= 0.10] = 4

        # Split
        _, X_test, _, y_test = train_test_split(
            X, y, test_size=params["test_size"], random_state=params["random_state"]
        )

        # Evaluate
        y_pred = model.predict(X_test)

        accuracy = accuracy_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred, average="weighted")

        label_names = ["Strong Sell", "Sell", "Hold", "Buy", "Strong Buy"]
        report = classification_report(y_test, y_pred, target_names=label_names, output_dict=True)

        metrics = {
            "accuracy": float(accuracy),
            "f1_weighted": float(f1),
            "per_class_f1": {
                name: float(report[name]["f1-score"]) for name in label_names
            },
        }

        # Save evaluation metrics
        eval_path = os.path.join(os.path.dirname(__file__), "evaluation_metrics.json")
        with open(eval_path, "w") as f:
            json.dump(metrics, f, indent=2)

        print(f"✓ Evaluation complete: Accuracy={accuracy:.4f}, F1={f1:.4f}")
        return True

    except Exception as e:
        print(f"✗ Evaluation failed: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
