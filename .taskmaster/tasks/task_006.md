# Task ID: 6

**Title:** Implement Signal Generation Engine

**Status:** pending

**Dependencies:** 2 ✓, 3 ✓, 5 ⧖

**Priority:** high

**Description:** Build SignalEngine to detect patterns from candle data and generate entry signals with confluence

**Details:**

Create src/strategy/signal_engine.py with:

SignalEngine class:
- __init__(event_bus, state, config):
  * Subscribe to CANDLE_CLOSED events
  * Store references to event_bus, state_store, strategy config

- on_candle_closed(event: Event) async:
  * Extract candle from event data
  * Add to state.candles
  * Skip if < 20 candles in state
  * Call _detect_patterns()
  * Call _check_entry_signal(candle)

- _detect_patterns() async:
  * Get candles list from state
  * Call detect_order_block(candles, config)
  * If OB found:
    - Add to state via state.add_order_block(ob)
    - Publish ORDER_BLOCK_DETECTED event
  * Call detect_fvg(candles, config)
  * If FVG found:
    - Add to state via state.add_fvg(fvg)
    - Publish FVG_DETECTED event

- _check_entry_signal(candle: dict) async:
  * Skip if state.current_position exists (already in trade)
  * Get current price from candle['close']
  * Bullish Entry:
    - Loop through state.get_valid_order_blocks('bullish')
    - Check if price in OB range (ob.bottom <= price <= ob.top)
    - Check for FVG confluence (price in bullish FVG range)
    - Publish ENTRY_SIGNAL event with: side='long', price, order_block, has_fvg_confluence, stop_loss (OB bottom - 0.2%), take_profit (price + 1%)
  * Bearish Entry:
    - Similar logic for bearish OBs
    - SL: OB top + 0.2%, TP: price - 1%

- Use loguru for signal generation logging

**Test Strategy:**

Unit test pattern detection flow with mock candles. Verify OB/FVG events published correctly. Test entry signal generation for both long/short scenarios. Confirm signals only generated when no position exists. Validate SL/TP calculation accuracy. Test confluence detection (OB + FVG overlap). Integration test with live EventBus.

## Subtasks

### 6.1. Set up SignalEngine class with EventBus subscription

**Status:** pending  
**Dependencies:** None  

Create SignalEngine class structure with initialization, EventBus subscription, and configuration storage

**Details:**

Create src/strategy/signal_engine.py with SignalEngine class. Implement __init__(event_bus, state, config) that stores references to event_bus, state_store, and strategy config. Subscribe to CANDLE_CLOSED events using event_bus.subscribe(EventType.CANDLE_CLOSED, self.on_candle_closed). Add loguru logger configuration for signal generation. Set up basic class structure with placeholder methods for on_candle_closed, _detect_patterns, and _check_entry_signal.

### 6.2. Implement candle processing and state management

**Status:** pending  
**Dependencies:** 6.1  

Build on_candle_closed handler to process incoming candles and maintain state with minimum candle validation

**Details:**

Implement on_candle_closed(event: Event) async method. Extract candle data from event.data. Add candle to state.candles list. Implement validation to skip processing if fewer than 20 candles exist in state (log skip reason). Call _detect_patterns() and _check_entry_signal(candle) after validation passes. Add error handling for malformed candle data. Log candle processing status at each step.

### 6.3. Create pattern detection integration (OB and FVG)

**Status:** pending  
**Dependencies:** 6.2  

Implement _detect_patterns method to identify order blocks and fair value gaps, publishing detection events

**Details:**

Implement _detect_patterns() async method. Retrieve candles list from state.candles. Call detect_order_block(candles, config) from pattern_detection module. If order block found, add to state via state.add_order_block(ob) and publish ORDER_BLOCK_DETECTED event with OB data. Call detect_fvg(candles, config) similarly. If FVG found, add to state via state.add_fvg(fvg) and publish FVG_DETECTED event. Log each pattern detection attempt and result. Handle cases where no patterns are detected.

### 6.4. Implement bullish entry signal logic with confluence detection

**Status:** pending  
**Dependencies:** 6.3  

Build bullish entry signal detection that checks for order block alignment and FVG confluence

**Details:**

Implement bullish entry logic in _check_entry_signal(candle: dict) async. Check if state.current_position exists - skip if already in trade. Extract current price from candle['close']. Loop through state.get_valid_order_blocks('bullish'). For each bullish OB, check if current price is within OB range (ob.bottom <= price <= ob.top). Check for FVG confluence by verifying if price also falls within any bullish FVG range from state.get_valid_fvgs('bullish'). Set has_fvg_confluence flag. If entry conditions met, prepare signal data with side='long', price, order_block reference, has_fvg_confluence flag. Log bullish signal detection with confluence status.

### 6.5. Implement bearish entry signal logic

**Status:** pending  
**Dependencies:** 6.4  

Build bearish entry signal detection mirroring bullish logic for short positions

**Details:**

Implement bearish entry logic in _check_entry_signal(candle: dict) async. Similar to bullish logic but for bearish patterns. Loop through state.get_valid_order_blocks('bearish'). Check if current price is within bearish OB range (ob.bottom <= price <= ob.top). Check for bearish FVG confluence using state.get_valid_fvgs('bearish'). If entry conditions met, prepare signal data with side='short', price, order_block reference, has_fvg_confluence flag. Log bearish signal detection with confluence status. Ensure both bullish and bearish checks can run in same method without conflicts.

### 6.6. Add stop-loss and take-profit calculation

**Status:** pending  
**Dependencies:** 6.5  

Implement SL/TP calculation logic for both long and short positions based on order block levels

**Details:**

Extend _check_entry_signal to calculate stop-loss and take-profit levels. For bullish signals: stop_loss = ob.bottom - (ob.bottom * 0.002) [0.2% below OB bottom], take_profit = price + (price * 0.01) [1% above entry]. For bearish signals: stop_loss = ob.top + (ob.top * 0.002) [0.2% above OB top], take_profit = price - (price * 0.01) [1% below entry]. Add SL and TP values to signal data. Publish ENTRY_SIGNAL event with complete data structure: {side, price, order_block, has_fvg_confluence, stop_loss, take_profit, timestamp}. Log calculated SL/TP levels with signal generation.

### 6.7. Comprehensive testing with mock candles and live EventBus

**Status:** pending  
**Dependencies:** 6.6  

Create integration tests simulating complete signal generation flow from candle data to entry signals

**Details:**

Create tests/test_signal_engine.py with comprehensive integration tests. Set up test fixtures with EventBus, StateStore, and SignalEngine. Generate mock candle sequences that produce known OB and FVG patterns. Test complete flow: publish CANDLE_CLOSED events → verify pattern detection → verify entry signals published. Test scenarios: (1) bullish entry with confluence, (2) bearish entry with confluence, (3) entry without confluence, (4) no entry signal when position exists, (5) no signal when insufficient candles, (6) multiple patterns but only one valid entry. Verify event publication order and data integrity. Test with realistic BTC/USDT price data. Measure signal generation latency.
