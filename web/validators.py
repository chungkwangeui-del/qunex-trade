"""
Input validators for trading application.
Provides reusable validation functions for tickers, prices, quantities, etc.
"""

import re
import logging
from typing import Optional, Tuple
from functools import wraps
from flask import jsonify, request
from datetime import timedelta
from typing import Tuple

logger = logging.getLogger(__name__)

# Valid US stock ticker pattern: 1-5 uppercase letters
# Some special tickers include numbers or dots (e.g., BRK.A, BRK.B)
TICKER_PATTERN = re.compile(r'^[A-Z]{1,5}(\.[A-Z])?$')

# Crypto ticker pattern (e.g., BTC, ETH, BTCUSDT)
CRYPTO_PATTERN = re.compile(r'^[A-Z]{2,10}(USDT|USD|BTC|ETH)?$')

# Reserved/invalid tickers that should be rejected
RESERVED_TICKERS = {'TEST', 'NULL', 'NONE', 'UNDEFINED', 'NAN'}


def validate_ticker(ticker: str, allow_crypto: bool = False) -> Tuple[bool, str, Optional[str]]:
    """
    Validate a stock/crypto ticker symbol.

    Args:
        ticker: The ticker symbol to validate
        allow_crypto: Whether to allow cryptocurrency tickers

    Returns:
        Tuple of (is_valid, error_message, normalized_ticker)
    """
    if not ticker:
        return False, "Ticker symbol is required", None

    # Normalize: uppercase and strip whitespace
    normalized = ticker.upper().strip()

    # Check length
    if len(normalized) < 1 or len(normalized) > 10:
        return False, "Ticker must be 1-10 characters", None

    # Check for reserved/invalid tickers
    if normalized in RESERVED_TICKERS:
        return False, f"'{normalized}' is not a valid ticker symbol", None

    # Check pattern
    if TICKER_PATTERN.match(normalized):
        return True, "", normalized

    if allow_crypto and CRYPTO_PATTERN.match(normalized):
        return True, "", normalized

    return False, f"'{ticker}' is not a valid ticker format. Use 1-5 letters (e.g., AAPL, MSFT)", None


def validate_price(price: any, min_price: float = 0.0001, max_price: float = 1000000) -> Tuple[bool, str, Optional[float]]:
    """
    Validate a price value.

    Args:
        price: The price to validate
        min_price: Minimum allowed price
        max_price: Maximum allowed price

    Returns:
        Tuple of (is_valid, error_message, validated_price)
    """
    if price is None:
        return False, "Price is required", None

    try:
        price_float = float(price)
    except (ValueError, TypeError):
        return False, "Price must be a number", None

    if price_float <= 0:
        return False, "Price must be greater than 0", None

    if price_float < min_price:
        return False, f"Price must be at least ${min_price}", None

    if price_float > max_price:
        return False, f"Price cannot exceed ${max_price:,.2f}", None

    return True, "", round(price_float, 4)


def validate_quantity(quantity: any, min_qty: float = 0.0001, max_qty: float = 1000000000) -> Tuple[bool, str, Optional[float]]:
    """
    Validate a quantity/shares value.

    Args:
        quantity: The quantity to validate
        min_qty: Minimum allowed quantity
        max_qty: Maximum allowed quantity

    Returns:
        Tuple of (is_valid, error_message, validated_quantity)
    """
    if quantity is None:
        return False, "Quantity is required", None

    try:
        qty_float = float(quantity)
    except (ValueError, TypeError):
        return False, "Quantity must be a number", None

    if qty_float <= 0:
        return False, "Quantity must be greater than 0", None

    if qty_float < min_qty:
        return False, f"Quantity must be at least {min_qty}", None

    if qty_float > max_qty:
        return False, f"Quantity cannot exceed {max_qty:,.0f}", None

    return True, "", qty_float


def validate_timeframe(timeframe: str) -> Tuple[bool, str, Optional[str]]:
    """
    Validate a chart timeframe.

    Args:
        timeframe: The timeframe to validate (e.g., '1m', '5m', '1h', '1d')

    Returns:
        Tuple of (is_valid, error_message, normalized_timeframe)
    """
    valid_timeframes = {
        '1m', '2m', '3m', '5m', '15m', '30m',  # Minutes
        '1h', '2h', '4h',  # Hours
        '1d', '1w', '1M',  # Day, Week, Month
        'minute', 'hour', 'day', 'week', 'month'  # Alternative formats
    }

    if not timeframe:
        return False, "Timeframe is required", None

    normalized = timeframe.strip()

    if normalized not in valid_timeframes:
        return False, f"Invalid timeframe '{timeframe}'. Valid options: {', '.join(sorted(valid_timeframes))}", None

    return True, "", normalized


def validate_date_range(start_date: str, end_date: str) -> Tuple[bool, str, Optional[Tuple]]:
    """
    Validate a date range.

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format

    Returns:
        Tuple of (is_valid, error_message, (start_datetime, end_datetime))
    """
    from datetime import datetime, timedelta

    date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')

    if not date_pattern.match(start_date):
        return False, "Start date must be in YYYY-MM-DD format", None

    if not date_pattern.match(end_date):
        return False, "End date must be in YYYY-MM-DD format", None

    try:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    except ValueError as e:
        return False, f"Invalid date: {e}", None

    if start_dt > end_dt:
        return False, "Start date must be before end date", None

    # Max 5 years range
    max_range = timedelta(days=365 * 5)
    if end_dt - start_dt > max_range:
        return False, "Date range cannot exceed 5 years", None

    return True, "", (start_dt, end_dt)


def require_valid_ticker(allow_crypto: bool = False):
    """
    Decorator to validate ticker parameter in Flask routes.
    Expects ticker as route parameter or in query string.

    Usage:
        @app.route('/api/quote/<ticker>')
        @require_valid_ticker()
        def get_quote(ticker):
            # ticker is guaranteed to be valid here
            pass
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check route parameter first
            ticker = kwargs.get('ticker') or request.args.get('ticker') or request.args.get('symbol')

            if not ticker:
                # Try to get from JSON body
                if request.is_json:
                    data = request.get_json(silent=True) or {}
                    ticker = data.get('ticker') or data.get('symbol')

            is_valid, error, normalized = validate_ticker(ticker, allow_crypto)

            if not is_valid:
                logger.warning(f"Invalid ticker rejected: {ticker} - {error}")
                return jsonify({
                    'success': False,
                    'error': error,
                    'code': 'INVALID_TICKER'
                }), 400

            # Update kwargs with normalized ticker
            if 'ticker' in kwargs:
                kwargs['ticker'] = normalized

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def sanitize_search_input(query: str, max_length: int = 100) -> str:
    """
    Sanitize user search input to prevent injection attacks.

    Args:
        query: User's search query
        max_length: Maximum allowed length

    Returns:
        Sanitized query string
    """
    if not query:
        return ""

    # Remove potentially dangerous characters
    sanitized = re.sub(r'[<>"\';(){}[\]\\]', '', query)

    # Truncate to max length
    sanitized = sanitized[:max_length]

    # Strip whitespace
    sanitized = sanitized.strip()

    return sanitized


class ValidationError(Exception):
    """Custom exception for validation errors."""

    def __init__(self, message: str, field: str = None, code: str = 'VALIDATION_ERROR'):
        self.message = message
        self.field = field
        self.code = code
        super().__init__(self.message)

    def to_dict(self):
        return {
            'success': False,
            'error': self.message,
            'field': self.field,
            'code': self.code
        }


def validate_trading_data(data: dict) -> dict:
    """
    Validate complete trading transaction data.

    Args:
        data: Dictionary with ticker, shares, price, transaction_type

    Returns:
        Validated and normalized data dictionary

    Raises:
        ValidationError: If any field is invalid
    """
    if not data:
        raise ValidationError("No data provided", code='NO_DATA')

    # Validate ticker
    is_valid, error, ticker = validate_ticker(data.get('ticker', ''))
    if not is_valid:
        raise ValidationError(error, field='ticker', code='INVALID_TICKER')

    # Validate shares
    is_valid, error, shares = validate_quantity(data.get('shares'))
    if not is_valid:
        raise ValidationError(error, field='shares', code='INVALID_QUANTITY')

    # Validate price
    is_valid, error, price = validate_price(data.get('price'))
    if not is_valid:
        raise ValidationError(error, field='price', code='INVALID_PRICE')

    # Validate transaction type
    transaction_type = str(data.get('transaction_type', 'buy')).lower().strip()
    if transaction_type not in ('buy', 'sell'):
        raise ValidationError(
            "Transaction type must be 'buy' or 'sell'",
            field='transaction_type',
            code='INVALID_TRANSACTION_TYPE'
        )

    return {
        'ticker': ticker,
        'shares': shares,
        'price': price,
        'transaction_type': transaction_type
    }
