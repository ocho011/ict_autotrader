"""
Order Processor for ICT AutoTrader

This module implements order lifecycle management:
- Order placement from entry signals
- Order tracking (placed → filled → closed)
- Position management
- Simulated order execution (MVP)

The processor subscribes to ENTRY_SIGNAL events and manages the complete
order lifecycle, emitting ORDER_PLACED, ORDER_FILLED, and POSITION_CLOSED
events as orders progress through their lifecycle.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger

from ..core.event_processor import EventProcessor
from ..core.event_bus import EventBus, Event, EventType
from ..core.models import Position


class OrderProcessor(EventProcessor):
    """
    Manages order placement and position lifecycle.

    This processor handles the complete trading lifecycle:
    1. Receives ENTRY_SIGNAL events
    2. Validates signal and places order (simulated for MVP)
    3. Emits ORDER_PLACED event
    4. Simulates order fill
    5. Emits ORDER_FILLED event
    6. Tracks position state
    7. Emits POSITION_CLOSED on exit (not implemented in MVP)

    For MVP, orders are immediately filled at the requested price.
    Future versions will integrate with real exchange APIs.

    Configuration:
        symbol (str): Trading symbol (default: "BTCUSDT")
        max_position_size (float): Maximum position size (default: 0.1)
        enable_simulation (bool): Use simulated fills (default: True)
        auto_close_positions (bool): Auto-close for testing (default: False)

    Examples:
        >>> bus = EventBus()
        >>> processor = OrderProcessor(bus)
        >>> await processor.start()
        >>>
        >>> # Will place order when ENTRY_SIGNAL received
        >>> await processor.stop()
    """

    def __init__(
        self,
        event_bus: EventBus,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize order processor with configuration.

        Args:
            event_bus (EventBus): Event bus for pub/sub
            config (Dict[str, Any], optional): Configuration overrides
        """
        super().__init__(event_bus)

        # Default configuration
        default_config = {
            "symbol": "BTCUSDT",
            "max_position_size": 0.1,  # BTC
            "enable_simulation": True,
            "auto_close_positions": False,  # For testing
        }

        # Merge with user config
        self._config = {**default_config, **(config or {})}

        # State initialization
        self._positions: Optional[Dict[str, Position]] = None
        self._order_id_counter: int = 0
        self._orders_placed: int = 0
        self._orders_filled: int = 0
        self._positions_closed: int = 0

    async def _on_start(self) -> None:
        """Initialize processor state on startup."""
        self._positions = {}
        self._order_id_counter = 0
        self._orders_placed = 0
        self._orders_filled = 0
        self._positions_closed = 0
        logger.info("OrderProcessor state initialized")

    async def _on_stop(self) -> None:
        """Cleanup processor state on shutdown."""
        if self._positions:
            # Log any open positions
            if len(self._positions) > 0:
                logger.warning(
                    f"Shutting down with {len(self._positions)} open position(s)"
                )
            self._positions.clear()
        logger.info("OrderProcessor state cleaned up")

    def _register_handlers(self) -> None:
        """Register handler for ENTRY_SIGNAL events."""
        self.event_bus.subscribe(EventType.ENTRY_SIGNAL, self._on_entry_signal)
        logger.debug("OrderProcessor registered for ENTRY_SIGNAL events")

    def _unregister_handlers(self) -> None:
        """Unregister handler from ENTRY_SIGNAL events."""
        self.event_bus.unsubscribe(EventType.ENTRY_SIGNAL, self._on_entry_signal)
        logger.debug("OrderProcessor unregistered from ENTRY_SIGNAL events")

    async def _on_entry_signal(self, event: Event) -> None:
        """
        Handle ENTRY_SIGNAL event and place order.

        Processing flow:
        1. Validate signal data
        2. Check position sizing limits
        3. Place order (simulated)
        4. Emit ORDER_PLACED event
        5. Simulate fill (MVP only)
        6. Emit ORDER_FILLED event
        7. Create and track Position

        Args:
            event (Event): ENTRY_SIGNAL event with signal data
        """
        try:
            signal = event.data

            # Validate signal data
            if not self._validate_signal(signal):
                logger.warning(f"Invalid signal received: {signal}")
                return

            # Generate order ID
            order_id = self._generate_order_id()

            # Place order
            order = await self._place_order(order_id, signal)
            if not order:
                return

            # Emit ORDER_PLACED event
            await self._publish_order_placed(order)

            # Simulate order fill (MVP)
            if self._config["enable_simulation"]:
                await self._simulate_fill(order)

        except Exception as e:
            logger.error(f"Error handling ENTRY_SIGNAL: {e}")
            await self._publish_error(e, "entry_signal_processing")

    def _validate_signal(self, signal: Dict[str, Any]) -> bool:
        """
        Validate signal data structure and values.

        Args:
            signal (Dict): Signal data from event

        Returns:
            bool: True if valid, False otherwise
        """
        required_fields = [
            "direction", "entry_price", "stop_loss",
            "take_profit", "confidence"
        ]

        # Check required fields
        for field in required_fields:
            if field not in signal:
                logger.warning(f"Missing required signal field: {field}")
                return False

        # Validate direction
        if signal["direction"] not in ["long", "short"]:
            logger.warning(f"Invalid direction: {signal['direction']}")
            return False

        # Validate prices are positive
        price_fields = ["entry_price", "stop_loss", "take_profit"]
        for field in price_fields:
            if signal[field] <= 0:
                logger.warning(f"Invalid {field}: {signal[field]}")
                return False

        # Validate risk-reward logic
        if signal["direction"] == "long":
            if signal["stop_loss"] >= signal["entry_price"]:
                logger.warning("Long signal: stop_loss must be < entry_price")
                return False
            if signal["take_profit"] <= signal["entry_price"]:
                logger.warning("Long signal: take_profit must be > entry_price")
                return False
        else:  # short
            if signal["stop_loss"] <= signal["entry_price"]:
                logger.warning("Short signal: stop_loss must be > entry_price")
                return False
            if signal["take_profit"] >= signal["entry_price"]:
                logger.warning("Short signal: take_profit must be < entry_price")
                return False

        return True

    def _generate_order_id(self) -> str:
        """
        Generate unique order ID.

        Returns:
            str: Order ID in format "order_N"
        """
        self._order_id_counter += 1
        return f"order_{self._order_id_counter}"

    async def _place_order(
        self,
        order_id: str,
        signal: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Place an order based on signal.

        For MVP, this is simulated. Future versions will integrate with
        real exchange APIs (Binance, etc.).

        Args:
            order_id (str): Unique order identifier
            signal (Dict): Signal data

        Returns:
            Dict or None: Order data if successful
        """
        try:
            # Calculate position size (simplified)
            position_size = self._config["max_position_size"]

            # Build order data
            order = {
                "order_id": order_id,
                "symbol": self._config["symbol"],
                "side": signal["direction"],
                "type": "MARKET",  # Simplified for MVP
                "entry_price": signal["entry_price"],
                "size": position_size,
                "stop_loss": signal["stop_loss"],
                "take_profit": signal["take_profit"],
                "status": "PLACED",
                "timestamp": datetime.utcnow(),
                "signal_confidence": signal.get("confidence", 0),
                "signal_reason": signal.get("reason", "")
            }

            self._orders_placed += 1

            logger.info(
                f"Placed {order['side']} order {order_id}: "
                f"{order['size']} {order['symbol']} @ {order['entry_price']:.2f}"
            )

            return order

        except Exception as e:
            logger.error(f"Failed to place order: {e}")
            return None

    async def _publish_order_placed(self, order: Dict[str, Any]) -> None:
        """
        Publish ORDER_PLACED event to queue.

        Args:
            order (Dict): Order data
        """
        try:
            event = Event(
                event_type=EventType.ORDER_PLACED,
                data=order,
                source="OrderProcessor"
            )

            await self.event_bus.publish(event)
            logger.debug(f"ORDER_PLACED event published for {order['order_id']}")

        except Exception as e:
            logger.error(f"Failed to publish ORDER_PLACED: {e}")

    async def _simulate_fill(self, order: Dict[str, Any]) -> None:
        """
        Simulate immediate order fill (MVP only).

        In production, this would listen for exchange fill notifications.
        For MVP, we immediately fill at the requested price.

        Args:
            order (Dict): Order data
        """
        try:
            # Simulate fill
            fill_data = {
                "order_id": order["order_id"],
                "symbol": order["symbol"],
                "side": order["side"],
                "fill_price": order["entry_price"],
                "filled_size": order["size"],
                "commission": order["size"] * 0.001,  # 0.1% commission
                "timestamp": datetime.utcnow()
            }

            self._orders_filled += 1

            logger.info(
                f"Simulated fill for {order['order_id']}: "
                f"{fill_data['filled_size']} @ {fill_data['fill_price']:.2f}"
            )

            # Emit ORDER_FILLED event
            await self._publish_order_filled(fill_data)

            # Create position
            await self._create_position(order, fill_data)

        except Exception as e:
            logger.error(f"Failed to simulate fill: {e}")

    async def _publish_order_filled(self, fill_data: Dict[str, Any]) -> None:
        """
        Publish ORDER_FILLED event to queue.

        Args:
            fill_data (Dict): Fill data
        """
        try:
            event = Event(
                event_type=EventType.ORDER_FILLED,
                data=fill_data,
                source="OrderProcessor"
            )

            await self.event_bus.publish(event)
            logger.debug(f"ORDER_FILLED event published for {fill_data['order_id']}")

        except Exception as e:
            logger.error(f"Failed to publish ORDER_FILLED: {e}")

    async def _create_position(
        self,
        order: Dict[str, Any],
        fill_data: Dict[str, Any]
    ) -> None:
        """
        Create Position model from order and fill data.

        Args:
            order (Dict): Order data
            fill_data (Dict): Fill data
        """
        try:
            # Create Position model
            position = Position(
                symbol=order["symbol"],
                side=order["side"],
                entry_price=fill_data["fill_price"],
                size=fill_data["filled_size"],
                stop_loss=order["stop_loss"],
                take_profit=order["take_profit"],
                timestamp=fill_data["timestamp"]
            )

            # Store position
            self._positions[order["order_id"]] = position

            # Calculate risk-reward
            rr_ratio = position.risk_reward_ratio()

            logger.info(
                f"Created position {order['order_id']}: "
                f"{position.side} {position.size} {position.symbol} @ "
                f"{position.entry_price:.2f} (R:R {rr_ratio:.2f})"
            )

            # Auto-close if enabled (for testing)
            if self._config["auto_close_positions"]:
                await self._close_position(order["order_id"], position, "AUTO_CLOSE")

        except Exception as e:
            logger.error(f"Failed to create position: {e}")

    async def _close_position(
        self,
        order_id: str,
        position: Position,
        reason: str
    ) -> None:
        """
        Close a position and emit POSITION_CLOSED event.

        Args:
            order_id (str): Order identifier
            position (Position): Position to close
            reason (str): Close reason
        """
        try:
            # Calculate P&L (simplified - assumes take profit hit)
            if position.side == "long":
                exit_price = position.take_profit
                pnl = (exit_price - position.entry_price) * position.size
            else:  # short
                exit_price = position.take_profit
                pnl = (position.entry_price - exit_price) * position.size

            # Build close data
            close_data = {
                "order_id": order_id,
                "symbol": position.symbol,
                "side": position.side,
                "entry_price": position.entry_price,
                "exit_price": exit_price,
                "size": position.size,
                "realized_pnl": pnl,
                "close_reason": reason,
                "timestamp": datetime.utcnow()
            }

            # Remove from active positions
            if order_id in self._positions:
                del self._positions[order_id]

            self._positions_closed += 1

            logger.info(
                f"Closed position {order_id}: "
                f"P&L=${pnl:.2f}, Reason={reason}"
            )

            # Emit POSITION_CLOSED event
            await self._publish_position_closed(close_data)

        except Exception as e:
            logger.error(f"Failed to close position: {e}")

    async def _publish_position_closed(self, close_data: Dict[str, Any]) -> None:
        """
        Publish POSITION_CLOSED event to queue.

        Args:
            close_data (Dict): Position close data
        """
        try:
            event = Event(
                event_type=EventType.POSITION_CLOSED,
                data=close_data,
                source="OrderProcessor"
            )

            await self.event_bus.publish(event)
            logger.debug(f"POSITION_CLOSED event published for {close_data['order_id']}")

        except Exception as e:
            logger.error(f"Failed to publish POSITION_CLOSED: {e}")

    async def _publish_error(self, error: Exception, context: str) -> None:
        """
        Publish ERROR event to queue for system errors.

        Args:
            error (Exception): The error that occurred
            context (str): Context where error occurred
        """
        try:
            event = Event(
                event_type=EventType.ERROR,
                data={
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                    "component": "OrderProcessor",
                    "context": context,
                    "timestamp": datetime.utcnow()
                },
                source="OrderProcessor"
            )

            await self.event_bus.publish(event)
            logger.debug(f"ERROR event published: {context}")

        except Exception as e:
            logger.error(f"Failed to publish ERROR event: {e}")

    @property
    def orders_placed_count(self) -> int:
        """Get total number of orders placed."""
        return self._orders_placed

    @property
    def orders_filled_count(self) -> int:
        """Get total number of orders filled."""
        return self._orders_filled

    @property
    def positions_closed_count(self) -> int:
        """Get total number of positions closed."""
        return self._positions_closed

    @property
    def open_positions_count(self) -> int:
        """Get number of currently open positions."""
        return len(self._positions) if self._positions else 0

    def get_position(self, order_id: str) -> Optional[Position]:
        """
        Get position by order ID.

        Args:
            order_id (str): Order identifier

        Returns:
            Position or None: Position if exists
        """
        return self._positions.get(order_id) if self._positions else None
