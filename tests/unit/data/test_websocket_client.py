"""
Unit tests for Binance WebSocket Client

Tests cover:
- Initialization with valid and invalid parameters
- Configuration loading (testnet/mainnet)
- Credential loading from environment variables
- AsyncClient creation with correct testnet flag
- BinanceSocketManager initialization
- Error handling for missing credentials
- Connection lifecycle management
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, mock_open
from pathlib import Path
import os

from src.data.websocket_client import (
    BinanceWebSocket,
    WebSocketCredentialError,
    WebSocketConfigError
)
from src.core.event_bus import EventBus


class TestBinanceWebSocketInitialization:
    """Test WebSocket client initialization."""

    def test_init_with_valid_params(self):
        """Test initialization with valid parameters."""
        event_bus = EventBus()
        ws = BinanceWebSocket(event_bus, "BTCUSDT", "15m")

        assert ws.event_bus is event_bus
        assert ws.symbol == "BTCUSDT"
        assert ws.interval == "15m"
        assert ws.client is None
        assert ws.bsm is None
        assert not ws.is_connected

    def test_init_normalizes_symbol_and_interval(self):
        """Test that symbol is uppercased and interval is lowercased."""
        event_bus = EventBus()
        ws = BinanceWebSocket(event_bus, "btcusdt", "15M")

        assert ws.symbol == "BTCUSDT"
        assert ws.interval == "15m"

    def test_init_with_custom_config_path(self):
        """Test initialization with custom config path."""
        event_bus = EventBus()
        custom_path = "/custom/path/config.yaml"
        ws = BinanceWebSocket(event_bus, "BTCUSDT", "15m", config_path=custom_path)

        assert ws.config_path == Path(custom_path)

    def test_init_with_invalid_event_bus(self):
        """Test initialization fails with invalid event_bus type."""
        with pytest.raises(TypeError, match="event_bus must be EventBus instance"):
            BinanceWebSocket("not_an_event_bus", "BTCUSDT", "15m")

    def test_init_with_empty_symbol(self):
        """Test initialization fails with empty symbol."""
        event_bus = EventBus()
        with pytest.raises(ValueError, match="symbol must be non-empty string"):
            BinanceWebSocket(event_bus, "", "15m")

    def test_init_with_empty_interval(self):
        """Test initialization fails with empty interval."""
        event_bus = EventBus()
        with pytest.raises(ValueError, match="interval must be non-empty string"):
            BinanceWebSocket(event_bus, "BTCUSDT", "")


class TestConfigurationLoading:
    """Test configuration file loading."""

    @pytest.fixture
    def ws(self):
        """Create WebSocket instance for testing."""
        event_bus = EventBus()
        return BinanceWebSocket(event_bus, "BTCUSDT", "15m")

    def test_load_config_testnet_true(self, ws):
        """Test loading config with testnet=true."""
        config_content = "use_testnet: true\nsymbol: BTCUSDT\ninterval: 15m"

        with patch("builtins.open", mock_open(read_data=config_content)):
            with patch.object(Path, "exists", return_value=True):
                config = ws._load_config()

        assert config["use_testnet"] is True

    def test_load_config_testnet_false(self, ws):
        """Test loading config with testnet=false."""
        config_content = "use_testnet: false\nsymbol: BTCUSDT\ninterval: 15m"

        with patch("builtins.open", mock_open(read_data=config_content)):
            with patch.object(Path, "exists", return_value=True):
                config = ws._load_config()

        assert config["use_testnet"] is False

    def test_load_config_file_not_found(self, ws):
        """Test error when config file doesn't exist."""
        with patch.object(Path, "exists", return_value=False):
            with pytest.raises(WebSocketConfigError, match="Configuration file not found"):
                ws._load_config()

    def test_load_config_empty_file(self, ws):
        """Test error when config file is empty."""
        with patch("builtins.open", mock_open(read_data="")):
            with patch.object(Path, "exists", return_value=True):
                with pytest.raises(WebSocketConfigError, match="Configuration file is empty"):
                    ws._load_config()

    def test_load_config_invalid_yaml(self, ws):
        """Test error when config file has invalid YAML."""
        # Create truly invalid YAML that will fail parsing
        invalid_yaml = "use_testnet: [\n  unclosed bracket"

        with patch("builtins.open", mock_open(read_data=invalid_yaml)):
            with patch.object(Path, "exists", return_value=True):
                with pytest.raises(WebSocketConfigError, match="Failed to parse configuration"):
                    ws._load_config()


class TestCredentialLoading:
    """Test credential loading from environment variables."""

    @pytest.fixture
    def ws(self):
        """Create WebSocket instance for testing."""
        event_bus = EventBus()
        return BinanceWebSocket(event_bus, "BTCUSDT", "15m")

    def test_load_testnet_credentials(self, ws, monkeypatch):
        """Test loading testnet credentials from environment."""
        monkeypatch.setenv("BINANCE_TESTNET_API_KEY", "test_key_123")
        monkeypatch.setenv("BINANCE_TESTNET_API_SECRET", "test_secret_456")

        api_key, api_secret = ws._load_credentials(use_testnet=True)

        assert api_key == "test_key_123"
        assert api_secret == "test_secret_456"

    def test_load_mainnet_credentials(self, ws, monkeypatch):
        """Test loading mainnet credentials from environment."""
        monkeypatch.setenv("BINANCE_MAINNET_API_KEY", "main_key_789")
        monkeypatch.setenv("BINANCE_MAINNET_API_SECRET", "main_secret_012")

        api_key, api_secret = ws._load_credentials(use_testnet=False)

        assert api_key == "main_key_789"
        assert api_secret == "main_secret_012"

    def test_load_credentials_missing_api_key(self, ws, monkeypatch):
        """Test error when API key is missing."""
        monkeypatch.setenv("BINANCE_TESTNET_API_SECRET", "test_secret")
        monkeypatch.delenv("BINANCE_TESTNET_API_KEY", raising=False)

        with pytest.raises(
            WebSocketCredentialError,
            match="Missing required testnet credentials: BINANCE_TESTNET_API_KEY"
        ):
            ws._load_credentials(use_testnet=True)

    def test_load_credentials_missing_api_secret(self, ws, monkeypatch):
        """Test error when API secret is missing."""
        monkeypatch.setenv("BINANCE_TESTNET_API_KEY", "test_key")
        monkeypatch.delenv("BINANCE_TESTNET_API_SECRET", raising=False)

        with pytest.raises(
            WebSocketCredentialError,
            match="Missing required testnet credentials: BINANCE_TESTNET_API_SECRET"
        ):
            ws._load_credentials(use_testnet=True)

    def test_load_credentials_missing_both(self, ws, monkeypatch):
        """Test error when both credentials are missing."""
        monkeypatch.delenv("BINANCE_MAINNET_API_KEY", raising=False)
        monkeypatch.delenv("BINANCE_MAINNET_API_SECRET", raising=False)

        with pytest.raises(
            WebSocketCredentialError,
            match="Missing required mainnet credentials: BINANCE_MAINNET_API_KEY, BINANCE_MAINNET_API_SECRET"
        ):
            ws._load_credentials(use_testnet=False)

    def test_load_credentials_placeholder_api_key(self, ws, monkeypatch):
        """Test error when API key is placeholder value."""
        monkeypatch.setenv("BINANCE_TESTNET_API_KEY", "your_api_key_here")
        monkeypatch.setenv("BINANCE_TESTNET_API_SECRET", "valid_secret")

        with pytest.raises(
            WebSocketCredentialError,
            match="BINANCE_TESTNET_API_KEY appears to be a placeholder value"
        ):
            ws._load_credentials(use_testnet=True)

    def test_load_credentials_placeholder_api_secret(self, ws, monkeypatch):
        """Test error when API secret is placeholder value."""
        monkeypatch.setenv("BINANCE_TESTNET_API_KEY", "valid_key")
        monkeypatch.setenv("BINANCE_TESTNET_API_SECRET", "your_secret_here")

        with pytest.raises(
            WebSocketCredentialError,
            match="BINANCE_TESTNET_API_SECRET appears to be a placeholder value"
        ):
            ws._load_credentials(use_testnet=True)


class TestConnectionLifecycle:
    """Test WebSocket connection and disconnection."""

    @pytest.fixture
    def ws(self):
        """Create WebSocket instance for testing."""
        event_bus = EventBus()
        return BinanceWebSocket(event_bus, "BTCUSDT", "15m")

    @pytest.mark.asyncio
    async def test_connect_testnet_success(self, ws, monkeypatch):
        """Test successful connection to testnet."""
        # Mock configuration
        config_content = "use_testnet: true\nsymbol: BTCUSDT"
        monkeypatch.setenv("BINANCE_TESTNET_API_KEY", "test_key")
        monkeypatch.setenv("BINANCE_TESTNET_API_SECRET", "test_secret")

        # Mock AsyncClient
        mock_client = AsyncMock()
        mock_bsm = Mock()

        with patch("builtins.open", mock_open(read_data=config_content)):
            with patch.object(Path, "exists", return_value=True):
                with patch("src.data.websocket_client.AsyncClient.create", return_value=mock_client):
                    with patch("src.data.websocket_client.BinanceSocketManager", return_value=mock_bsm):
                        await ws.connect()

        # Verify connection state
        assert ws.is_connected
        assert ws.client is mock_client
        assert ws.bsm is mock_bsm
        assert ws.is_testnet is True

    @pytest.mark.asyncio
    async def test_connect_mainnet_success(self, ws, monkeypatch):
        """Test successful connection to mainnet."""
        # Mock configuration
        config_content = "use_testnet: false\nsymbol: BTCUSDT"
        monkeypatch.setenv("BINANCE_MAINNET_API_KEY", "main_key")
        monkeypatch.setenv("BINANCE_MAINNET_API_SECRET", "main_secret")

        # Mock AsyncClient
        mock_client = AsyncMock()
        mock_bsm = Mock()

        with patch("builtins.open", mock_open(read_data=config_content)):
            with patch.object(Path, "exists", return_value=True):
                with patch("src.data.websocket_client.AsyncClient.create", return_value=mock_client):
                    with patch("src.data.websocket_client.BinanceSocketManager", return_value=mock_bsm):
                        await ws.connect()

        # Verify connection state
        assert ws.is_connected
        assert ws.is_testnet is False

    @pytest.mark.asyncio
    async def test_connect_missing_use_testnet_flag(self, ws, monkeypatch):
        """Test error when use_testnet flag is missing from config."""
        config_content = "symbol: BTCUSDT\ninterval: 15m"

        with patch("builtins.open", mock_open(read_data=config_content)):
            with patch.object(Path, "exists", return_value=True):
                with pytest.raises(
                    WebSocketConfigError,
                    match="Missing 'use_testnet' flag in configuration"
                ):
                    await ws.connect()

    @pytest.mark.asyncio
    async def test_connect_invalid_use_testnet_type(self, ws):
        """Test error when use_testnet flag has wrong type."""
        config_content = "use_testnet: 'yes'\nsymbol: BTCUSDT"

        with patch("builtins.open", mock_open(read_data=config_content)):
            with patch.object(Path, "exists", return_value=True):
                with pytest.raises(
                    WebSocketConfigError,
                    match="'use_testnet' must be boolean"
                ):
                    await ws.connect()

    @pytest.mark.asyncio
    async def test_disconnect(self, ws):
        """Test disconnection cleanup."""
        # Setup mock client
        mock_client = AsyncMock()
        ws.client = mock_client
        ws.bsm = Mock()

        await ws.disconnect()

        # Verify cleanup
        mock_client.close_connection.assert_called_once()
        assert ws.client is None
        assert ws.bsm is None
        assert not ws.is_connected

    @pytest.mark.asyncio
    async def test_disconnect_when_not_connected(self, ws):
        """Test that disconnect is safe when not connected."""
        # Should not raise exception
        await ws.disconnect()
        assert not ws.is_connected


class TestWebSocketProperties:
    """Test WebSocket client properties."""

    def test_is_connected_false_when_not_connected(self):
        """Test is_connected returns False initially."""
        event_bus = EventBus()
        ws = BinanceWebSocket(event_bus, "BTCUSDT", "15m")

        assert not ws.is_connected

    def test_is_connected_true_when_connected(self):
        """Test is_connected returns True after connection."""
        event_bus = EventBus()
        ws = BinanceWebSocket(event_bus, "BTCUSDT", "15m")

        # Mock connection
        ws.client = Mock()
        ws.bsm = Mock()

        assert ws.is_connected

    def test_is_testnet_none_initially(self):
        """Test is_testnet is None before connection."""
        event_bus = EventBus()
        ws = BinanceWebSocket(event_bus, "BTCUSDT", "15m")

        assert ws.is_testnet is None

    def test_is_testnet_after_connection(self):
        """Test is_testnet reflects connection type."""
        event_bus = EventBus()
        ws = BinanceWebSocket(event_bus, "BTCUSDT", "15m")

        ws._is_testnet = True
        assert ws.is_testnet is True

        ws._is_testnet = False
        assert ws.is_testnet is False

    def test_repr_disconnected(self):
        """Test string representation when disconnected."""
        event_bus = EventBus()
        ws = BinanceWebSocket(event_bus, "BTCUSDT", "15m")

        repr_str = repr(ws)
        assert "BTCUSDT" in repr_str
        assert "15m" in repr_str
        assert "disconnected" in repr_str

    def test_repr_connected_testnet(self):
        """Test string representation when connected to testnet."""
        event_bus = EventBus()
        ws = BinanceWebSocket(event_bus, "BTCUSDT", "15m")
        ws.client = Mock()
        ws.bsm = Mock()
        ws._is_testnet = True

        repr_str = repr(ws)
        assert "connected" in repr_str
        assert "testnet" in repr_str


class TestExponentialBackoff:
    """Test exponential backoff calculation for reconnection logic."""

    def test_backoff_first_attempt(self):
        """Test backoff delay for first retry attempt (attempt=0)."""
        event_bus = EventBus()
        ws = BinanceWebSocket(event_bus, "BTCUSDT", "15m")

        delay = ws._calculate_backoff(attempt=0)
        assert delay == 1.0  # initial_delay * (2^0) = 1.0

    def test_backoff_second_attempt(self):
        """Test backoff delay for second retry attempt (attempt=1)."""
        event_bus = EventBus()
        ws = BinanceWebSocket(event_bus, "BTCUSDT", "15m")

        delay = ws._calculate_backoff(attempt=1)
        assert delay == 2.0  # initial_delay * (2^1) = 2.0

    def test_backoff_third_attempt(self):
        """Test backoff delay for third retry attempt (attempt=2)."""
        event_bus = EventBus()
        ws = BinanceWebSocket(event_bus, "BTCUSDT", "15m")

        delay = ws._calculate_backoff(attempt=2)
        assert delay == 4.0  # initial_delay * (2^2) = 4.0

    def test_backoff_fourth_attempt(self):
        """Test backoff delay for fourth retry attempt (attempt=3)."""
        event_bus = EventBus()
        ws = BinanceWebSocket(event_bus, "BTCUSDT", "15m")

        delay = ws._calculate_backoff(attempt=3)
        assert delay == 8.0  # initial_delay * (2^3) = 8.0

    def test_backoff_max_delay_cap(self):
        """Test that backoff delay is capped at max_delay."""
        event_bus = EventBus()
        ws = BinanceWebSocket(event_bus, "BTCUSDT", "15m")

        # Attempt 10: 1 * (2^10) = 1024, but should be capped at 60
        delay = ws._calculate_backoff(attempt=10)
        assert delay == 60.0

    def test_backoff_with_custom_initial_delay(self):
        """Test backoff with custom initial delay."""
        event_bus = EventBus()
        ws = BinanceWebSocket(event_bus, "BTCUSDT", "15m")

        delay = ws._calculate_backoff(attempt=2, initial_delay=0.5)
        assert delay == 2.0  # 0.5 * (2^2) = 2.0

    def test_backoff_with_custom_max_delay(self):
        """Test backoff with custom max delay."""
        event_bus = EventBus()
        ws = BinanceWebSocket(event_bus, "BTCUSDT", "15m")

        delay = ws._calculate_backoff(attempt=10, max_delay=30.0)
        assert delay == 30.0  # Capped at custom max

    def test_backoff_with_custom_multiplier(self):
        """Test backoff with custom multiplier."""
        event_bus = EventBus()
        ws = BinanceWebSocket(event_bus, "BTCUSDT", "15m")

        delay = ws._calculate_backoff(attempt=2, multiplier=3.0)
        assert delay == 9.0  # 1.0 * (3^2) = 9.0

    def test_backoff_exponential_progression(self):
        """Test that backoff follows exponential progression up to cap."""
        event_bus = EventBus()
        ws = BinanceWebSocket(event_bus, "BTCUSDT", "15m")

        expected_delays = [1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 60.0, 60.0, 60.0, 60.0]

        for attempt, expected in enumerate(expected_delays):
            delay = ws._calculate_backoff(attempt)
            assert delay == expected, f"Attempt {attempt}: expected {expected}, got {delay}"


class TestKlineStreaming:
    """Test kline data streaming functionality."""

    @pytest.fixture
    def ws(self):
        """Create WebSocket instance for testing."""
        event_bus = EventBus()
        ws = BinanceWebSocket(event_bus, "BTCUSDT", "1m")
        # Mock connection
        ws.client = AsyncMock()
        ws.bsm = Mock()
        return ws

    @pytest.mark.asyncio
    async def test_start_kline_stream_not_connected(self):
        """Test that start_kline_stream fails if not connected."""
        event_bus = EventBus()
        ws = BinanceWebSocket(event_bus, "BTCUSDT", "1m")
        # Don't set client/bsm - ws is not connected

        with pytest.raises(RuntimeError, match="WebSocket is not connected"):
            await ws.start_kline_stream()

    @pytest.mark.asyncio
    async def test_handle_kline_closed_candle(self, ws):
        """Test processing a closed kline message."""
        # Start event bus for async publishing
        await ws.event_bus.start()

        # Track emitted events
        emitted_events = []

        async def capture_event(event):
            emitted_events.append(event)

        from src.core.event_bus import EventType
        ws.event_bus.subscribe(EventType.CANDLE_CLOSED, capture_event)

        # Create closed kline message
        kline_msg = {
            'e': 'kline',
            'E': 1234567890000,
            'k': {
                't': 1234567860000,  # Start time
                'T': 1234567920000,  # Close time
                'o': '45000.00',
                'h': '45100.00',
                'l': '44900.00',
                'c': '45050.00',
                'v': '100.5',
                'x': True  # Closed candle
            }
        }

        # Process the message
        await ws._handle_kline(kline_msg)

        # Give event bus time to process
        import asyncio
        await asyncio.sleep(0.1)

        # Stop event bus
        await ws.event_bus.stop()

        # Verify event was emitted
        assert len(emitted_events) == 1
        event = emitted_events[0]

        assert event.event_type == EventType.CANDLE_CLOSED
        assert event.data['symbol'] == 'BTCUSDT'
        assert event.data['interval'] == '1m'
        assert event.data['open'] == 45000.0
        assert event.data['high'] == 45100.0
        assert event.data['low'] == 44900.0
        assert event.data['close'] == 45050.0
        assert event.data['volume'] == 100.5

    @pytest.mark.asyncio
    async def test_handle_kline_open_candle_ignored(self, ws):
        """Test that open (not closed) klines are ignored."""
        # Start event bus
        await ws.event_bus.start()

        # Track emitted events
        emitted_events = []

        async def capture_event(event):
            emitted_events.append(event)

        from src.core.event_bus import EventType
        ws.event_bus.subscribe(EventType.CANDLE_CLOSED, capture_event)

        # Create open kline message (x=False)
        kline_msg = {
            'e': 'kline',
            'k': {
                'o': '45000.00',
                'h': '45100.00',
                'l': '44900.00',
                'c': '45050.00',
                'v': '100.5',
                'x': False  # Open candle - should be ignored
            }
        }

        # Process the message
        await ws._handle_kline(kline_msg)

        # Give event bus time to process
        import asyncio
        await asyncio.sleep(0.1)

        # Stop event bus
        await ws.event_bus.stop()

        # Verify no event was emitted
        assert len(emitted_events) == 0

    @pytest.mark.asyncio
    async def test_handle_kline_malformed_message(self, ws):
        """Test that malformed kline messages are handled gracefully."""
        # Start event bus
        await ws.event_bus.start()

        # Malformed message (missing 'k' field)
        malformed_msg = {'e': 'kline'}

        # Should not raise exception
        await ws._handle_kline(malformed_msg)

        # Give event bus time to process
        import asyncio
        await asyncio.sleep(0.1)

        await ws.event_bus.stop()

    @pytest.mark.asyncio
    async def test_handle_kline_invalid_price_data(self, ws):
        """Test handling of invalid price data in kline message."""
        # Start event bus
        await ws.event_bus.start()

        # Track emitted events
        emitted_events = []

        async def capture_event(event):
            emitted_events.append(event)

        from src.core.event_bus import EventType
        ws.event_bus.subscribe(EventType.CANDLE_CLOSED, capture_event)

        # Message with invalid price data
        kline_msg = {
            'e': 'kline',
            'k': {
                'o': 'invalid',  # Invalid price string
                'h': '45100.00',
                'l': '44900.00',
                'c': '45050.00',
                'v': '100.5',
                'x': True
            }
        }

        # Should handle error gracefully without crashing
        await ws._handle_kline(kline_msg)

        # Give event bus time to process
        import asyncio
        await asyncio.sleep(0.1)

        await ws.event_bus.stop()

        # Event should not be emitted due to error
        assert len(emitted_events) == 0

    @pytest.mark.asyncio
    async def test_start_kline_stream_with_reconnection_on_binance_api_exception(self, ws):
        """Test reconnection on BinanceAPIException with exponential backoff."""
        from binance.exceptions import BinanceAPIException
        import asyncio

        # Create mock response for BinanceAPIException
        mock_response = Mock()
        mock_response.text = "Connection lost"

        # Track which attempt we're on
        attempt_count = [0]

        # Track actual sleep delays from the retry loop (not our test delays)
        actual_delays = []
        original_sleep = asyncio.sleep

        async def mock_sleep(delay):
            actual_delays.append(delay)
            # Don't actually sleep in test

        # Create a factory that returns a new stream for each attempt
        def create_mock_stream():
            mock_stream = AsyncMock()
            current_attempt = attempt_count[0]
            attempt_count[0] += 1

            # First attempt fails, second succeeds
            if current_attempt == 0:
                mock_stream.recv = AsyncMock(side_effect=BinanceAPIException(response=mock_response, status_code=500, text="Connection lost"))
            else:
                # After first failure, stream works normally
                mock_stream.recv = AsyncMock(return_value={'k': {'x': False}})

            return mock_stream

        # Create mock context manager that returns a new stream each time
        def mock_socket(*args, **kwargs):
            mock_cm = AsyncMock()
            mock_cm.__aenter__ = AsyncMock(return_value=create_mock_stream())
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            return mock_cm

        # Mock kline_futures_socket to return the context manager
        ws.bsm.kline_futures_socket = mock_socket

        with patch('asyncio.sleep', mock_sleep):
            # Start stream with limited retries for testing
            task = asyncio.create_task(ws.start_kline_stream(max_retries=3))

            # Let it run briefly (use original sleep)
            await original_sleep(0.1)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Verify exponential backoff was used (first retry delay should be 1.0s)
        assert len(actual_delays) >= 1
        assert actual_delays[0] == 1.0  # First retry: 1 * (2^0) = 1.0

    @pytest.mark.asyncio
    async def test_start_kline_stream_with_max_retries_exhausted(self, ws):
        """Test that max retries are enforced and exception is raised."""
        from binance.exceptions import BinanceAPIException

        # Create mock response for BinanceAPIException
        mock_response = Mock()
        mock_response.text = "Persistent failure"

        # Mock stream that always fails
        mock_stream = AsyncMock()
        mock_stream.recv = AsyncMock(side_effect=BinanceAPIException(response=mock_response, status_code=500, text="Persistent failure"))

        # Create mock context manager
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_cm.__aexit__ = AsyncMock(return_value=None)

        # Mock kline_futures_socket to return the context manager
        ws.bsm.kline_futures_socket = Mock(return_value=mock_cm)

        # Mock sleep to speed up test
        with patch('asyncio.sleep', AsyncMock()):
            # Should raise exception after exhausting retries
            with pytest.raises(BinanceAPIException, match="Persistent failure"):
                await ws.start_kline_stream(max_retries=2)

    @pytest.mark.asyncio
    async def test_start_kline_stream_reconnection_on_timeout(self, ws):
        """Test reconnection on asyncio.TimeoutError."""
        import asyncio

        # Track which attempt we're on
        attempt_count = [0]

        # Track delays from retry loop
        actual_delays = []
        original_sleep = asyncio.sleep

        async def mock_sleep(delay):
            actual_delays.append(delay)

        # Create a factory that returns a new stream for each attempt
        def create_mock_stream():
            mock_stream = AsyncMock()
            current_attempt = attempt_count[0]
            attempt_count[0] += 1

            # First attempt times out, second succeeds
            if current_attempt == 0:
                mock_stream.recv = AsyncMock(side_effect=asyncio.TimeoutError("Connection timeout"))
            else:
                # After first failure, stream works normally
                mock_stream.recv = AsyncMock(return_value={'k': {'x': False}})

            return mock_stream

        # Create mock context manager that returns a new stream each time
        def mock_socket(*args, **kwargs):
            mock_cm = AsyncMock()
            mock_cm.__aenter__ = AsyncMock(return_value=create_mock_stream())
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            return mock_cm

        # Mock kline_futures_socket to return the context manager
        ws.bsm.kline_futures_socket = mock_socket

        with patch('asyncio.sleep', mock_sleep):
            task = asyncio.create_task(ws.start_kline_stream(max_retries=3))
            await original_sleep(0.1)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Verify reconnection attempt was made
        assert len(actual_delays) >= 1
        assert actual_delays[0] == 1.0

    @pytest.mark.asyncio
    async def test_start_kline_stream_reconnection_logging(self, ws, caplog):
        """Test that reconnection attempts are logged at WARNING level."""
        from binance.exceptions import BinanceAPIException
        import logging
        import asyncio

        # Configure caplog to capture WARNING level
        caplog.set_level(logging.WARNING)

        # Create mock response for BinanceAPIException
        mock_response = Mock()
        mock_response.text = "Connection error"

        # Track which attempt we're on
        attempt_count = [0]

        # Create a factory that returns a new stream for each attempt
        def create_mock_stream():
            mock_stream = AsyncMock()
            current_attempt = attempt_count[0]
            attempt_count[0] += 1

            # First attempt fails, second succeeds
            if current_attempt == 0:
                mock_stream.recv = AsyncMock(side_effect=BinanceAPIException(response=mock_response, status_code=500, text="Connection error"))
            else:
                # After first failure, stream works normally
                mock_stream.recv = AsyncMock(return_value={'k': {'x': False}})

            return mock_stream

        # Create mock context manager that returns a new stream each time
        def mock_socket(*args, **kwargs):
            mock_cm = AsyncMock()
            mock_cm.__aenter__ = AsyncMock(return_value=create_mock_stream())
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            return mock_cm

        # Mock kline_futures_socket to return the context manager
        ws.bsm.kline_futures_socket = mock_socket

        original_sleep = asyncio.sleep
        with patch('asyncio.sleep', AsyncMock()):
            task = asyncio.create_task(ws.start_kline_stream(max_retries=3))
            await original_sleep(0.1)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Verify WARNING log for reconnection
        warning_logs = [rec for rec in caplog.records if rec.levelname == 'WARNING']
        assert len(warning_logs) >= 1
        assert "Reconnection attempt" in warning_logs[0].message
        assert "1/3" in warning_logs[0].message  # Should show attempt 1/3

    @pytest.mark.asyncio
    async def test_start_kline_stream_custom_max_retries(self, ws):
        """Test custom max_retries parameter."""
        from binance.exceptions import BinanceAPIException

        # Create mock response for BinanceAPIException
        mock_response = Mock()
        mock_response.text = "Failure"

        # Mock stream that always fails
        mock_stream = AsyncMock()
        mock_stream.recv = AsyncMock(side_effect=BinanceAPIException(response=mock_response, status_code=500, text="Failure"))

        # Create mock context manager
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_cm.__aexit__ = AsyncMock(return_value=None)

        # Mock kline_futures_socket to return the context manager
        ws.bsm.kline_futures_socket = Mock(return_value=mock_cm)

        # Track attempts
        attempts = []
        async def mock_sleep(delay):
            attempts.append(delay)

        with patch('asyncio.sleep', mock_sleep):
            with pytest.raises(BinanceAPIException):
                await ws.start_kline_stream(max_retries=5)

        # Should have made 5 attempts total (0-indexed: 0, 1, 2, 3, 4)
        # Delays occur after failed attempts, so 4 delays for 5 attempts
        assert len(attempts) == 4
