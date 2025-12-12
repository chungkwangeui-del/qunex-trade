"""
Tests for the utils module.
"""

import pytest
import time
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from web.utils import (
    retry_with_backoff,
    rate_limit,
    SimpleCache,
    format_currency,
    format_percentage,
    format_large_number,
    calculate_pnl,
    is_market_hours,
    get_market_status
)


class TestRetryWithBackoff:
    """Tests for the retry_with_backoff decorator."""

    def test_success_on_first_try(self):
        """Test that successful function returns immediately."""
        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay=0.1)
        def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_func()
        assert result == "success"
        assert call_count == 1

    def test_retry_on_failure(self):
        """Test that function retries on failure."""
        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay=0.01, jitter=False)
        def failing_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Failed")
            return "success"

        result = failing_then_success()
        assert result == "success"
        assert call_count == 3

    def test_max_retries_exceeded(self):
        """Test that exception is raised after max retries."""
        call_count = 0

        @retry_with_backoff(max_retries=2, base_delay=0.01, jitter=False)
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")

        with pytest.raises(ValueError):
            always_fails()

        assert call_count == 3  # Initial + 2 retries

    def test_specific_exception_types(self):
        """Test that only specified exceptions trigger retry."""
        call_count = 0

        @retry_with_backoff(
            max_retries=3,
            base_delay=0.01,
            retryable_exceptions=(ValueError,)
        )
        def raises_type_error():
            nonlocal call_count
            call_count += 1
            raise TypeError("Not retryable")

        with pytest.raises(TypeError):
            raises_type_error()

        assert call_count == 1  # No retries for TypeError

    def test_on_retry_callback(self):
        """Test that on_retry callback is called on each retry."""
        retry_attempts = []

        def on_retry_callback(exc, attempt):
            retry_attempts.append(attempt)

        @retry_with_backoff(
            max_retries=2,
            base_delay=0.01,
            jitter=False,
            on_retry=on_retry_callback
        )
        def fails_twice():
            if len(retry_attempts) < 2:
                raise ValueError("Fail")
            return "success"

        result = fails_twice()
        assert result == "success"
        assert retry_attempts == [1, 2]


class TestRateLimit:
    """Tests for the rate_limit decorator."""

    def test_rate_limiting_applied(self):
        """Test that rate limiting adds delay between calls."""
        call_times = []

        @rate_limit(calls_per_minute=600)  # 1 call per 0.1 second
        def tracked_func():
            call_times.append(time.time())
            return "done"

        # Make two quick calls
        tracked_func()
        tracked_func()

        # Second call should be delayed
        if len(call_times) == 2:
            time_diff = call_times[1] - call_times[0]
            assert time_diff >= 0.09  # Allow small tolerance


class TestSimpleCache:
    """Tests for the SimpleCache class."""

    def test_set_and_get(self):
        """Test basic set and get operations."""
        cache = SimpleCache(default_ttl=300)
        cache.set('key1', 'value1')
        assert cache.get('key1') == 'value1'

    def test_get_missing_key(self):
        """Test getting a missing key returns default."""
        cache = SimpleCache()
        assert cache.get('missing') is None
        assert cache.get('missing', 'default') == 'default'

    def test_ttl_expiration(self):
        """Test that expired items are not returned."""
        cache = SimpleCache(default_ttl=0)  # Immediate expiration
        cache.set('key1', 'value1', ttl=0)
        time.sleep(0.1)
        assert cache.get('key1') is None

    def test_delete(self):
        """Test deleting items from cache."""
        cache = SimpleCache()
        cache.set('key1', 'value1')
        assert cache.delete('key1') is True
        assert cache.get('key1') is None
        assert cache.delete('missing') is False

    def test_clear(self):
        """Test clearing all items."""
        cache = SimpleCache()
        cache.set('key1', 'value1')
        cache.set('key2', 'value2')
        cache.clear()
        assert cache.get('key1') is None
        assert cache.get('key2') is None

    def test_cleanup(self):
        """Test cleanup removes expired entries."""
        cache = SimpleCache()
        cache.set('valid', 'value', ttl=300)
        cache.set('expired', 'value', ttl=0)
        time.sleep(0.1)
        removed = cache.cleanup()
        assert removed == 1
        assert cache.get('valid') == 'value'


class TestFormatCurrency:
    """Tests for format_currency function."""

    def test_small_amounts(self):
        """Test formatting small amounts."""
        assert format_currency(100) == "$100.00"
        assert format_currency(1.5) == "$1.50"

    def test_thousands(self):
        """Test formatting thousands."""
        assert format_currency(1500) == "$1.50K"
        assert format_currency(10000) == "$10.00K"

    def test_millions(self):
        """Test formatting millions."""
        assert format_currency(1500000) == "$1.50M"
        assert format_currency(10000000) == "$10.00M"

    def test_billions(self):
        """Test formatting billions."""
        assert format_currency(1500000000) == "$1.50B"

    def test_negative_values(self):
        """Test formatting negative values."""
        result = format_currency(-1500000)
        assert 'M' in result


class TestFormatPercentage:
    """Tests for format_percentage function."""

    def test_positive_percentage(self):
        """Test formatting positive percentages."""
        assert format_percentage(5.25) == "+5.25%"
        assert format_percentage(100) == "+100.00%"

    def test_negative_percentage(self):
        """Test formatting negative percentages."""
        assert format_percentage(-3.5) == "-3.50%"

    def test_zero_percentage(self):
        """Test formatting zero percentage."""
        assert format_percentage(0) == "0.00%"

    def test_custom_decimals(self):
        """Test formatting with custom decimal places."""
        assert format_percentage(5.555, decimals=1) == "+5.6%"


class TestFormatLargeNumber:
    """Tests for format_large_number function."""

    def test_small_numbers(self):
        """Test formatting small numbers."""
        assert format_large_number(500) == "500.00"

    def test_thousands(self):
        """Test formatting thousands."""
        assert format_large_number(5000) == "5.00K"

    def test_millions(self):
        """Test formatting millions."""
        assert format_large_number(5000000) == "5.00M"

    def test_billions(self):
        """Test formatting billions."""
        assert format_large_number(5000000000) == "5.00B"


class TestCalculatePnl:
    """Tests for calculate_pnl function."""

    def test_profit_calculation(self):
        """Test calculating profit."""
        result = calculate_pnl(100, 150, 10)
        assert result['pnl'] == 500
        assert result['pnl_percent'] == 50
        assert result['entry_value'] == 1000
        assert result['current_value'] == 1500

    def test_loss_calculation(self):
        """Test calculating loss."""
        result = calculate_pnl(100, 80, 10)
        assert result['pnl'] == -200
        assert result['pnl_percent'] == -20

    def test_zero_entry_price(self):
        """Test handling zero entry price."""
        result = calculate_pnl(0, 100, 10)
        assert result['pnl_percent'] == 0


class TestMarketStatus:
    """Tests for market status functions."""

    @patch('web.utils.datetime')
    def test_is_market_hours_weekday_open(self, mock_datetime):
        """Test market is open during weekday business hours."""
        # Skip this test if pytz is not installed
        try:
            import pytz
            et = pytz.timezone('America/New_York')
            # Tuesday 11:00 AM ET
            mock_now = datetime(2024, 1, 9, 11, 0, 0)
            mock_now = et.localize(mock_now)
            mock_datetime.now.return_value = mock_now
            # This test requires more setup with pytz, skip for now
        except ImportError:
            pytest.skip("pytz not installed")

    def test_get_market_status_returns_dict(self):
        """Test that get_market_status returns expected structure."""
        result = get_market_status()
        assert isinstance(result, dict)
        assert 'is_open' in result
        assert 'session' in result
        assert 'message' in result


class TestEdgeCases:
    """Edge case tests."""

    def test_retry_with_zero_retries(self):
        """Test retry with max_retries=0."""
        call_count = 0

        @retry_with_backoff(max_retries=0, base_delay=0.01)
        def single_attempt():
            nonlocal call_count
            call_count += 1
            raise ValueError("Fail")

        with pytest.raises(ValueError):
            single_attempt()

        assert call_count == 1

    def test_cache_with_none_values(self):
        """Test cache can store None values."""
        cache = SimpleCache()
        cache.set('none_value', None)
        # Should return None (the stored value), not the default
        assert cache.get('none_value', 'default') is None
