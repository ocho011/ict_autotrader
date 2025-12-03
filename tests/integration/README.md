# Integration Tests - Binance Testnet

This directory contains comprehensive integration tests for the BinanceWebSocket client with real Binance testnet connectivity.

## Prerequisites

### 1. Binance Testnet Account

Create a free Binance testnet account and obtain API credentials:

1. Visit [Binance Testnet](https://testnet.binancefuture.com/)
2. Create an account or login
3. Navigate to API Management
4. Create a new API key pair
5. Save your API Key and Secret Key securely

### 2. Environment Configuration

Create a `.env` file in the project root with your testnet credentials:

```bash
# Binance Testnet Credentials
BINANCE_TESTNET_API_KEY=your_actual_testnet_api_key_here
BINANCE_TESTNET_API_SECRET=your_actual_testnet_api_secret_here
```

**Security Note**: Never commit `.env` file to version control. It's included in `.gitignore`.

### 3. Config File

Ensure `config.yaml` in project root has testnet enabled:

```yaml
use_testnet: true
```

### 4. Dependencies

Install all required dependencies:

```bash
pip install -r requirements-dev.txt
```

## Running Integration Tests

### Run All Integration Tests

```bash
# Run all integration tests (will take 10-20 minutes)
pytest tests/integration/test_binance_testnet_integration.py -v

# Run with live output
pytest tests/integration/test_binance_testnet_integration.py -v -s
```

### Run Specific Test Classes

```bash
# Test initialization only
pytest tests/integration/test_binance_testnet_integration.py::TestBinanceTestnetInitialization -v

# Test candle events only
pytest tests/integration/test_binance_testnet_integration.py::TestCandleClosedEventFlow -v

# Test reconnection logic
pytest tests/integration/test_binance_testnet_integration.py::TestReconnectionLogic -v

# Test shutdown
pytest tests/integration/test_binance_testnet_integration.py::TestGracefulShutdown -v

# Test multi-interval
pytest tests/integration/test_binance_testnet_integration.py::TestMultiIntervalSupport -v
```

### Run Individual Tests

```bash
# Test WebSocket initialization
pytest tests/integration/test_binance_testnet_integration.py::TestBinanceTestnetInitialization::test_websocket_initialization_with_eventbus -v

# Test connection to testnet
pytest tests/integration/test_binance_testnet_integration.py::TestBinanceTestnetInitialization::test_websocket_connects_to_testnet -v

# Test candle event publishing
pytest tests/integration/test_binance_testnet_integration.py::TestCandleClosedEventFlow::test_candle_closed_events_published -v

# Test event data validation
pytest tests/integration/test_binance_testnet_integration.py::TestCandleClosedEventFlow::test_event_data_structure_validation -v
```

## Test Coverage

### TestBinanceTestnetInitialization
- ✅ WebSocket initialization with EventBus
- ✅ Connection to Binance testnet
- ✅ Testnet mode detection from config
- ✅ Client and SocketManager initialization

### TestCandleClosedEventFlow
- ✅ CANDLE_CLOSED event publishing on candle close
- ✅ Event data structure validation (all OHLCV fields)
- ✅ Event data type validation
- ✅ OHLCV relationship validation (high >= close, etc.)
- ✅ Symbol and interval verification

### TestReconnectionLogic
- ✅ Exponential backoff calculation verification
- ✅ Reconnection attempt configuration
- ✅ Network resilience (note: full simulation in unit tests)

### TestGracefulShutdown
- ✅ Graceful shutdown during active streaming
- ✅ stop() method functionality
- ✅ Async context manager cleanup
- ✅ Resource release verification
- ✅ Multiple disconnect safety

### TestMultiIntervalSupport
- ✅ 1-minute interval streaming (2-3 min runtime)
- ✅ 5-minute interval streaming (5-6 min runtime)
- ✅ Interval field verification in events

### TestConnectionLifecycleLogging
- ✅ Initialization logging
- ✅ Connection lifecycle logging
- ✅ Stream start/stop logging
- ✅ Shutdown logging

## Test Execution Times

| Test Class | Estimated Runtime | Description |
|------------|------------------|-------------|
| TestBinanceTestnetInitialization | ~10 seconds | Fast connection tests |
| TestCandleClosedEventFlow | 3-6 minutes | Waits for candle events |
| TestReconnectionLogic | ~5 seconds | Calculation verification |
| TestGracefulShutdown | ~30 seconds | Shutdown verification |
| TestMultiIntervalSupport | 8-12 minutes | Both 1m and 5m intervals |
| TestConnectionLifecycleLogging | ~30 seconds | Log verification |

**Total Runtime**: Approximately 10-20 minutes for full test suite

## Interpreting Test Results

### Success Indicators

```bash
tests/integration/test_binance_testnet_integration.py::TestCandleClosedEventFlow::test_candle_closed_events_published PASSED
```

- All events received successfully
- Data structure validated
- OHLCV relationships correct
- Clean shutdown completed

### Common Failures

#### Missing Credentials
```
SKIPPED - Testnet credentials not found
```
**Solution**: Set up `.env` file with valid testnet credentials

#### Connection Timeout
```
FAILED - asyncio.TimeoutError
```
**Solution**: Check internet connection and Binance testnet availability

#### No Events Received
```
AssertionError: Expected at least 1 candle event, got 0
```
**Solution**:
- Verify testnet credentials are valid
- Check config.yaml has `use_testnet: true`
- Ensure BTCUSDT is actively trading on testnet

#### Event Data Validation Failure
```
AssertionError: High should be >= close
```
**Solution**: This indicates data quality issue from testnet - rarely happens

## Continuous Integration

### Running in CI/CD

For CI/CD pipelines, integration tests should be run in a dedicated job with:

```yaml
# Example GitHub Actions job
integration-tests:
  runs-on: ubuntu-latest
  timeout-minutes: 30
  env:
    BINANCE_TESTNET_API_KEY: ${{ secrets.BINANCE_TESTNET_API_KEY }}
    BINANCE_TESTNET_API_SECRET: ${{ secrets.BINANCE_TESTNET_API_SECRET }}
  steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    - name: Install dependencies
      run: pip install -r requirements-dev.txt
    - name: Run integration tests
      run: pytest tests/integration/ -v --timeout=1800
```

### Skip in Quick Builds

To skip integration tests for fast builds:

```bash
# Run only unit tests
pytest tests/unit/ -v

# Skip integration marker
pytest -m "not integration" -v
```

## Troubleshooting

### Issue: Tests Skip Due to Credentials

**Check**:
```bash
# Verify .env file exists
ls -la .env

# Check env variables are loaded
python3 -c "from dotenv import load_dotenv; import os; load_dotenv(); print('Key:', os.getenv('BINANCE_TESTNET_API_KEY')[:10] if os.getenv('BINANCE_TESTNET_API_KEY') else 'Not found')"
```

**Fix**: Create `.env` file with actual testnet credentials

### Issue: Connection Refused

**Check**:
```bash
# Test testnet connectivity
curl -I https://testnet.binancefuture.com/fapi/v1/ping
```

**Fix**: Verify internet connection and testnet availability

### Issue: Slow Test Execution

This is **expected behavior** for integration tests:
- 1m interval needs ~2-3 minutes for 2 candles
- 5m interval needs ~5-6 minutes for 1 candle
- Total suite: 10-20 minutes

**Optimization**: Run specific test classes instead of full suite during development

## Development Workflow

### Quick Validation (30 seconds)
```bash
pytest tests/integration/test_binance_testnet_integration.py::TestBinanceTestnetInitialization -v
```

### Medium Test (~3 minutes)
```bash
pytest tests/integration/test_binance_testnet_integration.py::TestCandleClosedEventFlow::test_candle_closed_events_published -v
```

### Full Validation (10-20 minutes)
```bash
pytest tests/integration/test_binance_testnet_integration.py -v
```

## Success Criteria

All tests should **PASS** before marking task 4.7 as complete:

- [x] WebSocket initializes correctly with EventBus
- [x] Connection to testnet succeeds
- [x] CANDLE_CLOSED events publish on candle close
- [x] Event data structure is complete and valid
- [x] OHLCV data relationships are correct
- [x] Reconnection logic exists and backoff calculates properly
- [x] Graceful shutdown completes without errors
- [x] Resources are properly released
- [x] Both 1m and 5m intervals work correctly
- [x] Connection lifecycle is logged correctly

## Next Steps

After all integration tests pass:

1. Update task 4.7 status to `done`
2. Review logs for any warnings or issues
3. Document any testnet-specific behaviors observed
4. Consider adding performance metrics collection
5. Plan for mainnet migration testing (separate task)

## Support

If integration tests fail repeatedly:

1. Check [Binance Testnet Status](https://testnet.binancefuture.com/)
2. Verify credentials are for **testnet** not mainnet
3. Review WebSocket client logs in `logs/` directory
4. Check GitHub issues for known testnet issues
5. Contact maintainers with error logs
