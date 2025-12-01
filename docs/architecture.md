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

# Async queue-based publishing (non-blocking)
await bus.publish(event)  # Adds to queue without blocking

# Event processing lifecycle
await bus.start()   # Start background event processing loop
await bus.stop()    # Graceful shutdown with no event loss

# Synchronous emission (direct)
bus.emit(event)     # Calls all subscribers immediately
```

**Async Queue Architecture:**
- Non-blocking event publishing via `asyncio.Queue`
- Background event processing loop using `asyncio.create_task()`
- Graceful shutdown with 5-second timeout ensures no event loss
- Robust error handling with try-except-finally pattern for queue task tracking
- Properties: `is_running` (bool), `queue_size` (int)
- Comprehensive error logging with Loguru structured context

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

### 2. Trading Models (`src/core/models.py`)

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

# Create event bus
bus = EventBus()
await bus.start()

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

**Purpose:** Centralized state management for patterns and positions

**Managed State:**
- Candle history (200 candles max)
- Order Blocks (using `OrderBlock` model)
- Fair Value Gaps (using `FVG` model)
- Current position (using `Position` model)
- Daily P&L and trade count

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
