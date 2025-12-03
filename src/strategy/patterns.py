"""
Candlestick pattern analysis helper functions.

This module provides utility functions for analyzing candlestick patterns,
including body ratio calculations, candle direction detection, and data validation.
"""

from typing import Dict, Any


def validate_candle_data(candle: Dict[str, Any]) -> bool:
    """
    Verify candle has required OHLC fields and valid values.

    Args:
        candle: Dictionary containing OHLC data with keys: 'open', 'high', 'low', 'close'

    Returns:
        True if candle has all required fields and high >= low, False otherwise

    Examples:
        >>> validate_candle_data({'open': 100, 'high': 105, 'low': 99, 'close': 103})
        True
        >>> validate_candle_data({'open': 100, 'high': 99, 'low': 105, 'close': 103})
        False
        >>> validate_candle_data({'open': 100, 'close': 103})
        False
    """
    required_fields = ['open', 'high', 'low', 'close']

    # Check if all required fields exist
    if not all(field in candle for field in required_fields):
        return False

    try:
        # Validate all values are numeric by attempting conversion
        _ = float(candle['open'])
        high = float(candle['high'])
        low = float(candle['low'])
        _ = float(candle['close'])

        # Verify high >= low
        return high >= low
    except (ValueError, TypeError):
        return False


def calculate_body_ratio(candle: Dict[str, Any]) -> float:
    """
    Calculate candle body ratio: abs(close - open) / (high - low).

    The body ratio represents what percentage of the total candle range
    is occupied by the real body (open to close).

    Args:
        candle: Dictionary containing OHLC data

    Returns:
        Body ratio as float between 0.0 and 1.0.
        Returns 0.0 for zero-range candles or invalid data.

    Examples:
        >>> calculate_body_ratio({'open': 100, 'high': 110, 'low': 95, 'close': 105})
        0.3333333333333333
        >>> calculate_body_ratio({'open': 100, 'high': 100, 'low': 100, 'close': 100})
        0.0
    """
    if not validate_candle_data(candle):
        return 0.0

    try:
        open_price = float(candle['open'])
        high = float(candle['high'])
        low = float(candle['low'])
        close = float(candle['close'])

        total_range = high - low

        # Handle zero division for zero-range candles
        if total_range == 0:
            return 0.0

        body_size = abs(close - open_price)
        return body_size / total_range

    except (ValueError, TypeError, ZeroDivisionError):
        return 0.0


def is_bullish_candle(candle: Dict[str, Any]) -> bool:
    """
    Determine if candle is bullish (close > open).

    Args:
        candle: Dictionary containing OHLC data

    Returns:
        True if close > open, False otherwise

    Examples:
        >>> is_bullish_candle({'open': 100, 'high': 105, 'low': 99, 'close': 103})
        True
        >>> is_bullish_candle({'open': 100, 'high': 105, 'low': 99, 'close': 98})
        False
    """
    if not validate_candle_data(candle):
        return False

    try:
        return float(candle['close']) > float(candle['open'])
    except (ValueError, TypeError):
        return False


def is_bearish_candle(candle: Dict[str, Any]) -> bool:
    """
    Determine if candle is bearish (close < open).

    Args:
        candle: Dictionary containing OHLC data

    Returns:
        True if close < open, False otherwise

    Examples:
        >>> is_bearish_candle({'open': 100, 'high': 105, 'low': 99, 'close': 98})
        True
        >>> is_bearish_candle({'open': 100, 'high': 105, 'low': 99, 'close': 103})
        False
    """
    if not validate_candle_data(candle):
        return False

    try:
        return float(candle['close']) < float(candle['open'])
    except (ValueError, TypeError):
        return False


def get_candle_body_size(candle: Dict[str, Any]) -> float:
    """
    Calculate the absolute size of the candle body.

    Args:
        candle: Dictionary containing OHLC data

    Returns:
        Absolute difference between close and open.
        Returns 0.0 for invalid data.

    Examples:
        >>> get_candle_body_size({'open': 100, 'high': 105, 'low': 99, 'close': 103})
        3.0
        >>> get_candle_body_size({'open': 100, 'high': 105, 'low': 99, 'close': 98})
        2.0
    """
    if not validate_candle_data(candle):
        return 0.0

    try:
        open_price = float(candle['open'])
        close = float(candle['close'])
        return abs(close - open_price)
    except (ValueError, TypeError):
        return 0.0
