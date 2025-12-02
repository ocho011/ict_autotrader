"""
Signal Processor for ICT AutoTrader

This module implements trade signal generation from pattern confirmations:
- Combines Order Block and FVG detections into trade signals
- Implements confluence logic (multiple pattern alignment)
- Calculates entry, stop loss, and take profit levels
- Emits ENTRY_SIGNAL events when conditions align

The processor waits for pattern confirmations and generates signals
only when multiple patterns align in the same direction.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from loguru import logger

from ..core.event_processor import EventProcessor
from ..core.event_bus import EventBus, Event, EventType


class SignalProcessor(EventProcessor):
    """
    Generates trade signals from pattern confirmations.

    This processor listens for ORDER_BLOCK_DETECTED and FVG_DETECTED events,
    then combines them into trade signals when confluence is detected.

    Confluence requirements:
    - Patterns must be in the same direction (bullish/bearish)
    - Patterns must overlap or be nearby in price
    - Minimum confidence threshold must be met
    - Risk-reward ratio must meet minimum requirement

    Configuration:
        min_confidence (float): Minimum confidence score 0-100 (default: 70)
        min_risk_reward (float): Minimum R:R ratio (default: 2.0)
        require_confluence (bool): Require multiple patterns (default: True)
        pattern_proximity_percent (float): Max distance between patterns (default: 1.0)
        signal_timeout_seconds (int): Max age for pattern combination (default: 300)

    Examples:
        >>> bus = EventBus()
        >>> processor = SignalProcessor(bus)
        >>> await processor.start()
        >>>
        >>> # Will emit ENTRY_SIGNAL when Order Block + FVG align
        >>> await processor.stop()
    """

    def __init__(
        self,
        event_bus: EventBus,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize signal processor with configuration.

        Args:
            event_bus (EventBus): Event bus for pub/sub
            config (Dict[str, Any], optional): Configuration overrides
        """
        super().__init__(event_bus)

        # Default configuration
        default_config = {
            "min_confidence": 70,  # 0-100 score
            "min_risk_reward": 2.0,  # Minimum R:R ratio
            "require_confluence": True,  # Require multiple patterns
            "pattern_proximity_percent": 1.0,  # 1% max distance
            "signal_timeout_seconds": 300,  # 5 minutes
        }

        # Merge with user config
        self._config = {**default_config, **(config or {})}

        # State initialization
        self._recent_order_blocks: Optional[List] = None
        self._recent_fvgs: Optional[List] = None
        self._signal_count: int = 0

    async def _on_start(self) -> None:
        """Initialize processor state on startup."""
        self._recent_order_blocks = []
        self._recent_fvgs = []
        self._signal_count = 0
        logger.info("SignalProcessor state initialized")

    async def _on_stop(self) -> None:
        """Cleanup processor state on shutdown."""
        if self._recent_order_blocks:
            self._recent_order_blocks.clear()
        if self._recent_fvgs:
            self._recent_fvgs.clear()
        logger.info("SignalProcessor state cleaned up")

    def _register_handlers(self) -> None:
        """Register handlers for pattern detection events."""
        self.event_bus.subscribe(
            EventType.ORDER_BLOCK_DETECTED,
            self._on_order_block_detected
        )
        self.event_bus.subscribe(
            EventType.FVG_DETECTED,
            self._on_fvg_detected
        )
        logger.debug("SignalProcessor registered for pattern events")

    def _unregister_handlers(self) -> None:
        """Unregister handlers from pattern detection events."""
        self.event_bus.unsubscribe(
            EventType.ORDER_BLOCK_DETECTED,
            self._on_order_block_detected
        )
        self.event_bus.unsubscribe(
            EventType.FVG_DETECTED,
            self._on_fvg_detected
        )
        logger.debug("SignalProcessor unregistered from pattern events")

    async def _on_order_block_detected(self, event: Event) -> None:
        """
        Handle ORDER_BLOCK_DETECTED event.

        Stores the order block and checks for confluence with recent FVGs.

        Args:
            event (Event): ORDER_BLOCK_DETECTED event
        """
        try:
            pattern_data = event.data
            self._recent_order_blocks.append({
                "data": pattern_data,
                "timestamp": event.timestamp
            })

            logger.debug(
                f"Stored Order Block: {pattern_data['type']} @ "
                f"{pattern_data['bottom']:.2f}-{pattern_data['top']:.2f}"
            )

            # Check for confluence with recent FVGs
            await self._check_confluence()

            # Cleanup old patterns
            self._cleanup_old_patterns()

        except Exception as e:
            logger.error(f"Error handling ORDER_BLOCK_DETECTED: {e}")

    async def _on_fvg_detected(self, event: Event) -> None:
        """
        Handle FVG_DETECTED event.

        Stores the FVG and checks for confluence with recent Order Blocks.

        Args:
            event (Event): FVG_DETECTED event
        """
        try:
            pattern_data = event.data
            self._recent_fvgs.append({
                "data": pattern_data,
                "timestamp": event.timestamp
            })

            logger.debug(
                f"Stored FVG: {pattern_data['type']} @ "
                f"{pattern_data['bottom']:.2f}-{pattern_data['top']:.2f}"
            )

            # Check for confluence with recent Order Blocks
            await self._check_confluence()

            # Cleanup old patterns
            self._cleanup_old_patterns()

        except Exception as e:
            logger.error(f"Error handling FVG_DETECTED: {e}")

    async def _check_confluence(self) -> None:
        """
        Check for pattern confluence and generate signals.

        Confluence criteria:
        - Same direction (bullish/bearish)
        - Patterns overlap or are within proximity threshold
        - Meets minimum confidence score
        - Meets minimum risk-reward ratio
        """
        # If confluence required, need at least one of each pattern type
        if self._config["require_confluence"]:
            if not self._recent_order_blocks or not self._recent_fvgs:
                return

        # Find matching pattern combinations
        for ob_item in self._recent_order_blocks:
            for fvg_item in self._recent_fvgs:
                ob_data = ob_item["data"]
                fvg_data = fvg_item["data"]

                # Check if same direction
                if ob_data["type"] != fvg_data["type"]:
                    continue

                # Check proximity
                if not self._patterns_are_nearby(ob_data, fvg_data):
                    continue

                # Generate signal
                signal = self._generate_signal(ob_data, fvg_data)
                if signal:
                    await self._publish_signal(signal)
                    # Remove used patterns to avoid duplicate signals
                    self._recent_order_blocks.remove(ob_item)
                    self._recent_fvgs.remove(fvg_item)
                    return  # Only one signal per check

    def _patterns_are_nearby(
        self,
        ob_data: Dict[str, Any],
        fvg_data: Dict[str, Any]
    ) -> bool:
        """
        Check if two patterns are close enough for confluence.

        Patterns are considered nearby if they overlap or are within
        the proximity threshold percentage.

        Args:
            ob_data (Dict): Order Block data
            fvg_data (Dict): FVG data

        Returns:
            bool: True if patterns are nearby
        """
        ob_top = ob_data["top"]
        ob_bottom = ob_data["bottom"]
        fvg_top = fvg_data["top"]
        fvg_bottom = fvg_data["bottom"]

        # Check for overlap
        if (ob_bottom <= fvg_top and ob_top >= fvg_bottom):
            return True

        # Calculate distance between patterns
        if ob_bottom > fvg_top:
            # OB is above FVG
            distance = ob_bottom - fvg_top
            reference_price = (ob_bottom + fvg_top) / 2
        else:
            # FVG is above OB
            distance = fvg_bottom - ob_top
            reference_price = (fvg_bottom + ob_top) / 2

        # Calculate distance as percentage
        distance_percent = (distance / reference_price) * 100

        # Check if within proximity threshold
        max_proximity = self._config["pattern_proximity_percent"]
        return distance_percent <= max_proximity

    def _generate_signal(
        self,
        ob_data: Dict[str, Any],
        fvg_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Generate trade signal from pattern combination.

        Calculates entry price, stop loss, and take profit levels based on
        pattern positions and risk-reward requirements.

        Args:
            ob_data (Dict): Order Block data
            fvg_data (Dict): FVG data

        Returns:
            Dict or None: Signal data if valid, None otherwise
        """
        direction = ob_data["type"]  # Both patterns have same type

        # Calculate entry price (FVG 50% retracement or OB boundary)
        fvg_mid = (fvg_data["top"] + fvg_data["bottom"]) / 2

        if direction == "bullish":
            # Long signal
            entry_price = fvg_mid
            stop_loss = min(ob_data["bottom"], fvg_data["bottom"]) * 0.999  # Below both patterns

            # Calculate take profit based on risk-reward
            risk = entry_price - stop_loss
            min_rr = self._config["min_risk_reward"]
            take_profit = entry_price + (risk * min_rr)

        else:  # bearish
            # Short signal
            entry_price = fvg_mid
            stop_loss = max(ob_data["top"], fvg_data["top"]) * 1.001  # Above both patterns

            # Calculate take profit based on risk-reward
            risk = stop_loss - entry_price
            min_rr = self._config["min_risk_reward"]
            take_profit = entry_price - (risk * min_rr)

        # Calculate risk-reward ratio
        risk_amount = abs(entry_price - stop_loss)
        reward_amount = abs(take_profit - entry_price)
        risk_reward_ratio = reward_amount / risk_amount if risk_amount > 0 else 0

        # Validate risk-reward meets minimum
        if risk_reward_ratio < self._config["min_risk_reward"]:
            logger.debug(
                f"Signal rejected: R:R {risk_reward_ratio:.2f} < "
                f"minimum {self._config['min_risk_reward']}"
            )
            return None

        # Calculate confidence score
        confidence = self._calculate_confidence(ob_data, fvg_data)

        # Validate confidence meets minimum
        if confidence < self._config["min_confidence"]:
            logger.debug(
                f"Signal rejected: Confidence {confidence:.1f} < "
                f"minimum {self._config['min_confidence']}"
            )
            return None

        # Build signal data
        signal = {
            "direction": "long" if direction == "bullish" else "short",
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "risk_reward_ratio": risk_reward_ratio,
            "confidence": confidence,
            "patterns": ["order_block", "fvg"],
            "reason": (
                f"{direction.capitalize()} confluence: Order Block "
                f"({ob_data['bottom']:.2f}-{ob_data['top']:.2f}) + "
                f"FVG ({fvg_data['bottom']:.2f}-{fvg_data['top']:.2f})"
            )
        }

        logger.info(
            f"Generated {signal['direction']} signal: Entry={entry_price:.2f}, "
            f"SL={stop_loss:.2f}, TP={take_profit:.2f}, "
            f"R:R={risk_reward_ratio:.2f}, Confidence={confidence:.1f}"
        )

        return signal

    def _calculate_confidence(
        self,
        ob_data: Dict[str, Any],
        fvg_data: Dict[str, Any]
    ) -> float:
        """
        Calculate confidence score for signal (0-100).

        Factors:
        - Pattern overlap (more overlap = higher confidence)
        - Pattern freshness (recent = higher confidence)

        Args:
            ob_data (Dict): Order Block data
            fvg_data (Dict): FVG data

        Returns:
            float: Confidence score 0-100
        """
        confidence = 70.0  # Base confidence for confluence

        # Check for overlap (bonus confidence)
        ob_range = ob_data["top"] - ob_data["bottom"]
        fvg_range = fvg_data["top"] - fvg_data["bottom"]

        # Calculate overlap
        overlap_top = min(ob_data["top"], fvg_data["top"])
        overlap_bottom = max(ob_data["bottom"], fvg_data["bottom"])
        overlap = max(0, overlap_top - overlap_bottom)

        # Overlap percentage (relative to smaller pattern)
        smaller_range = min(ob_range, fvg_range)
        if smaller_range > 0:
            overlap_percent = overlap / smaller_range
            confidence += overlap_percent * 20  # Up to +20 for full overlap

        # Cap at 100
        return min(100.0, confidence)

    async def _publish_signal(self, signal: Dict[str, Any]) -> None:
        """
        Publish ENTRY_SIGNAL event to queue.

        Args:
            signal (Dict): Signal data
        """
        try:
            self._signal_count += 1

            event = Event(
                event_type=EventType.ENTRY_SIGNAL,
                data=signal,
                source="SignalProcessor"
            )

            await self.event_bus.publish(event)
            logger.info(f"ENTRY_SIGNAL #{self._signal_count} published")

        except Exception as e:
            logger.error(f"Failed to publish ENTRY_SIGNAL: {e}")

    def _cleanup_old_patterns(self) -> None:
        """
        Remove patterns older than timeout to prevent stale signals.
        """
        timeout = timedelta(seconds=self._config["signal_timeout_seconds"])
        cutoff_time = datetime.utcnow() - timeout

        # Cleanup old order blocks
        initial_ob_count = len(self._recent_order_blocks)
        self._recent_order_blocks = [
            item for item in self._recent_order_blocks
            if item["timestamp"] > cutoff_time
        ]
        removed_obs = initial_ob_count - len(self._recent_order_blocks)

        # Cleanup old FVGs
        initial_fvg_count = len(self._recent_fvgs)
        self._recent_fvgs = [
            item for item in self._recent_fvgs
            if item["timestamp"] > cutoff_time
        ]
        removed_fvgs = initial_fvg_count - len(self._recent_fvgs)

        if removed_obs > 0 or removed_fvgs > 0:
            logger.debug(
                f"Cleaned up {removed_obs} old Order Blocks and "
                f"{removed_fvgs} old FVGs (timeout: {timeout})"
            )

    @property
    def signal_count(self) -> int:
        """Get total number of signals generated."""
        return self._signal_count

    @property
    def pending_order_blocks(self) -> int:
        """Get number of order blocks awaiting confluence."""
        return len(self._recent_order_blocks) if self._recent_order_blocks else 0

    @property
    def pending_fvgs(self) -> int:
        """Get number of FVGs awaiting confluence."""
        return len(self._recent_fvgs) if self._recent_fvgs else 0
