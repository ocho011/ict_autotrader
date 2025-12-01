"""
Event Processor Infrastructure for ICT AutoTrader

This module provides the base infrastructure for event-driven processing:
- EventProcessor: Abstract base class for all event processors
- EventOrchestrator: Coordinates multiple processors and manages lifecycle

The processor system enables modular, loosely-coupled event handling where
each processor focuses on a specific domain (patterns, signals, orders).
"""

from abc import ABC, abstractmethod
from typing import List
from loguru import logger
from .event_bus import EventBus


class EventProcessor(ABC):
    """
    Abstract base class for event processors.

    Provides lifecycle management, error handling, and standardized
    patterns for processing events in the trading system. All processors
    inherit from this class to ensure consistent behavior.

    The processor lifecycle follows this pattern:
    1. Construction with EventBus dependency injection
    2. start() - registers handlers and initializes state
    3. Processing - handlers respond to events asynchronously
    4. stop() - unregisters handlers and cleanup

    Attributes:
        event_bus (EventBus): The event bus for pub/sub communication
        _is_started (bool): Whether the processor is currently running

    Examples:
        >>> class MyProcessor(EventProcessor):
        ...     def _register_handlers(self):
        ...         self.event_bus.subscribe(EventType.CANDLE_CLOSED, self._on_candle)
        ...
        ...     def _unregister_handlers(self):
        ...         self.event_bus.unsubscribe(EventType.CANDLE_CLOSED, self._on_candle)
        ...
        ...     async def _on_candle(self, event: Event):
        ...         # Process candle data
        ...         pass
        >>>
        >>> bus = EventBus()
        >>> processor = MyProcessor(bus)
        >>> await processor.start()
        >>> # ... process events ...
        >>> await processor.stop()
    """

    def __init__(self, event_bus: EventBus):
        """
        Initialize the processor with event bus dependency.

        Args:
            event_bus (EventBus): Event bus for subscribing to and emitting events
        """
        self.event_bus = event_bus
        self._is_started = False

    async def start(self) -> None:
        """
        Start the processor and register event handlers.

        This method:
        1. Checks if already started (idempotent)
        2. Calls custom startup hook (_on_start)
        3. Registers event handlers with the event bus
        4. Marks processor as started

        Raises:
            Exception: If handler registration fails (logged but not raised)

        Examples:
            >>> processor = MyProcessor(event_bus)
            >>> await processor.start()
            >>> assert processor.is_running == True
        """
        if self._is_started:
            logger.debug(f"{self.__class__.__name__} already started")
            return

        logger.info(f"Starting {self.__class__.__name__}")

        try:
            await self._on_start()
            self._register_handlers()
            self._is_started = True
            logger.info(f"{self.__class__.__name__} started successfully")
        except Exception as e:
            logger.error(f"Failed to start {self.__class__.__name__}: {e}")
            raise

    async def stop(self) -> None:
        """
        Stop the processor and unregister event handlers.

        This method:
        1. Checks if already stopped (idempotent)
        2. Unregisters event handlers from the event bus
        3. Calls custom shutdown hook (_on_stop)
        4. Marks processor as stopped

        Ensures graceful shutdown even if errors occur during cleanup.

        Examples:
            >>> processor = MyProcessor(event_bus)
            >>> await processor.start()
            >>> await processor.stop()
            >>> assert processor.is_running == False
        """
        if not self._is_started:
            logger.debug(f"{self.__class__.__name__} already stopped")
            return

        logger.info(f"Stopping {self.__class__.__name__}")

        try:
            self._unregister_handlers()
            await self._on_stop()
            self._is_started = False
            logger.info(f"{self.__class__.__name__} stopped successfully")
        except Exception as e:
            logger.error(f"Error during {self.__class__.__name__} shutdown: {e}")
            # Mark as stopped anyway to prevent hanging state
            self._is_started = False

    @abstractmethod
    def _register_handlers(self) -> None:
        """
        Register event handlers with the event bus.

        Subclasses must implement this to subscribe to relevant event types.
        This method is called during start() after _on_start().

        Examples:
            >>> def _register_handlers(self):
            ...     self.event_bus.subscribe(EventType.CANDLE_CLOSED, self._on_candle)
            ...     self.event_bus.subscribe(EventType.ORDER_FILLED, self._on_fill)
        """
        pass

    @abstractmethod
    def _unregister_handlers(self) -> None:
        """
        Unregister event handlers from the event bus.

        Subclasses must implement this to unsubscribe from event types.
        This method is called during stop() before _on_stop().

        Important: Must unsubscribe the same handlers registered in _register_handlers().

        Examples:
            >>> def _unregister_handlers(self):
            ...     self.event_bus.unsubscribe(EventType.CANDLE_CLOSED, self._on_candle)
            ...     self.event_bus.unsubscribe(EventType.ORDER_FILLED, self._on_fill)
        """
        pass

    async def _on_start(self) -> None:
        """
        Custom startup logic hook.

        Override this method to perform initialization tasks before
        handler registration (e.g., loading state, connecting to services).

        Default implementation does nothing.

        Examples:
            >>> async def _on_start(self):
            ...     self._patterns = []  # Initialize state
            ...     self._last_candle = None
            ...     logger.info("Pattern detector initialized")
        """
        pass

    async def _on_stop(self) -> None:
        """
        Custom shutdown logic hook.

        Override this method to perform cleanup tasks after
        handler unregistration (e.g., saving state, closing connections).

        Default implementation does nothing.

        Examples:
            >>> async def _on_stop(self):
            ...     await self._save_state()  # Persist state
            ...     self._patterns.clear()
            ...     logger.info("Pattern detector cleaned up")
        """
        pass

    @property
    def is_running(self) -> bool:
        """
        Check if the processor is currently running.

        Returns:
            bool: True if processor is started, False otherwise

        Examples:
            >>> processor = MyProcessor(event_bus)
            >>> processor.is_running
            False
            >>> await processor.start()
            >>> processor.is_running
            True
        """
        return self._is_started


class EventOrchestrator:
    """
    Orchestrates multiple event processors.

    Manages the lifecycle of multiple processors as a coordinated unit.
    Provides centralized control for starting, stopping, and monitoring
    processors in the event-driven trading system.

    The orchestrator ensures:
    - Processors start in registration order
    - Processors stop in reverse order (cleanup safety)
    - Failed processor doesn't break others
    - Centralized logging for system observability

    Attributes:
        event_bus (EventBus): The event bus shared by all processors
        _processors (List[EventProcessor]): Registered processors

    Examples:
        >>> bus = EventBus()
        >>> orchestrator = EventOrchestrator(bus)
        >>>
        >>> # Register processors
        >>> orchestrator.register(PatternProcessor(bus))
        >>> orchestrator.register(SignalProcessor(bus))
        >>> orchestrator.register(OrderProcessor(bus))
        >>>
        >>> # Start all processors
        >>> await orchestrator.start_all()
        >>>
        >>> # ... system runs ...
        >>>
        >>> # Stop all processors
        >>> await orchestrator.stop_all()
    """

    def __init__(self, event_bus: EventBus):
        """
        Initialize the orchestrator with an event bus.

        Args:
            event_bus (EventBus): Event bus to be shared with all processors
        """
        self.event_bus = event_bus
        self._processors: List[EventProcessor] = []

    def register(self, processor: EventProcessor) -> None:
        """
        Register a processor with the orchestrator.

        Processors should be registered before starting. Registration order
        determines startup order (and reverse determines shutdown order).

        Args:
            processor (EventProcessor): Processor instance to register

        Examples:
            >>> orchestrator = EventOrchestrator(event_bus)
            >>> orchestrator.register(PatternProcessor(event_bus))
            >>> orchestrator.register(SignalProcessor(event_bus))
        """
        self._processors.append(processor)
        logger.info(
            f"Registered {processor.__class__.__name__} "
            f"({len(self._processors)} total processors)"
        )

    async def start_all(self) -> None:
        """
        Start all registered processors in order.

        Processors are started in registration order. If a processor fails
        to start, the error is logged but other processors continue to start.
        This ensures partial system functionality even if one component fails.

        Raises:
            Exception: Only if all processors fail to start

        Examples:
            >>> await orchestrator.start_all()
            # Output:
            # INFO: Starting 3 processors
            # INFO: Starting PatternProcessor
            # INFO: Starting SignalProcessor
            # INFO: Starting OrderProcessor
            # INFO: All processors started successfully
        """
        logger.info(f"Starting {len(self._processors)} processor(s)")

        failed_count = 0
        for processor in self._processors:
            try:
                await processor.start()
            except Exception as e:
                logger.error(
                    f"Failed to start {processor.__class__.__name__}: {e}"
                )
                failed_count += 1

        if failed_count == len(self._processors):
            raise RuntimeError("All processors failed to start")
        elif failed_count > 0:
            logger.warning(
                f"{failed_count} of {len(self._processors)} processors failed to start"
            )
        else:
            logger.info("All processors started successfully")

    async def stop_all(self) -> None:
        """
        Stop all registered processors in reverse order.

        Processors are stopped in reverse registration order to ensure
        proper cleanup dependencies (last in, first out). Errors during
        shutdown are logged but don't prevent other processors from stopping.

        Examples:
            >>> await orchestrator.stop_all()
            # Output:
            # INFO: Stopping 3 processor(s)
            # INFO: Stopping OrderProcessor
            # INFO: Stopping SignalProcessor
            # INFO: Stopping PatternProcessor
            # INFO: All processors stopped successfully
        """
        logger.info(f"Stopping {len(self._processors)} processor(s)")

        failed_count = 0
        # Stop in reverse order (LIFO - last in, first out)
        for processor in reversed(self._processors):
            try:
                await processor.stop()
            except Exception as e:
                logger.error(
                    f"Failed to stop {processor.__class__.__name__}: {e}"
                )
                failed_count += 1

        if failed_count > 0:
            logger.warning(
                f"{failed_count} of {len(self._processors)} processors "
                f"failed to stop cleanly"
            )
        else:
            logger.info("All processors stopped successfully")

    @property
    def processor_count(self) -> int:
        """
        Get the number of registered processors.

        Returns:
            int: Count of registered processors

        Examples:
            >>> orchestrator.processor_count
            3
        """
        return len(self._processors)

    @property
    def running_count(self) -> int:
        """
        Get the number of currently running processors.

        Returns:
            int: Count of processors in running state

        Examples:
            >>> orchestrator.running_count
            3
        """
        return sum(1 for p in self._processors if p.is_running)
