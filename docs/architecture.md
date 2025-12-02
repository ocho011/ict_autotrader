# ICT Auto Trader - System Architecture

## Overview

ICT Auto Trader is an event-driven automated trading system for Binance USDT perpetual futures, implementing Inner Circle Trader (ICT) pattern recognition strategies.

## System Components

### 1. Event Bus (`src/core/event_bus.py`)

**Purpose:** Central publish-subscribe event system for decoupled component communication

**Key Features:**
- Asynchronous event processing
- Non-blocking event publishing
- Type-safe event handlers
- Simple queue-based architecture (MVP)
- Comprehensive validation and auto-timestamping

**Core Components:**

#### Event Dataclass
The `Event` dataclass is the foundation of the event system, encapsulating all event information:

```python
@dataclass
class Event:
    event_type: EventType   # Type-safe event classification
    data: Dict[str, Any]    # Event payload (validated as dict)
    source: str             # Component that emitted the event
    timestamp: datetime     # Auto-generated if not provided
```

**Validation Features:**
- `__post_init__` validation ensures `event_type` is an `EventType` enum member
- Data payload must be a dictionary (raises `TypeError` otherwise)
- Timestamp auto-generated using `datetime.utcnow()` if not provided
- Immutable event data ensures consistency across subscribers

**Usage Example:**
```python
# Create event with auto-timestamp
event = Event(
    event_type=EventType.CANDLE_CLOSED,
    data={"symbol": "BTCUSDT", "close": 45000.0},
    source="data_collector"
)

# Validation prevents invalid events
# TypeError raised for non-EventType or non-dict data
```

#### EventBus
Implements the Observer pattern for event distribution with async queue processing:

**Core Methods:**
```python
bus = EventBus()

# Subscribe to events
bus.subscribe(EventType.CANDLE_CLOSED, on_candle_closed)

# Event processing lifecycle (must start BEFORE publishing)
await bus.start()   # Start background event processing loop

# Async queue-based publishing (non-blocking)
await bus.publish(event)  # Adds to queue without blocking

# Graceful shutdown
await bus.stop()    # Graceful shutdown with no event loss

# Synchronous emission (direct, does not require start())
bus.emit(event)     # Calls all subscribers immediately
```

**Async Queue Architecture:**
- Non-blocking event publishing via `asyncio.Queue`
- Lazy queue initialization in `start()` ensures correct event loop binding
- Background event processing loop using `asyncio.create_task()`
- Graceful shutdown with 5-second timeout ensures no event loss
- Robust error handling with try-except-finally pattern for queue task tracking
- Properties: `is_running` (bool), `queue_size` (int)
- Comprehensive error logging with Loguru structured context

**Important:** The queue is created lazily when `start()` is called, not during `__init__`. This ensures the queue is bound to the correct event loop, preventing "Future attached to different loop" errors in async testing and multi-loop environments.

**Event Dispatching with Timeout Protection:**
- Supports both synchronous and asynchronous handlers
- 1.0s timeout protection for all handlers to prevent hanging
- Async handlers: Direct `await` with `asyncio.wait_for()` timeout
- Sync handlers: Execute in thread pool via `asyncio.to_thread()` to avoid blocking event loop
- Timeout errors logged but don't crash the dispatcher
- Handlers for the same event type can be mixed (sync + async)
- Uses `loguru` for structured logging with event type and handler count

**Event Flow:**
```
WebSocket → CANDLE_CLOSED
           ↓
Strategy → ORDER_BLOCK_DETECTED / FVG_DETECTED
           ↓
Signal → ENTRY_SIGNAL
           ↓
Order Manager → ORDER_PLACED / ORDER_FILLED
           ↓
Discord → Notification
```

### 2. WebSocket Client (`src/data/websocket_client.py`)

**Purpose:** Real-time market data streaming from Binance with secure credential management

**Key Features:**
- Separate testnet/mainnet credential handling
- Configuration-driven environment selection
- AsyncClient lifecycle management
- Comprehensive error handling and validation
- Event-driven architecture integration

**Core Components:**

#### BinanceWebSocket Class
Manages WebSocket connection lifecycle for Binance market data streaming:

```python
from src.core.event_bus import EventBus
from src.data.websocket_client import BinanceWebSocket

# Initialize WebSocket client
event_bus = EventBus()
ws = BinanceWebSocket(
    event_bus=event_bus,
    symbol='BTCUSDT',
    interval='15m',
    config_path='config.yaml'  # Optional
)

# Connect to Binance (reads credentials and config)
await ws.connect()

# Check connection status
if ws.is_connected:
    print(f"Connected to {'testnet' if ws.is_testnet else 'mainnet'}")

# Disconnect and cleanup
await ws.disconnect()
```

**Security Architecture:**

1. **Credential Segregation:**
   - Testnet: `BINANCE_TESTNET_API_KEY`, `BINANCE_TESTNET_API_SECRET`
   - Mainnet: `BINANCE_MAINNET_API_KEY`, `BINANCE_MAINNET_API_SECRET`
   - Automatic selection based on `config.yaml` `use_testnet` flag

2. **Validation Layers:**
   - Environment variable existence check
   - Placeholder value detection (`your_*_here`, `placeholder`)
   - Configuration file validation (YAML syntax, required fields)
   - Type checking for testnet boolean flag

3. **Error Handling:**
   - `WebSocketCredentialError`: Missing/invalid credentials
   - `WebSocketConfigError`: Configuration file issues
   - Clear error messages guide proper configuration

**Configuration (config.yaml):**
```yaml
use_testnet: true  # true for testnet, false for mainnet
symbol: BTCUSDT
interval: 15m
```

**Environment Variables (.env):**
```bash
# Testnet credentials (safe for testing)
BINANCE_TESTNET_API_KEY=your_testnet_key
BINANCE_TESTNET_API_SECRET=your_testnet_secret

# Mainnet credentials (REAL trading)
BINANCE_MAINNET_API_KEY=your_mainnet_key
BINANCE_MAINNET_API_SECRET=your_mainnet_secret
```

**Connection Lifecycle:**
```
Initialize → Load Config → Load Credentials → Create AsyncClient → Initialize BinanceSocketManager
                ↓                ↓                    ↓                      ↓
           config.yaml    Environment Vars    testnet parameter    BinanceSocketManager(client)
```

**Instance Variables:**
- `event_bus`: EventBus instance for event publishing
- `symbol`: Trading pair (normalized uppercase)
- `interval`: Candlestick interval (normalized lowercase)
- `client`: AsyncClient instance (None when disconnected)
- `bsm`: BinanceSocketManager instance (None when disconnected)
- `config_path`: Path to config.yaml

**Properties:**
- `is_connected`: Boolean indicating connection status
- `is_testnet`: Boolean indicating environment (None if not connected)

**Error Scenarios:**

1. **Missing Credentials:**
   ```python
   # WebSocketCredentialError: Missing required testnet credentials: BINANCE_TESTNET_API_KEY
   ```

2. **Placeholder Credentials:**
   ```python
   # WebSocketCredentialError: BINANCE_TESTNET_API_KEY appears to be a placeholder value
   ```

3. **Invalid Config:**
   ```python
   # WebSocketConfigError: Missing 'use_testnet' flag in configuration file
   # WebSocketConfigError: 'use_testnet' must be boolean (true/false)
   ```

**Kline Streaming Implementation:**

The WebSocket client includes complete kline (candlestick) streaming functionality:

```python
# Start streaming kline data
await ws.connect()  # Must connect first
await ws.start_kline_stream()  # Runs indefinitely, processing klines

# Stream lifecycle:
# 1. Validates connection state (raises RuntimeError if not connected)
# 2. Creates async context manager via bsm.kline_futures_socket()
# 3. Enters infinite loop to receive messages
# 4. Processes each kline message via _handle_kline()
# 5. Emits CANDLE_CLOSED events when candles close
```

**Message Processing (_handle_kline):**
- Filters for closed candles only (`x=True` flag)
- Extracts OHLCV data: open, high, low, close, volume
- Converts timestamps from milliseconds to datetime
- Creates CANDLE_CLOSED events with complete candle data
- Publishes events asynchronously via EventBus
- Handles errors gracefully without crashing stream

**Event Publishing:**
```python
# Event data structure for CANDLE_CLOSED
event_data = {
    'symbol': 'BTCUSDT',
    'interval': '15m',
    'open': 45000.0,
    'high': 45100.0,
    'low': 44900.0,
    'close': 45050.0,
    'volume': 100.5,
    'timestamp': datetime(2025, 12, 3, ...)
}

# Published via EventBus for downstream processing
await event_bus.publish(Event(
    event_type=EventType.CANDLE_CLOSED,
    data=event_data,
    source='BinanceWebSocket'
))
```

**Logging:**
- INFO level: Stream connection status
- DEBUG level: Individual candle close events with OHLCV data
- ERROR level: Stream errors and message processing failures

**Test Coverage:** 35 unit tests covering all functionality
- Initialization validation
- Configuration loading (testnet/mainnet)
- Credential loading and validation
- Connection lifecycle
- Error handling
- Kline streaming and message processing (5 tests)
  - Connection state validation
  - Closed candle event emission
  - Open candle filtering (ignored)
  - Malformed message handling
  - Invalid price data error handling

### 3. Trading Models (`src/core/models.py`)

**Purpose:** Type-safe trading dataclasses with comprehensive validation

**Implementation:** Pydantic BaseModel for superior validation and serialization

**Data Models:**

#### OrderBlock (Immutable)
Represents institutional order zones (support/resistance levels):

```python
class OrderBlock(BaseModel):
    model_config = {"frozen": True}  # Immutable

    type: Literal["bullish", "bearish"]  # Direction
    top: float                           # Upper boundary (>0, must be > bottom)
    bottom: float                        # Lower boundary (>0)
    timestamp: datetime                  # When detected
    touches: int = 0                     # Touch count (≥0)
    is_valid: bool = True                # Still valid?
```

**Validation:**
- Top > bottom price range check
- Positive prices required
- Non-negative touch count
- Type-safe direction with Literal

#### FVG - Fair Value Gap (Immutable)
Represents price inefficiencies to be filled:

```python
class FVG(BaseModel):
    model_config = {"frozen": True}  # Immutable

    type: Literal["bullish", "bearish"]  # Direction
    top: float                           # Upper boundary (>0, must be > bottom)
    bottom: float                        # Lower boundary (>0)
    timestamp: datetime                  # When created
    filled_percent: float = 0.0          # Fill % (0-100, auto-normalized to 2 decimals)
    is_valid: bool = True                # Still tradeable?
```

**Validation:**
- Top > bottom price range check
- Filled percent: 0-100 range with 2-decimal precision
- Automatic normalization of fill percentage

#### Position (Mutable)
Represents active trading positions:

```python
class Position(BaseModel):
    # NOT frozen - allows trailing stop updates

    symbol: str                          # Trading pair (uppercase, e.g., "BTCUSDT")
    side: Literal["long", "short"]       # Direction
    entry_price: float                   # Entry (>0)
    size: float                          # Position size (>0)
    stop_loss: float                     # SL level (>0)
    take_profit: float                   # TP level (>0)
    timestamp: datetime                  # When opened (auto-generated)

    def risk_reward_ratio(self) -> float:
        """Calculate R:R ratio (reward/risk)"""
```

**Validation:**
- Symbol must be uppercase letters only
- All prices and size must be positive
- **Long positions:** stop_loss < entry_price, take_profit > entry_price
- **Short positions:** stop_loss > entry_price, take_profit < entry_price
- Risk/reward ratio calculation method

**Design Decisions:**
- **Pydantic over dataclasses:** Superior validation, JSON serialization, better error messages
- **Immutability for historical data:** OrderBlock/FVG are frozen (historical facts)
- **Mutability for live positions:** Position allows updates (trailing stops, partial exits)
- **Field validators:** Declarative validation using `@model_validator` instead of `__post_init__`
- **Type safety:** Literal types for direction/side fields

**Usage Example:**
```python
from src.core.models import OrderBlock, FVG, Position
from datetime import datetime

# Create immutable order block
ob = OrderBlock(
    type="bullish",
    top=45000.0,
    bottom=44500.0,
    timestamp=datetime.utcnow()
)

# Create position with validation
pos = Position(
    symbol="BTCUSDT",
    side="long",
    entry_price=45000.0,
    size=0.1,
    stop_loss=44500.0,  # Must be below entry for long
    take_profit=46000.0  # Must be above entry for long
)

# Calculate risk/reward
rr = pos.risk_reward_ratio()  # 2.0
```

### 3. Event Processor Infrastructure (`src/core/event_processor.py`)

**Purpose:** Base infrastructure for event-driven processor lifecycle management

The event processor framework provides standardized lifecycle management for all event-processing components in the system, ensuring consistent startup/shutdown behavior and event handler registration.

**Key Components:**

#### EventProcessor (Abstract Base Class)
Base class for all event processors with standardized lifecycle:

```python
class EventProcessor(ABC):
    """
    Abstract base class for event processors with lifecycle management.

    Provides:
    - Standardized start/stop lifecycle
    - Handler registration/unregistration
    - Idempotent state transitions
    - Subclass hooks for custom initialization
    """

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._is_running = False

    async def start(self) -> None:
        """Start processor: _on_start() → _register_handlers()"""

    async def stop(self) -> None:
        """Stop processor: _unregister_handlers() → _on_stop()"""

    # Abstract methods to implement
    @abstractmethod
    def _register_handlers(self) -> None:
        """Subscribe to EventBus events"""

    @abstractmethod
    def _unregister_handlers(self) -> None:
        """Unsubscribe from EventBus events"""

    # Optional hooks
    async def _on_start(self) -> None:
        """Hook for startup initialization (optional)"""

    async def _on_stop(self) -> None:
        """Hook for cleanup (optional)"""
```

**Lifecycle Flow:**
```
start() → _on_start() → _register_handlers() → is_running = True
stop()  → _unregister_handlers() → _on_stop() → is_running = False
```

**Design Features:**
- **Idempotent Operations:** Multiple start/stop calls are safe (no-op if already in state)
- **Template Method Pattern:** Enforces consistent lifecycle across all processors
- **Hook Methods:** `_on_start()` and `_on_stop()` for processor-specific initialization
- **State Management:** `is_running` property tracks processor state

#### EventOrchestrator
Coordinates multiple processors with centralized lifecycle management:

```python
class EventOrchestrator:
    """
    Orchestrates multiple event processors with centralized lifecycle.

    Features:
    - Bulk start/stop operations
    - Reverse-order shutdown (LIFO)
    - Error handling without cascade failures
    - Status tracking and monitoring
    """

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._processors: List[EventProcessor] = []

    def register(self, processor: EventProcessor) -> None:
        """Register processor for orchestration"""

    async def start_all(self) -> None:
        """Start all processors in registration order"""

    async def stop_all(self) -> None:
        """Stop all processors in reverse order (LIFO)"""
```

**Key Behaviors:**
- **LIFO Shutdown:** Processors stop in reverse registration order (dependencies first)
- **Error Isolation:** Failures in one processor don't prevent others from starting/stopping
- **Centralized Control:** Single point for system-wide processor management
- **Monitoring:** `processor_count` and `running_count` properties for status tracking

**Usage Example:**
```python
from src.core.event_bus import EventBus
from src.core.event_processor import EventOrchestrator
from src.processors import PatternProcessor, SignalProcessor, OrderProcessor

# Create event bus and start it FIRST
bus = EventBus()
await bus.start()  # Must start before any processors publish events

# Create orchestrator
orchestrator = EventOrchestrator(bus)

# Register processors in dependency order
orchestrator.register(PatternProcessor(bus))
orchestrator.register(SignalProcessor(bus))
orchestrator.register(OrderProcessor(bus))

# Start all processors
await orchestrator.start_all()

# System running...

# Graceful shutdown (reverse order)
await orchestrator.stop_all()
await bus.stop()
```

**Processor Implementation Example:**
```python
class PatternProcessor(EventProcessor):
    def __init__(self, event_bus: EventBus, config: Optional[Dict] = None):
        super().__init__(event_bus)
        self._config = config or {}
        self._candle_history = None

    async def _on_start(self) -> None:
        """Initialize state on startup"""
        self._candle_history = deque(maxlen=100)
        logger.info("PatternProcessor initialized")

    def _register_handlers(self) -> None:
        """Subscribe to events"""
        self.event_bus.subscribe(EventType.CANDLE_CLOSED, self._on_candle_closed)

    def _unregister_handlers(self) -> None:
        """Unsubscribe from events"""
        self.event_bus.unsubscribe(EventType.CANDLE_CLOSED, self._on_candle_closed)

    async def _on_stop(self) -> None:
        """Cleanup state on shutdown"""
        if self._candle_history:
            self._candle_history.clear()
        logger.info("PatternProcessor cleaned up")

    async def _on_candle_closed(self, event: Event) -> None:
        """Handle candle events"""
        # Processing logic...
```

**Benefits:**
- **Consistent Lifecycle:** All processors follow same startup/shutdown pattern
- **Separation of Concerns:** Business logic separate from lifecycle management
- **Testability:** Easy to test processors in isolation
- **Maintainability:** Clear structure makes system easier to understand and modify
- **Error Recovery:** Graceful degradation when processors fail

### 4. State Store (`src/core/state_store.py`)

**Purpose:** Centralized state management for trading patterns and candle history

**Status:** ✅ Implemented (Task 3.3 - 2025-12-02)

The StateStore provides in-memory state management for pattern-based trading decisions with automatic memory management and type-safe filtering capabilities.

**Core Features:**
- **Candle History Management:** Fixed-size deque (500 candles default) with FIFO automatic cleanup
- **Pattern Storage:** Separate collections for OrderBlocks and FVGs with validity tracking
- **Type-Safe Filtering:** Literal type hints for compile-time safety on bullish/bearish queries
- **Memory Efficiency:** Automatic candle overflow handling via deque maxlen

**Implementation:**

```python
from collections import deque
from typing import Optional, List, Literal
from .models import OrderBlock, FVG

class StateStore:
    def __init__(self, candle_history_size: int = 500):
        """
        Initialize state store with configurable history size.

        Args:
            candle_history_size: Max candles to retain (default: 500)
        """
        self.candles: deque = deque(maxlen=candle_history_size)
        self.order_blocks: List[OrderBlock] = []
        self.fvgs: List[FVG] = []
```

**Core Methods:**

#### Storage Methods
```python
def add_candle(self, candle: dict) -> None:
    """
    Append candle dict to candles deque.

    Auto-removes oldest candle when maxlen reached (FIFO).
    """

def add_order_block(self, ob: OrderBlock) -> None:
    """
    Store OrderBlock pattern (both valid and invalid).
    """

def add_fvg(self, fvg: FVG) -> None:
    """
    Store FVG pattern (both valid and invalid).
    """
```

#### Query Methods with Type Filtering
```python
def get_valid_order_blocks(
    self,
    ob_type: Optional[Literal["bullish", "bearish"]] = None
) -> List[OrderBlock]:
    """
    Get valid order blocks with optional type filtering.

    Two-stage filtering:
    1. Filter by is_valid=True
    2. Optionally filter by type

    Args:
        ob_type: "bullish", "bearish", or None (all valid)

    Returns:
        List of valid OrderBlocks matching criteria
    """

def get_valid_fvgs(
    self,
    fvg_type: Optional[Literal["bullish", "bearish"]] = None
) -> List[FVG]:
    """
    Get valid FVGs with optional type filtering.

    Args:
        fvg_type: "bullish", "bearish", or None (all valid)

    Returns:
        List of valid FVGs matching criteria
    """
```

**Design Decisions:**
- **Simple Data Container:** No inheritance from EventProcessor (focused responsibility)
- **Deque for Candles:** Automatic FIFO memory management without manual cleanup
- **Lists for Patterns:** Manual management allows historical pattern tracking
- **Two-Stage Filtering:** Validity check first, then optional type filter for efficiency
- **Literal Type Hints:** Compile-time type safety for bullish/bearish parameters

**Usage Example:**
```python
from src.core import StateStore
from src.core.models import OrderBlock, FVG
from datetime import datetime

# Initialize store
store = StateStore(candle_history_size=500)

# Add candle data
candle = {
    "open": 45000.0,
    "high": 45100.0,
    "low": 44900.0,
    "close": 45050.0,
    "volume": 123.45
}
store.add_candle(candle)

# Store patterns
ob = OrderBlock(
    type="bullish",
    top=45000.0,
    bottom=44500.0,
    timestamp=datetime.utcnow(),
    is_valid=True
)
store.add_order_block(ob)

# Query valid patterns
all_valid_obs = store.get_valid_order_blocks()  # All valid OBs
bullish_obs = store.get_valid_order_blocks(ob_type="bullish")  # Bullish only
bearish_fvgs = store.get_valid_fvgs(fvg_type="bearish")  # Bearish FVGs only
```

**Testing:**
- **Test Suite:** `tests/unit/core/test_state_store.py` (913 lines)
- **Test Coverage:** 33/33 tests passed, 98% code coverage (46/46 statements)
- **Test Execution Time:** 0.09s (well under 5s requirement)
- **Test Categories:**
  - Initialization and configuration (4 tests)
  - Candle storage and deque behavior (3 tests)
  - Pattern addition (4 tests)
  - Validity filtering (13 tests)
  - Pattern cleanup logic (13 tests - comprehensive edge cases)

#### Pattern Cleanup Logic

**Status:** ✅ Implemented (Task 3.4 - 2025-12-02)

The StateStore includes automatic cleanup of old patterns to prevent unbounded memory growth:

```python
def _cleanup_old_patterns(self, max_age_candles: int = 500) -> None:
    """
    Remove patterns older than max_age_candles threshold.

    Age is measured by candle count (index-based), not time duration.
    Patterns are kept if their timestamp corresponds to a candle within
    the last max_age_candles candles.

    Args:
        max_age_candles: Maximum candle age to retain patterns for.
            Default 500 aligns with candle deque maxlen.
    """
```

**Cleanup Features:**
- **Automatic Invocation:** Called at the end of every `add_candle()` operation
- **Index-Based Age:** Measures age by candle count, not time duration
- **Timestamp Filtering:** Patterns filtered by comparing timestamps against cutoff candle
- **Default Threshold:** 500 candles (aligns with candle deque size)
- **Minimal Logging:** DEBUG-level logging only when patterns actually removed
- **Edge Case Handling:** Gracefully handles empty candles, invalid thresholds, missing timestamps

**Implementation Details:**
1. Calculate cutoff index: `len(candles) - max_age_candles`
2. Early return if insufficient candles or invalid parameters
3. Get cutoff timestamp from candle at cutoff index
4. Filter both OrderBlocks and FVGs: keep only patterns with `timestamp >= cutoff_timestamp`
5. Log removed count at DEBUG level if any patterns removed

**Memory Management:**
- **Candles:** Automatic FIFO cleanup via deque maxlen (500)
- **Patterns:** Manual cleanup via `_cleanup_old_patterns()` called on each candle addition
- **Prevents:** Unbounded memory growth while retaining relevant patterns

**Testing:** ✅ Verified (Task 3.5 - 2025-12-02)
- **Test Suite:** `tests/unit/core/test_state_store.py` - TestPatternCleanup class
- **Test Coverage:** 13/13 cleanup tests passed, 98% overall code coverage
- **Comprehensive Test Cases:**
  - Old pattern removal (OrderBlocks and FVGs)
  - Recent pattern preservation
  - Empty candles edge case
  - Insufficient candles handling (cutoff_index <= 0)
  - Invalid threshold handling (max_age <= 0, max_age > candles)
  - Missing timestamp field graceful handling
  - Auto-cleanup verification on add_candle()
  - Mixed age patterns (some old, some recent)
  - Validity flag preservation during cleanup
  - Boundary conditions and cutoff calculations

**Integration Points:**
- **Task 4 (WebSocket):** Calls `add_candle()` on CANDLE_CLOSED events (triggers auto-cleanup)
- **Task 6 (SignalEngine):** Uses `get_valid_order_blocks()` and `get_valid_fvgs()` for pattern analysis
- **Task 8 (OrderManager):** Queries `candles` deque for recent price action

### 4. WebSocket Client (`src/data/websocket_client.py`)

**Purpose:** Real-time market data streaming from Binance

**Responsibilities:**
- Establish and maintain WebSocket connection
- Subscribe to kline (candle) streams
- Parse and normalize candle data
- Publish CANDLE_CLOSED events

**Configuration:**
- Symbol: BTCUSDT (MVP)
- Interval: 15m (MVP)
- Testnet mode enabled

### 5. Strategy Engine (`src/strategy/signal_engine.py`)

**Purpose:** Pattern detection and entry signal generation

**ICT Patterns Implemented:**
- **Order Blocks (OB):**
  - Detection: Strong candle (body >70%) following opposite-direction candle
  - Validation: Touch counting, age limit
  - Types: Bullish OB, Bearish OB

- **Fair Value Gaps (FVG):**
  - Detection: Gap between candle[i].high and candle[i+2].low (bullish)
  - Validation: Fill percentage tracking
  - Types: Bullish FVG, Bearish FVG

**Signal Generation:**
- Entry on price touching OB zone
- Confluence with FVG increases signal strength
- Stop loss: OB boundary ± 0.2%
- Take profit: 1% (bullish) / -1% (bearish)

### 6. Order Manager (`src/execution/order_manager.py`)

**Purpose:** Trade execution and position management

**Responsibilities:**
- Process entry signals
- Calculate position size (from RiskManager)
- Place market orders
- Set stop-loss and take-profit orders
- Update position state

**Order Types:**
- MARKET: Entry orders
- STOP_MARKET: Stop-loss
- TAKE_PROFIT_MARKET: Take-profit

### 7. Risk Manager (`src/execution/risk_manager.py`)

**Purpose:** Position sizing and risk control

**Risk Parameters:**
- Risk per trade: 1% of balance
- Max daily loss: 3% of balance
- Max position size: 10% of balance
- Max daily trades: 5

**Position Sizing Formula:**
```
risk_amount = balance × risk_per_trade_percent
price_risk = |entry_price - stop_loss|
position_size = min(
    risk_amount / price_risk,
    balance × max_position_percent / entry_price
)
```

### 8. Discord Notifier (`src/notification/discord.py`)

**Purpose:** Real-time trade notifications via Discord webhook

**Notifications:**
- Position opened (entry price, size, SL/TP)
- Position closed (P&L, exit reason)
- System errors

**Message Format:**
- Embedded messages with color coding
- Green: Profitable trades
- Red: Loss trades
- Fields: Symbol, Entry, Size, SL, TP, P&L

## Event Types

```python
class EventType(Enum):
    # Data Events
    CANDLE_CLOSED = "candle_closed"

    # Pattern Events
    ORDER_BLOCK_DETECTED = "order_block_detected"
    FVG_DETECTED = "fvg_detected"

    # Trading Events
    ENTRY_SIGNAL = "entry_signal"
    ORDER_PLACED = "order_placed"
    ORDER_FILLED = "order_filled"
    POSITION_CLOSED = "position_closed"

    # System Events
    ERROR = "error"
```

## Data Flow Diagram

```
┌──────────────┐
│   Binance    │
│   WebSocket  │
└──────┬───────┘
       │ Candle Data
       ▼
┌──────────────┐
│  Event Bus   │◀──────────────┐
└──┬───────────┘               │
   │                           │
   │ CANDLE_CLOSED             │
   ▼                           │
┌──────────────┐               │
│ State Store  │               │
│ (Add Candle) │               │
└──────────────┘               │
   │                           │
   ▼                           │
┌──────────────┐               │
│   Strategy   │               │
│    Engine    │               │
└──┬───────────┘               │
   │ Pattern Detection         │
   │                           │
   ├─ OB_DETECTED ─────────────┤
   ├─ FVG_DETECTED ────────────┤
   │                           │
   │ Entry Signal Check        │
   ▼                           │
   ENTRY_SIGNAL ───────────────┤
                               │
                               ▼
                        ┌──────────────┐
                        │     Risk     │
                        │   Manager    │
                        └──────┬───────┘
                               │
                               ▼
                        ┌──────────────┐
                        │    Order     │
                        │   Manager    │
                        └──────┬───────┘
                               │
                               │ ORDER_FILLED
                               ▼
                        ┌──────────────┐
                        │   Discord    │
                        │  Notifier    │
                        └──────────────┘
```

## Technology Stack

### Core Dependencies (Production)

- **Language:** Python 3.9+
- **Async Framework:** asyncio
- **Exchange Library:** python-binance (>=1.0.19)
  - Binance API integration for trading and market data
- **Configuration Management:**
  - python-dotenv (>=1.0.0) - Environment variable loading
  - PyYAML (>=6.0) - YAML configuration parsing
- **Logging:** loguru (>=0.7.0)
  - Advanced logging with rotation and formatting
- **Data Validation:** pydantic (>=2.0.0)
  - Type-safe settings and data models
- **HTTP Client:** aiohttp (>=3.9.0)
  - Asynchronous HTTP requests for notifications

### Development Dependencies

- **Testing Framework:** pytest (>=8.0.0)
  - pytest-asyncio (>=0.23.0) - Async test support
  - pytest-cov (>=4.1.0) - Coverage reporting
  - pytest-mock (>=3.12.0) - Mocking utilities
- **Code Quality:**
  - black (>=24.0.0) - Code formatting
  - flake8 (>=7.0.0) - Linting
  - mypy (>=1.8.0) - Type checking
  - isort (>=5.13.0) - Import sorting
- **Development Tools:**
  - ipython (>=8.20.0) - Interactive shell
  - ipdb (>=0.13.13) - Debugger

### Installation

```bash
# Production dependencies
pip install -r requirements.txt

# Development dependencies
pip install -r requirements-dev.txt
```

## Configuration Files

### .env (Secrets)
```bash
BINANCE_API_KEY=xxx
BINANCE_API_SECRET=xxx
DISCORD_WEBHOOK_URL=xxx
```

### config.yaml (Trading Parameters)
```yaml
trading:
  symbol: "BTCUSDT"
  interval: "15m"
  use_testnet: true

strategy:
  order_block:
    min_body_ratio: 0.7
    max_touches: 3
  fvg:
    min_gap_percent: 0.1

risk:
  risk_per_trade_percent: 1.0
  max_daily_loss_percent: 3.0
  max_position_percent: 10.0
  max_daily_trades: 5
```

## Future Enhancements (Post-MVP)

- **Phase 1:** Market Structure (BOS/CHoCH), Multi-timeframe
- **Phase 2:** Bounded queues, worker pools for scalability
- **Phase 3:** Liquidity sweep patterns
- **Phase 4:** React dashboard, real-time monitoring
- **Phase 5:** Mainnet deployment, backtesting engine

---

**Last Updated:** 2025-11-30
**Version:** MVP v0.1.0
