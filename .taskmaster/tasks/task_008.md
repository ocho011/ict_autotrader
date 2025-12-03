# Task ID: 8

**Title:** Implement Order Manager for Trade Execution

**Status:** pending

**Dependencies:** 2 ✓, 3 ✓, 7

**Priority:** high

**Description:** Build OrderManager to execute market orders, set stop-loss/take-profit, and manage position lifecycle

**Details:**

Create src/execution/order_manager.py with:

OrderManager class:
- __init__(event_bus, state, risk_manager, client):
  * Subscribe to ENTRY_SIGNAL events
  * Store references to event_bus, state_store, risk_manager, Binance client

- on_entry_signal(event: Event) async:
  * Extract signal data from event
  * Check risk_manager.can_trade() - skip if False
  * Calculate position size via risk_manager.calculate_position_size(entry_price, stop_loss)
  * Skip if position_size <= 0
  * Determine side: 'BUY' for long, 'SELL' for short
  * Execute market order:
    - await client.futures_create_order(
        symbol=symbol,
        side=side,
        type='MARKET',
        quantity=position_size
      )
  * Log order execution
  * Call _set_stop_loss_take_profit(side, position_size, stop_loss, take_profit)
  * Create Position object and store in state.current_position
  * Publish ORDER_FILLED event with order and position data
  * On exception: log error and publish ERROR event

- _set_stop_loss_take_profit(side, quantity, stop_loss, take_profit) async:
  * Determine close_side: 'SELL' for long, 'BUY' for short
  * Create STOP_MARKET order:
    - await client.futures_create_order(
        symbol=symbol,
        side=close_side,
        type='STOP_MARKET',
        stopPrice=round(stop_loss, 2),
        quantity=quantity,
        reduceOnly=True
      )
  * Create TAKE_PROFIT_MARKET order:
    - await client.futures_create_order(
        symbol=symbol,
        side=close_side,
        type='TAKE_PROFIT_MARKET',
        stopPrice=round(take_profit, 2),
        quantity=quantity,
        reduceOnly=True
      )
  * Log SL/TP placement

- Use testnet for all orders initially
- Add comprehensive error handling for order failures

**Test Strategy:**

Integration test with Binance Testnet. Verify market orders execute successfully. Confirm SL/TP orders are placed with correct prices and reduceOnly flag. Test position state updates after order fill. Verify events published correctly. Test error handling for insufficient margin, invalid quantities. Monitor testnet account for actual order placement.

## Subtasks

### 8.1. Set up OrderManager class structure and event subscriptions

**Status:** pending  
**Dependencies:** None  

Create the OrderManager class with initialization logic, store dependencies, and subscribe to ENTRY_SIGNAL events

**Details:**

Create src/execution/order_manager.py with OrderManager class. Implement __init__(event_bus, state, risk_manager, client) to store references to event_bus, state_store, risk_manager, and Binance client. Subscribe to ENTRY_SIGNAL events using event_bus.subscribe(EventType.ENTRY_SIGNAL, self.on_entry_signal). Set up logging for the OrderManager. Ensure all dependencies are properly injected and stored as instance variables.

### 8.2. Implement entry signal processing and validation logic

**Status:** pending  
**Dependencies:** 8.1  

Build the on_entry_signal handler to extract signal data, validate trading conditions, and calculate position size

**Details:**

Implement async on_entry_signal(event: Event) method. Extract signal data (symbol, entry_price, stop_loss, take_profit, direction) from event. Check risk_manager.can_trade() and skip execution if False. Call risk_manager.calculate_position_size(entry_price, stop_loss) to get position size. Skip execution if position_size <= 0. Determine order side ('BUY' for long, 'SELL' for short) based on signal direction. Add comprehensive logging for validation steps and decisions.

### 8.3. Create market order execution logic with error handling

**Status:** pending  
**Dependencies:** 8.2  

Implement the core market order placement functionality using Binance Futures API with comprehensive error handling

**Details:**

Within on_entry_signal, implement market order execution using await client.futures_create_order(symbol=symbol, side=side, type='MARKET', quantity=position_size). Add try/except block to catch order execution errors (insufficient margin, invalid quantity, network errors, API errors). Log successful order execution with order details. On exception, log detailed error information and publish ERROR event with error context. Ensure all orders use testnet configuration initially.

### 8.4. Implement stop-loss order placement functionality

**Status:** pending  
**Dependencies:** 8.3  

Create the logic to place STOP_MARKET orders for position protection after market order execution

**Details:**

Implement _set_stop_loss_take_profit helper method with parameters (side, quantity, stop_loss, take_profit). Determine close_side: 'SELL' for long positions, 'BUY' for short positions. Create STOP_MARKET order using await client.futures_create_order(symbol=symbol, side=close_side, type='STOP_MARKET', stopPrice=round(stop_loss, 2), quantity=quantity, reduceOnly=True). Add error handling for SL order failures. Log SL order placement with order ID and price.

### 8.5. Implement take-profit order placement functionality

**Status:** pending  
**Dependencies:** 8.4  

Create the logic to place TAKE_PROFIT_MARKET orders for position exits after market order execution

**Details:**

Within _set_stop_loss_take_profit method, create TAKE_PROFIT_MARKET order using await client.futures_create_order(symbol=symbol, side=close_side, type='TAKE_PROFIT_MARKET', stopPrice=round(take_profit, 2), quantity=quantity, reduceOnly=True). Use same close_side determination as stop-loss. Add error handling for TP order failures. Log TP order placement with order ID and price. Ensure both SL and TP orders are placed sequentially in the same method.

### 8.6. Add position state management and event publishing

**Status:** pending  
**Dependencies:** 8.5  

Implement position object creation, state storage, and ORDER_FILLED event publishing after successful order execution

**Details:**

After successful market order execution, create Position object with fields: symbol, side, entry_price, quantity, stop_loss, take_profit, entry_time (current timestamp), status='OPEN'. Store position in state.current_position. Publish ORDER_FILLED event using event_bus.publish() with event data containing order details and position object. Include all relevant order information (order_id, filled_price, filled_quantity) in event data. Add logging for position creation and event publishing.

### 8.7. Integration testing with Binance Testnet and comprehensive error handling

**Status:** pending  
**Dependencies:** 8.1, 8.2, 8.3, 8.4, 8.5, 8.6  

Perform end-to-end integration testing on Binance Testnet and validate all error scenarios

**Details:**

Set up integration test environment with Binance Testnet credentials. Create test scenarios: (1) successful long position with SL/TP, (2) successful short position with SL/TP, (3) rejected trade due to risk checks, (4) insufficient margin error, (5) invalid quantity error, (6) network timeout, (7) SL/TP order placement failure. Verify all events published correctly (ENTRY_SIGNAL → ORDER_FILLED or ERROR). Test position state updates. Validate order IDs and prices in logs. Confirm reduceOnly flag on SL/TP orders. Document test results and error scenarios.
