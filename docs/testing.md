# ICT Auto Trader - Testing Strategy

## Testing Philosophy

**Test-Driven Development (TDD):** All components must have tests before being marked complete.

**Coverage Target:** Minimum 80% code coverage for production code in `src/`

**Test Pyramid:**
```
        ┌─────────────┐
        │ Integration │  ← 20% (End-to-end workflows)
        │    Tests    │
        └─────────────┘
       ┌───────────────┐
       │  Unit Tests   │  ← 80% (Individual components)
       └───────────────┘
```

## Test Organization

### Directory Structure

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures and pytest configuration
├── unit/                    # Unit tests (80% of tests)
│   ├── __init__.py
│   ├── test_event_bus.py
│   ├── test_state_store.py
│   ├── test_patterns.py     # OB/FVG detection logic
│   ├── test_risk_manager.py
│   └── test_signal_engine.py
├── integration/             # Integration tests (20% of tests)
│   ├── __init__.py
│   ├── test_websocket_flow.py    # WebSocket → Event → Strategy flow
│   └── test_order_execution.py   # Signal → Order → Position flow
└── fixtures/                # Test data and mocks
    ├── __init__.py
    ├── candle_data.py       # Synthetic BTCUSDT candles
    └── mock_binance.py      # AsyncClient mock responses
```

## Unit Testing Guidelines

### 1. Event Bus Tests (`test_event_bus.py`)

**Test Coverage:**
- ✅ Event subscription
- ✅ Event publishing (async)
- ✅ Event dispatch to multiple handlers
- ✅ Handler error isolation (one failing handler doesn't block others)
- ✅ Event queue handling

**Example Test:**
```python
@pytest.mark.asyncio
async def test_event_dispatch_to_multiple_handlers():
    """Test that one event triggers all subscribed handlers."""
    bus = EventBus()
    received_events = []

    async def handler1(event):
        received_events.append(('handler1', event.type))

    async def handler2(event):
        received_events.append(('handler2', event.type))

    bus.subscribe(EventType.CANDLE_CLOSED, handler1)
    bus.subscribe(EventType.CANDLE_CLOSED, handler2)

    event = Event(type=EventType.CANDLE_CLOSED, data={'test': True})
    await bus.publish(event)

    # Process events
    await asyncio.sleep(0.1)

    assert len(received_events) == 2
```

### 2. State Store Tests (`test_state_store.py`)

**Test Coverage:**
- ✅ Candle addition and deque limit
- ✅ Order Block addition and cleanup
- ✅ FVG addition and cleanup
- ✅ Pattern validation (touches, age)
- ✅ Position tracking

### 3. Pattern Detection Tests (`test_patterns.py`)

**Test Coverage:**
- ✅ Bullish Order Block detection
- ✅ Bearish Order Block detection
- ✅ Bullish FVG detection
- ✅ Bearish FVG detection
- ✅ Invalid patterns (edge cases)

**Critical Test Data:**
```python
# Bullish OB: Strong green candle after red
candles = [
    {'open': 100, 'high': 105, 'low': 95, 'close': 96},  # Red
    {'open': 96, 'high': 110, 'low': 95, 'close': 108},  # Strong green → OB at candle[0]
]

# Bullish FVG: Gap between c1.high and c3.low
candles = [
    {'open': 100, 'high': 102, 'low': 98, 'close': 101},   # c1
    {'open': 101, 'high': 106, 'low': 100, 'close': 105},  # c2 (ignored)
    {'open': 105, 'high': 110, 'low': 103, 'close': 108},  # c3
]
# FVG: c1.high (102) < c3.low (103) ✓
```

### 4. Risk Manager Tests (`test_risk_manager.py`)

**Test Coverage:**
- ✅ Position size calculation
- ✅ Daily loss limit enforcement
- ✅ Max trade count enforcement
- ✅ Max position percent enforcement
- ✅ Balance retrieval (mocked)

**Mocking Binance API:**
```python
@pytest.fixture
def mock_binance_balance(mocker):
    """Mock AsyncClient.futures_account_balance()"""
    mock_response = [
        {'asset': 'USDT', 'balance': '10000.00'},
        {'asset': 'BTC', 'balance': '0.00'}
    ]
    return mocker.patch(
        'binance.AsyncClient.futures_account_balance',
        return_value=mock_response
    )
```

## Integration Testing Guidelines

### 1. Binance Testnet Integration Tests (`test_binance_testnet_integration.py`)

**Scenario:** End-to-end WebSocket client with real testnet connectivity

**Purpose:** Comprehensive validation of BinanceWebSocket client with actual Binance testnet, ensuring production-ready reliability.

**Test Classes:**

#### TestBinanceTestnetInitialization
- WebSocket initialization with EventBus integration
- Connection establishment to Binance testnet
- Testnet mode detection from configuration
- AsyncClient and BinanceSocketManager setup validation

#### TestCandleClosedEventFlow
- CANDLE_CLOSED event publishing verification (only on candle close)
- Event data structure validation (all OHLCV fields present)
- Event data type verification (float, datetime, string types)
- OHLCV relationship validation (high >= close, low <= open, etc.)
- Symbol and interval field matching

#### TestReconnectionLogic
- Exponential backoff calculation verification
- Reconnection attempt configuration validation
- Network resilience design confirmation

#### TestGracefulShutdown
- Graceful shutdown during active streaming
- stop() method functionality verification
- Async context manager cleanup validation
- Resource release and leak prevention
- Multiple disconnect() call safety

#### TestMultiIntervalSupport
- 1-minute interval streaming verification
- 5-minute interval streaming verification
- Interval field accuracy in event data

#### TestConnectionLifecycleLogging
- Connection establishment logging
- Stream start/stop logging
- Shutdown completion logging

**Prerequisites:**
```bash
# 1. Binance testnet account with API credentials
# 2. Create .env file in project root:
BINANCE_TESTNET_API_KEY=your_testnet_api_key
BINANCE_TESTNET_API_SECRET=your_testnet_api_secret

# 3. Ensure config.yaml has:
use_testnet: true
```

**Running Integration Tests:**
```bash
# All integration tests (~10-20 minutes)
pytest tests/integration/test_binance_testnet_integration.py -v

# Specific test class
pytest tests/integration/test_binance_testnet_integration.py::TestCandleClosedEventFlow -v

# Individual test
pytest tests/integration/test_binance_testnet_integration.py::TestBinanceTestnetInitialization::test_websocket_connects_to_testnet -v

# With live output
pytest tests/integration/test_binance_testnet_integration.py -v -s
```

**Test Execution Times:**
- Initialization tests: ~10 seconds
- Event flow tests (1m interval): 3-6 minutes (waits for real candles)
- Event flow tests (5m interval): 5-8 minutes (waits for real candles)
- Shutdown tests: ~30 seconds
- Full suite: 10-20 minutes

**Test Markers:**
- `@pytest.mark.integration` - Requires external services (testnet)
- `@pytest.mark.asyncio` - Async test execution
- `@pytest.mark.timeout(N)` - Per-test timeout limits

**Fixtures:**
- `event_bus` - EventBus instance
- `event_bus_started` - Started EventBus with automatic cleanup
- `testnet_credentials` - Validates credentials or skips test
- `config_path` - Locates config.yaml

**Success Criteria:**
- ✅ All 11 integration tests pass
- ✅ No resource leaks detected
- ✅ Events contain valid OHLCV data
- ✅ Graceful shutdown completes cleanly
- ✅ Both 1m and 5m intervals work correctly

**Documentation:**
See `tests/integration/README.md` for:
- Detailed setup instructions
- Troubleshooting guide
- CI/CD integration examples
- Common failure scenarios and solutions

### 2. WebSocket Flow Test (`test_websocket_flow.py`)

**Scenario:** End-to-end candle processing
```
WebSocket receives candle
  → CANDLE_CLOSED event published
  → StateStore adds candle
  → Strategy detects pattern
  → OB_DETECTED/FVG_DETECTED events published
```

**Test Approach:**
- Mock `BinanceSocketManager` to inject test candles
- Verify event flow through EventBus
- Validate StateStore updates

### 3. Order Execution Flow Test (`test_order_execution.py`)

**Scenario:** Signal to order execution
```
ENTRY_SIGNAL event
  → RiskManager calculates size
  → OrderManager places order (mocked)
  → ORDER_FILLED event published
  → Position updated in StateStore
  → Discord notification sent (mocked)
```

**Test Approach:**
- Mock `AsyncClient.futures_create_order()`
- Verify order parameters (side, type, quantity)
- Validate stop-loss and take-profit orders
- Check Discord webhook called with correct data

## Test Fixtures

### Shared Fixtures (`conftest.py`)

```python
@pytest.fixture
def sample_candle():
    """Single candle for basic tests."""
    return {
        'timestamp': 1700000000000,
        'open': 35000.0,
        'high': 35100.0,
        'low': 34900.0,
        'close': 35050.0,
        'volume': 100.5
    }

@pytest.fixture
def sample_candles():
    """20 candles for pattern detection tests."""
    # Returns list of 20 candles with realistic price action
    ...

@pytest.fixture
def event_loop():
    """Pytest-asyncio event loop configuration."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
```

## Running Tests

### Basic Test Execution
```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=src --cov-report=html tests/

# Run specific test file
pytest tests/unit/test_event_bus.py

# Run specific test
pytest tests/unit/test_event_bus.py::test_event_subscription

# Run with verbose output
pytest -v tests/
```

### Coverage Report
```bash
# Generate HTML coverage report
pytest --cov=src --cov-report=html tests/

# View report
open htmlcov/index.html
```

### Async Test Configuration

**pytest.ini or pyproject.toml:**
```ini
[pytest]
asyncio_mode = auto
```

This enables automatic async test detection without `@pytest.mark.asyncio` decorators.

## Mock vs Real Testing

### Unit Tests: ALWAYS Mock
- Binance API calls
- WebSocket connections
- Discord webhooks
- File I/O
- Time (use `freezegun`)

### Integration Tests: Selective Mocking
- Mock: Binance API, Discord
- Real: EventBus, StateStore, Strategy logic
- Testnet: Optional for final validation

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt -r requirements-dev.txt
      - run: pytest --cov=src --cov-report=xml tests/
      - uses: codecov/codecov-action@v3
```

## Test Quality Checklist

Before marking a subtask complete:

- [ ] All new code has corresponding unit tests
- [ ] Tests cover happy path and edge cases
- [ ] Async functions properly tested with `pytest-asyncio`
- [ ] External dependencies mocked appropriately
- [ ] Integration tests verify component interactions
- [ ] Coverage target ≥80% maintained
- [ ] All tests pass: `pytest tests/`
- [ ] No test warnings or deprecations

## Best Practices

### ✅ DO:
- Write tests before marking code complete
- Use descriptive test names (`test_bullish_ob_detection_with_strong_green_candle`)
- Mock all external I/O (API, network, disk)
- Test both success and failure scenarios
- Use fixtures for reusable test data
- Keep tests isolated (no shared state)

### ❌ DON'T:
- Skip tests to "save time"
- Test implementation details (test behavior, not internals)
- Use real API keys in tests
- Rely on test execution order
- Leave print statements in tests
- Commit failing tests

---

**Last Updated:** 2025-12-03
**Coverage Goal:** ≥80%
**Test Framework:** pytest + pytest-asyncio
**Integration Tests:** Binance Testnet (task 4.7 complete)
