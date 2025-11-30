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
Implements the Observer pattern for event distribution:

```python
bus = EventBus()
bus.subscribe(EventType.CANDLE_CLOSED, on_candle_closed)
bus.emit(event)  # Calls all subscribers
```

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

### 2. State Store (`src/core/state_store.py`)

**Purpose:** Centralized state management for patterns and positions

**Managed State:**
- Candle history (200 candles max)
- Order Blocks (with touch counting and validation)
- Fair Value Gaps (with fill tracking)
- Current position
- Daily P&L and trade count

**Data Structures:**
- `OrderBlock`: type, top, bottom, timestamp, touches, is_valid
- `FVG`: type, top, bottom, timestamp, filled_percent, is_valid
- `Position`: symbol, side, entry_price, size, stop_loss, take_profit

### 3. WebSocket Client (`src/data/websocket_client.py`)

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

### 4. Strategy Engine (`src/strategy/signal_engine.py`)

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

### 5. Order Manager (`src/execution/order_manager.py`)

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

### 6. Risk Manager (`src/execution/risk_manager.py`)

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

### 7. Discord Notifier (`src/notification/discord.py`)

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
