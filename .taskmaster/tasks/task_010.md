# Task ID: 10

**Title:** Implement Main Application Entry Point and Integration

**Status:** pending

**Dependencies:** 2 ✓, 3 ✓, 4 ✓, 6, 7, 8, 9

**Priority:** high

**Description:** Create main.py to orchestrate all components, load configuration, and run the complete trading system

**Details:**

Create src/main.py with:

- Import all components:
  * asyncio, os, yaml, dotenv
  * loguru logger
  * binance AsyncClient
  * EventBus, StateStore
  * BinanceWebSocket
  * SignalEngine
  * OrderManager, RiskManager
  * DiscordNotifier

- main() async function:
  * Load .env with load_dotenv()
  * Load config.yaml with yaml.safe_load()
  * Initialize loguru logger:
    - Console output with INFO level
    - File output to logs/trader.log with rotation
  * Create EventBus instance
  * Create StateStore instance
  * Create AsyncClient for Binance:
    - API key/secret from os.getenv()
    - testnet flag from config['trading']['use_testnet']
  * Create RiskManager(config['risk'], client)
  * Create BinanceWebSocket(event_bus, symbol, interval)
  * Create SignalEngine(event_bus, state, config['strategy'])
  * Create OrderManager(event_bus, state, risk_manager, client)
  * Create DiscordNotifier(event_bus, webhook_url)
  * Log startup information:
    - Symbol, Interval, Testnet status
    - Risk parameters
  * Connect WebSocket: await ws_client.connect()
  * Run event loop and WebSocket stream concurrently:
    - await asyncio.gather(
        event_bus.start(),
        ws_client.start_kline_stream()
      )

- Add graceful shutdown:
  * Catch KeyboardInterrupt
  * Call event_bus.stop()
  * Close Binance client
  * Log shutdown message

- if __name__ == "__main__":
  * asyncio.run(main())

- Add config validation on startup
- Create logs/ directory if it doesn't exist

**Test Strategy:**

End-to-end integration test: Run main.py with Testnet. Verify all components initialize successfully. Check WebSocket connects and receives candle data. Monitor logs for CANDLE_CLOSED events. Test pattern detection triggers. Verify signal generation and order placement flow. Test Discord notifications. Run for 1 hour to ensure stability. Test graceful shutdown with Ctrl+C.

## Subtasks

### 10.1. Create configuration loading system with environment and YAML validation

**Status:** pending  
**Dependencies:** None  

Implement configuration loading from .env and config.yaml files with comprehensive validation to ensure all required settings are present and valid before system initialization.

**Details:**

Create configuration loading module in src/main.py:
- Import python-dotenv, yaml, os modules
- Implement load_dotenv() to load environment variables from .env file
- Create load_config() function to read and parse config.yaml using yaml.safe_load()
- Implement validate_config() function to check:
  * Required sections exist: trading, risk, strategy
  * Required env vars exist: BINANCE_API_KEY, BINANCE_API_SECRET, DISCORD_WEBHOOK_URL
  * Symbol and interval are valid strings
  * Risk parameters are within valid ranges (risk_per_trade 0.01-0.05, max_positions > 0)
  * Strategy config has required fields: ob_lookback, fvg_threshold, risk_reward_ratio
- Raise ConfigurationError with descriptive messages if validation fails
- Return validated config dict for use by main application

### 10.2. Set up logging infrastructure with file rotation and console output

**Status:** pending  
**Dependencies:** 10.1  

Configure loguru logger with dual output to console and rotating log files, ensuring proper log directory creation and appropriate log levels for debugging and production use.

**Details:**

Implement logging setup in src/main.py:
- Import loguru logger
- Create setup_logging() function:
  * Create logs/ directory using os.makedirs(exist_ok=True)
  * Remove default logger handler
  * Add console sink:
    - Format: "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
    - Level: INFO
    - Colorize: True
  * Add file sink:
    - Path: logs/trader.log
    - Rotation: "10 MB" or "1 day"
    - Retention: "7 days"
    - Level: DEBUG
    - Format: "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
  * Log initial message: "Logging system initialized"
- Call setup_logging() early in main() function

### 10.3. Initialize core infrastructure components (EventBus, StateStore, AsyncClient)

**Status:** pending  
**Dependencies:** 10.1, 10.2  

Create and initialize the foundational components required by all trading subsystems: EventBus for event-driven architecture, StateStore for shared state, and Binance AsyncClient for exchange connectivity.

**Details:**

Implement core component initialization in main() function:
- Import EventBus from src/core/event_bus
- Import StateStore from src/core/state
- Import AsyncClient from binance
- Create EventBus instance: event_bus = EventBus()
- Create StateStore instance: state = StateStore()
- Initialize Binance AsyncClient:
  * api_key = os.getenv('BINANCE_API_KEY')
  * api_secret = os.getenv('BINANCE_API_SECRET')
  * testnet = config['trading']['use_testnet']
  * client = await AsyncClient.create(api_key, api_secret, testnet=testnet)
- Log successful initialization:
  * logger.info(f"Core components initialized")
  * logger.info(f"Testnet mode: {testnet}")
- Store references for later use and cleanup
- Add to cleanup in shutdown handler

### 10.4. Initialize trading components (WebSocket, SignalEngine, OrderManager, RiskManager)

**Status:** pending  
**Dependencies:** 10.3  

Create and wire up all trading-specific components that handle market data streaming, pattern detection, signal generation, risk management, and order execution.

**Details:**

Implement trading component initialization in main() function:
- Import BinanceWebSocket from src/data/websocket_client
- Import SignalEngine from src/strategy/signal_engine
- Import OrderManager from src/execution/order_manager
- Import RiskManager from src/execution/risk_manager
- Extract trading config:
  * symbol = config['trading']['symbol']
  * interval = config['trading']['interval']
- Create RiskManager:
  * risk_manager = RiskManager(config['risk'], client)
  * Log risk parameters: logger.info(f"Risk settings: {config['risk']}")
- Create BinanceWebSocket:
  * ws_client = BinanceWebSocket(event_bus, symbol, interval)
- Create SignalEngine:
  * signal_engine = SignalEngine(event_bus, state, config['strategy'])
- Create OrderManager:
  * order_manager = OrderManager(event_bus, state, risk_manager, client)
- Log trading setup:
  * logger.info(f"Trading {symbol} on {interval} timeframe")
- Store references for shutdown cleanup

### 10.5. Set up Discord notification system integration

**Status:** pending  
**Dependencies:** 10.3  

Initialize Discord webhook integration for real-time notifications of trading events, errors, and system status updates.

**Details:**

Implement Discord notifier setup in main() function:
- Import DiscordNotifier from src/notification/discord
- Get Discord webhook URL:
  * webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
  * Validate webhook_url is not None/empty
- Create DiscordNotifier:
  * notifier = DiscordNotifier(event_bus, webhook_url)
  * Verify subscription to ORDER_FILLED, POSITION_CLOSED, ERROR events
- Send startup notification:
  * content = f"🚀 트레이딩 시스템 시작\nSymbol: {symbol}\nInterval: {interval}\nTestnet: {testnet}"
  * await notifier.send(content)
- Log Discord setup:
  * logger.info("Discord notifications enabled")
- Store reference for shutdown notification
- Add shutdown notification in cleanup:
  * await notifier.send("🛑 트레이딩 시스템 종료")
- Handle missing webhook URL gracefully (log warning, continue without notifications)

### 10.6. Implement concurrent execution with asyncio.gather for event loop and data streaming

**Status:** pending  
**Dependencies:** 10.4, 10.5  

Set up concurrent async execution of EventBus processing loop and WebSocket data streaming using asyncio.gather, ensuring both run simultaneously and handle errors properly.

**Details:**

Implement concurrent execution in main() function:
- Connect WebSocket before starting streams:
  * await ws_client.connect()
  * logger.info("WebSocket connected to Binance")
- Create list of concurrent tasks:
  * tasks = [
      event_bus.start(),  # Event processing loop
      ws_client.start_kline_stream()  # WebSocket data stream
    ]
- Execute concurrently using asyncio.gather:
  * await asyncio.gather(*tasks, return_exceptions=True)
- Handle exceptions from gather:
  * Check if any task returned exception
  * Log errors with stack traces
  * Re-raise critical exceptions
- Add timeout mechanism:
  * Wrap gather in asyncio.wait_for with optional timeout
  * Handle TimeoutError appropriately
- Log concurrent execution start:
  * logger.info("Starting event bus and WebSocket streams...")
- Ensure proper cancellation on shutdown

### 10.7. Add graceful shutdown handling with cleanup and resource management

**Status:** pending  
**Dependencies:** 10.6  

Implement comprehensive shutdown logic to handle KeyboardInterrupt, cleanup all resources, close connections, and ensure data integrity on exit.

**Details:**

Implement graceful shutdown in main() function:
- Wrap main execution in try/except:
  * try:
      # Core initialization (tasks 3-6)
      # Concurrent execution
  * except KeyboardInterrupt:
      logger.info("Received shutdown signal (Ctrl+C)")
  * except Exception as e:
      logger.error(f"Fatal error: {e}")
      logger.exception(e)
  * finally:
      # Cleanup code
- Implement cleanup sequence:
  * Log shutdown start: logger.info("Shutting down gracefully...")
  * Send Discord shutdown notification (if enabled)
  * Stop EventBus: await event_bus.stop()
  * Close WebSocket: await ws_client.close()
  * Close Binance client: await client.close_connection()
  * Log final positions and P&L from state
  * Log shutdown complete: logger.info("Shutdown complete")
- Add timeout for cleanup operations (10 seconds)
- Ensure __main__ block calls asyncio.run(main())
- Handle cleanup failures gracefully (log but don't crash)

### 10.8. Perform end-to-end integration testing with full system validation

**Status:** pending  
**Dependencies:** 10.7  

Conduct comprehensive integration testing of the complete trading system from startup through trading operations to shutdown, validating all component interactions and data flows.

**Details:**

Create comprehensive E2E integration test:
- Test complete startup sequence:
  * Config loading and validation
  * Logging initialization
  * All component creation and initialization
  * Discord startup notification
  * WebSocket connection establishment
- Test runtime operations:
  * WebSocket receives and processes candle data
  * CANDLE_CLOSED events published to EventBus
  * StateStore accumulates candles correctly
  * Pattern detection triggers (mock candles if needed)
  * Signal generation and ORDER events
  * Order execution flow (testnet orders)
  * Discord notifications for trades
- Test error scenarios:
  * Invalid config handling
  * WebSocket disconnection and reconnection
  * Order rejection handling
  * Exception propagation and logging
- Test shutdown sequence:
  * Graceful cleanup on Ctrl+C
  * All resources properly closed
  * Final state logged
  * Discord shutdown notification
- Performance validation:
  * Event processing latency < 100ms
  * WebSocket message handling rate
  * Memory usage stability over time
- Create integration test script in tests/test_e2e.py
- Document test results and any issues found
