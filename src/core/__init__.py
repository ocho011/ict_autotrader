"""
Core module for event-driven architecture.

This module provides the foundational components for the trading system:
- EventBus: Publish-subscribe event system
- EventProcessor: Base class for event processors
- EventOrchestrator: Processor lifecycle coordinator
- StateStore: Pattern and position state management
"""

from .event_processor import EventProcessor, EventOrchestrator

__all__ = [
    "EventProcessor",
    "EventOrchestrator",
]
