"""
Integration tests for full event processing pipeline.

Tests cover the complete event flow:
CANDLE_CLOSED → PatternProcessor → ORDER_BLOCK/FVG_DETECTED
             → SignalProcessor → ENTRY_SIGNAL
             → OrderProcessor → ORDER_PLACED → ORDER_FILLED → POSITION_CLOSED

Verifies:
- End-to-end event flow
- Data integrity across processors
- No event loss or timeout issues
- Proper processor coordination
"""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime
from typing import List, Dict, Any

from src.core.event_bus import EventBus, Event, EventType
from src.core.event_processor import EventOrchestrator
from src.processors.pattern_processor import PatternProcessor
from src.processors.signal_processor import SignalProcessor
from src.processors.order_processor import OrderProcessor


@pytest_asyncio.fixture
async def event_pipeline():
    """
    Create full event processing pipeline with all components.

    Returns:
        Tuple: (event_bus, orchestrator, event_tracker)
    """
    # Create event bus
    bus = EventBus()
    await bus.start()

    # Create orchestrator
    orchestrator = EventOrchestrator(bus)

    # Create and register processors
    pattern_processor = PatternProcessor(bus)
    signal_processor = SignalProcessor(bus)
    order_processor = OrderProcessor(bus, config={"auto_close_positions": True})

    orchestrator.register(pattern_processor)
    orchestrator.register(signal_processor)
    orchestrator.register(order_processor)

    # Start all processors
    await orchestrator.start_all()

    # Event tracker for verification
    event_tracker = EventTracker(bus)
    await event_tracker.start()

    yield bus, orchestrator, event_tracker

    # Cleanup
    await orchestrator.stop_all()
    await event_tracker.stop()
    await bus.stop()


class EventTracker:
    """Helper class to track all events for verification."""

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.events: Dict[EventType, List[Event]] = {
            event_type: [] for event_type in EventType
        }

    async def start(self):
        """Subscribe to all event types."""
        for event_type in EventType:
            self.event_bus.subscribe(event_type, self._track_event)

    async def stop(self):
        """Unsubscribe from all event types."""
        for event_type in EventType:
            self.event_bus.unsubscribe(event_type, self._track_event)

    async def _track_event(self, event: Event):
        """Track received event."""
        self.events[event.event_type].append(event)

    def get_events(self, event_type: EventType) -> List[Event]:
        """Get all events of a specific type."""
        return self.events[event_type]

    def event_count(self, event_type: EventType) -> int:
        """Get count of events of a specific type."""
        return len(self.events[event_type])

    def clear(self):
        """Clear all tracked events."""
        for event_type in EventType:
            self.events[event_type].clear()


def create_bullish_candle_setup() -> List[Dict[str, Any]]:
    """
    Create 3-candle setup that should trigger bullish Order Block and FVG.

    Returns:
        List of candle data dictionaries
    """
    base_time = datetime.utcnow()

    candles = [
        # Candle 0 - Setup for FVG
        {
            "symbol": "BTCUSDT",
            "open": 44000.0,
            "high": 44200.0,
            "low": 43900.0,
            "close": 44100.0,
            "volume": 100.0,
            "timestamp": base_time
        },
        # Candle 1 - Strong bullish candle (creates Order Block)
        {
            "symbol": "BTCUSDT",
            "open": 44100.0,
            "high": 45500.0,  # Large body
            "low": 44000.0,
            "close": 45200.0,  # Strong close
            "volume": 500.0,  # High volume
            "timestamp": base_time
        },
        # Candle 2 - Creates FVG with candle 0
        {
            "symbol": "BTCUSDT",
            "open": 45200.0,
            "high": 45400.0,
            "low": 44500.0,  # Gap: candle[0].high (44200) < candle[2].low (44500)
            "close": 45300.0,
            "volume": 200.0,
            "timestamp": base_time
        },
    ]

    return candles


@pytest.mark.asyncio
async def test_full_pipeline_bullish_signal(event_pipeline):
    """Test complete pipeline from candle to order placement (bullish)."""
    bus, orchestrator, tracker = event_pipeline

    # Create bullish candle setup
    candles = create_bullish_candle_setup()

    # Emit candles
    for candle_data in candles:
        event = Event(
            EventType.CANDLE_CLOSED,
            candle_data,
            "test"
        )
        await bus.publish(event)
        await asyncio.sleep(0.1)  # Allow processing

    # Wait for full pipeline processing
    await asyncio.sleep(0.5)

    # Verify events were emitted in correct order
    assert tracker.event_count(EventType.CANDLE_CLOSED) == 3
    assert tracker.event_count(EventType.ORDER_BLOCK_DETECTED) >= 1
    assert tracker.event_count(EventType.FVG_DETECTED) >= 1
    assert tracker.event_count(EventType.ENTRY_SIGNAL) >= 1
    assert tracker.event_count(EventType.ORDER_PLACED) >= 1
    assert tracker.event_count(EventType.ORDER_FILLED) >= 1
    assert tracker.event_count(EventType.POSITION_CLOSED) >= 1  # Auto-closed

    # Verify signal data integrity
    signals = tracker.get_events(EventType.ENTRY_SIGNAL)
    assert len(signals) > 0
    signal_data = signals[0].data
    assert signal_data["direction"] == "long"
    assert signal_data["entry_price"] > 0
    assert signal_data["stop_loss"] < signal_data["entry_price"]
    assert signal_data["take_profit"] > signal_data["entry_price"]
    assert signal_data["confidence"] >= 70

    # Verify order data integrity
    orders = tracker.get_events(EventType.ORDER_PLACED)
    assert len(orders) > 0
    order_data = orders[0].data
    assert order_data["side"] == "long"
    assert order_data["entry_price"] == signal_data["entry_price"]
    assert order_data["stop_loss"] == signal_data["stop_loss"]
    assert order_data["take_profit"] == signal_data["take_profit"]


@pytest.mark.asyncio
async def test_pipeline_concurrent_candles(event_pipeline):
    """Test pipeline handles multiple concurrent candles."""
    bus, orchestrator, tracker = event_pipeline

    # Emit multiple candle sets concurrently
    candle_sets = [create_bullish_candle_setup() for _ in range(3)]

    for candle_set in candle_sets:
        for candle_data in candle_set:
            event = Event(EventType.CANDLE_CLOSED, candle_data, "test")
            await bus.publish(event)

    # Wait for processing
    await asyncio.sleep(1.0)

    # Should process all candles without loss
    assert tracker.event_count(EventType.CANDLE_CLOSED) == 9  # 3 sets * 3 candles
    # Should generate multiple signals (may not be exactly 3 due to confluence timing)
    assert tracker.event_count(EventType.ENTRY_SIGNAL) >= 1


@pytest.mark.asyncio
async def test_pipeline_event_order(event_pipeline):
    """Test events are processed in correct order."""
    bus, orchestrator, tracker = event_pipeline

    # Create candle setup
    candles = create_bullish_candle_setup()

    # Track event timestamps
    event_times = []

    # Modified tracker to record timestamps
    async def time_tracker(event: Event):
        event_times.append((event.event_type, event.timestamp))

    for event_type in EventType:
        bus.subscribe(event_type, time_tracker)

    # Emit candles
    for candle_data in candles:
        event = Event(EventType.CANDLE_CLOSED, candle_data, "test")
        await bus.publish(event)
        await asyncio.sleep(0.1)

    # Wait for processing
    await asyncio.sleep(0.5)

    # Verify logical event order (timestamps should be ascending for same flow)
    # CANDLE_CLOSED should come before ORDER_BLOCK_DETECTED
    candle_times = [t for et, t in event_times if et == EventType.CANDLE_CLOSED]
    ob_times = [t for et, t in event_times if et == EventType.ORDER_BLOCK_DETECTED]

    if candle_times and ob_times:
        assert min(ob_times) >= min(candle_times)


@pytest.mark.asyncio
async def test_pipeline_no_signal_without_confluence(event_pipeline):
    """Test signal processor doesn't emit without pattern confluence."""
    bus, orchestrator, tracker = event_pipeline

    # Emit single candle (no FVG possible, but might create Order Block)
    candle_data = {
        "symbol": "BTCUSDT",
        "open": 44000.0,
        "high": 45000.0,
        "low": 43900.0,
        "close": 44800.0,
        "volume": 500.0,
        "timestamp": datetime.utcnow()
    }

    event = Event(EventType.CANDLE_CLOSED, candle_data, "test")
    await bus.publish(event)

    # Wait for processing
    await asyncio.sleep(0.5)

    # Should process candle
    assert tracker.event_count(EventType.CANDLE_CLOSED) == 1
    # May or may not create Order Block (depends on body ratio)
    # But should NOT create signal without confluence
    assert tracker.event_count(EventType.ENTRY_SIGNAL) == 0


@pytest.mark.asyncio
async def test_pipeline_error_resilience(event_pipeline):
    """Test pipeline continues processing despite errors."""
    bus, orchestrator, tracker = event_pipeline

    # Emit invalid candle (should be handled gracefully)
    invalid_candle = {
        "symbol": "BTCUSDT",
        "open": -100,  # Invalid negative price
        "high": 45000.0,
        "low": 43900.0,
        "close": 44800.0,
        "volume": 500.0,
        "timestamp": datetime.utcnow()
    }

    invalid_event = Event(EventType.CANDLE_CLOSED, invalid_candle, "test")
    await bus.publish(invalid_event)
    await asyncio.sleep(0.2)

    # Then emit valid candles
    valid_candles = create_bullish_candle_setup()
    for candle_data in valid_candles:
        event = Event(EventType.CANDLE_CLOSED, candle_data, "test")
        await bus.publish(event)
        await asyncio.sleep(0.1)

    await asyncio.sleep(0.5)

    # Should process valid candles despite invalid one
    assert tracker.event_count(EventType.CANDLE_CLOSED) == 4  # 1 invalid + 3 valid
    # Should generate signals from valid candles
    assert tracker.event_count(EventType.ENTRY_SIGNAL) >= 1


@pytest.mark.asyncio
async def test_pipeline_processor_states(event_pipeline):
    """Test all processors maintain correct state."""
    bus, orchestrator, tracker = event_pipeline

    # All processors should be running
    assert orchestrator.running_count == 3

    # Emit candles to generate activity
    candles = create_bullish_candle_setup()
    for candle_data in candles:
        event = Event(EventType.CANDLE_CLOSED, candle_data, "test")
        await bus.publish(event)
        await asyncio.sleep(0.1)

    await asyncio.sleep(0.5)

    # Processors should still be running after activity
    assert orchestrator.running_count == 3


@pytest.mark.asyncio
async def test_pipeline_performance(event_pipeline):
    """Test pipeline processes events within acceptable time."""
    bus, orchestrator, tracker = event_pipeline

    # Emit large number of candles
    start_time = asyncio.get_event_loop().time()

    for _ in range(10):
        candle_data = {
            "symbol": "BTCUSDT",
            "open": 44000.0,
            "high": 44500.0,
            "low": 43900.0,
            "close": 44300.0,
            "volume": 100.0,
            "timestamp": datetime.utcnow()
        }
        event = Event(EventType.CANDLE_CLOSED, candle_data, "test")
        await bus.publish(event)

    # Wait for processing
    await asyncio.sleep(1.0)

    end_time = asyncio.get_event_loop().time()
    elapsed = end_time - start_time

    # Should process 10 candles in under 2 seconds
    assert elapsed < 2.0
    assert tracker.event_count(EventType.CANDLE_CLOSED) == 10
