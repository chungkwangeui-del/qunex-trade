"""
Automated Model Retraining Cron Job

Runs weekly to:
1. Execute DVC pipeline (dvc repro)
2. Compare new model performance to production model
3. Promote new model only if it's better
4. Log all decisions

Schedule: Weekly on Sunday at midnight (0 0 * * 0)
"""

import os
import sys
import json
import shutil
import subprocess
from datetime import datetime, timezone
from datetime import timezone

# Add parent directory and web directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
web_dir = os.path.join(parent_dir, "web")
sys.path.insert(0, web_dir)
sys.path.insert(0, parent_dir)

from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)


load_dotenv()


def run_command(cmd):
    """Run shell command and return output.

    Security: Uses shell=False with command list to prevent command injection.
    """
    try:
        # Convert string command to list for shell=False
        if isinstance(cmd, str):
            cmd = cmd.split()

        result = subprocess.run(
            cmd,
            shell=False,  # nosec B602 - Security: prevent command injection
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout, None
    except subprocess.CalledProcessError as e:
        return None, e.stderr


def main():
    """Run DVC pipeline and promote model if better."""
    log_file = "retrain.log"

    def log(msg):
        timestamp = datetime.now(timezone.utc).isoformat()
        log_msg = f"[{timestamp}] {msg}"
        logger.info(log_msg)
        with open(log_file, "a") as f:
            f.write(log_msg + "\n")

    try:
        log("=" * 80)
        log("AUTOMATED MODEL RETRAINING START")
        log("=" * 80)

        # Step 1: Run DVC pipeline
        log("Step 1: Running DVC pipeline (dvc repro)...")
        stdout, stderr = run_command("dvc repro")

        if stderr:
            log(f"WARNING: DVC pipeline had warnings:\n{stderr}")

        if stdout:
            log(f"DVC output:\n{stdout}")

        log("✓ DVC pipeline complete")

        # Step 2: Load new model metrics
        ml_dir = os.path.join(os.path.dirname(__file__), "..", "ml")
        new_metrics_path = os.path.join(ml_dir, "evaluation_metrics.json")

        if not os.path.exists(new_metrics_path):
            log("✗ ERROR: New model evaluation metrics not found")
            return False

        with open(new_metrics_path, "r") as f:
            new_metrics = json.load(f)

        log(f"New model performance: {new_metrics}")

        # Step 3: Load production model metrics (if exists)
        prod_metrics_path = os.path.join(ml_dir, "models", "production_metrics.json")

        if os.path.exists(prod_metrics_path):
            with open(prod_metrics_path, "r") as f:
                prod_metrics = json.load(f)

            log(f"Production model performance: {prod_metrics}")

            # Compare F1 scores
            new_f1 = new_metrics.get("f1_weighted", 0)
            prod_f1 = prod_metrics.get("f1_weighted", 0)

            log(f"Comparison: New F1={new_f1:.4f} vs Prod F1={prod_f1:.4f}")

            if new_f1 <= prod_f1:
                log("✗ New model is NOT better. Keeping production model.")
                return False

            log("✓ New model is better! Promoting to production...")
        else:
            log("No production model found. Promoting new model as first production model.")

        # Step 4: Promote new model to production
        new_model_path = os.path.join(ml_dir, "models", "model.pkl")
        new_explainer_path = os.path.join(ml_dir, "models", "explainer.pkl")

        prod_model_path = os.path.join(ml_dir, "models", "production_model.pkl")
        prod_explainer_path = os.path.join(ml_dir, "models", "production_explainer.pkl")

        # Backup existing production model
        if os.path.exists(prod_model_path):
            backup_timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            backup_model_path = os.path.join(
                ml_dir, "models", f"backup_model_{backup_timestamp}.pkl"
            )
            shutil.copy(prod_model_path, backup_model_path)
            log(f"✓ Backed up production model to {backup_model_path}")

        # Copy new model to production
        shutil.copy(new_model_path, prod_model_path)
        shutil.copy(new_explainer_path, prod_explainer_path)
        shutil.copy(new_metrics_path, prod_metrics_path)

        log("✓ New model promoted to production")
        log("=" * 80)
        log("RETRAINING SUCCESS")
        log("=" * 80)

        return True

    except Exception as e:
        log(f"✗ ERROR: Retraining failed - {e}")
        import traceback

        log(traceback.format_exc())
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
