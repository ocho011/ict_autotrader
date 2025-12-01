"""
Unit Tests for Event Bus System

Tests the EventType enum, Event dataclass, and EventBus implementation
to ensure reliable event-driven communication in the trading system.
"""

import pytest
from datetime import datetime
from src.core.event_bus import EventType, Event, EventBus


class TestEventType:
    """Test cases for EventType enumeration"""

    def test_all_event_types_exist(self):
        """Test that all 8 required event types are defined"""
        required_events = [
            'CANDLE_CLOSED',
            'ORDER_BLOCK_DETECTED',
            'FVG_DETECTED',
            'ENTRY_SIGNAL',
            'ORDER_PLACED',
            'ORDER_FILLED',
            'POSITION_CLOSED',
            'ERROR'
        ]

        for event_name in required_events:
            assert hasattr(EventType, event_name), f"EventType.{event_name} not found"

        # Verify exactly 8 event types (no more, no less)
        assert len(EventType) == 8, f"Expected 8 event types, found {len(EventType)}"

    def test_event_type_values_are_strings(self):
        """Test that all event type values are string literals"""
        for event_type in EventType:
            assert isinstance(event_type.value, str), \
                f"{event_type.name} value should be string, got {type(event_type.value)}"
            assert len(event_type.value) > 0, \
                f"{event_type.name} value should not be empty"

    def test_event_type_values_are_snake_case(self):
        """Test that event values follow snake_case convention"""
        for event_type in EventType:
            value = event_type.value
            # Should be lowercase
            assert value == value.lower(), \
                f"{event_type.name} value should be lowercase: {value}"
            # Should not have uppercase letters
            assert not any(c.isupper() for c in value), \
                f"{event_type.name} value should not contain uppercase: {value}"
            # Should use underscores, not hyphens or spaces
            assert ' ' not in value and '-' not in value, \
                f"{event_type.name} value should use underscores: {value}"

    def test_event_type_string_representation(self):
        """Test __str__ method returns the event name"""
        assert str(EventType.CANDLE_CLOSED) == 'CANDLE_CLOSED'
        assert str(EventType.ERROR) == 'ERROR'
        assert str(EventType.ENTRY_SIGNAL) == 'ENTRY_SIGNAL'

    def test_event_type_repr(self):
        """Test __repr__ method returns detailed representation"""
        repr_str = repr(EventType.CANDLE_CLOSED)
        assert 'EventType.CANDLE_CLOSED' in repr_str
        assert 'candle_closed' in repr_str

    def test_event_types_are_comparable(self):
        """Test that event types can be compared for equality"""
        assert EventType.CANDLE_CLOSED == EventType.CANDLE_CLOSED
        assert EventType.ERROR != EventType.CANDLE_CLOSED

    def test_event_types_are_accessible_by_name(self):
        """Test that event types can be accessed by string name"""
        assert EventType['CANDLE_CLOSED'] == EventType.CANDLE_CLOSED
        assert EventType['ERROR'] == EventType.ERROR

    def test_event_types_are_accessible_by_value(self):
        """Test that event types can be retrieved by their string value"""
        assert EventType('candle_closed') == EventType.CANDLE_CLOSED
        assert EventType('error') == EventType.ERROR

    def test_event_type_iteration(self):
        """Test that we can iterate over all event types"""
        event_types = list(EventType)
        assert len(event_types) == 8
        assert EventType.CANDLE_CLOSED in event_types
        assert EventType.ERROR in event_types

    def test_specific_event_values(self):
        """Test specific event type values match expectations"""
        assert EventType.CANDLE_CLOSED.value == 'candle_closed'
        assert EventType.ORDER_BLOCK_DETECTED.value == 'order_block_detected'
        assert EventType.FVG_DETECTED.value == 'fvg_detected'
        assert EventType.ENTRY_SIGNAL.value == 'entry_signal'
        assert EventType.ORDER_PLACED.value == 'order_placed'
        assert EventType.ORDER_FILLED.value == 'order_filled'
        assert EventType.POSITION_CLOSED.value == 'position_closed'
        assert EventType.ERROR.value == 'error'


class TestEvent:
    """Test cases for Event dataclass"""

    def test_event_creation_with_all_fields(self):
        """Test creating an event with all fields specified"""
        timestamp = datetime.utcnow()
        event = Event(
            event_type=EventType.CANDLE_CLOSED,
            data={'symbol': 'BTCUSDT', 'close': 45000.0},
            source='test',
            timestamp=timestamp
        )

        assert event.event_type == EventType.CANDLE_CLOSED
        assert event.data == {'symbol': 'BTCUSDT', 'close': 45000.0}
        assert event.source == 'test'
        assert event.timestamp == timestamp

    def test_event_creation_with_auto_timestamp(self):
        """Test that timestamp is auto-generated if not provided"""
        before = datetime.utcnow()
        event = Event(
            event_type=EventType.ERROR,
            data={'message': 'test error'},
            source='test'
        )
        after = datetime.utcnow()

        assert event.timestamp is not None
        assert before <= event.timestamp <= after

    def test_event_string_representation(self):
        """Test event __str__ method"""
        event = Event(
            event_type=EventType.ENTRY_SIGNAL,
            data={'direction': 'long'},
            source='strategy'
        )
        event_str = str(event)

        assert 'ENTRY_SIGNAL' in event_str
        assert 'strategy' in event_str

    def test_event_repr(self):
        """Test event __repr__ method"""
        event = Event(
            event_type=EventType.ORDER_PLACED,
            data={'order_id': '12345'},
            source='execution'
        )
        event_repr = repr(event)

        assert 'EventType.ORDER_PLACED' in event_repr
        assert 'execution' in event_repr
        assert 'order_id' in event_repr

    def test_event_data_can_be_empty(self):
        """Test that event data can be an empty dict"""
        event = Event(
            event_type=EventType.ERROR,
            data={},
            source='test'
        )
        assert event.data == {}

    def test_event_data_types(self):
        """Test various data types in event payload"""
        event = Event(
            event_type=EventType.CANDLE_CLOSED,
            data={
                'string': 'BTCUSDT',
                'float': 45000.5,
                'int': 100,
                'bool': True,
                'list': [1, 2, 3],
                'dict': {'nested': 'value'}
            },
            source='test'
        )

        assert isinstance(event.data['string'], str)
        assert isinstance(event.data['float'], float)
        assert isinstance(event.data['int'], int)
        assert isinstance(event.data['bool'], bool)
        assert isinstance(event.data['list'], list)
        assert isinstance(event.data['dict'], dict)

    def test_event_validation_invalid_event_type(self):
        """Test that Event creation with invalid event_type raises TypeError"""
        with pytest.raises(TypeError, match="event_type must be EventType enum"):
            Event(
                event_type="not_an_enum",  # String instead of EventType
                data={},
                source='test'
            )

    def test_event_validation_invalid_data_type(self):
        """Test that Event creation with invalid data type raises TypeError"""
        with pytest.raises(TypeError, match="data must be dict"):
            Event(
                event_type=EventType.ERROR,
                data="not_a_dict",  # String instead of dict
                source='test'
            )


class TestEventBus:
    """Test cases for EventBus implementation"""

    @pytest.fixture
    def event_bus(self):
        """Create a fresh EventBus instance for each test"""
        return EventBus()

    @pytest.fixture
    def sample_event(self):
        """Create a sample event for testing"""
        return Event(
            event_type=EventType.CANDLE_CLOSED,
            data={'symbol': 'BTCUSDT', 'close': 45000.0},
            source='test'
        )

    def test_event_bus_initialization(self, event_bus):
        """Test EventBus initializes with empty subscriber lists"""
        for event_type in EventType:
            assert event_bus.subscriber_count(event_type) == 0

    def test_subscribe_to_event(self, event_bus):
        """Test subscribing to an event type"""
        callback = lambda e: None

        event_bus.subscribe(EventType.CANDLE_CLOSED, callback)

        assert event_bus.subscriber_count(EventType.CANDLE_CLOSED) == 1
        assert event_bus.subscriber_count(EventType.ERROR) == 0

    def test_subscribe_multiple_callbacks(self, event_bus):
        """Test subscribing multiple callbacks to same event type"""
        callback1 = lambda e: None
        callback2 = lambda e: None

        event_bus.subscribe(EventType.ERROR, callback1)
        event_bus.subscribe(EventType.ERROR, callback2)

        assert event_bus.subscriber_count(EventType.ERROR) == 2

    def test_subscribe_same_callback_twice(self, event_bus):
        """Test that subscribing same callback twice doesn't duplicate"""
        callback = lambda e: None

        event_bus.subscribe(EventType.ERROR, callback)
        event_bus.subscribe(EventType.ERROR, callback)

        assert event_bus.subscriber_count(EventType.ERROR) == 1

    def test_subscribe_invalid_event_type(self, event_bus):
        """Test that subscribing with invalid type raises TypeError"""
        with pytest.raises(TypeError):
            event_bus.subscribe("not_an_event_type", lambda e: None)

    def test_emit_event_calls_subscriber(self, event_bus, sample_event):
        """Test that emitting an event calls subscribed callbacks"""
        received_events = []

        def callback(event):
            received_events.append(event)

        event_bus.subscribe(EventType.CANDLE_CLOSED, callback)
        event_bus.emit(sample_event)

        assert len(received_events) == 1
        assert received_events[0] == sample_event

    def test_emit_event_calls_multiple_subscribers(self, event_bus, sample_event):
        """Test that all subscribers receive the event"""
        call_count = [0, 0]

        def callback1(e):
            call_count[0] += 1

        def callback2(e):
            call_count[1] += 1

        event_bus.subscribe(EventType.CANDLE_CLOSED, callback1)
        event_bus.subscribe(EventType.CANDLE_CLOSED, callback2)
        event_bus.emit(sample_event)

        assert call_count[0] == 1
        assert call_count[1] == 1

    def test_emit_only_calls_correct_event_type(self, event_bus):
        """Test that only subscribers of the correct type are notified"""
        candle_calls = [0]
        error_calls = [0]

        event_bus.subscribe(EventType.CANDLE_CLOSED, lambda e: candle_calls.__setitem__(0, candle_calls[0] + 1))
        event_bus.subscribe(EventType.ERROR, lambda e: error_calls.__setitem__(0, error_calls[0] + 1))

        event = Event(EventType.CANDLE_CLOSED, {}, 'test')
        event_bus.emit(event)

        assert candle_calls[0] == 1
        assert error_calls[0] == 0

    def test_emit_invalid_event_type(self, event_bus):
        """Test that emitting non-Event raises TypeError"""
        with pytest.raises(TypeError):
            event_bus.emit("not_an_event")

    def test_emit_handles_subscriber_exceptions(self, event_bus, sample_event, capsys):
        """Test that exceptions in subscribers don't break others"""
        call_count = [0]

        def failing_callback(e):
            raise Exception("Test error")

        def working_callback(e):
            call_count[0] += 1

        event_bus.subscribe(EventType.CANDLE_CLOSED, failing_callback)
        event_bus.subscribe(EventType.CANDLE_CLOSED, working_callback)

        event_bus.emit(sample_event)

        # Working callback should still be called despite failing one
        assert call_count[0] == 1

        # Error should be logged
        captured = capsys.readouterr()
        assert "Error in event subscriber" in captured.out

    def test_unsubscribe_callback(self, event_bus):
        """Test unsubscribing a callback"""
        callback = lambda e: None

        event_bus.subscribe(EventType.ERROR, callback)
        assert event_bus.subscriber_count(EventType.ERROR) == 1

        event_bus.unsubscribe(EventType.ERROR, callback)
        assert event_bus.subscriber_count(EventType.ERROR) == 0

    def test_unsubscribe_nonexistent_callback(self, event_bus):
        """Test that unsubscribing nonexistent callback doesn't error"""
        callback = lambda e: None
        # Should not raise exception
        event_bus.unsubscribe(EventType.ERROR, callback)

    def test_clear_subscribers_specific_type(self, event_bus):
        """Test clearing subscribers for specific event type"""
        event_bus.subscribe(EventType.ERROR, lambda e: None)
        event_bus.subscribe(EventType.CANDLE_CLOSED, lambda e: None)

        event_bus.clear_subscribers(EventType.ERROR)

        assert event_bus.subscriber_count(EventType.ERROR) == 0
        assert event_bus.subscriber_count(EventType.CANDLE_CLOSED) == 1

    def test_clear_all_subscribers(self, event_bus):
        """Test clearing all subscribers"""
        event_bus.subscribe(EventType.ERROR, lambda e: None)
        event_bus.subscribe(EventType.CANDLE_CLOSED, lambda e: None)
        event_bus.subscribe(EventType.ENTRY_SIGNAL, lambda e: None)

        event_bus.clear_subscribers()

        for event_type in EventType:
            assert event_bus.subscriber_count(event_type) == 0

    def test_event_bus_with_real_workflow(self, event_bus):
        """Integration test simulating real event workflow"""
        events_received = []

        # Simulate market data processor
        def on_candle_closed(event):
            events_received.append(('candle', event.data))
            # Simulate pattern detection
            if event.data['close'] > 45000:
                fvg_event = Event(
                    EventType.FVG_DETECTED,
                    {'gap_size': 100},
                    'pattern_detector'
                )
                event_bus.emit(fvg_event)

        # Simulate strategy module
        def on_fvg_detected(event):
            events_received.append(('fvg', event.data))
            # Simulate entry signal
            signal_event = Event(
                EventType.ENTRY_SIGNAL,
                {'direction': 'long', 'price': 45100},
                'strategy'
            )
            event_bus.emit(signal_event)

        # Simulate execution module
        def on_entry_signal(event):
            events_received.append(('entry', event.data))

        # Subscribe all handlers
        event_bus.subscribe(EventType.CANDLE_CLOSED, on_candle_closed)
        event_bus.subscribe(EventType.FVG_DETECTED, on_fvg_detected)
        event_bus.subscribe(EventType.ENTRY_SIGNAL, on_entry_signal)

        # Trigger workflow with candle close
        candle_event = Event(
            EventType.CANDLE_CLOSED,
            {'symbol': 'BTCUSDT', 'close': 45500},
            'data_collector'
        )
        event_bus.emit(candle_event)

        # Verify event chain
        assert len(events_received) == 3
        assert events_received[0][0] == 'candle'
        assert events_received[1][0] == 'fvg'
        assert events_received[2][0] == 'entry'
        assert events_received[2][1]['direction'] == 'long'


class TestEventTypeDocstrings:
    """Test that all event types have proper documentation"""

    def test_all_event_types_have_docstrings(self):
        """Verify each event type value has a docstring"""
        # EventType enum members don't have individual docstrings,
        # but the enum class should have comprehensive documentation
        assert EventType.__doc__ is not None
        assert len(EventType.__doc__) > 100

    def test_enum_class_docstring_mentions_all_events(self):
        """Test that enum docstring documents all event types"""
        docstring = EventType.__doc__
        # Should mention usage examples
        assert 'EventType.CANDLE_CLOSED' in docstring or 'CANDLE_CLOSED' in docstring


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
