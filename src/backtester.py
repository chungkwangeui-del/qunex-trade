"""
Proper Backtesting System with Walk-Forward Validation
No Lookahead Bias - Only uses data available at prediction time
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
from sklearn.model_selection import TimeSeriesSplit

from src.data_collector import PennyStockCollector
from src.labeling import SurgeLabeler
from src.feature_engineering import FeatureEngineer
from src.ml_models import MLModelTrainer
from src.utils import load_config, setup_logging


class WalkForwardBacktester:
    """Walk-forward backtesting without lookahead bias"""

    def __init__(self, config_path: str = 'config.yaml'):
        self.config = load_config(config_path)
        self.logger = setup_logging(self.config)

        self.data_collector = PennyStockCollector(self.config)
        self.labeler = SurgeLabeler(self.config)
        self.feature_engineer = FeatureEngineer(self.config)

    def prepare_data_no_lookahead(self, df: pd.DataFrame, current_date: pd.Timestamp) -> Tuple:
        """
        Prepare data without lookahead bias
        Only uses data available up to current_date
        """
        # Only use data up to current_date
        historical_data = df[df['date'] <= current_date].copy()

        if len(historical_data) == 0:
            return None, None, None, None

        # Create features (no future data used)
        historical_data = self.feature_engineer.create_all_features(historical_data)

        # Add volume surge and gap features to all data
        historical_data = self.labeler.detect_volume_surge(historical_data)
        historical_data = self.labeler.detect_gap_up(historical_data)

        # Create labels ONLY for training data (past)
        # We don't create labels for the current prediction point
        prediction_window = self.config['surge'].get('prediction_window', 10)
        train_data = historical_data[historical_data['date'] < current_date - pd.Timedelta(days=prediction_window)].copy()

        # Calculate MAX future returns WITHIN window for training data
        # This captures if stock surged 50% at ANY point within 10 days
        self.logger.info(f"Calculating max returns within {prediction_window} days (this may take a while)...")
        train_data[f'max_return_{prediction_window}d'] = self.labeler.calculate_max_return_within_window(
            train_data, prediction_window
        )

        # Create binary labels using config threshold (50% surge)
        surge_threshold = self.config['surge']['default_threshold']
        train_data[f'surge_{prediction_window}d'] = (
            train_data[f'max_return_{prediction_window}d'] >= surge_threshold
        ).astype(int)
        target_col = f'surge_{prediction_window}d'

        # Drop rows with NaN labels
        train_data = train_data.dropna(subset=[target_col])

        # Get feature columns (exclude future returns and surge columns)
        exclude_cols = ['ticker', 'date', 'open', 'high', 'low', 'close', 'volume',
                       'dividends', 'stock_splits', 'capital_gains']
        exclude_cols.extend([col for col in train_data.columns if col.startswith('future_') or col.startswith('surge_')])
        feature_cols = [col for col in train_data.columns if col not in exclude_cols]

        # Handle missing values
        train_data = self.feature_engineer.handle_missing_values(train_data, method='drop')

        # Prediction data (current date) - has same features except labels
        pred_data = historical_data[historical_data['date'] == current_date].copy()

        if len(train_data) == 0 or len(pred_data) == 0:
            return None, None, None, None

        return train_data, pred_data, feature_cols, target_col

    def simulate_trade_with_daily_monitoring(self, df: pd.DataFrame, ticker: str,
                                             entry_date: pd.Timestamp, entry_price: float,
                                             max_holding_days: int = 10) -> Dict:
        """
        Simulate a trade with daily monitoring for:
        1. Take profit: +50% target
        2. Stop loss: -5%
        3. Max holding period: 10 days

        Returns:
            Dict with exit details
        """
        take_profit_threshold = self.config['backtesting']['take_profit']
        stop_loss_threshold = self.config['backtesting']['stop_loss']

        # Get all future data for this ticker
        future_data = df[
            (df['ticker'] == ticker) &
            (df['date'] > entry_date)
        ].sort_values('date').head(max_holding_days)

        if len(future_data) == 0:
            return {'exit_reason': 'no_data', 'exit_price': None, 'exit_date': None}

        # Check each day
        for idx, row in future_data.iterrows():
            current_return = (row['close'] - entry_price) / entry_price

            # Check take profit (+50%)
            if current_return >= take_profit_threshold:
                return {
                    'exit_reason': 'take_profit',
                    'exit_price': row['close'],
                    'exit_date': row['date'],
                    'actual_return': current_return,
                    'holding_days': (row['date'] - entry_date).days
                }

            # Check stop loss (-5%)
            if current_return <= -stop_loss_threshold:
                return {
                    'exit_reason': 'stop_loss',
                    'exit_price': row['close'],
                    'exit_date': row['date'],
                    'actual_return': current_return,
                    'holding_days': (row['date'] - entry_date).days
                }

        # Max holding period reached - exit at last available price
        last_row = future_data.iloc[-1]
        final_return = (last_row['close'] - entry_price) / entry_price

        return {
            'exit_reason': 'max_holding',
            'exit_price': last_row['close'],
            'exit_date': last_row['date'],
            'actual_return': final_return,
            'holding_days': (last_row['date'] - entry_date).days
        }

    def walk_forward_backtest(self, df: pd.DataFrame,
                             train_period_days: int = 365,
                             rebalance_frequency_days: int = 30,
                             prediction_window: int = 5) -> Dict:
        """
        Walk-forward backtesting

        Args:
            df: Complete historical data
            train_period_days: Days of data to use for training
            rebalance_frequency_days: How often to retrain and rebalance
            prediction_window: Days to hold position

        Returns:
            Dictionary with backtest results
        """
        self.logger.info("="*70)
        self.logger.info("WALK-FORWARD BACKTESTING (NO LOOKAHEAD BIAS)")
        self.logger.info("="*70)

        # Sort by date
        df = df.sort_values(['ticker', 'date']).reset_index(drop=True)

        # Get unique dates
        all_dates = sorted(df['date'].unique())

        # Start date = first date + train_period
        start_idx = len([d for d in all_dates if d < all_dates[0] + pd.Timedelta(days=train_period_days)])
        if start_idx >= len(all_dates):
            self.logger.error("Not enough data for training period")
            return {}

        backtest_dates = all_dates[start_idx::rebalance_frequency_days]

        self.logger.info(f"Backtest period: {all_dates[start_idx]} to {all_dates[-1]}")
        self.logger.info(f"Number of rebalance dates: {len(backtest_dates)}")
        self.logger.info(f"Training period: {train_period_days} days")
        self.logger.info(f"Rebalance frequency: {rebalance_frequency_days} days")

        # Track performance - INDEPENDENT TRADES (no portfolio aggregation)
        all_predictions = []
        trades = []  # Each trade is independent

        for i, current_date in enumerate(backtest_dates):
            self.logger.info(f"\n--- Rebalance {i+1}/{len(backtest_dates)}: {current_date} ---")

            # Prepare data (no lookahead)
            result = self.prepare_data_no_lookahead(df, current_date)

            if result[0] is None:
                self.logger.warning(f"Skipping {current_date} - insufficient data")
                continue

            train_data, pred_data, feature_cols, target_col = result

            # Train model on historical data only
            X_train = train_data[feature_cols].values
            y_train = train_data[target_col].values

            # Check if there's enough class balance
            unique_classes = np.unique(y_train)
            class_counts = np.bincount(y_train.astype(int))

            if len(unique_classes) < 2:
                self.logger.warning(f"Only one class in training data: {unique_classes}")
                continue

            # Train ensemble of models
            ml_trainer = MLModelTrainer(self.config)

            # Use simple models for speed
            rf_model = ml_trainer.create_random_forest()
            rf_model.fit(X_train, y_train)

            # Skip XGBoost if causing issues, use RF and LGBM only
            try:
                xgb_model = ml_trainer.create_xgboost()
                xgb_model.fit(X_train, y_train)
                use_xgb = True
            except Exception as e:
                self.logger.warning(f"XGBoost training failed: {str(e)}, using RF and LGBM only")
                use_xgb = False

            lgbm_model = ml_trainer.create_lightgbm()
            try:
                lgbm_model.fit(X_train, y_train, eval_set=[(X_train, y_train)])
            except:
                lgbm_model.fit(X_train, y_train)

            # Make predictions on current date data
            tickers_today = pred_data['ticker'].unique()
            predictions_today = []

            for ticker in tickers_today:
                ticker_data = pred_data[pred_data['ticker'] == ticker]

                if len(ticker_data) == 0:
                    continue

                # Extract features
                try:
                    X_pred = ticker_data[feature_cols].values

                    # Ensemble prediction
                    rf_pred = rf_model.predict_proba(X_pred)[0][1]
                    lgbm_pred = lgbm_model.predict_proba(X_pred)[0][1]

                    if use_xgb:
                        xgb_pred = xgb_model.predict_proba(X_pred)[0][1]
                        avg_prob = (rf_pred + xgb_pred + lgbm_pred) / 3
                    else:
                        avg_prob = (rf_pred + lgbm_pred) / 2

                    current_price = ticker_data['close'].iloc[0]

                    predictions_today.append({
                        'date': current_date,
                        'ticker': ticker,
                        'surge_probability': avg_prob,
                        'entry_price': current_price,
                        'prediction': 1 if avg_prob >= 0.5 else 0  # Lowered from 0.7 to 0.5
                    })
                except Exception as e:
                    self.logger.warning(f"Error predicting {ticker}: {str(e)}")
                    continue

            if not predictions_today:
                self.logger.warning(f"No predictions for {current_date}")
                continue

            # Sort by probability and select top picks
            predictions_today = sorted(predictions_today, key=lambda x: x['surge_probability'], reverse=True)
            top_picks = [p for p in predictions_today if p['prediction'] == 1][:5]  # Top 5

            self.logger.info(f"Top picks: {len(top_picks)} stocks")

            if not top_picks:
                self.logger.info("No stocks meet threshold")
                continue

            # Simulate trades with daily monitoring (50% take profit, 5% stop loss, 10-day max)
            for pick in top_picks:
                ticker = pick['ticker']
                entry_price = pick['entry_price']

                # Simulate trade with daily monitoring
                exit_info = self.simulate_trade_with_daily_monitoring(
                    df, ticker, current_date, entry_price, max_holding_days=prediction_window
                )

                if exit_info['exit_price'] is not None:
                    pick.update(exit_info)
                    pick['profit_loss'] = exit_info['actual_return'] * 100  # As percentage

                    all_predictions.append(pick)
                    trades.append(pick)

                    # Log with exit reason
                    exit_reason_emoji = {
                        'take_profit': '🎯',
                        'stop_loss': '⛔',
                        'max_holding': '⏰'
                    }
                    emoji = exit_reason_emoji.get(exit_info['exit_reason'], '📊')

                    self.logger.info(
                        f"  {emoji} {ticker}: {exit_info['actual_return']*100:.2f}% "
                        f"(${entry_price:.2f} → ${exit_info['exit_price']:.2f}) "
                        f"[{exit_info['exit_reason']}] {exit_info.get('holding_days', 0)}d"
                    )
                else:
                    self.logger.warning(f"  {ticker}: No exit data available")

        # Calculate performance metrics - INDEPENDENT TRADES
        results = self.calculate_performance_metrics(trades)

        # Save results
        self.save_backtest_results(trades, results)

        return results

    def calculate_performance_metrics(self, trades: List[Dict]) -> Dict:
        """
        Calculate backtest performance metrics for INDEPENDENT TRADES
        Each trade is treated independently, statistics are averaged
        """
        if not trades:
            return {'error': 'No trades executed'}

        trades_df = pd.DataFrame([t for t in trades if 'actual_return' in t])

        if len(trades_df) == 0:
            return {'error': 'No completed trades'}

        # Basic stats - INDEPENDENT TRADES
        total_trades = len(trades_df)
        winning_trades = len(trades_df[trades_df['actual_return'] > 0])
        losing_trades = len(trades_df[trades_df['actual_return'] < 0])
        breakeven_trades = len(trades_df[trades_df['actual_return'] == 0])

        win_rate = winning_trades / total_trades if total_trades > 0 else 0

        # Average statistics across all independent trades
        avg_return = trades_df['actual_return'].mean()
        median_return = trades_df['actual_return'].median()
        std_return = trades_df['actual_return'].std()

        max_return = trades_df['actual_return'].max()
        min_return = trades_df['actual_return'].min()

        # Average win/loss amounts
        avg_win = trades_df[trades_df['actual_return'] > 0]['actual_return'].mean() if winning_trades > 0 else 0
        avg_loss = trades_df[trades_df['actual_return'] < 0]['actual_return'].mean() if losing_trades > 0 else 0

        # Profit factor
        total_wins = trades_df[trades_df['actual_return'] > 0]['actual_return'].sum() if winning_trades > 0 else 0
        total_losses = abs(trades_df[trades_df['actual_return'] < 0]['actual_return'].sum()) if losing_trades > 0 else 0
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')

        # Exit reason statistics
        exit_reason_counts = {}
        if 'exit_reason' in trades_df.columns:
            exit_reason_counts = trades_df['exit_reason'].value_counts().to_dict()
            take_profit_count = exit_reason_counts.get('take_profit', 0)
            stop_loss_count = exit_reason_counts.get('stop_loss', 0)
            max_holding_count = exit_reason_counts.get('max_holding', 0)

            # Success rate (take_profit / total)
            success_rate = take_profit_count / total_trades if total_trades > 0 else 0
        else:
            take_profit_count = stop_loss_count = max_holding_count = 0
            success_rate = 0

        # Average holding days
        avg_holding_days = trades_df['holding_days'].mean() if 'holding_days' in trades_df.columns else 0

        # Sharpe ratio (assuming 252 trading days, 2% risk-free rate)
        if std_return > 0:
            sharpe_ratio = (avg_return - 0.02/252) / std_return * np.sqrt(252)
        else:
            sharpe_ratio = 0

        # Simulated cumulative return (if each trade used $10,000)
        # This is NOT portfolio compounding, just sum of all returns
        simulated_initial = 10000
        simulated_total_return = avg_return * total_trades  # Sum of all returns
        simulated_final = simulated_initial * (1 + simulated_total_return)

        results = {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'breakeven_trades': breakeven_trades,
            'win_rate': win_rate,
            'avg_return_per_trade': avg_return,
            'median_return': median_return,
            'std_return': std_return,
            'max_return': max_return,
            'min_return': min_return,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe_ratio,
            'simulated_total_return': simulated_total_return,
            'simulated_final_value': simulated_final,
            # Exit reason statistics
            'take_profit_count': take_profit_count,
            'stop_loss_count': stop_loss_count,
            'max_holding_count': max_holding_count,
            'success_rate_50pct': success_rate,  # % that hit +50%
            'avg_holding_days': avg_holding_days
        }

        # Log summary
        self.logger.info("\n" + "="*70)
        self.logger.info("BACKTEST RESULTS SUMMARY (INDEPENDENT TRADES)")
        self.logger.info("="*70)
        self.logger.info(f"Total Trades: {total_trades}")
        self.logger.info(f"Win Rate: {win_rate*100:.2f}%")
        self.logger.info(f"  - Winning Trades: {winning_trades}")
        self.logger.info(f"  - Losing Trades: {losing_trades}")
        self.logger.info(f"  - Breakeven Trades: {breakeven_trades}")
        self.logger.info(f"")
        self.logger.info(f"Average Return per Trade: {avg_return*100:.2f}%")
        self.logger.info(f"Median Return per Trade: {median_return*100:.2f}%")
        self.logger.info(f"Std Dev: {std_return*100:.2f}%")
        self.logger.info(f"  - Best Trade: {max_return*100:.2f}%")
        self.logger.info(f"  - Worst Trade: {min_return*100:.2f}%")
        self.logger.info(f"  - Avg Win: {avg_win*100:.2f}%")
        self.logger.info(f"  - Avg Loss: {avg_loss*100:.2f}%")
        self.logger.info(f"")
        self.logger.info(f"Profit Factor: {profit_factor:.2f}")
        self.logger.info(f"Sharpe Ratio: {sharpe_ratio:.2f}")
        self.logger.info(f"")
        self.logger.info(f"Exit Reasons:")
        self.logger.info(f"  🎯 Take Profit (+50%): {take_profit_count} ({success_rate*100:.1f}%)")
        self.logger.info(f"  ⛔ Stop Loss (-5%): {stop_loss_count}")
        self.logger.info(f"  ⏰ Max Holding (10d): {max_holding_count}")
        self.logger.info(f"  Avg Holding Period: {avg_holding_days:.1f} days")
        self.logger.info(f"")
        self.logger.info(f"Simulated Total Return: {simulated_total_return*100:.2f}%")
        self.logger.info(f"  (If $10,000 invested in each trade independently)")
        self.logger.info("="*70)

        return results

    def save_backtest_results(self, trades: List[Dict], results: Dict):
        """Save backtest results to files"""
        # Save trades
        trades_df = pd.DataFrame([t for t in trades if 'actual_return' in t])

        if not trades_df.empty:
            trades_file = f"{self.config['output']['results_dir']}/backtest_trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            trades_df.to_csv(trades_file, index=False)
            self.logger.info(f"Trades saved to: {trades_file}")

        # Save summary
        summary_df = pd.DataFrame([results])
        summary_file = f"{self.config['output']['results_dir']}/backtest_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        summary_df.to_csv(summary_file, index=False)
        self.logger.info(f"Summary saved to: {summary_file}")


if __name__ == '__main__':
    # Run backtest
    backtester = WalkForwardBacktester()

    # Load data
    collector = PennyStockCollector(backtester.config)
    df = collector.load_data()

    if df.empty:
        print("No data available. Run training first.")
    else:
        # Run walk-forward backtest
        results = backtester.walk_forward_backtest(
            df,
            train_period_days=365,  # Use 1 year for training
            rebalance_frequency_days=30,  # Retrain monthly
            prediction_window=5  # Hold for 5 days
        )
