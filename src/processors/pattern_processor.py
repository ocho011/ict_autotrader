"""
Pattern Processor for ICT AutoTrader

This module implements pattern detection for ICT (Inner Circle Trader) methodology:
- Order Block detection: Institutional order zones (support/resistance)
- Fair Value Gap (FVG) detection: Price inefficiencies that tend to be filled

The processor subscribes to CANDLE_CLOSED events and analyzes price action
to identify these key patterns, emitting ORDER_BLOCK_DETECTED and FVG_DETECTED
events when patterns are found.
"""

from typing import Dict, Any, List, Optional
from collections import deque
from datetime import datetime
from loguru import logger

from ..core.event_processor import EventProcessor
from ..core.event_bus import EventBus, Event, EventType
from ..core.models import OrderBlock, FVG


class PatternProcessor(EventProcessor):
    """
    Detects Order Blocks and Fair Value Gaps from candle data.

    This processor analyzes incoming candle data to identify ICT patterns:
    - Order Blocks: Strong institutional zones marked by large-bodied candles
    - FVGs: Price gaps created by rapid market movement

    The processor maintains a sliding window of recent candles for analysis
    and automatically cleans up old patterns to prevent memory leaks.

    Configuration:
        min_order_block_body_ratio (float): Minimum body-to-range ratio (default: 0.6)
        min_fvg_gap_percent (float): Minimum gap size as % of price (default: 0.3)
        max_candle_history (int): Maximum candles to keep in memory (default: 100)
        pattern_ttl_candles (int): Pattern validity lifetime in candles (default: 50)

    Examples:
        >>> bus = EventBus()
        >>> processor = PatternProcessor(bus)
        >>> await processor.start()
        >>>
        >>> # Emit candle event
        >>> candle = Event(
        ...     EventType.CANDLE_CLOSED,
        ...     {"open": 44000, "high": 45000, "low": 43900, "close": 44800, ...},
        ...     "market_data"
        ... )
        >>> await bus.publish(candle)
        >>>
        >>> await processor.stop()
    """

    def __init__(
        self,
        event_bus: EventBus,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize pattern processor with configuration.

        Args:
            event_bus (EventBus): Event bus for pub/sub
            config (Dict[str, Any], optional): Configuration overrides
        """
        super().__init__(event_bus)

        # Default configuration
        default_config = {
            "min_order_block_body_ratio": 0.6,  # 60% body to range ratio
            "min_fvg_gap_percent": 0.3,  # 0.3% of price for meaningful gap
            "max_candle_history": 100,  # Memory management
            "pattern_ttl_candles": 50,  # Pattern validity lifetime
        }

        # Merge with user config
        self._config = {**default_config, **(config or {})}

        # State initialization (actual objects created in _on_start)
        self._candle_history: Optional[deque] = None
        self._detected_order_blocks: Optional[List] = None
        self._detected_fvgs: Optional[List] = None
        self._candle_count: int = 0

    async def _on_start(self) -> None:
        """Initialize processor state on startup."""
        self._candle_history = deque(
            maxlen=self._config["max_candle_history"]
        )
        self._detected_order_blocks = []
        self._detected_fvgs = []
        self._candle_count = 0
        logger.info("PatternProcessor state initialized")

    async def _on_stop(self) -> None:
        """Cleanup processor state on shutdown."""
        if self._candle_history:
            self._candle_history.clear()
        if self._detected_order_blocks:
            self._detected_order_blocks.clear()
        if self._detected_fvgs:
            self._detected_fvgs.clear()
        logger.info("PatternProcessor state cleaned up")

    def _register_handlers(self) -> None:
        """Register handler for CANDLE_CLOSED events."""
        self.event_bus.subscribe(EventType.CANDLE_CLOSED, self._on_candle_closed)
        logger.debug("PatternProcessor registered for CANDLE_CLOSED events")

    def _unregister_handlers(self) -> None:
        """Unregister handler from CANDLE_CLOSED events."""
        self.event_bus.unsubscribe(EventType.CANDLE_CLOSED, self._on_candle_closed)
        logger.debug("PatternProcessor unregistered from CANDLE_CLOSED events")

    async def _on_candle_closed(self, event: Event) -> None:
        """
        Handle CANDLE_CLOSED event and detect patterns.

        Processing flow:
        1. Validate candle data
        2. Add to history
        3. Detect Order Block from current candle
        4. Detect FVG from last 3 candles (if enough history)
        5. Emit pattern events
        6. Cleanup old patterns

        Args:
            event (Event): CANDLE_CLOSED event with candle data
        """
        try:
            candle_data = event.data

            # Validate candle data structure
            if not self._validate_candle(candle_data):
                logger.warning(f"Invalid candle data received: {candle_data}")
                return

            # Add to history
            self._candle_history.append(candle_data)
            self._candle_count += 1

            logger.debug(
                f"Processing candle {self._candle_count}: "
                f"{candle_data.get('symbol')} @ {candle_data.get('close')}"
            )

            # Detect Order Block from current candle
            order_block = self._detect_order_block(candle_data)
            if order_block:
                await self._emit_order_block(order_block)

            # Detect FVG (requires at least 3 candles)
            if len(self._candle_history) >= 3:
                fvg = self._detect_fvg()
                if fvg:
                    await self._emit_fvg(fvg)

            # Cleanup old patterns
            self._cleanup_old_patterns()

        except Exception as e:
            logger.error(f"Error processing candle in PatternProcessor: {e}")

    def _validate_candle(self, candle_data: Dict[str, Any]) -> bool:
        """
        Validate candle data structure and values.

        Args:
            candle_data (Dict): Candle data from event

        Returns:
            bool: True if valid, False otherwise
        """
        required_fields = ["open", "high", "low", "close", "volume", "timestamp"]

        # Check required fields exist
        for field in required_fields:
            if field not in candle_data:
                logger.warning(f"Missing required field: {field}")
                return False

        # Validate price values are positive
        price_fields = ["open", "high", "low", "close"]
        for field in price_fields:
            if candle_data[field] <= 0:
                logger.warning(f"Invalid {field} price: {candle_data[field]}")
                return False

        # Validate high >= low
        if candle_data["high"] < candle_data["low"]:
            logger.warning(
                f"Invalid price range: high {candle_data['high']} < "
                f"low {candle_data['low']}"
            )
            return False

        # Validate volume is non-negative
        if candle_data["volume"] < 0:
            logger.warning(f"Invalid volume: {candle_data['volume']}")
            return False

        return True

    def _detect_order_block(self, candle_data: Dict[str, Any]) -> Optional[OrderBlock]:
        """
        Detect Order Block from a single candle.

        Order Blocks are identified by:
        - Strong bullish/bearish candles (large body relative to range)
        - Body ratio exceeds minimum threshold
        - Represent institutional order zones

        Args:
            candle_data (Dict): Candle OHLC data

        Returns:
            OrderBlock or None: Detected order block if found
        """
        open_price = candle_data["open"]
        high = candle_data["high"]
        low = candle_data["low"]
        close = candle_data["close"]
        timestamp = candle_data["timestamp"]

        # Calculate candle metrics
        body_size = abs(close - open_price)
        total_range = high - low

        # Skip zero-range candles (doji, etc.)
        if total_range == 0:
            return None

        # Calculate body ratio
        body_ratio = body_size / total_range

        # Check if strong candle (meets minimum body ratio)
        min_ratio = self._config["min_order_block_body_ratio"]
        if body_ratio < min_ratio:
            return None

        # Determine bullish or bearish
        if close > open_price:
            # Bullish order block
            ob_type = "bullish"
            ob_bottom = low
            ob_top = high
        else:
            # Bearish order block
            ob_type = "bearish"
            ob_bottom = low
            ob_top = high

        # Create OrderBlock model
        try:
            order_block = OrderBlock(
                type=ob_type,
                top=ob_top,
                bottom=ob_bottom,
                timestamp=timestamp,
                touches=0,
                is_valid=True
            )

            logger.info(
                f"Detected {ob_type} Order Block: "
                f"{ob_bottom:.2f} - {ob_top:.2f} (body ratio: {body_ratio:.2%})"
            )

            return order_block

        except Exception as e:
            logger.error(f"Failed to create OrderBlock model: {e}")
            return None

    def _detect_fvg(self) -> Optional[FVG]:
        """
        Detect Fair Value Gap from last 3 candles.

        FVG detection requires:
        - At least 3 candles in history
        - Gap between candle[0] and candle[2] (middle candle creates gap)
        - Gap size exceeds minimum threshold

        Bullish FVG: candle[0].high < candle[2].low
        Bearish FVG: candle[0].low > candle[2].high

        Returns:
            FVG or None: Detected FVG if found
        """
        if len(self._candle_history) < 3:
            return None

        # Get last 3 candles
        candles = list(self._candle_history)[-3:]
        candle_0 = candles[0]  # Oldest
        candle_1 = candles[1]  # Middle (creates the gap)
        candle_2 = candles[2]  # Most recent

        # Check for bullish FVG
        if candle_0["high"] < candle_2["low"]:
            fvg_type = "bullish"
            fvg_bottom = candle_0["high"]
            fvg_top = candle_2["low"]
            gap_size = fvg_top - fvg_bottom

        # Check for bearish FVG
        elif candle_0["low"] > candle_2["high"]:
            fvg_type = "bearish"
            fvg_top = candle_0["low"]
            fvg_bottom = candle_2["high"]
            gap_size = fvg_top - fvg_bottom

        else:
            # No gap detected
            return None

        # Calculate gap percentage relative to price
        avg_price = (fvg_top + fvg_bottom) / 2
        gap_percent = (gap_size / avg_price) * 100

        # Check if gap meets minimum size threshold
        min_gap_percent = self._config["min_fvg_gap_percent"]
        if gap_percent < min_gap_percent:
            return None

        # Create FVG model
        try:
            fvg = FVG(
                type=fvg_type,
                top=fvg_top,
                bottom=fvg_bottom,
                timestamp=candle_2["timestamp"],
                filled_percent=0.0,
                is_valid=True
            )

            logger.info(
                f"Detected {fvg_type} FVG: "
                f"{fvg_bottom:.2f} - {fvg_top:.2f} "
                f"(gap: {gap_percent:.2%})"
            )

            return fvg

        except Exception as e:
            logger.error(f"Failed to create FVG model: {e}")
            return None

    async def _emit_order_block(self, order_block: OrderBlock) -> None:
        """
        Emit ORDER_BLOCK_DETECTED event.

        Args:
            order_block (OrderBlock): Detected order block
        """
        try:
            # Store in detected patterns
            self._detected_order_blocks.append({
                "pattern": order_block,
                "detected_at_candle": self._candle_count
            })

            # Create event with order block data
            event = Event(
                event_type=EventType.ORDER_BLOCK_DETECTED,
                data={
                    "type": order_block.type,
                    "top": order_block.top,
                    "bottom": order_block.bottom,
                    "timestamp": order_block.timestamp,
                    "order_block": order_block.model_dump()
                },
                source="PatternProcessor"
            )

            # Publish event
            await self.event_bus.publish(event)
            logger.debug("ORDER_BLOCK_DETECTED event published")

        except Exception as e:
            logger.error(f"Failed to emit ORDER_BLOCK_DETECTED event: {e}")

    async def _emit_fvg(self, fvg: FVG) -> None:
        """
        Emit FVG_DETECTED event.

        Args:
            fvg (FVG): Detected fair value gap
        """
        try:
            # Store in detected patterns
            self._detected_fvgs.append({
                "pattern": fvg,
                "detected_at_candle": self._candle_count
            })

            # Create event with FVG data
            event = Event(
                event_type=EventType.FVG_DETECTED,
                data={
                    "type": fvg.type,
                    "top": fvg.top,
                    "bottom": fvg.bottom,
                    "timestamp": fvg.timestamp,
                    "fvg": fvg.model_dump()
                },
                source="PatternProcessor"
            )

            # Publish event
            await self.event_bus.publish(event)
            logger.debug("FVG_DETECTED event published")

        except Exception as e:
            logger.error(f"Failed to emit FVG_DETECTED event: {e}")

    def _cleanup_old_patterns(self) -> None:
        """
        Remove patterns older than TTL to prevent memory leaks.

        Patterns are considered expired if they were detected more than
        pattern_ttl_candles ago.
        """
        ttl = self._config["pattern_ttl_candles"]
        cutoff_candle = self._candle_count - ttl

        # Cleanup old order blocks
        initial_ob_count = len(self._detected_order_blocks)
        self._detected_order_blocks = [
            item for item in self._detected_order_blocks
            if item["detected_at_candle"] > cutoff_candle
        ]
        removed_obs = initial_ob_count - len(self._detected_order_blocks)

        # Cleanup old FVGs
        initial_fvg_count = len(self._detected_fvgs)
        self._detected_fvgs = [
            item for item in self._detected_fvgs
            if item["detected_at_candle"] > cutoff_candle
        ]
        removed_fvgs = initial_fvg_count - len(self._detected_fvgs)

        if removed_obs > 0 or removed_fvgs > 0:
            logger.debug(
                f"Cleaned up {removed_obs} old Order Blocks and "
                f"{removed_fvgs} old FVGs"
            )

    @property
    def candle_count(self) -> int:
        """Get total number of candles processed."""
        return self._candle_count

    @property
    def order_block_count(self) -> int:
        """Get number of active order blocks."""
        return len(self._detected_order_blocks) if self._detected_order_blocks else 0

    @property
    def fvg_count(self) -> int:
        """Get number of active FVGs."""
        return len(self._detected_fvgs) if self._detected_fvgs else 0
