"""
Event Bus System for ICT AutoTrader

This module provides the event-driven architecture foundation for the trading system.
It includes event type definitions and the event bus infrastructure for decoupled
communication between system components.

The event bus enables loose coupling between components while maintaining clear
data flow and system observability through centralized event handling.
"""

from enum import Enum
from typing import Any, Callable, Dict, List
from dataclasses import dataclass
from datetime import datetime
import asyncio
from loguru import logger


class EventType(Enum):
    """
    Enumeration of all event types in the ICT AutoTrader MVP system.

    Each event type represents a significant occurrence in the trading lifecycle,
    from market data updates to trade execution and error handling. Events are
    used for inter-component communication in a decoupled architecture.

    Event values are string literals to ensure clear logging and debugging.
    All components should use these enum members rather than raw strings.

    Examples:
        >>> EventType.CANDLE_CLOSED
        <EventType.CANDLE_CLOSED: 'candle_closed'>

        >>> EventType.CANDLE_CLOSED.value
        'candle_closed'

        >>> str(EventType.ENTRY_SIGNAL)
        'EventType.ENTRY_SIGNAL'
    """

    CANDLE_CLOSED = "candle_closed"
    """
    Emitted when a candlestick period completes.

    This event triggers pattern analysis and strategy evaluation.
    Payload typically includes: symbol, interval, open, high, low, close, volume, timestamp.

    Use case: Market data processing triggers strategy analysis on each candle close.
    """

    ORDER_BLOCK_DETECTED = "order_block_detected"
    """
    Emitted when an Order Block pattern is identified in price action.

    Order Blocks represent institutional activity zones where smart money likely placed orders.
    These are key support/resistance levels in ICT methodology.

    Payload includes: price level, timeframe, bullish/bearish direction, strength score.

    Use case: Pattern detection component signals potential entry zones to strategy module.
    """

    FVG_DETECTED = "fvg_detected"
    """
    Emitted when a Fair Value Gap (FVG) is detected.

    FVGs are inefficiencies in price action where the market moved too quickly,
    creating gaps that price tends to fill later. Critical for ICT entry timing.

    Payload includes: gap range (high/low), direction, volume imbalance, mitigation status.

    Use case: Identifies potential entry zones based on price inefficiencies.
    """

    ENTRY_SIGNAL = "entry_signal"
    """
    Emitted when strategy conditions align for a trade entry.

    This is a high-priority event that triggers the execution module to prepare
    and place an order. Combines multiple pattern confirmations into a trade decision.

    Payload includes: direction (long/short), entry price, stop loss, take profit,
                     confidence score, strategy reason.

    Use case: Strategy module signals execution module to enter a position.
    """

    ORDER_PLACED = "order_placed"
    """
    Emitted when an order is successfully submitted to the exchange.

    Indicates the order has been accepted by Binance but not yet filled.
    Important for tracking order lifecycle and system state.

    Payload includes: order_id, symbol, side, type, quantity, price, status.

    Use case: Execution confirms order submission; risk management monitors open orders.
    """

    ORDER_FILLED = "order_filled"
    """
    Emitted when an exchange order is completely filled.

    Critical event indicating position entry/exit completion. Triggers position
    tracking updates and notification delivery.

    Payload includes: order_id, fill_price, filled_quantity, commission, timestamp.

    Use case: Updates position state, calculates P&L, sends notifications.
    """

    POSITION_CLOSED = "position_closed"
    """
    Emitted when a trading position is fully closed (exited).

    Marks the end of a trade lifecycle. Used for performance tracking,
    risk management updates, and trade journaling.

    Payload includes: position_id, entry_price, exit_price, realized_pnl,
                     holding_time, close_reason.

    Use case: Final P&L calculation, risk limit updates, performance analytics.
    """

    ERROR = "error"
    """
    Emitted when a system error or exception occurs.

    Generic error event for exception handling, logging, and system monitoring.
    Allows centralized error handling and notification of critical failures.

    Payload includes: error_type, error_message, component, severity, stack_trace.

    Use case: Central error logging, critical failure notifications, system health monitoring.
    """

    def __str__(self) -> str:
        """
        Return the string representation of the event type.

        Returns:
            str: The event type name (e.g., 'CANDLE_CLOSED')
        """
        return self.name

    def __repr__(self) -> str:
        """
        Return the detailed representation of the event type.

        Returns:
            str: Full representation including class and value
        """
        return f"<EventType.{self.name}: '{self.value}'>"


@dataclass
class Event:
    """
    Event data structure for the event bus system.

    Encapsulates all information about an event occurrence, including type,
    payload data, and metadata for tracking and debugging.

    Attributes:
        event_type (EventType): The type of event being emitted
        data (Dict[str, Any]): Event payload data specific to the event type
        timestamp (datetime): When the event was created
        source (str): Component or module that emitted the event

    Examples:
        >>> event = Event(
        ...     event_type=EventType.CANDLE_CLOSED,
        ...     data={'symbol': 'BTCUSDT', 'close': 45000.0},
        ...     source='data_collector'
        ... )
        >>> event.event_type
        <EventType.CANDLE_CLOSED: 'candle_closed'>
    """

    event_type: EventType
    data: Dict[str, Any]
    source: str
    timestamp: datetime = None

    def __post_init__(self):
        """
        Validate event data and set timestamp if not provided.

        Raises:
            TypeError: If event_type is not EventType or data is not dict
        """
        # Validate event_type is EventType enum member
        if not isinstance(self.event_type, EventType):
            raise TypeError(
                f"event_type must be EventType enum, got {type(self.event_type).__name__}"
            )

        # Validate data is dictionary
        if not isinstance(self.data, dict):
            raise TypeError(
                f"data must be dict, got {type(self.data).__name__}"
            )

        # Set timestamp to current time if not provided
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

    def __str__(self) -> str:
        """Return human-readable event description."""
        return f"Event({self.event_type.name} from {self.source} at {self.timestamp})"

    def __repr__(self) -> str:
        """Return detailed event representation."""
        return (
            f"Event(event_type={self.event_type!r}, "
            f"source='{self.source}', "
            f"timestamp={self.timestamp!r}, "
            f"data={self.data!r})"
        )


class EventBus:
    """
    Central event bus for publish-subscribe event handling.

    The EventBus implements the Observer pattern, allowing components to subscribe
    to specific event types and receive notifications when those events occur.
    This enables loose coupling between system components.

    Features:
        - Type-safe event subscription using EventType enum
        - Multiple subscribers per event type
        - Synchronous event delivery (async version can be added later)
        - Central event logging and debugging

    Thread Safety:
        Current implementation is NOT thread-safe. For multi-threaded use,
        add locking mechanisms or use async/await with asyncio.

    Examples:
        >>> bus = EventBus()
        >>>
        >>> def on_candle_closed(event: Event):
        ...     print(f"Candle closed: {event.data['close']}")
        >>>
        >>> bus.subscribe(EventType.CANDLE_CLOSED, on_candle_closed)
        >>> bus.emit(Event(EventType.CANDLE_CLOSED, {'close': 45000}, 'data'))
        Candle closed: 45000
    """

    def __init__(self):
        """Initialize the event bus with empty subscriber lists and async queue."""
        self._subscribers: Dict[EventType, List[Callable[[Event], None]]] = {
            event_type: [] for event_type in EventType
        }
        self._queue: asyncio.Queue = None  # Created in start() to use correct event loop
        self._running: bool = False
        self._task: asyncio.Task = None

    def subscribe(self, event_type: EventType, callback: Callable[[Event], None]) -> None:
        """
        Subscribe to a specific event type.

        Args:
            event_type (EventType): The event type to subscribe to
            callback (Callable): Function to call when event occurs.
                               Must accept an Event parameter.

        Raises:
            TypeError: If event_type is not an EventType enum member

        Examples:
            >>> bus = EventBus()
            >>> bus.subscribe(EventType.ERROR, lambda e: print(f"Error: {e.data}"))
        """
        if not isinstance(event_type, EventType):
            raise TypeError(f"event_type must be EventType enum, got {type(event_type)}")

        if callback not in self._subscribers[event_type]:
            self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: EventType, callback: Callable[[Event], None]) -> None:
        """
        Unsubscribe from a specific event type.

        Args:
            event_type (EventType): The event type to unsubscribe from
            callback (Callable): The callback function to remove

        Examples:
            >>> def my_handler(event):
            ...     pass
            >>> bus.subscribe(EventType.ERROR, my_handler)
            >>> bus.unsubscribe(EventType.ERROR, my_handler)
        """
        if callback in self._subscribers[event_type]:
            self._subscribers[event_type].remove(callback)

    def emit(self, event: Event) -> None:
        """
        Emit an event to all subscribers.

        Synchronously calls all registered callbacks for the event type.
        Exceptions in callbacks are caught and logged to prevent one subscriber
        from breaking others.

        Args:
            event (Event): The event to emit

        Raises:
            TypeError: If event is not an Event instance

        Examples:
            >>> bus = EventBus()
            >>> event = Event(EventType.CANDLE_CLOSED, {'price': 45000}, 'test')
            >>> bus.emit(event)
        """
        if not isinstance(event, Event):
            raise TypeError(f"event must be Event instance, got {type(event)}")

        # Call all subscribers for this event type
        for callback in self._subscribers[event.event_type]:
            try:
                callback(event)
            except Exception as e:
                # Log error but don't break other subscribers
                # In production, this should use proper logging
                print(f"Error in event subscriber: {e}")
                # Could emit ERROR event here, but avoid infinite loops

    def subscriber_count(self, event_type: EventType) -> int:
        """
        Get the number of subscribers for an event type.

        Args:
            event_type (EventType): The event type to check

        Returns:
            int: Number of registered subscribers

        Examples:
            >>> bus = EventBus()
            >>> bus.subscriber_count(EventType.CANDLE_CLOSED)
            0
        """
        return len(self._subscribers[event_type])

    def clear_subscribers(self, event_type: EventType = None) -> None:
        """
        Clear subscribers for a specific event type or all events.

        Args:
            event_type (EventType, optional): Event type to clear.
                                            If None, clears all subscribers.

        Examples:
            >>> bus = EventBus()
            >>> bus.clear_subscribers(EventType.ERROR)  # Clear ERROR subscribers
            >>> bus.clear_subscribers()  # Clear all subscribers
        """
        if event_type is None:
            # Clear all subscribers
            for event_type in EventType:
                self._subscribers[event_type].clear()
        else:
            self._subscribers[event_type].clear()

    async def publish(self, event: Event) -> None:
        """
        Publish an event to the async queue for non-blocking emission.

        This method adds events to an async queue without blocking the caller.
        Events are processed asynchronously by the event loop started with start().

        Args:
            event (Event): The event to publish

        Raises:
            TypeError: If event is not an Event instance
            RuntimeError: If event bus is not started

        Examples:
            >>> bus = EventBus()
            >>> await bus.start()  # Start event processing loop
            >>> event = Event(EventType.CANDLE_CLOSED, {'price': 45000}, 'data')
            >>> await bus.publish(event)  # Non-blocking publish
        """
        if not isinstance(event, Event):
            raise TypeError(f"event must be Event instance, got {type(event)}")

        if self._queue is None:
            raise RuntimeError("Event bus not started. Call start() first.")

        # Non-blocking queue insertion
        self._queue.put_nowait(event)

    async def start(self) -> None:
        """
        Start the async event processing loop.

        This method creates and runs the event processing task that continuously
        reads events from the queue and dispatches them to subscribers.

        The processing loop runs until stop() is called.

        Examples:
            >>> bus = EventBus()
            >>> await bus.start()
            >>> # Event processing is now active
            >>> await bus.publish(event)
            >>> await bus.stop()
        """
        if self._running:
            return  # Already running

        # Create queue in the current event loop to avoid "different loop" errors
        self._queue = asyncio.Queue()
        self._running = True
        self._task = asyncio.create_task(self._process_events())

    async def _process_events(self) -> None:
        """
        Internal event processing loop.

        Continuously reads events from the queue and dispatches them to subscribers.
        Runs until _running flag is set to False AND queue is empty.
        """
        while True:
            event = None
            try:
                # Wait for event with timeout to allow checking _running flag
                event = await asyncio.wait_for(self._queue.get(), timeout=0.1)

                # Dispatch event to all subscribers
                await self._dispatch(event)

            except asyncio.TimeoutError:
                # No event available - check if we should exit
                if not self._running and self._queue.empty():
                    break
                continue
            except Exception as e:
                # Log error but keep processing
                logger.error(f"Error processing event: {e}")
            finally:
                # Always mark task as done if we got an event
                if event is not None:
                    self._queue.task_done()

    async def _dispatch(self, event: Event) -> None:
        """
        Dispatch an event to all subscribers with timeout protection.

        Calls all registered callbacks for the event type, supporting both
        synchronous and asynchronous handlers. Each handler is protected by
        a 1.0s timeout to prevent hanging.

        Async handlers are awaited directly with timeout protection.
        Sync handlers are executed in a thread pool to avoid blocking the event loop.

        Args:
            event (Event): The event to dispatch

        Examples:
            >>> async def async_handler(event: Event):
            ...     await asyncio.sleep(0.1)
            ...
            >>> def sync_handler(event: Event):
            ...     time.sleep(0.1)
            ...
            >>> bus.subscribe(EventType.CANDLE_CLOSED, async_handler)
            >>> bus.subscribe(EventType.CANDLE_CLOSED, sync_handler)
            >>> await bus._dispatch(event)  # Both handlers called with timeout
        """
        handlers = self._subscribers[event.event_type]
        handler_count = len(handlers)

        logger.debug(
            f"Dispatching event {event.event_type.value} to {handler_count} handler(s)"
        )

        for callback in handlers:
            try:
                # Check if handler is async coroutine function
                if asyncio.iscoroutinefunction(callback):
                    # Async handler: await with timeout
                    await asyncio.wait_for(callback(event), timeout=1.0)
                else:
                    # Sync handler: run in thread pool with timeout
                    await asyncio.wait_for(
                        asyncio.to_thread(callback, event),
                        timeout=1.0
                    )
            except asyncio.TimeoutError:
                # Handler exceeded timeout - log warning but continue
                logger.warning(
                    f"Handler {callback.__name__} for event {event.event_type.value} "
                    f"exceeded 1.0s timeout"
                )
            except Exception as e:
                # Log error but don't break other subscribers
                logger.error(
                    f"Error in event subscriber {callback.__name__} "
                    f"for {event.event_type.value}: {e}"
                )

    async def stop(self) -> None:
        """
        Stop the event processing loop and wait for queue to be processed.

        This method gracefully shuts down the event bus by:
        1. Setting the running flag to False
        2. Waiting for all queued events to be processed (with timeout)
        3. Cancelling the processing task

        No events are lost during shutdown (unless timeout is reached).

        Examples:
            >>> bus = EventBus()
            >>> await bus.start()
            >>> # ... process events ...
            >>> await bus.stop()  # Graceful shutdown
        """
        if not self._running:
            return  # Not running

        self._running = False

        # Wait for all queued events to be processed (with 5s timeout)
        try:
            await asyncio.wait_for(self._queue.join(), timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning("Event queue did not drain within 5s timeout")

        # Cancel the processing task
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass  # Expected when cancelling

    @property
    def is_running(self) -> bool:
        """
        Check if the event bus is currently running.

        Returns:
            bool: True if event processing is active, False otherwise
        """
        return self._running

    @property
    def queue_size(self) -> int:
        """
        Get the current number of events in the queue.

        Returns:
            int: Number of events waiting to be processed (0 if not started)
        """
        if self._queue is None:
            return 0
        return self._queue.qsize()
