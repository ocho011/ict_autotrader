# Task ID: 2

**Title:** Implement Event Bus and Core Event System

**Status:** done

**Dependencies:** 1 ✓

**Priority:** high

**Description:** Build the foundational event-driven architecture with EventBus, Event dataclass, and EventType enum

**Details:**

Create src/core/event_bus.py with:
- EventType enum containing all MVP event types (CANDLE_CLOSED, ORDER_BLOCK_DETECTED, FVG_DETECTED, ENTRY_SIGNAL, ORDER_PLACED, ORDER_FILLED, POSITION_CLOSED, ERROR)
- Event dataclass with fields: type (EventType), data (Dict[str, Any]), timestamp (datetime, auto-generated)
- EventBus class implementing async pub/sub pattern:
  * _subscribers: Dict[EventType, List[Callable]]
  * _queue: asyncio.Queue for event buffering
  * subscribe(event_type, handler) method
  * publish(event) async method (non-blocking)
  * start() async method with event processing loop
  * _dispatch(event) async method to call handlers
  * stop() method for graceful shutdown
- Add comprehensive error handling with loguru logging
- Use asyncio.wait_for with 1.0s timeout to prevent blocking
- Ensure handlers can be both sync and async functions

**Test Strategy:**

Unit test EventBus with mock handlers subscribing to events. Verify events are dispatched to correct subscribers. Test async and sync handler execution. Verify queue doesn't block on timeout. Test error handling when handlers raise exceptions. Confirm events maintain order of publication.

## Subtasks

### 2.1. Create EventType enum with all MVP event types

**Status:** done  
**Dependencies:** None  

Define the EventType enumeration containing all required event types for the MVP system

**Details:**

Create src/core/event_bus.py and define EventType enum with the following members: CANDLE_CLOSED, ORDER_BLOCK_DETECTED, FVG_DETECTED, ENTRY_SIGNAL, ORDER_PLACED, ORDER_FILLED, POSITION_CLOSED, ERROR. Use Python's enum.Enum class. Add docstrings explaining each event type's purpose. Ensure enum values are string literals for clear logging.

### 2.2. Implement Event dataclass with validation and auto-timestamp

**Status:** done  
**Dependencies:** 2.1  

Create the Event dataclass that will represent all events flowing through the system

**Details:**

In src/core/event_bus.py, implement Event dataclass using @dataclass decorator with: type field (EventType), data field (Dict[str, Any]), timestamp field (datetime with default_factory=datetime.now for auto-generation). Add __post_init__ validation to ensure type is EventType instance and data is dict. Import required types from typing and datetime modules.

### 2.3. Build subscriber management with subscribe/unsubscribe methods

**Status:** done  
**Dependencies:** 2.2  

Implement the subscriber registration system to allow handlers to listen for specific event types

**Details:**

In EventBus class, add _subscribers attribute as Dict[EventType, List[Callable]]. Implement subscribe(event_type: EventType, handler: Callable) method that appends handler to the list for that event type, creating new list if needed. Implement unsubscribe(event_type: EventType, handler: Callable) method to remove handler from list. Add validation to ensure event_type is EventType and handler is callable. Include loguru logging for subscribe/unsubscribe operations.

### 2.4. Implement async event queue and publish mechanism

**Status:** done  
**Dependencies:** 2.3  

Create the asynchronous event queue and publish method for non-blocking event emission

**Details:**

In EventBus class, add _queue attribute as asyncio.Queue() in __init__. Implement async publish(event: Event) method that calls _queue.put_nowait(event) for non-blocking publish. Add _running flag to control event loop. Implement start() async method that creates event processing loop: while _running, await _queue.get(), call _dispatch(event), handle queue.task_done(). Add stop() method to set _running=False and await queue processing completion.

### 2.5. Create event dispatching with timeout and sync/async handler support

**Status:** done  
**Dependencies:** 2.4  

Implement the core event dispatch mechanism that calls registered handlers with timeout protection

**Details:**

Implement _dispatch(event: Event) async method in EventBus. Get handlers from _subscribers[event.type]. For each handler, check if asyncio.iscoroutinefunction(handler). If async, use await asyncio.wait_for(handler(event), timeout=1.0). If sync, wrap in asyncio.create_task(asyncio.to_thread(handler, event)) with wait_for timeout. Catch asyncio.TimeoutError and log warning. Use loguru for dispatching logs showing event type and handler count.

### 2.6. Add comprehensive error handling, logging, and unit tests

**Status:** done  
**Dependencies:** 2.5  

Implement robust error handling throughout EventBus and create comprehensive test suite

**Details:**

Wrap all handler calls in try-except blocks to catch and log exceptions without stopping event processing. Add loguru logging at key points: event published, handler called, handler completed, handler error, timeout. Configure loguru to use structured logging with context (event_type, handler_name). Create tests/core/test_event_bus.py with pytest test cases covering: all event types, event validation, subscribe/unsubscribe, publish/dispatch flow, sync/async handlers, timeout handling, error handling, graceful shutdown, event ordering preservation.
