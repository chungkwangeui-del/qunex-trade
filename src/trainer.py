"""
Training Pipeline
End-to-end training pipeline for both ML and DL models
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, Tuple, List
from sklearn.model_selection import train_test_split

from src.data_collector import PennyStockCollector
from src.labeling import SurgeLabeler
from src.feature_engineering import FeatureEngineer
from src.ml_models import MLModelTrainer
from src.utils import load_config, setup_logging, ensure_directories

# Try to import DL models (optional)
try:
    from src.dl_models import (TimeSeriesDataGenerator, LSTMModel, GRUModel,
                               TransformerModel, DLModelEvaluator)
    DL_AVAILABLE = True
except ImportError:
    DL_AVAILABLE = False
    import logging
    logging.warning("Deep learning models not available. TensorFlow not installed.")


class PennyStockTrainer:
    """Complete training pipeline"""

    def __init__(self, config_path: str = 'config.yaml'):
        self.config = load_config(config_path)
        self.logger = setup_logging(self.config)
        ensure_directories(self.config)

        # Initialize components
        self.data_collector = PennyStockCollector(self.config)
        self.labeler = SurgeLabeler(self.config)
        self.feature_engineer = FeatureEngineer(self.config)
        self.ml_trainer = MLModelTrainer(self.config)

    def load_or_collect_data(self, force_collect: bool = False) -> pd.DataFrame:
        """Load existing data or collect new data"""
        if not force_collect:
            self.logger.info("Attempting to load existing data...")
            df = self.data_collector.load_data()
            if not df.empty:
                return df

        self.logger.info("Collecting new data...")
        df = self.data_collector.collect_all_data(use_screening=True)
        return df

    def prepare_data(self, df: pd.DataFrame, target_window: int = 5,
                    label_type: str = 'binary') -> Tuple:
        """
        Prepare data for training

        Args:
            df: Raw data DataFrame
            target_window: Prediction window
            label_type: 'binary' or 'multiclass'

        Returns:
            Tuple of (features_df, target_col, feature_cols)
        """
        self.logger.info("Preparing data...")

        # Create features
        df = self.feature_engineer.create_all_features(df)

        # Create labels
        df, target_col = self.labeler.create_training_labels(df, target_window, label_type)

        # Select feature columns
        feature_cols = self.feature_engineer.select_features(df)

        # Handle missing values
        df = self.feature_engineer.handle_missing_values(df, method='drop')

        self.logger.info(f"Data prepared: {len(df)} samples, {len(feature_cols)} features")

        return df, target_col, feature_cols

    def split_data(self, df: pd.DataFrame, feature_cols: List[str],
                  target_col: str) -> Tuple:
        """
        Split data into train, validation, and test sets

        Args:
            df: DataFrame with features and labels
            feature_cols: List of feature column names
            target_col: Target column name

        Returns:
            Tuple of (X_train, X_val, X_test, y_train, y_val, y_test)
        """
        self.logger.info("Splitting data...")

        X = df[feature_cols].values
        y = df[target_col].values

        # First split: train+val vs test
        test_size = self.config['training']['test_size']
        X_temp, X_test, y_temp, y_test = train_test_split(
            X, y, test_size=test_size, shuffle=False, random_state=42
        )

        # Second split: train vs val
        val_size = self.config['training']['validation_size']
        val_ratio = val_size / (1 - test_size)
        X_train, X_val, y_train, y_val = train_test_split(
            X_temp, y_temp, test_size=val_ratio, shuffle=False, random_state=42
        )

        self.logger.info(f"Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")

        return X_train, X_val, X_test, y_train, y_val, y_test

    def train_ml_models(self, X_train: np.ndarray, y_train: np.ndarray,
                       X_val: np.ndarray, y_val: np.ndarray,
                       X_test: np.ndarray, y_test: np.ndarray,
                       feature_cols: List[str]) -> Dict:
        """Train all machine learning models"""
        self.logger.info("Training ML models...")

        results = self.ml_trainer.train_all_models(
            X_train, y_train,
            X_val, y_val,
            X_test, y_test,
            feature_cols
        )

        # Create ensemble
        ensemble_results = self.ml_trainer.create_ensemble(
            X_train, y_train,
            X_test, y_test
        )
        results['Ensemble'] = ensemble_results

        # Save all models
        self.ml_trainer.save_all_models()

        return results

    def train_dl_models(self, df: pd.DataFrame, feature_cols: List[str],
                       target_col: str, num_classes: int = 2) -> Dict:
        """Train all deep learning models"""
        if not DL_AVAILABLE:
            self.logger.warning("Deep learning not available. Skipping DL training.")
            return {}

        self.logger.info("Training DL models...")

        # Create sequences
        sequence_length = self.config['dl_models']['lstm']['sequence_length']
        seq_generator = TimeSeriesDataGenerator(sequence_length)

        X_seq, y_seq, tickers = seq_generator.create_sequences_by_ticker(
            df, feature_cols, target_col
        )

        self.logger.info(f"Created {len(X_seq)} sequences")

        # Split data
        test_size = self.config['training']['test_size']
        val_size = self.config['training']['validation_size']

        # Train-test split
        X_temp, X_test, y_temp, y_test = train_test_split(
            X_seq, y_seq, test_size=test_size, shuffle=False, random_state=42
        )

        # Train-val split
        val_ratio = val_size / (1 - test_size)
        X_train, X_val, y_train, y_val = train_test_split(
            X_temp, y_temp, test_size=val_ratio, shuffle=False, random_state=42
        )

        input_shape = (X_train.shape[1], X_train.shape[2])
        self.logger.info(f"Input shape: {input_shape}")

        results = {}
        evaluator = DLModelEvaluator()

        # LSTM
        self.logger.info("Training LSTM...")
        lstm = LSTMModel(self.config, input_shape, num_classes)
        lstm.build_model()
        lstm.train(X_train, y_train, X_val, y_val,
                  save_path=f"{self.config['output']['models_dir']}/lstm_best.h5")
        results['LSTM'] = evaluator.evaluate(lstm.model, X_test, y_test, 'LSTM')

        # GRU
        self.logger.info("Training GRU...")
        gru = GRUModel(self.config, input_shape, num_classes)
        gru.build_model()
        gru.train(X_train, y_train, X_val, y_val,
                 save_path=f"{self.config['output']['models_dir']}/gru_best.h5")
        results['GRU'] = evaluator.evaluate(gru.model, X_test, y_test, 'GRU')

        # Transformer
        self.logger.info("Training Transformer...")
        transformer = TransformerModel(self.config, input_shape, num_classes)
        transformer.build_model()
        transformer.train(X_train, y_train, X_val, y_val,
                         save_path=f"{self.config['output']['models_dir']}/transformer_best.h5")
        results['Transformer'] = evaluator.evaluate(transformer.model, X_test, y_test, 'Transformer')

        return results

    def train_all(self, force_collect: bool = False, target_window: int = 5,
                 label_type: str = 'binary', train_dl: bool = True) -> Dict:
        """
        Complete training pipeline

        Args:
            force_collect: Force data collection
            target_window: Prediction window
            label_type: 'binary' or 'multiclass'
            train_dl: Whether to train deep learning models

        Returns:
            Dictionary with all results
        """
        self.logger.info("="*50)
        self.logger.info("STARTING PENNY STOCK SURGE PREDICTION TRAINING")
        self.logger.info("="*50)

        # Load or collect data
        df = self.load_or_collect_data(force_collect)

        if df.empty:
            self.logger.error("No data available. Exiting.")
            return {}

        # Prepare data
        df, target_col, feature_cols = self.prepare_data(df, target_window, label_type)

        # Determine number of classes
        num_classes = len(df[target_col].unique())
        self.logger.info(f"Number of classes: {num_classes}")

        # Split data for ML models
        X_train, X_val, X_test, y_train, y_val, y_test = self.split_data(
            df, feature_cols, target_col
        )

        all_results = {}

        # Train ML models
        ml_results = self.train_ml_models(
            X_train, y_train,
            X_val, y_val,
            X_test, y_test,
            feature_cols
        )
        all_results['ML'] = ml_results

        # Train DL models (optional)
        if train_dl:
            dl_results = self.train_dl_models(df, feature_cols, target_col, num_classes)
            all_results['DL'] = dl_results

        # Save results summary
        self.save_results_summary(all_results)

        self.logger.info("="*50)
        self.logger.info("TRAINING COMPLETE")
        self.logger.info("="*50)

        return all_results

    def save_results_summary(self, results: Dict):
        """Save training results summary"""
        summary = []

        # ML results
        if 'ML' in results:
            for model_name, model_results in results['ML'].items():
                summary.append({
                    'Model': model_name,
                    'Type': 'ML',
                    'Accuracy': model_results['accuracy'],
                    'ROC_AUC': model_results.get('roc_auc', None)
                })

        # DL results
        if 'DL' in results:
            for model_name, model_results in results['DL'].items():
                summary.append({
                    'Model': model_name,
                    'Type': 'DL',
                    'Accuracy': model_results['accuracy'],
                    'ROC_AUC': model_results.get('roc_auc', None)
                })

        # Create DataFrame
        summary_df = pd.DataFrame(summary)

        # Save to CSV
        output_path = f"{self.config['output']['results_dir']}/training_summary.csv"
        summary_df.to_csv(output_path, index=False)

        self.logger.info(f"\nResults Summary:")
        self.logger.info(f"\n{summary_df.to_string()}")
        self.logger.info(f"\nSummary saved to {output_path}")


if __name__ == '__main__':
    # Example usage
    trainer = PennyStockTrainer()
    results = trainer.train_all(
        force_collect=False,
        target_window=5,
        label_type='binary',
        train_dl=True
    )
