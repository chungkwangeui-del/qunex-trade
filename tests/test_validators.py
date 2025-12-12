"""
Tests for the validators module.
"""

import pytest
from web.validators import (
    validate_ticker,
    validate_price,
    validate_quantity,
    validate_timeframe,
    validate_date_range,
    sanitize_search_input,
    ValidationError,
    validate_trading_data
)


class TestValidateTicker:
    """Tests for ticker validation."""

    def test_valid_tickers(self):
        """Test that valid tickers pass validation."""
        valid_tickers = ['AAPL', 'MSFT', 'A', 'AB', 'ABCDE', 'BRK.A', 'BRK.B']
        for ticker in valid_tickers:
            is_valid, error, normalized = validate_ticker(ticker)
            assert is_valid, f"'{ticker}' should be valid, got error: {error}"
            assert normalized == ticker.upper()

    def test_lowercase_tickers_normalized(self):
        """Test that lowercase tickers are normalized to uppercase."""
        is_valid, error, normalized = validate_ticker('aapl')
        assert is_valid
        assert normalized == 'AAPL'

    def test_tickers_with_whitespace(self):
        """Test that tickers with whitespace are trimmed."""
        is_valid, error, normalized = validate_ticker('  AAPL  ')
        assert is_valid
        assert normalized == 'AAPL'

    def test_empty_ticker_rejected(self):
        """Test that empty tickers are rejected."""
        is_valid, error, normalized = validate_ticker('')
        assert not is_valid
        assert 'required' in error.lower()

    def test_none_ticker_rejected(self):
        """Test that None tickers are rejected."""
        is_valid, error, normalized = validate_ticker(None)
        assert not is_valid

    def test_too_long_ticker_rejected(self):
        """Test that very long tickers are rejected."""
        is_valid, error, normalized = validate_ticker('ABCDEFGHIJK')
        assert not is_valid

    def test_invalid_characters_rejected(self):
        """Test that tickers with invalid characters are rejected."""
        invalid_tickers = ['AAP1', 'AAPL!', 'AA PL', 'A-A', 'A@PL']
        for ticker in invalid_tickers:
            is_valid, error, normalized = validate_ticker(ticker)
            assert not is_valid, f"'{ticker}' should be invalid"

    def test_reserved_tickers_rejected(self):
        """Test that reserved tickers are rejected."""
        reserved = ['TEST', 'NULL', 'NONE', 'UNDEFINED', 'NAN']
        for ticker in reserved:
            is_valid, error, normalized = validate_ticker(ticker)
            assert not is_valid, f"'{ticker}' should be rejected as reserved"

    def test_crypto_tickers_rejected_by_default(self):
        """Test that crypto tickers are rejected when allow_crypto=False."""
        is_valid, error, normalized = validate_ticker('BTCUSDT', allow_crypto=False)
        assert not is_valid

    def test_crypto_tickers_allowed_when_enabled(self):
        """Test that crypto tickers pass when allow_crypto=True."""
        crypto_tickers = ['BTC', 'ETH', 'BTCUSDT', 'ETHUSDT', 'SOLUSDT']
        for ticker in crypto_tickers:
            is_valid, error, normalized = validate_ticker(ticker, allow_crypto=True)
            assert is_valid, f"'{ticker}' should be valid crypto ticker"


class TestValidatePrice:
    """Tests for price validation."""

    def test_valid_prices(self):
        """Test that valid prices pass validation."""
        valid_prices = [0.01, 1.0, 100, 1000.50, 999999]
        for price in valid_prices:
            is_valid, error, validated = validate_price(price)
            assert is_valid, f"{price} should be valid, got error: {error}"

    def test_zero_price_rejected(self):
        """Test that zero price is rejected."""
        is_valid, error, validated = validate_price(0)
        assert not is_valid
        assert 'greater than 0' in error.lower()

    def test_negative_price_rejected(self):
        """Test that negative prices are rejected."""
        is_valid, error, validated = validate_price(-10)
        assert not is_valid

    def test_none_price_rejected(self):
        """Test that None price is rejected."""
        is_valid, error, validated = validate_price(None)
        assert not is_valid
        assert 'required' in error.lower()

    def test_string_price_converted(self):
        """Test that string prices are converted to float."""
        is_valid, error, validated = validate_price('10.50')
        assert is_valid
        assert validated == 10.50

    def test_invalid_string_rejected(self):
        """Test that non-numeric strings are rejected."""
        is_valid, error, validated = validate_price('abc')
        assert not is_valid
        assert 'number' in error.lower()

    def test_price_below_minimum_rejected(self):
        """Test that prices below minimum are rejected."""
        is_valid, error, validated = validate_price(0.00001, min_price=0.0001)
        assert not is_valid

    def test_price_above_maximum_rejected(self):
        """Test that prices above maximum are rejected."""
        is_valid, error, validated = validate_price(2000000, max_price=1000000)
        assert not is_valid


class TestValidateQuantity:
    """Tests for quantity validation."""

    def test_valid_quantities(self):
        """Test that valid quantities pass validation."""
        valid_quantities = [1, 10, 100, 0.5, 1000000]
        for qty in valid_quantities:
            is_valid, error, validated = validate_quantity(qty)
            assert is_valid, f"{qty} should be valid"

    def test_zero_quantity_rejected(self):
        """Test that zero quantity is rejected."""
        is_valid, error, validated = validate_quantity(0)
        assert not is_valid

    def test_negative_quantity_rejected(self):
        """Test that negative quantities are rejected."""
        is_valid, error, validated = validate_quantity(-5)
        assert not is_valid

    def test_string_quantity_converted(self):
        """Test that string quantities are converted."""
        is_valid, error, validated = validate_quantity('100')
        assert is_valid
        assert validated == 100.0


class TestValidateTimeframe:
    """Tests for timeframe validation."""

    def test_valid_timeframes(self):
        """Test that valid timeframes pass."""
        valid_timeframes = ['1m', '5m', '15m', '1h', '4h', '1d', '1w']
        for tf in valid_timeframes:
            is_valid, error, validated = validate_timeframe(tf)
            assert is_valid, f"'{tf}' should be valid"

    def test_invalid_timeframe_rejected(self):
        """Test that invalid timeframes are rejected."""
        is_valid, error, validated = validate_timeframe('10m')
        assert not is_valid

    def test_empty_timeframe_rejected(self):
        """Test that empty timeframe is rejected."""
        is_valid, error, validated = validate_timeframe('')
        assert not is_valid


class TestValidateDateRange:
    """Tests for date range validation."""

    def test_valid_date_range(self):
        """Test that valid date ranges pass."""
        is_valid, error, dates = validate_date_range('2024-01-01', '2024-12-31')
        assert is_valid
        assert dates is not None
        assert dates[0].year == 2024

    def test_invalid_date_format_rejected(self):
        """Test that invalid date formats are rejected."""
        is_valid, error, dates = validate_date_range('01-01-2024', '12-31-2024')
        assert not is_valid
        assert 'YYYY-MM-DD' in error

    def test_start_after_end_rejected(self):
        """Test that start date after end date is rejected."""
        is_valid, error, dates = validate_date_range('2024-12-31', '2024-01-01')
        assert not is_valid
        assert 'before' in error.lower()

    def test_range_too_long_rejected(self):
        """Test that date ranges > 5 years are rejected."""
        is_valid, error, dates = validate_date_range('2015-01-01', '2025-01-01')
        assert not is_valid
        assert '5 years' in error


class TestSanitizeSearchInput:
    """Tests for search input sanitization."""

    def test_normal_input_unchanged(self):
        """Test that normal input passes through."""
        result = sanitize_search_input('AAPL stock')
        assert result == 'AAPL stock'

    def test_dangerous_characters_removed(self):
        """Test that dangerous characters are removed."""
        result = sanitize_search_input('<script>alert("xss")</script>')
        assert '<' not in result
        assert '>' not in result
        assert '"' not in result

    def test_sql_injection_characters_removed(self):
        """Test that SQL injection characters are removed."""
        result = sanitize_search_input("'; DROP TABLE users; --")
        assert "'" not in result
        assert ';' not in result

    def test_long_input_truncated(self):
        """Test that long input is truncated."""
        long_input = 'a' * 200
        result = sanitize_search_input(long_input, max_length=100)
        assert len(result) == 100

    def test_empty_input(self):
        """Test that empty input returns empty string."""
        assert sanitize_search_input('') == ''
        assert sanitize_search_input(None) == ''


class TestValidateTradingData:
    """Tests for complete trading data validation."""

    def test_valid_trading_data(self):
        """Test that valid trading data passes."""
        data = {
            'ticker': 'AAPL',
            'shares': 100,
            'price': 150.50,
            'transaction_type': 'buy'
        }
        result = validate_trading_data(data)
        assert result['ticker'] == 'AAPL'
        assert result['shares'] == 100
        assert result['price'] == 150.50
        assert result['transaction_type'] == 'buy'

    def test_missing_data_raises_error(self):
        """Test that missing data raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_trading_data(None)
        assert exc_info.value.code == 'NO_DATA'

    def test_invalid_ticker_raises_error(self):
        """Test that invalid ticker raises ValidationError."""
        data = {
            'ticker': 'INVALID123',
            'shares': 100,
            'price': 150.50,
            'transaction_type': 'buy'
        }
        with pytest.raises(ValidationError) as exc_info:
            validate_trading_data(data)
        assert exc_info.value.field == 'ticker'

    def test_invalid_transaction_type_raises_error(self):
        """Test that invalid transaction type raises ValidationError."""
        data = {
            'ticker': 'AAPL',
            'shares': 100,
            'price': 150.50,
            'transaction_type': 'trade'  # Should be 'buy' or 'sell'
        }
        with pytest.raises(ValidationError) as exc_info:
            validate_trading_data(data)
        assert exc_info.value.field == 'transaction_type'

    def test_data_normalized(self):
        """Test that data is normalized properly."""
        data = {
            'ticker': 'aapl',  # lowercase
            'shares': '100',    # string
            'price': '150.50',  # string
            'transaction_type': 'BUY'  # uppercase
        }
        result = validate_trading_data(data)
        assert result['ticker'] == 'AAPL'
        assert result['shares'] == 100.0
        assert result['price'] == 150.50
        assert result['transaction_type'] == 'buy'


class TestValidationError:
    """Tests for ValidationError exception."""

    def test_error_attributes(self):
        """Test that ValidationError has correct attributes."""
        error = ValidationError('Test error', field='test_field', code='TEST_CODE')
        assert error.message == 'Test error'
        assert error.field == 'test_field'
        assert error.code == 'TEST_CODE'

    def test_to_dict(self):
        """Test that to_dict returns correct format."""
        error = ValidationError('Test error', field='ticker', code='INVALID')
        result = error.to_dict()
        assert result['success'] is False
        assert result['error'] == 'Test error'
        assert result['field'] == 'ticker'
        assert result['code'] == 'INVALID'
