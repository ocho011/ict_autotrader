"""
State management for trading patterns and candles.

This module provides centralized state storage for:
- Candle history with automatic size management
- Order Block pattern tracking with validation
- Fair Value Gap (FVG) pattern tracking with validation

The StateStore acts as an in-memory cache for pattern-based trading decisions,
maintaining collections that can be queried by type and validity.
"""

from collections import deque
from typing import Optional, List, Literal
from .models import OrderBlock, FVG


class StateStore:
    """
    State management for trading patterns and candles.

    Maintains collections of candles, order blocks, and FVGs with
    filtering capabilities for pattern-based trading decisions.

    The StateStore uses:
    - deque for candles: automatic memory management with maxlen
    - lists for patterns: manual management with is_valid filtering

    Attributes:
        candles: Fixed-size deque of candle dictionaries (OHLCV format)
        order_blocks: List of OrderBlock instances (both valid and invalid)
        fvgs: List of FVG instances (both valid and invalid)

    Examples:
        >>> store = StateStore(candle_history_size=500)
        >>> store.add_candle({"open": 45000, "high": 45100, ...})
        >>> ob = OrderBlock(type="bullish", top=45000, bottom=44500, ...)
        >>> store.add_order_block(ob)
        >>> valid_bullish_obs = store.get_valid_order_blocks(ob_type="bullish")
    """

    def __init__(self, candle_history_size: int = 500):
        """
        Initialize StateStore with empty collections.

        Args:
            candle_history_size: Maximum number of candles to retain.
                Default 500 provides sufficient history for pattern detection
                while maintaining memory efficiency. When limit is reached,
                oldest candles are automatically removed (FIFO).

        Raises:
            ValueError: If candle_history_size is not positive.

        Examples:
            >>> store = StateStore()  # Default 500 candles
            >>> store = StateStore(candle_history_size=1000)  # Extended history
        """
        if candle_history_size <= 0:
            raise ValueError(
                f"candle_history_size must be positive, got {candle_history_size}"
            )

        self.candles: deque = deque(maxlen=candle_history_size)
        self.order_blocks: List[OrderBlock] = []
        self.fvgs: List[FVG] = []

    def add_candle(self, candle: dict) -> None:
        """
        Append candle dict to candles deque.

        The candle is added to the end of the deque. If the deque is at
        maxlen, the oldest candle is automatically removed.

        Args:
            candle: Candle data dictionary. Expected to contain OHLCV fields:
                - open: Opening price
                - high: Highest price
                - low: Lowest price
                - close: Closing price
                - volume: Trading volume
                - timestamp: Candle timestamp (optional)

        Examples:
            >>> store = StateStore()
            >>> candle = {
            ...     "open": 45000.0,
            ...     "high": 45100.0,
            ...     "low": 44900.0,
            ...     "close": 45050.0,
            ...     "volume": 123.45
            ... }
            >>> store.add_candle(candle)
            >>> len(store.candles)
            1
        """
        self.candles.append(candle)

    def add_order_block(self, ob: OrderBlock) -> None:
        """
        Append OrderBlock to order_blocks list.

        Stores both valid and invalid order blocks. Use get_valid_order_blocks()
        to retrieve only currently valid patterns.

        Args:
            ob: Validated OrderBlock instance. Must be a properly constructed
                OrderBlock with all required fields.

        Examples:
            >>> from datetime import datetime
            >>> store = StateStore()
            >>> ob = OrderBlock(
            ...     type="bullish",
            ...     top=45000.0,
            ...     bottom=44500.0,
            ...     timestamp=datetime.utcnow(),
            ...     is_valid=True
            ... )
            >>> store.add_order_block(ob)
            >>> len(store.order_blocks)
            1
        """
        self.order_blocks.append(ob)

    def add_fvg(self, fvg: FVG) -> None:
        """
        Append FVG to fvgs list.

        Stores both valid and invalid FVGs. Use get_valid_fvgs()
        to retrieve only currently valid patterns.

        Args:
            fvg: Validated FVG instance. Must be a properly constructed
                FVG with all required fields.

        Examples:
            >>> from datetime import datetime
            >>> store = StateStore()
            >>> fvg = FVG(
            ...     type="bullish",
            ...     top=45000.0,
            ...     bottom=44800.0,
            ...     timestamp=datetime.utcnow(),
            ...     filled_percent=25.0,
            ...     is_valid=True
            ... )
            >>> store.add_fvg(fvg)
            >>> len(store.fvgs)
            1
        """
        self.fvgs.append(fvg)

    def get_valid_order_blocks(
        self,
        ob_type: Optional[Literal["bullish", "bearish"]] = None
    ) -> List[OrderBlock]:
        """
        Get valid order blocks, optionally filtered by type.

        Returns order blocks where is_valid=True. Optionally filters
        by bullish or bearish type for directional analysis.

        Args:
            ob_type: Optional type filter. Valid values:
                - "bullish": Return only bullish order blocks
                - "bearish": Return only bearish order blocks
                - None: Return all valid order blocks (default)

        Returns:
            List of OrderBlocks with is_valid=True, optionally filtered by type.
            Returns empty list if no valid order blocks match the criteria.

        Examples:
            >>> store = StateStore()
            >>> ob1 = OrderBlock(type="bullish", top=45000, bottom=44500, ...)
            >>> ob2 = OrderBlock(type="bearish", top=45500, bottom=45000, ...)
            >>> ob3 = OrderBlock(type="bullish", top=44000, bottom=43500,
            ...                  is_valid=False, ...)
            >>> store.add_order_block(ob1)
            >>> store.add_order_block(ob2)
            >>> store.add_order_block(ob3)
            >>>
            >>> # Get all valid order blocks
            >>> valid_obs = store.get_valid_order_blocks()
            >>> len(valid_obs)
            2
            >>>
            >>> # Get only bullish order blocks
            >>> bullish_obs = store.get_valid_order_blocks(ob_type="bullish")
            >>> len(bullish_obs)
            1
            >>> bullish_obs[0].type
            'bullish'
        """
        # First filter by validity
        valid_obs = [ob for ob in self.order_blocks if ob.is_valid]

        # Then filter by type if specified
        if ob_type is not None:
            return [ob for ob in valid_obs if ob.type == ob_type]

        return valid_obs

    def get_valid_fvgs(
        self,
        fvg_type: Optional[Literal["bullish", "bearish"]] = None
    ) -> List[FVG]:
        """
        Get valid FVGs, optionally filtered by type.

        Returns FVGs where is_valid=True. Optionally filters
        by bullish or bearish type for directional analysis.

        Args:
            fvg_type: Optional type filter. Valid values:
                - "bullish": Return only bullish FVGs
                - "bearish": Return only bearish FVGs
                - None: Return all valid FVGs (default)

        Returns:
            List of FVGs with is_valid=True, optionally filtered by type.
            Returns empty list if no valid FVGs match the criteria.

        Examples:
            >>> store = StateStore()
            >>> fvg1 = FVG(type="bullish", top=45000, bottom=44800, ...)
            >>> fvg2 = FVG(type="bearish", top=45500, bottom=45300, ...)
            >>> fvg3 = FVG(type="bullish", top=44000, bottom=43800,
            ...            is_valid=False, ...)
            >>> store.add_fvg(fvg1)
            >>> store.add_fvg(fvg2)
            >>> store.add_fvg(fvg3)
            >>>
            >>> # Get all valid FVGs
            >>> valid_fvgs = store.get_valid_fvgs()
            >>> len(valid_fvgs)
            2
            >>>
            >>> # Get only bearish FVGs
            >>> bearish_fvgs = store.get_valid_fvgs(fvg_type="bearish")
            >>> len(bearish_fvgs)
            1
            >>> bearish_fvgs[0].type
            'bearish'
        """
        # First filter by validity
        valid_fvgs = [fvg for fvg in self.fvgs if fvg.is_valid]

        # Then filter by type if specified
        if fvg_type is not None:
            return [fvg for fvg in valid_fvgs if fvg.type == fvg_type]

        return valid_fvgs
