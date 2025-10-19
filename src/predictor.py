"""
Real-time Prediction System
Makes predictions on live penny stock data
"""

import numpy as np
import pandas as pd
import logging
import joblib
from typing import Dict, List, Tuple
from datetime import datetime

from src.data_collector import PennyStockCollector
from src.feature_engineering import FeatureEngineer
from src.utils import load_config, setup_logging

# Try to import DL models (optional)
try:
    from src.dl_models import TimeSeriesDataGenerator
    from tensorflow import keras
    DL_AVAILABLE = True
except ImportError:
    DL_AVAILABLE = False
    keras = None


class PennyStockPredictor:
    """Make predictions on penny stocks"""

    def __init__(self, config_path: str = 'config.yaml'):
        self.config = load_config(config_path)
        self.logger = setup_logging(self.config)

        self.data_collector = PennyStockCollector(self.config)
        self.feature_engineer = FeatureEngineer(self.config)

        self.ml_models = {}
        self.dl_models = {}
        self.feature_cols = None
        self.scaler = None

    def load_models(self, model_types: List[str] = ['RandomForest', 'XGBoost', 'LightGBM']):
        """
        Load trained models

        Args:
            model_types: List of model names to load
        """
        models_dir = self.config['output']['models_dir']

        for model_type in model_types:
            try:
                model_path = f"{models_dir}/{model_type}.pkl"
                model = joblib.load(model_path)
                self.ml_models[model_type] = model
                self.logger.info(f"Loaded {model_type} from {model_path}")
            except Exception as e:
                self.logger.error(f"Error loading {model_type}: {str(e)}")

    def load_dl_models(self, model_types: List[str] = ['LSTM', 'GRU', 'Transformer']):
        """Load trained deep learning models"""
        if not DL_AVAILABLE:
            self.logger.warning("Deep learning not available. Cannot load DL models.")
            return

        models_dir = self.config['output']['models_dir']

        for model_type in model_types:
            try:
                model_path = f"{models_dir}/{model_type.lower()}_best.h5"
                model = keras.models.load_model(model_path)
                self.dl_models[model_type] = model
                self.logger.info(f"Loaded {model_type} from {model_path}")
            except Exception as e:
                self.logger.error(f"Error loading {model_type}: {str(e)}")

    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare features for prediction"""
        # Create features
        df = self.feature_engineer.create_all_features(df)

        # Get feature columns (same as training)
        if self.feature_cols is None:
            self.feature_cols = self.feature_engineer.select_features(df)

        return df

    def predict_single_stock(self, ticker: str, model_name: str = 'XGBoost') -> Dict:
        """
        Make prediction for a single stock

        Args:
            ticker: Stock ticker
            model_name: Name of model to use

        Returns:
            Dictionary with prediction results
        """
        self.logger.info(f"Predicting for {ticker}...")

        # Download recent data
        from datetime import datetime, timedelta
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')

        df = self.data_collector.download_stock_data(ticker, start_date, end_date)

        if df is None or df.empty:
            self.logger.error(f"No data available for {ticker}")
            return {'ticker': ticker, 'error': 'No data available'}

        # Prepare features
        df = self.prepare_features(df)

        # Handle missing values
        df = self.feature_engineer.handle_missing_values(df, method='forward_fill')

        # Get last row (most recent data)
        if len(df) == 0:
            return {'ticker': ticker, 'error': 'No valid data after feature engineering'}

        latest_data = df.iloc[-1]

        # Extract features
        X = latest_data[self.feature_cols].values.reshape(1, -1)

        # Make prediction
        if model_name in self.ml_models:
            model = self.ml_models[model_name]
            prediction = model.predict(X)[0]
            probability = model.predict_proba(X)[0]

            result = {
                'ticker': ticker,
                'date': latest_data['date'],
                'current_price': latest_data['close'],
                'prediction': int(prediction),
                'surge_probability': float(probability[1]) if len(probability) > 1 else float(probability[0]),
                'model': model_name,
                'timestamp': datetime.now()
            }

        else:
            result = {'ticker': ticker, 'error': f'Model {model_name} not loaded'}

        return result

    def predict_multiple_stocks(self, tickers: List[str], model_name: str = 'XGBoost',
                               top_n: int = None) -> pd.DataFrame:
        """
        Make predictions for multiple stocks

        Args:
            tickers: List of stock tickers
            model_name: Name of model to use
            top_n: Return only top N predictions

        Returns:
            DataFrame with predictions
        """
        self.logger.info(f"Predicting for {len(tickers)} stocks...")

        results = []

        for ticker in tickers:
            try:
                result = self.predict_single_stock(ticker, model_name)
                if 'error' not in result:
                    results.append(result)
            except Exception as e:
                self.logger.error(f"Error predicting {ticker}: {str(e)}")

        # Create DataFrame
        results_df = pd.DataFrame(results)

        if results_df.empty:
            self.logger.warning("No predictions generated")
            return results_df

        # Sort by surge probability
        results_df = results_df.sort_values('surge_probability', ascending=False)

        # Filter by confidence threshold
        confidence_threshold = self.config['prediction']['confidence_threshold']
        results_df = results_df[results_df['surge_probability'] >= confidence_threshold]

        # Return top N
        if top_n:
            results_df = results_df.head(top_n)

        self.logger.info(f"Generated {len(results_df)} predictions above threshold")

        return results_df

    def predict_ensemble(self, ticker: str, models: List[str] = None) -> Dict:
        """
        Make ensemble prediction using multiple models

        Args:
            ticker: Stock ticker
            models: List of model names (default: all loaded models)

        Returns:
            Dictionary with ensemble prediction
        """
        if models is None:
            models = list(self.ml_models.keys())

        self.logger.info(f"Making ensemble prediction for {ticker} using {len(models)} models")

        predictions = []
        probabilities = []

        for model_name in models:
            result = self.predict_single_stock(ticker, model_name)
            if 'error' not in result:
                predictions.append(result['prediction'])
                probabilities.append(result['surge_probability'])

        if not predictions:
            return {'ticker': ticker, 'error': 'No valid predictions'}

        # Average predictions
        avg_probability = np.mean(probabilities)
        final_prediction = 1 if avg_probability >= 0.5 else 0

        result = {
            'ticker': ticker,
            'prediction': final_prediction,
            'surge_probability': avg_probability,
            'model': 'Ensemble',
            'num_models': len(predictions),
            'timestamp': datetime.now()
        }

        return result

    def scan_market(self, use_screening: bool = True, model_name: str = 'XGBoost',
                   top_n: int = 20) -> pd.DataFrame:
        """
        Scan market for surge opportunities

        Args:
            use_screening: Whether to screen stocks first
            model_name: Model to use for predictions
            top_n: Number of top predictions to return

        Returns:
            DataFrame with top surge candidates
        """
        self.logger.info("Scanning market for surge opportunities...")

        # Get penny stock universe
        tickers = self.data_collector.get_penny_stock_universe()

        # Screen if requested
        if use_screening:
            tickers = self.data_collector.screen_penny_stocks(tickers)

        # Make predictions
        results = self.predict_multiple_stocks(tickers, model_name, top_n)

        # Save results
        if not results.empty:
            output_path = f"{self.config['output']['results_dir']}/market_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            results.to_csv(output_path, index=False)
            self.logger.info(f"Market scan results saved to {output_path}")

        return results

    def backtest_predictions(self, df: pd.DataFrame, model_name: str = 'XGBoost',
                           window: int = 5) -> Dict:
        """
        Backtest predictions on historical data

        Args:
            df: DataFrame with historical data
            model_name: Model to use
            window: Prediction window

        Returns:
            Dictionary with backtest results
        """
        self.logger.info(f"Backtesting {model_name} on historical data...")

        # Prepare features
        df = self.prepare_features(df)
        df = self.feature_engineer.handle_missing_values(df, method='drop')

        # Get features and calculate actual returns
        X = df[self.feature_cols].values
        df[f'actual_return_{window}d'] = df.groupby('ticker')['close'].pct_change(periods=window).shift(-window)

        # Make predictions
        if model_name in self.ml_models:
            model = self.ml_models[model_name]
            predictions = model.predict(X)
            probabilities = model.predict_proba(X)[:, 1] if hasattr(model, 'predict_proba') else predictions

            df['prediction'] = predictions
            df['surge_probability'] = probabilities

            # Calculate metrics
            # Stocks predicted to surge
            surge_predictions = df[df['prediction'] == 1]

            # Actual performance of predicted surges
            if len(surge_predictions) > 0:
                avg_return = surge_predictions[f'actual_return_{window}d'].mean()
                hit_rate = (surge_predictions[f'actual_return_{window}d'] >= 0.30).mean()

                results = {
                    'model': model_name,
                    'total_predictions': len(surge_predictions),
                    'average_return': avg_return,
                    'hit_rate': hit_rate,
                    'predictions_df': surge_predictions
                }

                self.logger.info(f"Backtest Results:")
                self.logger.info(f"  Total Surge Predictions: {len(surge_predictions)}")
                self.logger.info(f"  Average Return: {avg_return:.2%}")
                self.logger.info(f"  Hit Rate (>=30% gain): {hit_rate:.2%}")

                return results
            else:
                self.logger.warning("No surge predictions made")
                return {'error': 'No surge predictions'}

        else:
            return {'error': f'Model {model_name} not loaded'}


if __name__ == '__main__':
    # Example usage
    predictor = PennyStockPredictor()

    # Load models
    predictor.load_models(['RandomForest', 'XGBoost', 'LightGBM'])

    # Scan market
    top_stocks = predictor.scan_market(use_screening=True, model_name='XGBoost', top_n=20)

    print("\nTop Surge Candidates:")
    print(top_stocks)
