# Task ID: 7

**Title:** Implement Risk Manager for Position Sizing and Limits

**Status:** pending

**Dependencies:** 1 ✓

**Priority:** high

**Description:** Create RiskManager to calculate position sizes and enforce risk limits (max daily loss, max trades, risk per trade)

**Details:**

Create src/execution/risk_manager.py with:

RiskManager class:
- __init__(config: dict, client: AsyncClient):
  * Store risk config from config.yaml
  * Store Binance client reference
  * Initialize daily_loss: float = 0.0
  * Initialize trade_count: int = 0

- get_account_balance() async -> float:
  * Call client.futures_account_balance()
  * Find USDT balance
  * Return as float

- can_trade() -> bool:
  * Check if daily_loss >= max_daily_loss_percent (default 3%)
  * Check if trade_count >= max_daily_trades (default 5)
  * Return False if limits exceeded, True otherwise
  * Log warnings when limits hit

- calculate_position_size(entry_price: float, stop_loss: float) -> float:
  * Get current balance via get_account_balance()
  * Calculate risk_amount = balance * (risk_per_trade_percent / 100) (default 1%)
  * Calculate price_risk = abs(entry_price - stop_loss)
  * Return 0 if price_risk == 0 (avoid division by zero)
  * Calculate position_size = risk_amount / price_risk
  * Calculate max_size = balance * (max_position_percent / 100) / entry_price (default 10%)
  * Return min(position_size, max_size) rounded to 3 decimals
  * Log position size calculation details

- record_trade_result(pnl: float):
  * Add negative PnL to daily_loss
  * Increment trade_count
  * Log trade result

- reset_daily():
  * Reset daily_loss = 0.0
  * Reset trade_count = 0
  * Log daily reset (call at UTC midnight)

- Use config parameters: risk_per_trade_percent, max_daily_loss_percent, max_position_percent, max_daily_trades

**Test Strategy:**

Unit test position sizing with various entry/SL prices. Verify position size respects both risk and max position limits. Test can_trade() enforcement for daily loss and trade count limits. Mock Binance client for balance queries. Verify rounding to 3 decimals. Test edge cases: zero price risk, insufficient balance, max limits hit.

## Subtasks

### 7.1. Create RiskManager initialization with config and Binance client

**Status:** pending  
**Dependencies:** None  

Set up the RiskManager class constructor to accept configuration and Binance client, initializing daily tracking variables

**Details:**

Create src/execution/risk_manager.py with RiskManager class. Implement __init__(config: dict, client: AsyncClient) that stores risk configuration parameters (risk_per_trade_percent, max_daily_loss_percent, max_position_percent, max_daily_trades) from config dictionary, stores the Binance AsyncClient reference for later API calls, and initializes daily_loss: float = 0.0 and trade_count: int = 0 for tracking daily activity. Add proper type hints and docstrings.

### 7.2. Implement async balance retrieval from Binance API

**Status:** pending  
**Dependencies:** 7.1  

Create the get_account_balance method to asynchronously fetch USDT balance from Binance Futures API

**Details:**

Implement get_account_balance() async -> float method that calls client.futures_account_balance() to retrieve account balance information, filters the response to find the USDT asset entry, extracts the balance value and converts it to float, and handles potential API errors with appropriate logging. Include error handling for network issues, API rate limits, and missing USDT balance.

### 7.3. Implement daily limit checking (can_trade method)

**Status:** pending  
**Dependencies:** 7.1  

Create the can_trade method to enforce daily loss and trade count limits

**Details:**

Implement can_trade() -> bool method that checks if daily_loss has reached or exceeded max_daily_loss_percent threshold (default 3% of account balance), checks if trade_count has reached or exceeded max_daily_trades limit (default 5 trades), returns False if either limit is exceeded (preventing further trading), returns True if trading is allowed, and logs warning messages when limits are hit with details about current values and thresholds.

### 7.4. Create position sizing calculation with risk/max position limits

**Status:** pending  
**Dependencies:** 7.2  

Implement the calculate_position_size method with risk-based and maximum position size constraints

**Details:**

Implement calculate_position_size(entry_price: float, stop_loss: float) -> float that calls get_account_balance() to get current balance, calculates risk_amount = balance * (risk_per_trade_percent / 100) using default 1% risk per trade, calculates price_risk = abs(entry_price - stop_loss) as the price distance to stop loss, returns 0 if price_risk == 0 to avoid division by zero, calculates position_size = risk_amount / price_risk for risk-based sizing, calculates max_size = balance * (max_position_percent / 100) / entry_price using default 10% max position, returns min(position_size, max_size) rounded to 3 decimals to respect both constraints, and logs all intermediate calculation values for debugging.

### 7.5. Add trade result tracking and daily reset logic

**Status:** pending  
**Dependencies:** 7.1  

Implement methods to record trade outcomes and reset daily tracking variables

**Details:**

Implement record_trade_result(pnl: float) method that adds negative PnL values to daily_loss (only tracking losses, not gains), increments trade_count by 1, and logs the trade result with PnL and updated daily totals. Implement reset_daily() method that resets daily_loss to 0.0, resets trade_count to 0, and logs the daily reset event with timestamp (should be called at UTC midnight). Add clear logging for both methods to track daily trading activity.

### 7.6. Create comprehensive unit tests with mocked client and edge cases

**Status:** pending  
**Dependencies:** 7.1, 7.2, 7.3, 7.4, 7.5  

Build complete test suite covering all RiskManager functionality with mocked Binance client and edge case validation

**Details:**

Create tests/execution/test_risk_manager.py with comprehensive test coverage: mock AsyncClient for all Binance API calls, test full position sizing workflow with various entry/SL combinations, verify both risk-based and max position limits are enforced correctly, test can_trade enforcement for both daily loss and trade count limits, test edge cases including zero price risk, division by zero protection, very small/large position sizes, API failures during balance retrieval, missing config parameters, test daily reset functionality, verify all rounding is exactly 3 decimals, test integration between record_trade_result and can_trade limit enforcement, and achieve >90% code coverage.
