"""
Unit tests for Event dataclass and EventBus system.

Tests cover:
- Event creation with valid and invalid data
- Timestamp auto-generation
- Validation error handling
- EventType and dict type enforcement
- Event immutability considerations
"""

import pytest
from datetime import datetime
from src.core.event_bus import Event, EventType, EventBus


class TestEvent:
    """Test suite for Event dataclass."""

    def test_event_creation_valid_data(self):
        """Test creating Event with valid EventType and dict data."""
        # Arrange
        event_type = EventType.CANDLE_CLOSED
        data = {"symbol": "BTCUSDT", "close": 45000.0}
        source = "data_collector"

        # Act
        event = Event(event_type=event_type, data=data, source=source)

        # Assert
        assert event.event_type == EventType.CANDLE_CLOSED
        assert event.data == {"symbol": "BTCUSDT", "close": 45000.0}
        assert event.source == "data_collector"
        assert isinstance(event.timestamp, datetime)

    def test_event_timestamp_auto_generation(self):
        """Test that timestamp is automatically generated when not provided."""
        # Arrange & Act
        event = Event(
            event_type=EventType.ENTRY_SIGNAL,
            data={"direction": "long"},
            source="strategy"
        )

        # Assert
        assert event.timestamp is not None
        assert isinstance(event.timestamp, datetime)
        # Timestamp should be recent (within last second)
        time_diff = (datetime.utcnow() - event.timestamp).total_seconds()
        assert time_diff < 1.0

    def test_event_timestamp_custom(self):
        """Test that custom timestamp is preserved."""
        # Arrange
        custom_time = datetime(2025, 1, 1, 12, 0, 0)

        # Act
        event = Event(
            event_type=EventType.ORDER_FILLED,
            data={"price": 45000.0},
            source="exchange",
            timestamp=custom_time
        )

        # Assert
        assert event.timestamp == custom_time

    def test_event_invalid_type_raises_typeerror(self):
        """Test that invalid event_type raises TypeError."""
        # Arrange
        invalid_type = "candle_closed"  # String instead of EventType enum

        # Act & Assert
        with pytest.raises(TypeError) as exc_info:
            Event(event_type=invalid_type, data={}, source="test")

        assert "event_type must be EventType enum" in str(exc_info.value)

    def test_event_invalid_data_raises_typeerror(self):
        """Test that non-dict data raises TypeError."""
        # Arrange
        invalid_data = "not a dict"  # String instead of dict

        # Act & Assert
        with pytest.raises(TypeError) as exc_info:
            Event(event_type=EventType.ERROR, data=invalid_data, source="test")

        assert "data must be dict" in str(exc_info.value)

    def test_event_invalid_data_list_raises_typeerror(self):
        """Test that list data raises TypeError."""
        # Arrange
        invalid_data = ["item1", "item2"]  # List instead of dict

        # Act & Assert
        with pytest.raises(TypeError) as exc_info:
            Event(event_type=EventType.ERROR, data=invalid_data, source="test")

        assert "data must be dict" in str(exc_info.value)

    def test_event_invalid_data_none_raises_typeerror(self):
        """Test that None data raises TypeError."""
        # Act & Assert
        with pytest.raises(TypeError) as exc_info:
            Event(event_type=EventType.ERROR, data=None, source="test")

        assert "data must be dict" in str(exc_info.value)

    def test_event_empty_dict_valid(self):
        """Test that empty dict is valid data."""
        # Act
        event = Event(event_type=EventType.ERROR, data={}, source="test")

        # Assert
        assert event.data == {}

    def test_event_str_representation(self):
        """Test Event __str__ method."""
        # Arrange
        event = Event(
            event_type=EventType.CANDLE_CLOSED,
            data={"symbol": "BTCUSDT"},
            source="data_collector"
        )

        # Act
        str_repr = str(event)

        # Assert
        assert "CANDLE_CLOSED" in str_repr
        assert "data_collector" in str_repr
        assert "Event(" in str_repr

    def test_event_repr_representation(self):
        """Test Event __repr__ method."""
        # Arrange
        event = Event(
            event_type=EventType.ORDER_PLACED,
            data={"order_id": "123"},
            source="execution"
        )

        # Act
        repr_str = repr(event)

        # Assert
        assert "Event(" in repr_str
        assert "event_type=" in repr_str
        assert "source=" in repr_str
        assert "timestamp=" in repr_str
        assert "data=" in repr_str

    def test_event_different_event_types(self):
        """Test Event creation with all EventType enum members."""
        # Arrange
        event_types = [
            EventType.CANDLE_CLOSED,
            EventType.ORDER_BLOCK_DETECTED,
            EventType.FVG_DETECTED,
            EventType.ENTRY_SIGNAL,
            EventType.ORDER_PLACED,
            EventType.ORDER_FILLED,
            EventType.POSITION_CLOSED,
            EventType.ERROR
        ]

        # Act & Assert
        for event_type in event_types:
            event = Event(event_type=event_type, data={}, source="test")
            assert event.event_type == event_type

    def test_event_complex_data_structure(self):
        """Test Event with complex nested data structure."""
        # Arrange
        complex_data = {
            "symbol": "BTCUSDT",
            "price": 45000.0,
            "metadata": {
                "source": "binance",
                "confidence": 0.95
            },
            "levels": [44000, 45000, 46000]
        }

        # Act
        event = Event(
            event_type=EventType.ENTRY_SIGNAL,
            data=complex_data,
            source="strategy"
        )

        # Assert
        assert event.data == complex_data
        assert event.data["metadata"]["confidence"] == 0.95
        assert len(event.data["levels"]) == 3


class TestEventBus:
    """Test suite for EventBus publish-subscribe system."""

    def test_eventbus_creation(self):
        """Test EventBus initialization."""
        # Act
        bus = EventBus()

        # Assert
        assert bus is not None
        assert bus.subscriber_count(EventType.CANDLE_CLOSED) == 0

    def test_eventbus_subscribe(self):
        """Test subscribing to event types."""
        # Arrange
        bus = EventBus()
        callback_called = []

        def callback(event: Event):
            callback_called.append(event)

        # Act
        bus.subscribe(EventType.CANDLE_CLOSED, callback)

        # Assert
        assert bus.subscriber_count(EventType.CANDLE_CLOSED) == 1

    def test_eventbus_emit_calls_subscriber(self):
        """Test that emitting event calls subscribed callbacks."""
        # Arrange
        bus = EventBus()
        received_events = []

        def callback(event: Event):
            received_events.append(event)

        bus.subscribe(EventType.CANDLE_CLOSED, callback)

        # Act
        event = Event(
            event_type=EventType.CANDLE_CLOSED,
            data={"symbol": "BTCUSDT"},
            source="test"
        )
        bus.emit(event)

        # Assert
        assert len(received_events) == 1
        assert received_events[0] == event

    def test_eventbus_multiple_subscribers(self):
        """Test multiple subscribers for same event type."""
        # Arrange
        bus = EventBus()
        callback1_calls = []
        callback2_calls = []

        def callback1(event: Event):
            callback1_calls.append(event)

        def callback2(event: Event):
            callback2_calls.append(event)

        bus.subscribe(EventType.ERROR, callback1)
        bus.subscribe(EventType.ERROR, callback2)

        # Act
        event = Event(event_type=EventType.ERROR, data={"msg": "test"}, source="test")
        bus.emit(event)

        # Assert
        assert len(callback1_calls) == 1
        assert len(callback2_calls) == 1

    def test_eventbus_unsubscribe(self):
        """Test unsubscribing from events."""
        # Arrange
        bus = EventBus()
        callback_calls = []

        def callback(event: Event):
            callback_calls.append(event)

        bus.subscribe(EventType.ENTRY_SIGNAL, callback)

        # Act
        bus.unsubscribe(EventType.ENTRY_SIGNAL, callback)
        event = Event(event_type=EventType.ENTRY_SIGNAL, data={}, source="test")
        bus.emit(event)

        # Assert
        assert len(callback_calls) == 0
        assert bus.subscriber_count(EventType.ENTRY_SIGNAL) == 0

    def test_eventbus_invalid_event_type_subscribe(self):
        """Test subscribing with invalid event type raises TypeError."""
        # Arrange
        bus = EventBus()

        # Act & Assert
        with pytest.raises(TypeError):
            bus.subscribe("invalid", lambda e: None)

    def test_eventbus_invalid_event_emit(self):
        """Test emitting non-Event raises TypeError."""
        # Arrange
        bus = EventBus()

        # Act & Assert
        with pytest.raises(TypeError):
            bus.emit("not an event")

    def test_eventbus_clear_subscribers(self):
        """Test clearing all subscribers for an event type."""
        # Arrange
        bus = EventBus()
        bus.subscribe(EventType.CANDLE_CLOSED, lambda e: None)
        bus.subscribe(EventType.CANDLE_CLOSED, lambda e: None)

        # Act
        bus.clear_subscribers(EventType.CANDLE_CLOSED)

        # Assert
        assert bus.subscriber_count(EventType.CANDLE_CLOSED) == 0

    def test_eventbus_clear_all_subscribers(self):
        """Test clearing subscribers for all event types."""
        # Arrange
        bus = EventBus()
        bus.subscribe(EventType.CANDLE_CLOSED, lambda e: None)
        bus.subscribe(EventType.ERROR, lambda e: None)

        # Act
        bus.clear_subscribers()

        # Assert
        assert bus.subscriber_count(EventType.CANDLE_CLOSED) == 0
        assert bus.subscriber_count(EventType.ERROR) == 0
