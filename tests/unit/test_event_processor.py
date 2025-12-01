"""
Unit tests for EventProcessor and EventOrchestrator base classes.

Tests cover:
- EventProcessor lifecycle (start/stop)
- Handler registration/unregistration
- EventOrchestrator coordination
- Error handling and edge cases
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock
from datetime import datetime

from src.core.event_processor import EventProcessor, EventOrchestrator
from src.core.event_bus import EventBus, Event, EventType


class MockProcessor(EventProcessor):
    """Mock processor for testing base class functionality."""

    def __init__(self, event_bus: EventBus):
        super().__init__(event_bus)
        self.register_called = False
        self.unregister_called = False
        self.on_start_called = False
        self.on_stop_called = False
        self.handler_calls = []

    def _register_handlers(self) -> None:
        self.register_called = True
        self.event_bus.subscribe(EventType.CANDLE_CLOSED, self._mock_handler)

    def _unregister_handlers(self) -> None:
        self.unregister_called = True
        self.event_bus.unsubscribe(EventType.CANDLE_CLOSED, self._mock_handler)

    async def _on_start(self) -> None:
        self.on_start_called = True

    async def _on_stop(self) -> None:
        self.on_stop_called = True

    async def _mock_handler(self, event: Event) -> None:
        self.handler_calls.append(event)


@pytest.fixture
def event_bus():
    """Create EventBus instance for tests."""
    return EventBus()


@pytest.fixture
def mock_processor(event_bus):
    """Create MockProcessor instance for tests."""
    return MockProcessor(event_bus)


class TestEventProcessor:
    """Tests for EventProcessor base class."""

    @pytest.mark.asyncio
    async def test_processor_initialization(self, event_bus):
        """Test processor initializes with event bus."""
        processor = MockProcessor(event_bus)
        assert processor.event_bus is event_bus
        assert processor.is_running is False

    @pytest.mark.asyncio
    async def test_processor_start(self, mock_processor):
        """Test processor start lifecycle."""
        await mock_processor.start()

        assert mock_processor.is_running is True
        assert mock_processor.on_start_called is True
        assert mock_processor.register_called is True

    @pytest.mark.asyncio
    async def test_processor_stop(self, mock_processor):
        """Test processor stop lifecycle."""
        await mock_processor.start()
        await mock_processor.stop()

        assert mock_processor.is_running is False
        assert mock_processor.on_stop_called is True
        assert mock_processor.unregister_called is True

    @pytest.mark.asyncio
    async def test_processor_idempotent_start(self, mock_processor):
        """Test starting processor multiple times is idempotent."""
        await mock_processor.start()
        await mock_processor.start()  # Second start should be no-op

        assert mock_processor.is_running is True
        # Should only call once
        assert mock_processor.on_start_called is True

    @pytest.mark.asyncio
    async def test_processor_idempotent_stop(self, mock_processor):
        """Test stopping processor multiple times is idempotent."""
        await mock_processor.start()
        await mock_processor.stop()
        await mock_processor.stop()  # Second stop should be no-op

        assert mock_processor.is_running is False

    @pytest.mark.asyncio
    async def test_processor_handler_integration(self, event_bus, mock_processor):
        """Test processor handlers receive events."""
        await event_bus.start()
        await mock_processor.start()

        # Emit test event
        event = Event(
            EventType.CANDLE_CLOSED,
            {"price": 45000},
            "test"
        )
        await event_bus.publish(event)

        # Allow processing
        await asyncio.sleep(0.2)

        assert len(mock_processor.handler_calls) == 1
        assert mock_processor.handler_calls[0].data["price"] == 45000

        await mock_processor.stop()
        await event_bus.stop()

    @pytest.mark.asyncio
    async def test_processor_unregister_stops_events(self, event_bus, mock_processor):
        """Test unregistered handlers don't receive events."""
        await event_bus.start()
        await mock_processor.start()

        # Emit event while active
        event1 = Event(EventType.CANDLE_CLOSED, {"price": 45000}, "test")
        await event_bus.publish(event1)
        await asyncio.sleep(0.2)

        # Stop processor
        await mock_processor.stop()

        # Emit event after stopped
        event2 = Event(EventType.CANDLE_CLOSED, {"price": 46000}, "test")
        await event_bus.publish(event2)
        await asyncio.sleep(0.2)

        # Should only receive first event
        assert len(mock_processor.handler_calls) == 1

        await event_bus.stop()


class TestEventOrchestrator:
    """Tests for EventOrchestrator class."""

    @pytest.mark.asyncio
    async def test_orchestrator_initialization(self, event_bus):
        """Test orchestrator initializes with event bus."""
        orchestrator = EventOrchestrator(event_bus)
        assert orchestrator.event_bus is event_bus
        assert orchestrator.processor_count == 0

    @pytest.mark.asyncio
    async def test_orchestrator_register_processor(self, event_bus):
        """Test registering processors with orchestrator."""
        orchestrator = EventOrchestrator(event_bus)
        processor1 = MockProcessor(event_bus)
        processor2 = MockProcessor(event_bus)

        orchestrator.register(processor1)
        orchestrator.register(processor2)

        assert orchestrator.processor_count == 2

    @pytest.mark.asyncio
    async def test_orchestrator_start_all(self, event_bus):
        """Test starting all registered processors."""
        orchestrator = EventOrchestrator(event_bus)
        processor1 = MockProcessor(event_bus)
        processor2 = MockProcessor(event_bus)

        orchestrator.register(processor1)
        orchestrator.register(processor2)

        await orchestrator.start_all()

        assert processor1.is_running is True
        assert processor2.is_running is True
        assert orchestrator.running_count == 2

    @pytest.mark.asyncio
    async def test_orchestrator_stop_all(self, event_bus):
        """Test stopping all registered processors."""
        orchestrator = EventOrchestrator(event_bus)
        processor1 = MockProcessor(event_bus)
        processor2 = MockProcessor(event_bus)

        orchestrator.register(processor1)
        orchestrator.register(processor2)

        await orchestrator.start_all()
        await orchestrator.stop_all()

        assert processor1.is_running is False
        assert processor2.is_running is False
        assert orchestrator.running_count == 0

    @pytest.mark.asyncio
    async def test_orchestrator_stop_reverse_order(self, event_bus):
        """Test processors stop in reverse order (LIFO)."""
        orchestrator = EventOrchestrator(event_bus)
        stop_order = []

        class OrderTrackingProcessor(MockProcessor):
            def __init__(self, event_bus, name):
                super().__init__(event_bus)
                self.name = name

            async def _on_stop(self):
                await super()._on_stop()
                stop_order.append(self.name)

        processor1 = OrderTrackingProcessor(event_bus, "P1")
        processor2 = OrderTrackingProcessor(event_bus, "P2")
        processor3 = OrderTrackingProcessor(event_bus, "P3")

        orchestrator.register(processor1)
        orchestrator.register(processor2)
        orchestrator.register(processor3)

        await orchestrator.start_all()
        await orchestrator.stop_all()

        # Should stop in reverse order: P3, P2, P1
        assert stop_order == ["P3", "P2", "P1"]

    @pytest.mark.asyncio
    async def test_orchestrator_handles_start_failure(self, event_bus):
        """Test orchestrator continues if one processor fails to start."""
        orchestrator = EventOrchestrator(event_bus)

        class FailingProcessor(MockProcessor):
            async def _on_start(self):
                raise RuntimeError("Start failed")

        good_processor = MockProcessor(event_bus)
        bad_processor = FailingProcessor(event_bus)

        orchestrator.register(good_processor)
        orchestrator.register(bad_processor)

        # Should not raise exception
        await orchestrator.start_all()

        # Good processor should be running
        assert good_processor.is_running is True
        # Bad processor should not be running
        assert bad_processor.is_running is False

    @pytest.mark.asyncio
    async def test_orchestrator_handles_stop_failure(self, event_bus):
        """Test orchestrator continues if one processor fails to stop."""
        orchestrator = EventOrchestrator(event_bus)

        class FailingProcessor(MockProcessor):
            async def _on_stop(self):
                raise RuntimeError("Stop failed")

        good_processor = MockProcessor(event_bus)
        bad_processor = FailingProcessor(event_bus)

        orchestrator.register(good_processor)
        orchestrator.register(bad_processor)

        await orchestrator.start_all()
        # Should not raise exception
        await orchestrator.stop_all()

        # Both should be marked as stopped despite failure
        assert good_processor.is_running is False
        assert bad_processor.is_running is False
