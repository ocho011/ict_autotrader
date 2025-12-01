"""
Event Processors for ICT AutoTrader

This package contains domain-specific event processors for the trading system:
- PatternProcessor: Detects Order Blocks and Fair Value Gaps
- SignalProcessor: Combines patterns into trade signals
- OrderProcessor: Manages order placement and position lifecycle

Each processor extends EventProcessor base class and integrates with the
EventBus for loosely-coupled event-driven architecture.

Examples:
    >>> from src.core.event_bus import EventBus
    >>> from src.core.event_processor import EventOrchestrator
    >>> from src.processors import PatternProcessor, SignalProcessor, OrderProcessor
    >>>
    >>> # Create event bus
    >>> bus = EventBus()
    >>> await bus.start()
    >>>
    >>> # Create orchestrator and register processors
    >>> orchestrator = EventOrchestrator(bus)
    >>> orchestrator.register(PatternProcessor(bus))
    >>> orchestrator.register(SignalProcessor(bus))
    >>> orchestrator.register(OrderProcessor(bus))
    >>>
    >>> # Start all processors
    >>> await orchestrator.start_all()
    >>>
    >>> # System is now running and processing events
    >>> # ...
    >>>
    >>> # Shutdown
    >>> await orchestrator.stop_all()
    >>> await bus.stop()
"""

from .pattern_processor import PatternProcessor
from .signal_processor import SignalProcessor
from .order_processor import OrderProcessor

__all__ = [
    "PatternProcessor",
    "SignalProcessor",
    "OrderProcessor",
]
