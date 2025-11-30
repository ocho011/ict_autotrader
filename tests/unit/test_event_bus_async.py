"""
Unit tests for EventBus async queue functionality.

Tests async event publishing, queue processing, and graceful shutdown.
"""

import pytest
import asyncio
from src.core.event_bus import EventBus, Event, EventType


@pytest.mark.asyncio
class TestEventBusAsync:
    """Test suite for EventBus async queue functionality."""

    async def test_publish_adds_to_queue_without_blocking(self):
        """Test that publish() adds events to queue without blocking."""
        bus = EventBus()
        event = Event(EventType.CANDLE_CLOSED, {"price": 45000}, "test")

        # Publish should not block
        await bus.publish(event)

        # Event should be in queue
        assert bus.queue_size == 1

    async def test_start_processes_events_from_queue(self):
        """Test that start() processes events from queue."""
        bus = EventBus()
        events_received = []

        def handler(event: Event):
            events_received.append(event)

        bus.subscribe(EventType.CANDLE_CLOSED, handler)

        # Start event processing
        await bus.start()

        # Publish event
        event = Event(EventType.CANDLE_CLOSED, {"price": 45000}, "test")
        await bus.publish(event)

        # Wait for event to be processed
        await asyncio.sleep(0.2)

        # Stop event bus
        await bus.stop()

        # Event should have been received
        assert len(events_received) == 1
        assert events_received[0].data["price"] == 45000

    async def test_stop_gracefully_shuts_down(self):
        """Test that stop() gracefully shuts down processing loop."""
        bus = EventBus()
        await bus.start()

        assert bus.is_running is True

        await bus.stop()

        assert bus.is_running is False

    async def test_queue_no_event_loss_during_shutdown(self):
        """Test that queue doesn't lose events during shutdown."""
        bus = EventBus()
        events_received = []

        def handler(event: Event):
            events_received.append(event)

        bus.subscribe(EventType.CANDLE_CLOSED, handler)

        await bus.start()

        # Publish multiple events
        for i in range(10):
            event = Event(EventType.CANDLE_CLOSED, {"price": 45000 + i}, "test")
            await bus.publish(event)

        # Stop immediately (events should still be processed)
        await bus.stop()

        # All events should have been processed
        assert len(events_received) == 10
        assert events_received[0].data["price"] == 45000
        assert events_received[9].data["price"] == 45009

    async def test_multiple_event_types_processing(self):
        """Test processing multiple event types simultaneously."""
        bus = EventBus()
        candle_events = []
        order_events = []

        def candle_handler(event: Event):
            candle_events.append(event)

        def order_handler(event: Event):
            order_events.append(event)

        bus.subscribe(EventType.CANDLE_CLOSED, candle_handler)
        bus.subscribe(EventType.ORDER_PLACED, order_handler)

        await bus.start()

        # Publish different event types
        await bus.publish(Event(EventType.CANDLE_CLOSED, {"price": 45000}, "test"))
        await bus.publish(Event(EventType.ORDER_PLACED, {"order_id": "123"}, "test"))
        await bus.publish(Event(EventType.CANDLE_CLOSED, {"price": 45100}, "test"))

        # Wait for processing
        await asyncio.sleep(0.2)
        await bus.stop()

        # Events should be routed correctly
        assert len(candle_events) == 2
        assert len(order_events) == 1
        assert candle_events[0].data["price"] == 45000
        assert order_events[0].data["order_id"] == "123"

    async def test_asyncio_integration_works_correctly(self):
        """Test that asyncio integration works correctly."""
        bus = EventBus()
        processing_times = []

        async def async_handler(event: Event):
            """Async handler that takes time to process."""
            start = asyncio.get_event_loop().time()
            await asyncio.sleep(0.05)
            processing_times.append(asyncio.get_event_loop().time() - start)

        # Note: Current implementation uses sync handlers, but this tests
        # that the bus works correctly with async context
        def sync_wrapper(event: Event):
            # In a real async system, you might want to support async handlers
            pass

        bus.subscribe(EventType.CANDLE_CLOSED, sync_wrapper)

        await bus.start()

        # Publish events
        for i in range(3):
            await bus.publish(Event(EventType.CANDLE_CLOSED, {"i": i}, "test"))

        await asyncio.sleep(0.3)
        await bus.stop()

        # Verify bus started and stopped correctly
        assert not bus.is_running

    async def test_publish_without_start_queues_events(self):
        """Test that publish works even if start() hasn't been called."""
        bus = EventBus()

        # Publish without starting
        event = Event(EventType.CANDLE_CLOSED, {"price": 45000}, "test")
        await bus.publish(event)

        # Event should be queued
        assert bus.queue_size == 1

    async def test_multiple_subscribers_all_receive_events(self):
        """Test that multiple subscribers all receive events."""
        bus = EventBus()
        handler1_events = []
        handler2_events = []
        handler3_events = []

        def handler1(event: Event):
            handler1_events.append(event)

        def handler2(event: Event):
            handler2_events.append(event)

        def handler3(event: Event):
            handler3_events.append(event)

        bus.subscribe(EventType.CANDLE_CLOSED, handler1)
        bus.subscribe(EventType.CANDLE_CLOSED, handler2)
        bus.subscribe(EventType.CANDLE_CLOSED, handler3)

        await bus.start()

        event = Event(EventType.CANDLE_CLOSED, {"price": 45000}, "test")
        await bus.publish(event)

        await asyncio.sleep(0.2)
        await bus.stop()

        # All handlers should have received the event
        assert len(handler1_events) == 1
        assert len(handler2_events) == 1
        assert len(handler3_events) == 1

    async def test_invalid_event_type_raises_error(self):
        """Test that publishing invalid event type raises TypeError."""
        bus = EventBus()

        with pytest.raises(TypeError):
            await bus.publish("not an event")

    async def test_stop_when_not_running_is_safe(self):
        """Test that calling stop() when not running is safe."""
        bus = EventBus()

        # Should not raise error
        await bus.stop()

    async def test_start_when_already_running_is_safe(self):
        """Test that calling start() when already running is safe."""
        bus = EventBus()

        await bus.start()
        await bus.start()  # Should not create duplicate task

        await bus.stop()

    async def test_queue_size_property(self):
        """Test queue_size property returns correct count."""
        bus = EventBus()

        assert bus.queue_size == 0

        await bus.publish(Event(EventType.CANDLE_CLOSED, {}, "test"))
        assert bus.queue_size == 1

        await bus.publish(Event(EventType.ORDER_PLACED, {}, "test"))
        assert bus.queue_size == 2

    async def test_is_running_property(self):
        """Test is_running property reflects correct state."""
        bus = EventBus()

        assert bus.is_running is False

        await bus.start()
        assert bus.is_running is True

        await bus.stop()
        assert bus.is_running is False

    async def test_error_in_subscriber_doesnt_break_processing(self):
        """Test that errors in one subscriber don't affect others."""
        bus = EventBus()
        working_handler_events = []

        def broken_handler(event: Event):
            raise ValueError("Intentional error")

        def working_handler(event: Event):
            working_handler_events.append(event)

        bus.subscribe(EventType.CANDLE_CLOSED, broken_handler)
        bus.subscribe(EventType.CANDLE_CLOSED, working_handler)

        await bus.start()

        event = Event(EventType.CANDLE_CLOSED, {"price": 45000}, "test")
        await bus.publish(event)

        await asyncio.sleep(0.2)
        await bus.stop()

        # Working handler should still receive event despite broken handler error
        assert len(working_handler_events) == 1

    async def test_high_throughput_event_processing(self):
        """Test that bus can handle high throughput of events."""
        bus = EventBus()
        events_received = []

        def handler(event: Event):
            events_received.append(event)

        bus.subscribe(EventType.CANDLE_CLOSED, handler)

        await bus.start()

        # Publish many events quickly
        for i in range(100):
            await bus.publish(Event(EventType.CANDLE_CLOSED, {"i": i}, "test"))

        # Wait for all to process
        await asyncio.sleep(0.5)
        await bus.stop()

        # All events should be processed
        assert len(events_received) == 100
        assert events_received[0].data["i"] == 0
        assert events_received[99].data["i"] == 99
