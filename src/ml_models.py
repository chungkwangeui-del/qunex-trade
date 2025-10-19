"""
Machine Learning Models
Implements Random Forest, XGBoost, LightGBM, and ensemble models
"""

import numpy as np
import pandas as pd
import logging
import joblib
from typing import Dict, Tuple, List
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score, accuracy_score
from sklearn.model_selection import cross_val_score, GridSearchCV
import xgboost as xgb
import lightgbm as lgb


class MLModelTrainer:
    """Train and evaluate machine learning models"""

    def __init__(self, config):
        self.config = config
        self.models = {}
        self.logger = logging.getLogger(__name__)

    def create_random_forest(self) -> RandomForestClassifier:
        """Create Random Forest model"""
        params = self.config['ml_models']['random_forest']
        model = RandomForestClassifier(**params)
        self.logger.info(f"Random Forest created with params: {params}")
        return model

    def create_xgboost(self) -> xgb.XGBClassifier:
        """Create XGBoost model"""
        params = self.config['ml_models']['xgboost']
        model = xgb.XGBClassifier(
            **params,
            use_label_encoder=False,
            eval_metric='logloss'
        )
        self.logger.info(f"XGBoost created with params: {params}")
        return model

    def create_lightgbm(self) -> lgb.LGBMClassifier:
        """Create LightGBM model"""
        params = self.config['ml_models']['lightgbm']
        model = lgb.LGBMClassifier(**params, verbose=-1)
        self.logger.info(f"LightGBM created with params: {params}")
        return model

    def train_model(self, model, X_train: np.ndarray, y_train: np.ndarray,
                   X_val: np.ndarray = None, y_val: np.ndarray = None,
                   model_name: str = 'model'):
        """
        Train a single model

        Args:
            model: ML model to train
            X_train: Training features
            y_train: Training labels
            X_val: Validation features (optional)
            y_val: Validation labels (optional)
            model_name: Name of the model

        Returns:
            Trained model
        """
        self.logger.info(f"Training {model_name}...")

        # Train with validation set if provided (for early stopping)
        if X_val is not None and y_val is not None:
            if isinstance(model, xgb.XGBClassifier):
                # XGBoost 3.x uses callbacks for early stopping
                model.fit(
                    X_train, y_train,
                    eval_set=[(X_val, y_val)],
                    verbose=False
                )
            elif isinstance(model, lgb.LGBMClassifier):
                model.fit(
                    X_train, y_train,
                    eval_set=[(X_val, y_val)],
                    callbacks=[lgb.early_stopping(stopping_rounds=self.config['training']['early_stopping_patience'])]
                )
            else:
                model.fit(X_train, y_train)
        else:
            model.fit(X_train, y_train)

        self.logger.info(f"{model_name} training complete")
        self.models[model_name] = model

        return model

    def evaluate_model(self, model, X_test: np.ndarray, y_test: np.ndarray,
                      model_name: str = 'model') -> Dict:
        """
        Evaluate model performance

        Args:
            model: Trained model
            X_test: Test features
            y_test: Test labels
            model_name: Name of the model

        Returns:
            Dictionary with evaluation metrics
        """
        self.logger.info(f"Evaluating {model_name}...")

        # Predictions
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)

        # Metrics
        accuracy = accuracy_score(y_test, y_pred)

        # ROC AUC (handle binary and multiclass)
        try:
            if len(np.unique(y_test)) == 2:
                roc_auc = roc_auc_score(y_test, y_pred_proba[:, 1])
            else:
                roc_auc = roc_auc_score(y_test, y_pred_proba, multi_class='ovr')
        except:
            roc_auc = None

        # Classification report
        report = classification_report(y_test, y_pred, output_dict=True)

        # Confusion matrix
        cm = confusion_matrix(y_test, y_pred)

        results = {
            'model_name': model_name,
            'accuracy': accuracy,
            'roc_auc': roc_auc,
            'classification_report': report,
            'confusion_matrix': cm,
            'predictions': y_pred,
            'prediction_probabilities': y_pred_proba
        }

        # Log results
        self.logger.info(f"{model_name} Results:")
        self.logger.info(f"  Accuracy: {accuracy:.4f}")
        if roc_auc:
            self.logger.info(f"  ROC AUC: {roc_auc:.4f}")
        self.logger.info(f"\nClassification Report:\n{classification_report(y_test, y_pred)}")

        return results

    def cross_validate(self, model, X: np.ndarray, y: np.ndarray,
                      cv: int = 5, model_name: str = 'model') -> Dict:
        """
        Perform cross-validation

        Args:
            model: ML model
            X: Features
            y: Labels
            cv: Number of cross-validation folds
            model_name: Name of the model

        Returns:
            Dictionary with CV results
        """
        self.logger.info(f"Cross-validating {model_name} with {cv} folds...")

        scores = cross_val_score(model, X, y, cv=cv, scoring='accuracy')

        results = {
            'model_name': model_name,
            'cv_scores': scores,
            'cv_mean': scores.mean(),
            'cv_std': scores.std()
        }

        self.logger.info(f"{model_name} CV Results:")
        self.logger.info(f"  Mean Accuracy: {scores.mean():.4f} (+/- {scores.std():.4f})")

        return results

    def hyperparameter_tuning(self, model_type: str, X_train: np.ndarray,
                             y_train: np.ndarray, param_grid: Dict) -> Tuple:
        """
        Perform hyperparameter tuning using GridSearchCV

        Args:
            model_type: Type of model ('rf', 'xgb', 'lgbm')
            X_train: Training features
            y_train: Training labels
            param_grid: Parameter grid for tuning

        Returns:
            Tuple of (best_model, best_params)
        """
        self.logger.info(f"Hyperparameter tuning for {model_type}...")

        # Create base model
        if model_type == 'rf':
            base_model = RandomForestClassifier(random_state=42)
        elif model_type == 'xgb':
            base_model = xgb.XGBClassifier(use_label_encoder=False, eval_metric='logloss', random_state=42)
        elif model_type == 'lgbm':
            base_model = lgb.LGBMClassifier(random_state=42, verbose=-1)
        else:
            raise ValueError(f"Unknown model type: {model_type}")

        # Grid search
        grid_search = GridSearchCV(
            base_model,
            param_grid,
            cv=3,
            scoring='accuracy',
            n_jobs=-1,
            verbose=1
        )

        grid_search.fit(X_train, y_train)

        self.logger.info(f"Best parameters: {grid_search.best_params_}")
        self.logger.info(f"Best score: {grid_search.best_score_:.4f}")

        return grid_search.best_estimator_, grid_search.best_params_

    def get_feature_importance(self, model, feature_names: List[str],
                              top_n: int = 20) -> pd.DataFrame:
        """
        Get feature importance from model

        Args:
            model: Trained model
            feature_names: List of feature names
            top_n: Number of top features to return

        Returns:
            DataFrame with feature importance
        """
        if hasattr(model, 'feature_importances_'):
            importance = model.feature_importances_
        else:
            self.logger.warning("Model does not have feature_importances_")
            return pd.DataFrame()

        # Create DataFrame
        importance_df = pd.DataFrame({
            'feature': feature_names,
            'importance': importance
        }).sort_values('importance', ascending=False)

        # Log top features
        self.logger.info(f"\nTop {top_n} Important Features:")
        for idx, row in importance_df.head(top_n).iterrows():
            self.logger.info(f"  {row['feature']}: {row['importance']:.4f}")

        return importance_df

    def train_all_models(self, X_train: np.ndarray, y_train: np.ndarray,
                        X_val: np.ndarray, y_val: np.ndarray,
                        X_test: np.ndarray, y_test: np.ndarray,
                        feature_names: List[str]) -> Dict:
        """
        Train all ML models

        Args:
            X_train: Training features
            y_train: Training labels
            X_val: Validation features
            y_val: Validation labels
            X_test: Test features
            y_test: Test labels
            feature_names: List of feature names

        Returns:
            Dictionary with all results
        """
        results = {}

        # Random Forest
        rf_model = self.create_random_forest()
        rf_model = self.train_model(rf_model, X_train, y_train, X_val, y_val, 'RandomForest')
        results['RandomForest'] = self.evaluate_model(rf_model, X_test, y_test, 'RandomForest')
        results['RandomForest']['feature_importance'] = self.get_feature_importance(rf_model, feature_names)

        # XGBoost
        xgb_model = self.create_xgboost()
        xgb_model = self.train_model(xgb_model, X_train, y_train, X_val, y_val, 'XGBoost')
        results['XGBoost'] = self.evaluate_model(xgb_model, X_test, y_test, 'XGBoost')
        results['XGBoost']['feature_importance'] = self.get_feature_importance(xgb_model, feature_names)

        # LightGBM
        lgbm_model = self.create_lightgbm()
        lgbm_model = self.train_model(lgbm_model, X_train, y_train, X_val, y_val, 'LightGBM')
        results['LightGBM'] = self.evaluate_model(lgbm_model, X_test, y_test, 'LightGBM')
        results['LightGBM']['feature_importance'] = self.get_feature_importance(lgbm_model, feature_names)

        return results

    def create_ensemble(self, X_train: np.ndarray, y_train: np.ndarray,
                       X_test: np.ndarray, y_test: np.ndarray) -> Dict:
        """
        Create ensemble model by averaging predictions

        Args:
            X_train: Training features
            y_train: Training labels
            X_test: Test features
            y_test: Test labels

        Returns:
            Dictionary with ensemble results
        """
        self.logger.info("Creating ensemble model...")

        # Get predictions from all models
        predictions = []
        probabilities = []

        for model_name, model in self.models.items():
            pred_proba = model.predict_proba(X_test)
            probabilities.append(pred_proba)

        # Average probabilities
        avg_proba = np.mean(probabilities, axis=0)
        ensemble_pred = np.argmax(avg_proba, axis=1)

        # Evaluate ensemble
        accuracy = accuracy_score(y_test, ensemble_pred)

        try:
            if len(np.unique(y_test)) == 2:
                roc_auc = roc_auc_score(y_test, avg_proba[:, 1])
            else:
                roc_auc = roc_auc_score(y_test, avg_proba, multi_class='ovr')
        except:
            roc_auc = None

        results = {
            'model_name': 'Ensemble',
            'accuracy': accuracy,
            'roc_auc': roc_auc,
            'predictions': ensemble_pred,
            'prediction_probabilities': avg_proba
        }

        self.logger.info(f"Ensemble Results:")
        self.logger.info(f"  Accuracy: {accuracy:.4f}")
        if roc_auc:
            self.logger.info(f"  ROC AUC: {roc_auc:.4f}")

        return results

    def save_model(self, model_name: str, filepath: str = None):
        """Save trained model"""
        if model_name not in self.models:
            self.logger.error(f"Model {model_name} not found")
            return

        if filepath is None:
            filepath = f"{self.config['output']['models_dir']}/{model_name}.pkl"

        joblib.dump(self.models[model_name], filepath)
        self.logger.info(f"Model saved to {filepath}")

    def load_model(self, filepath: str, model_name: str = None):
        """Load trained model"""
        model = joblib.load(filepath)

        if model_name:
            self.models[model_name] = model

        self.logger.info(f"Model loaded from {filepath}")
        return model

    def save_all_models(self):
        """Save all trained models"""
        for model_name in self.models.keys():
            self.save_model(model_name)
