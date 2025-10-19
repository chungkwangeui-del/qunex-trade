"""
Utility functions for penny stock prediction system
"""

import os
import yaml
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path


def load_config(config_path='config.yaml'):
    """Load configuration from YAML file"""
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config


def setup_logging(config):
    """Setup logging configuration"""
    log_level = getattr(logging, config['logging']['level'])
    log_file = config['logging']['log_file']

    # Create logs directory if it doesn't exist
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

    return logging.getLogger(__name__)


def ensure_directories(config):
    """Ensure all required directories exist"""
    dirs = [
        config['output']['models_dir'],
        config['output']['data_dir'],
        config['output']['results_dir'],
        config['output']['plots_dir'],
        'logs'
    ]

    for dir_path in dirs:
        os.makedirs(dir_path, exist_ok=True)


def get_date_range(lookback_days):
    """Get start and end dates for data collection"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=lookback_days)
    return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')


def save_dataframe(df, filename, data_dir='data'):
    """Save dataframe to CSV file"""
    filepath = os.path.join(data_dir, filename)
    df.to_csv(filepath, index=False)
    logging.info(f"Data saved to {filepath}")


def load_dataframe(filename, data_dir='data'):
    """Load dataframe from CSV file"""
    filepath = os.path.join(data_dir, filename)
    if os.path.exists(filepath):
        df = pd.read_csv(filepath)
        logging.info(f"Data loaded from {filepath}")
        return df
    else:
        logging.warning(f"File not found: {filepath}")
        return None


def calculate_returns(prices, periods=[1, 3, 5, 7, 10]):
    """Calculate returns for multiple periods"""
    returns = {}
    for period in periods:
        returns[f'return_{period}d'] = prices.pct_change(periods=period)
    return pd.DataFrame(returns)


def detect_outliers(data, column, method='iqr', threshold=1.5):
    """Detect outliers in data using IQR method"""
    if method == 'iqr':
        Q1 = data[column].quantile(0.25)
        Q3 = data[column].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - threshold * IQR
        upper_bound = Q3 + threshold * IQR
        outliers = (data[column] < lower_bound) | (data[column] > upper_bound)
    elif method == 'zscore':
        z_scores = np.abs((data[column] - data[column].mean()) / data[column].std())
        outliers = z_scores > threshold
    else:
        raise ValueError(f"Unknown method: {method}")

    return outliers


def normalize_data(data, method='minmax'):
    """Normalize data using specified method"""
    if method == 'minmax':
        return (data - data.min()) / (data.max() - data.min())
    elif method == 'zscore':
        return (data - data.mean()) / data.std()
    else:
        raise ValueError(f"Unknown normalization method: {method}")


def split_train_test(X, y, test_size=0.2, shuffle=False):
    """Split data into train and test sets"""
    from sklearn.model_selection import train_test_split
    return train_test_split(X, y, test_size=test_size, shuffle=shuffle, random_state=42)


def get_trading_days(start_date, end_date):
    """Get list of trading days between start and end date"""
    from pandas.tseries.offsets import BDay
    return pd.date_range(start=start_date, end=end_date, freq=BDay())


class ProgressTracker:
    """Track progress of operations"""

    def __init__(self, total, desc='Processing'):
        from tqdm import tqdm
        self.pbar = tqdm(total=total, desc=desc)

    def update(self, n=1):
        self.pbar.update(n)

    def close(self):
        self.pbar.close()


def format_percentage(value):
    """Format value as percentage"""
    return f"{value * 100:.2f}%"


def format_currency(value):
    """Format value as currency"""
    return f"${value:,.2f}"


def calculate_sharpe_ratio(returns, risk_free_rate=0.02):
    """Calculate Sharpe ratio"""
    excess_returns = returns - risk_free_rate / 252  # Daily risk-free rate
    return np.sqrt(252) * excess_returns.mean() / excess_returns.std()


def calculate_max_drawdown(returns):
    """Calculate maximum drawdown"""
    cumulative = (1 + returns).cumprod()
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max
    return drawdown.min()
