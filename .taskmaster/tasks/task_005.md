# Task ID: 5

**Title:** Implement Order Block and FVG Pattern Detection

**Status:** in-progress

**Dependencies:** 3 ✓

**Priority:** high

**Description:** Create pattern detection logic for ICT Order Blocks and Fair Value Gaps (FVG)

**Details:**

Create src/strategy/patterns.py with detection functions:

Order Block Detection:
- detect_order_block(candles: list, config: dict) -> Optional[OrderBlock]
- Logic:
  * Require minimum 5 candles
  * Examine last 2 candles (current and previous)
  * Calculate body_ratio = abs(close - open) / (high - low)
  * If body_ratio > min_body_ratio (default 0.7):
    - Bullish OB: strong bullish candle after bearish candle
      → Return OrderBlock(type='bullish', top=prev.high, bottom=prev.low, timestamp=prev.timestamp)
    - Bearish OB: strong bearish candle after bullish candle
      → Return OrderBlock(type='bearish', top=prev.high, bottom=prev.low, timestamp=prev.timestamp)

FVG Detection:
- detect_fvg(candles: list, config: dict) -> Optional[FVG]
- Logic:
  * Require minimum 3 candles
  * Check last 3 candles (c1, c2, c3)
  * Bullish FVG: c1.high < c3.low (gap between first and third candle)
    → Return FVG(type='bullish', top=c3.low, bottom=c1.high, timestamp=c2.timestamp)
  * Bearish FVG: c1.low > c3.high
    → Return FVG(type='bearish', top=c1.low, bottom=c3.high, timestamp=c2.timestamp)
  * Validate gap size >= min_gap_percent (default 0.1%)

- Use config parameters from config.yaml
- Return None if patterns not detected
- Add helper functions for candle body/wick calculations

**Test Strategy:**

Unit tests with synthetic candle data covering edge cases: strong bullish/bearish candles, FVG gaps, invalid patterns (insufficient candles, small gaps, weak candles). Verify OB detection requires 70%+ body ratio. Confirm FVG only triggers on valid gaps. Test with real historical data from Binance.

## Subtasks

### 5.1. Create helper functions for candle body/wick calculations

**Status:** done  
**Dependencies:** None  

Implement utility functions to calculate candle body ratio, wick sizes, and validate candle strength for pattern detection

**Details:**

Create src/strategy/patterns.py with helper functions:
- calculate_body_ratio(candle: dict) -> float: Calculate abs(close - open) / (high - low), handle zero division by returning 0.0
- is_bullish_candle(candle: dict) -> bool: Return True if close > open
- is_bearish_candle(candle: dict) -> bool: Return True if close < open
- get_candle_body_size(candle: dict) -> float: Return abs(close - open)
- validate_candle_data(candle: dict) -> bool: Verify candle has required OHLC fields and high >= low

Each function should handle edge cases like missing fields, invalid values, and zero-range candles. Add type hints and docstrings.

### 5.2. REPURPOSED: Create comprehensive unit tests for Order Block detection

**Status:** pending  
**Dependencies:** 5.1  

Create unit tests for _detect_order_block() method in pattern_processor.py to verify Order Block detection logic with various candle patterns and edge cases

**Details:**

Create tests/unit/processors/test_pattern_processor.py (Order Block section):

Test _detect_order_block() method:
- test_detect_bullish_order_block: Strong bullish candle (body_ratio > 60%) triggers detection
- test_detect_bearish_order_block: Strong bearish candle (body_ratio > 60%) triggers detection
- test_order_block_zero_range_candle: Candle with high=low returns None (no detection)
- test_order_block_weak_body_ratio: Candle with body_ratio < 60% returns None
- test_order_block_boundary_conditions: Test exactly 60% body ratio (edge case)
- test_order_block_extreme_body_ratio: Test 100% body ratio (full body candle)
- test_order_block_event_emission: Verify ORDER_BLOCK_DETECTED event is published with correct data
- test_order_block_model_creation: Verify OrderBlock dataclass fields (type, top, bottom, timestamp, touches, is_valid)

Use pytest with mock EventBus to verify event publishing. Test with synthetic candle dictionaries containing OHLC data.

REASON FOR REPURPOSE: Original task duplicated existing pattern_processor.py implementation (lines 206-275). Tests are critical as the existing implementation has NO test coverage.

### 5.3. REPURPOSED: Create comprehensive unit tests for FVG detection

**Status:** pending  
**Dependencies:** 5.1  

Create unit tests for _detect_fvg() method in pattern_processor.py to verify Fair Value Gap detection with 3-candle sequences and gap validation

**Details:**

Create tests/unit/processors/test_pattern_processor.py (FVG section):

Test _detect_fvg() method:
- test_detect_bullish_fvg: Candles with c1.high < c3.low and gap >= 0.3% triggers detection
- test_detect_bearish_fvg: Candles with c1.low > c3.high and gap >= 0.3% triggers detection
- test_fvg_insufficient_candles: Less than 3 candles returns None
- test_fvg_small_gap: Gap size below 0.3% threshold returns None
- test_fvg_no_gap: Overlapping candles (c1.high >= c3.low) returns None
- test_fvg_gap_calculation: Verify gap_percent calculation accuracy
- test_fvg_event_emission: Verify FVG_DETECTED event is published with correct data
- test_fvg_model_creation: Verify FVG dataclass fields (type, top, bottom, timestamp, filled_percent, is_valid)

Implement realistic 3-candle sequences with known gap sizes. Mock EventBus to capture FVG_DETECTED events.

REASON FOR REPURPOSE: Original task duplicated existing pattern_processor.py implementation (lines 277-340). Tests are critical as the existing implementation has NO test coverage.

### 5.4. REPURPOSED: Create unit tests for PatternProcessor lifecycle and configuration

**Status:** pending  
**Dependencies:** None  

Create unit tests for PatternProcessor state management, configuration handling, pattern cleanup, and memory management in pattern_processor.py

**Details:**

Create tests/unit/processors/test_pattern_processor.py (Lifecycle/Config section):

Test _on_start() and _on_stop() lifecycle:
- test_on_start_initializes_state: Verify _candle_history, _detected_order_blocks, _detected_fvgs, _candle_count initialized
- test_on_stop_cleans_state: Verify all collections cleared
- test_multiple_start_stop_cycles: State properly reset between restarts

Test configuration handling:
- test_default_config_values: Verify default min_order_block_body_ratio=0.6, min_fvg_gap_percent=0.3, etc.
- test_custom_config_override: Pass custom config, verify used in detection
- test_partial_config_merge: Custom values override defaults, missing use defaults
- test_invalid_config_handling: Negative values, out-of-range thresholds handled gracefully

Test _cleanup_old_patterns():
- test_cleanup_removes_old_patterns: Patterns older than TTL removed
- test_cleanup_preserves_recent_patterns: Recent patterns retained
- test_cleanup_handles_empty_lists: No errors when no patterns exist
- test_cleanup_ttl_boundary: Patterns exactly at TTL edge case

Test memory management:
- test_candle_history_maxlen: Deque respects max_candle_history limit
- test_pattern_count_properties: order_block_count, fvg_count, candle_count accurate

REASON FOR REPURPOSE: Original task duplicated existing pattern_processor.py config handling. This addresses critical gap of ZERO test coverage for 464 lines of production code.

### 5.5. REPURPOSED: Create integration tests for pattern detection pipeline

**Status:** pending  
**Dependencies:** 5.2, 5.3, 5.4  

Create end-to-end integration tests for the complete pattern detection pipeline from CANDLE_CLOSED events through pattern detection to event emission

**Details:**

Create tests/integration/test_pattern_pipeline.py for end-to-end testing:

Test complete event-driven flow:
- test_candle_to_order_block_pipeline: CANDLE_CLOSED event → _detect_order_block → ORDER_BLOCK_DETECTED event
- test_candle_to_fvg_pipeline: 3 CANDLE_CLOSED events → _detect_fvg → FVG_DETECTED event
- test_concurrent_pattern_detection: Single candle triggers both OB and FVG detection
- test_event_data_integrity: Verify event data contains all required fields (type, top, bottom, timestamp)

Test multi-candle sequences:
- test_realistic_bullish_sequence: 10 bullish candles, verify OB/FVG detected appropriately
- test_realistic_bearish_sequence: 10 bearish candles, verify OB/FVG detected appropriately
- test_mixed_market_conditions: Alternating bull/bear, consolidation periods
- test_state_persistence: Pattern detection maintains state across multiple candles

Test EventBus integration:
- test_event_subscription: Verify processor registers for CANDLE_CLOSED
- test_event_publishing: Mock EventBus.publish, verify pattern events emitted
- test_event_unsubscription: Verify cleanup on processor stop

Test pattern storage:
- test_detected_patterns_stored: Verify patterns added to _detected_order_blocks/_detected_fvgs
- test_pattern_metadata: Verify detected_at_candle tracking

Use pytest-asyncio for async tests. Create realistic candle fixtures simulating market conditions.

REASON FOR REPURPOSE: Original task was unit tests for already-tested patterns.py. This addresses integration testing gap for event-driven architecture.

### 5.6. REPURPOSED: Add Binance Testnet real data validation tests

**Status:** pending  
**Dependencies:** 5.2, 5.3, 5.4, 5.5  

Test pattern detection with actual Binance Testnet WebSocket data to verify production-like scenarios and performance

**Details:**

Create tests/integration/test_binance_patterns.py for real data validation:

Test with real Binance Testnet data:
- test_real_websocket_candles: Connect to Binance Testnet WebSocket, receive 20 real CANDLE_CLOSED events
- test_pattern_detection_with_real_data: Process real candles through PatternProcessor, verify no crashes
- test_real_order_block_detection: Validate OB detection on actual market conditions
- test_real_fvg_detection: Validate FVG detection on actual market conditions

Test data structure compatibility:
- test_binance_candle_format: Verify Binance candle format matches expected structure
- test_field_type_conversions: Confirm string/float conversions work correctly
- test_timestamp_handling: Validate Binance timestamp format compatibility

Performance benchmarks:
- test_detection_latency: Measure pattern detection time per candle (target <10ms)
- test_memory_usage: Monitor memory growth over 100 candles (should be stable)
- test_event_throughput: Verify system handles rapid candle events (>10 candles/sec)

Multi-symbol validation:
- test_btcusdt_patterns: Verify patterns on BTCUSDT (high volatility)
- test_ethusdt_patterns: Verify patterns on ETHUSDT (medium volatility)
- test_cross_symbol_consistency: Pattern behavior consistent across symbols

Real scenario tests:
- test_consolidation_period: Low volatility, few patterns expected
- test_breakout_period: High volatility, multiple patterns expected
- test_trending_market: Sustained direction, OB patterns expected

Use pytest-asyncio. Requires Binance Testnet connection (already configured in Task 4.7).

REASON FOR REPURPOSE: Original task focused on patterns.py validation. This provides critical production-readiness validation for pattern_processor.py with real market data.
