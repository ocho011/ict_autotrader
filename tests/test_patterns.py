"""
Unit tests for candlestick pattern helper functions.

Tests cover normal cases, edge cases, and error handling for all
pattern analysis utility functions.
"""

import pytest
from src.strategy.patterns import (
    validate_candle_data,
    calculate_body_ratio,
    is_bullish_candle,
    is_bearish_candle,
    get_candle_body_size
)


class TestValidateCandleData:
    """Test suite for validate_candle_data function."""

    def test_valid_candle(self):
        """Test validation passes for valid candle data."""
        candle = {'open': 100.0, 'high': 105.0, 'low': 95.0, 'close': 103.0}
        assert validate_candle_data(candle) is True

    def test_high_equals_low(self):
        """Test validation passes when high equals low (zero-range candle)."""
        candle = {'open': 100.0, 'high': 100.0, 'low': 100.0, 'close': 100.0}
        assert validate_candle_data(candle) is True

    def test_high_less_than_low(self):
        """Test validation fails when high < low."""
        candle = {'open': 100.0, 'high': 95.0, 'low': 105.0, 'close': 103.0}
        assert validate_candle_data(candle) is False

    def test_missing_open(self):
        """Test validation fails when 'open' field is missing."""
        candle = {'high': 105.0, 'low': 95.0, 'close': 103.0}
        assert validate_candle_data(candle) is False

    def test_missing_high(self):
        """Test validation fails when 'high' field is missing."""
        candle = {'open': 100.0, 'low': 95.0, 'close': 103.0}
        assert validate_candle_data(candle) is False

    def test_missing_low(self):
        """Test validation fails when 'low' field is missing."""
        candle = {'open': 100.0, 'high': 105.0, 'close': 103.0}
        assert validate_candle_data(candle) is False

    def test_missing_close(self):
        """Test validation fails when 'close' field is missing."""
        candle = {'open': 100.0, 'high': 105.0, 'low': 95.0}
        assert validate_candle_data(candle) is False

    def test_non_numeric_values(self):
        """Test validation fails with non-numeric values."""
        candle = {'open': 'invalid', 'high': 105.0, 'low': 95.0, 'close': 103.0}
        assert validate_candle_data(candle) is False

    def test_none_values(self):
        """Test validation fails with None values."""
        candle = {'open': None, 'high': 105.0, 'low': 95.0, 'close': 103.0}
        assert validate_candle_data(candle) is False

    def test_empty_dict(self):
        """Test validation fails for empty dictionary."""
        assert validate_candle_data({}) is False


class TestCalculateBodyRatio:
    """Test suite for calculate_body_ratio function."""

    def test_normal_bullish_candle(self):
        """Test body ratio calculation for normal bullish candle."""
        candle = {'open': 100.0, 'high': 110.0, 'low': 95.0, 'close': 105.0}
        # Body size = |105 - 100| = 5, Total range = 110 - 95 = 15
        # Ratio = 5/15 = 0.3333...
        assert abs(calculate_body_ratio(candle) - 0.3333333333) < 0.0001

    def test_normal_bearish_candle(self):
        """Test body ratio calculation for normal bearish candle."""
        candle = {'open': 105.0, 'high': 110.0, 'low': 95.0, 'close': 100.0}
        # Body size = |100 - 105| = 5, Total range = 110 - 95 = 15
        # Ratio = 5/15 = 0.3333...
        assert abs(calculate_body_ratio(candle) - 0.3333333333) < 0.0001

    def test_full_body_candle(self):
        """Test candle where body occupies entire range."""
        candle = {'open': 100.0, 'high': 110.0, 'low': 100.0, 'close': 110.0}
        # Body size = |110 - 100| = 10, Total range = 110 - 100 = 10
        # Ratio = 10/10 = 1.0
        assert calculate_body_ratio(candle) == 1.0

    def test_doji_candle(self):
        """Test doji candle (open equals close)."""
        candle = {'open': 105.0, 'high': 110.0, 'low': 100.0, 'close': 105.0}
        # Body size = |105 - 105| = 0, Total range = 110 - 100 = 10
        # Ratio = 0/10 = 0.0
        assert calculate_body_ratio(candle) == 0.0

    def test_zero_range_candle(self):
        """Test zero-range candle (all prices equal)."""
        candle = {'open': 100.0, 'high': 100.0, 'low': 100.0, 'close': 100.0}
        # Zero division case - should return 0.0
        assert calculate_body_ratio(candle) == 0.0

    def test_invalid_candle_data(self):
        """Test with invalid candle data."""
        candle = {'open': 100.0, 'close': 105.0}  # Missing high and low
        assert calculate_body_ratio(candle) == 0.0

    def test_small_body_large_wicks(self):
        """Test candle with small body and large wicks."""
        candle = {'open': 100.0, 'high': 120.0, 'low': 80.0, 'close': 101.0}
        # Body size = |101 - 100| = 1, Total range = 120 - 80 = 40
        # Ratio = 1/40 = 0.025
        assert abs(calculate_body_ratio(candle) - 0.025) < 0.0001


class TestIsBullishCandle:
    """Test suite for is_bullish_candle function."""

    def test_bullish_candle(self):
        """Test detection of bullish candle."""
        candle = {'open': 100.0, 'high': 105.0, 'low': 99.0, 'close': 103.0}
        assert is_bullish_candle(candle) is True

    def test_bearish_candle(self):
        """Test bearish candle returns False."""
        candle = {'open': 100.0, 'high': 105.0, 'low': 95.0, 'close': 98.0}
        assert is_bullish_candle(candle) is False

    def test_doji_candle(self):
        """Test doji candle (open equals close) returns False."""
        candle = {'open': 100.0, 'high': 105.0, 'low': 95.0, 'close': 100.0}
        assert is_bullish_candle(candle) is False

    def test_invalid_data(self):
        """Test with invalid candle data."""
        candle = {'open': 100.0, 'close': 105.0}  # Missing fields
        assert is_bullish_candle(candle) is False

    def test_non_numeric_values(self):
        """Test with non-numeric values."""
        candle = {'open': 'invalid', 'high': 105.0, 'low': 95.0, 'close': 103.0}
        assert is_bullish_candle(candle) is False


class TestIsBearishCandle:
    """Test suite for is_bearish_candle function."""

    def test_bearish_candle(self):
        """Test detection of bearish candle."""
        candle = {'open': 100.0, 'high': 105.0, 'low': 95.0, 'close': 98.0}
        assert is_bearish_candle(candle) is True

    def test_bullish_candle(self):
        """Test bullish candle returns False."""
        candle = {'open': 100.0, 'high': 105.0, 'low': 99.0, 'close': 103.0}
        assert is_bearish_candle(candle) is False

    def test_doji_candle(self):
        """Test doji candle (open equals close) returns False."""
        candle = {'open': 100.0, 'high': 105.0, 'low': 95.0, 'close': 100.0}
        assert is_bearish_candle(candle) is False

    def test_invalid_data(self):
        """Test with invalid candle data."""
        candle = {'open': 100.0, 'close': 95.0}  # Missing fields
        assert is_bearish_candle(candle) is False

    def test_non_numeric_values(self):
        """Test with non-numeric values."""
        candle = {'open': 'invalid', 'high': 105.0, 'low': 95.0, 'close': 98.0}
        assert is_bearish_candle(candle) is False


class TestGetCandleBodySize:
    """Test suite for get_candle_body_size function."""

    def test_bullish_body_size(self):
        """Test body size calculation for bullish candle."""
        candle = {'open': 100.0, 'high': 105.0, 'low': 99.0, 'close': 103.0}
        assert get_candle_body_size(candle) == 3.0

    def test_bearish_body_size(self):
        """Test body size calculation for bearish candle."""
        candle = {'open': 100.0, 'high': 105.0, 'low': 95.0, 'close': 98.0}
        assert get_candle_body_size(candle) == 2.0

    def test_doji_body_size(self):
        """Test body size for doji candle (open equals close)."""
        candle = {'open': 100.0, 'high': 105.0, 'low': 95.0, 'close': 100.0}
        assert get_candle_body_size(candle) == 0.0

    def test_large_body_size(self):
        """Test body size for large price movement."""
        candle = {'open': 100.0, 'high': 150.0, 'low': 90.0, 'close': 145.0}
        assert get_candle_body_size(candle) == 45.0

    def test_invalid_data(self):
        """Test with invalid candle data."""
        candle = {'open': 100.0, 'close': 105.0}  # Missing fields
        assert get_candle_body_size(candle) == 0.0

    def test_non_numeric_values(self):
        """Test with non-numeric values."""
        candle = {'open': 'invalid', 'high': 105.0, 'low': 95.0, 'close': 103.0}
        assert get_candle_body_size(candle) == 0.0

    def test_decimal_body_size(self):
        """Test body size with decimal values."""
        candle = {'open': 100.5, 'high': 105.0, 'low': 99.0, 'close': 103.2}
        assert abs(get_candle_body_size(candle) - 2.7) < 0.0001


class TestIntegrationScenarios:
    """Integration tests combining multiple helper functions."""

    def test_strong_bullish_candle(self):
        """Test analysis of strong bullish candle with large body."""
        candle = {'open': 100.0, 'high': 110.0, 'low': 99.0, 'close': 109.0}

        assert validate_candle_data(candle) is True
        assert is_bullish_candle(candle) is True
        assert is_bearish_candle(candle) is False
        assert get_candle_body_size(candle) == 9.0
        # Body ratio should be high (9/11 = 0.818...)
        assert calculate_body_ratio(candle) > 0.8

    def test_weak_bearish_candle(self):
        """Test analysis of weak bearish candle with small body."""
        candle = {'open': 100.0, 'high': 110.0, 'low': 90.0, 'close': 99.0}

        assert validate_candle_data(candle) is True
        assert is_bullish_candle(candle) is False
        assert is_bearish_candle(candle) is True
        assert get_candle_body_size(candle) == 1.0
        # Body ratio should be low (1/20 = 0.05)
        assert calculate_body_ratio(candle) < 0.1

    def test_spinning_top_pattern(self):
        """Test analysis of spinning top (small body, equal wicks)."""
        candle = {'open': 100.0, 'high': 105.0, 'low': 95.0, 'close': 101.0}

        assert validate_candle_data(candle) is True
        assert is_bullish_candle(candle) is True
        assert get_candle_body_size(candle) == 1.0
        # Small body ratio (1/10 = 0.1)
        assert calculate_body_ratio(candle) == 0.1
