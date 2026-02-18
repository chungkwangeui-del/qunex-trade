"""
Utility functions for the trading application.
Includes data fetching, retry logic, caching helpers, and common operations.
"""

import time
import random
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Callable, TypeVar, Optional, Any
from functools import wraps
from datetime import timedelta
from datetime import timezone
from typing import Dict
from typing import Optional
from typing import Any
from typing import Tuple

logger = logging.getLogger(__name__)

T = TypeVar('T')


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: tuple = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None
):
    """
    Decorator that retries a function with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential backoff calculation
        jitter: Whether to add random jitter to prevent thundering herd
        retryable_exceptions: Tuple of exception types to retry on
        on_retry: Optional callback function called on each retry (exception, attempt_number)

    Usage:
        @retry_with_backoff(max_retries=3, base_delay=1.0)
        def fetch_data():
            return api.get_data()
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e

                    if attempt == max_retries:
                        logger.error(
                            f"{func.__name__} failed after {max_retries + 1} attempts: {e}"
                        )
                        raise

                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (exponential_base ** attempt), max_delay)

                    # Add jitter (±25%)
                    if jitter:
                        delay = delay * (0.75 + random.random() * 0.5)

                    logger.warning(
                        f"{func.__name__} attempt {attempt + 1}/{max_retries + 1} failed: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )

                    if on_retry:
                        on_retry(e, attempt + 1)

                    time.sleep(delay)

            raise last_exception
        return wrapper
    return decorator


def rate_limit(calls_per_minute: int = 60):
    """
    Simple rate limiter decorator for API calls.

    Args:
        calls_per_minute: Maximum allowed calls per minute

    Usage:
        @rate_limit(calls_per_minute=30)
        def call_api():
            return api.request()
    """
    min_interval = 60.0 / calls_per_minute
    last_called = {}

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            func_name = func.__name__
            now = time.time()

            if func_name in last_called:
                elapsed = now - last_called[func_name]
                if elapsed < min_interval:
                    sleep_time = min_interval - elapsed
                    logger.debug(f"Rate limiting {func_name}: sleeping {sleep_time:.2f}s")
                    time.sleep(sleep_time)

            last_called[func_name] = time.time()
            return func(*args, **kwargs)
        return wrapper
    return decorator


class SimpleCache:
    """
    Simple in-memory cache with TTL support.

    Usage:
        cache = SimpleCache(default_ttl=300)  # 5 minute default TTL
        cache.set('key', 'value')
        value = cache.get('key')
    """

    def __init__(self, default_ttl: int = 300):
        self._cache: Dict[str, tuple] = {}
        self._default_ttl = default_ttl

    def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache if not expired."""
        if key not in self._cache:
            return default

        value, expires_at = self._cache[key]
        if datetime.now() > expires_at:
            del self._cache[key]
            return default

        return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL."""
        ttl = ttl if ttl is not None else self._default_ttl
        expires_at = datetime.now() + timedelta(seconds=ttl)
        self._cache[key] = (value, expires_at)

    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()

    def cleanup(self) -> int:
        """Remove expired entries. Returns count of removed entries."""
        now = datetime.now()
        expired_keys = [
            key for key, (_, expires_at) in self._cache.items()
            if now > expires_at
        ]
        for key in expired_keys:
            del self._cache[key]
        return len(expired_keys)


def format_currency(value: float, currency: str = 'USD') -> str:
    """Format a number as currency string."""
    if currency == 'USD':
        if abs(value) >= 1_000_000_000:
            return f"${value/1_000_000_000:.2f}B"
        elif abs(value) >= 1_000_000:
            return f"${value/1_000_000:.2f}M"
        elif abs(value) >= 1_000:
            return f"${value/1_000:.2f}K"
        else:
            return f"${value:,.2f}"
    return f"{value:,.2f} {currency}"


def format_percentage(value: float, decimals: int = 2) -> str:
    """Format a number as percentage string."""
    sign = '+' if value > 0 else ''
    return f"{sign}{value:.{decimals}f}%"


def format_large_number(value: float) -> str:
    """Format large numbers with K/M/B suffixes."""
    if abs(value) >= 1_000_000_000:
        return f"{value/1_000_000_000:.2f}B"
    elif abs(value) >= 1_000_000:
        return f"{value/1_000_000:.2f}M"
    elif abs(value) >= 1_000:
        return f"{value/1_000:.2f}K"
    return f"{value:.2f}"


def calculate_pnl(entry_price: float, current_price: float, shares: float) -> Dict[str, float]:
    """
    Calculate profit/loss for a position.

    Returns:
        Dictionary with pnl, pnl_percent, entry_value, current_value
    """
    entry_value = entry_price * shares
    current_value = current_price * shares
    pnl = current_value - entry_value
    pnl_percent = ((current_price - entry_price) / entry_price * 100) if entry_price > 0 else 0

    return {
        'pnl': round(pnl, 2),
        'pnl_percent': round(pnl_percent, 2),
        'entry_value': round(entry_value, 2),
        'current_value': round(current_value, 2)
    }


def is_market_hours() -> bool:
    """
    Check if US stock market is currently open.
    Market hours: 9:30 AM - 4:00 PM ET, Monday-Friday
    """
    import pytz

    try:
        et = pytz.timezone('America/New_York')
        now = datetime.now(et)

        # Check if weekend
        if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False

        # Market hours: 9:30 AM - 4:00 PM ET
        market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)

        return market_open <= now <= market_close
    except Exception:
        # Fallback: assume market is open during weekday business hours
        now = datetime.now()
        if now.weekday() >= 5:
            return False
        return 9 <= now.hour < 16


def get_market_status() -> Dict[str, Any]:
    """
    Get detailed market status including pre-market and after-hours.

    Returns:
        Dictionary with status, next_open, next_close, session type
    """
    import pytz

    try:
        et = pytz.timezone('America/New_York')
        now = datetime.now(et)

        def make_datetime(date_obj, hour, minute=0):
            """Create timezone-aware datetime in ET for given date and time."""
            naive = datetime(
                year=date_obj.year,
                month=date_obj.month,
                day=date_obj.day,
                hour=hour,
                minute=minute,
                second=0,
                microsecond=0
            )
            return et.localize(naive)

        def get_next_trading_day(date_obj):
            """Return the next weekday date (Mon-Fri) after the given date."""
            next_day = date_obj + timedelta(days=1)
            while next_day.weekday() >= 5:
                next_day += timedelta(days=1)
            return next_day

        result = {
            'is_open': False,
            'session': 'closed',
            'message': '',
            'next_open': None,
            'next_close': None
        }

        today = now.date()
        pre_market_dt = make_datetime(today, 4)
        regular_open_dt = make_datetime(today, 9, 30)
        regular_close_dt = make_datetime(today, 16)
        after_hours_close_dt = make_datetime(today, 20)

        # Weekend handling: jump to next Monday (or next weekday if holiday logic added later)
        if now.weekday() >= 5:
            next_trading_day = get_next_trading_day(today)
            result['message'] = 'Market closed (weekend)'
            result['next_open'] = make_datetime(next_trading_day, 4)
            result['next_close'] = make_datetime(next_trading_day, 20)
            return result

        next_trading_day = get_next_trading_day(today)
        next_pre_market = make_datetime(next_trading_day, 4)
        next_after_hours_close = make_datetime(next_trading_day, 20)

        hour = now.hour
        minute = now.minute
        current_time = hour * 60 + minute

        pre_market_start = 4 * 60  # 4:00 AM
        market_open = 9 * 60 + 30  # 9:30 AM
        market_close = 16 * 60  # 4:00 PM
        after_hours_end = 20 * 60  # 8:00 PM

        if current_time < pre_market_start:
            result['session'] = 'overnight'
            result['message'] = 'Pre-market opens at 4:00 AM ET'
            result['next_open'] = pre_market_dt
            result['next_close'] = after_hours_close_dt
        elif current_time < market_open:
            result['session'] = 'pre_market'
            result['message'] = 'Pre-market trading (4:00 AM - 9:30 AM ET)'
            result['next_open'] = regular_open_dt
            result['next_close'] = after_hours_close_dt
        elif current_time < market_close:
            result['is_open'] = True
            result['session'] = 'regular'
            result['message'] = 'Market open (9:30 AM - 4:00 PM ET)'
            result['next_open'] = next_pre_market
            result['next_close'] = regular_close_dt
        elif current_time < after_hours_end:
            result['session'] = 'after_hours'
            result['message'] = 'After-hours trading (4:00 PM - 8:00 PM ET)'
            result['next_open'] = next_pre_market
            result['next_close'] = after_hours_close_dt
        else:
            result['session'] = 'closed'
            result['message'] = 'Market closed for the day'
            result['next_open'] = next_pre_market
            result['next_close'] = next_after_hours_close

        return result

    except Exception as e:
        logger.error(f"Error getting market status: {e}")
        return {
            'is_open': False,
            'session': 'unknown',
            'message': 'Unable to determine market status'
        }


# Moved get_news_articles and get_economic_events to src/services/db_service.py
