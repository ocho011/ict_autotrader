# Task ID: 9

**Title:** Implement Discord Notification System

**Status:** pending

**Dependencies:** 2 ✓

**Priority:** medium

**Description:** Create Discord webhook integration to send real-time notifications for trades, positions, and errors

**Details:**

Create src/notification/discord.py with:

DiscordNotifier class:
- __init__(event_bus, webhook_url):
  * Subscribe to: ORDER_FILLED, POSITION_CLOSED, ERROR events
  * Store Discord webhook URL from .env

- send(content: str, embed: dict = None) async:
  * Prepare payload with content and optional embed
  * Use aiohttp.ClientSession to POST to webhook URL
  * Handle rate limits and errors gracefully

- on_order_filled(event: Event) async:
  * Extract position from event data
  * Create embed:
    - Title: "🟢 포지션 오픈: {side.upper()}"
    - Color: 0x00ff00 (green) for long, 0xff0000 (red) for short
    - Fields:
      * 심볼: position.symbol
      * 진입가: $XX,XXX.XX
      * 수량: X.XXX
      * SL: $XX,XXX.XX
      * TP: $XX,XXX.XX
  * Call send() with embed

- on_position_closed(event: Event) async:
  * Extract PnL and reason from event data
  * Create embed:
    - Title: "🟢 포지션 종료" (green) or "🔴 포지션 종료" (red) based on PnL
    - Color: 0x00ff00 for profit, 0xff0000 for loss
    - Fields:
      * PnL: $±XXX.XX
      * 종료 사유: SL/TP/Manual
  * Call send() with embed

- on_error(event: Event) async:
  * Extract error message from event data
  * Send simple message: "⚠️ **Error**: {error_message}"
  * Include context if available

- Use Korean labels as specified in PRD
- Format currency with commas and 2 decimal places

**Test Strategy:**

Integration test with real Discord webhook. Verify notifications sent for ORDER_FILLED, POSITION_CLOSED, ERROR events. Check embed formatting and colors. Test rate limit handling. Verify Korean text renders correctly. Test with mock events for various scenarios (long/short, profit/loss, errors).

## Subtasks

### 9.1. Set up DiscordNotifier class with webhook URL and event subscriptions

**Status:** pending  
**Dependencies:** None  

Create src/notification/discord.py with DiscordNotifier class that initializes with event_bus and webhook_url, subscribes to ORDER_FILLED, POSITION_CLOSED, and ERROR events from the event bus

**Details:**

Create DiscordNotifier.__init__(event_bus, webhook_url) method that stores the Discord webhook URL from .env configuration and subscribes to three event types: ORDER_FILLED, POSITION_CLOSED, ERROR. Store event_bus reference for publishing/subscribing. Validate webhook_url format. Set up instance variables for webhook URL and event bus reference. Register event handlers: on_order_filled, on_position_closed, on_error with corresponding event types.

### 9.2. Implement base send method with aiohttp and rate limiting

**Status:** pending  
**Dependencies:** 9.1  

Create async send(content, embed) method that posts messages to Discord webhook URL using aiohttp, with proper rate limit handling and error recovery

**Details:**

Implement DiscordNotifier.send(content: str, embed: dict = None) async method. Use aiohttp.ClientSession to POST to webhook URL. Prepare payload with content and optional embed dict. Handle Discord rate limits (429 status) with exponential backoff. Implement retry logic for temporary failures. Handle network errors gracefully with logging. Close aiohttp session properly. Return success/failure status. Log all webhook calls with timestamp and payload size.

### 9.3. Create ORDER_FILLED notification with Korean embed formatting

**Status:** pending  
**Dependencies:** 9.2  

Implement on_order_filled event handler that creates formatted Discord embed with Korean labels for position open notifications

**Details:**

Implement DiscordNotifier.on_order_filled(event: Event) async method. Extract position data from event.data. Create Discord embed with title '🟢 포지션 오픈: {side.upper()}'. Set color to 0x00ff00 (green) for LONG, 0xff0000 (red) for SHORT. Add embed fields with Korean labels: 심볼 (symbol), 진입가 (entry price formatted as $XX,XXX.XX), 수량 (quantity with 3 decimals), SL (stop loss price), TP (take profit price). Format all currency values with commas and 2 decimal places. Call send() method with embed. Handle missing or invalid position data gracefully.

### 9.4. Create POSITION_CLOSED notification with PnL display

**Status:** pending  
**Dependencies:** 9.2  

Implement on_position_closed event handler that creates formatted Discord embed showing profit/loss and close reason with Korean labels

**Details:**

Implement DiscordNotifier.on_position_closed(event: Event) async method. Extract PnL amount and close reason from event.data. Create embed with title '🟢 포지션 종료' (green) for profit (PnL > 0) or '🔴 포지션 종료' (red) for loss (PnL <= 0). Set color to 0x00ff00 for profit, 0xff0000 for loss. Add embed fields: PnL formatted as '$±XXX.XX' with + for profit, - for loss, and 종료 사유 (close reason) showing 'SL', 'TP', or 'Manual'. Format PnL with commas and 2 decimals. Call send() with embed. Handle edge cases like zero PnL.

### 9.5. Add ERROR notification and integration testing with real webhook

**Status:** pending  
**Dependencies:** 9.3, 9.4  

Implement on_error event handler for error notifications and perform integration testing with actual Discord webhook to verify all notification types

**Details:**

Implement DiscordNotifier.on_error(event: Event) async method. Extract error message and optional context from event.data. Send simple text message format: '⚠️ **Error**: {error_message}'. Include context details if available in separate lines. Call send() with content only (no embed). Perform integration testing with real Discord webhook URL from .env. Test all three notification types: ORDER_FILLED (long/short), POSITION_CLOSED (profit/loss with SL/TP/Manual reasons), ERROR (with/without context). Verify Korean text renders correctly in Discord. Test rate limiting with rapid successive messages. Verify embed colors and formatting appear correctly in Discord client.
