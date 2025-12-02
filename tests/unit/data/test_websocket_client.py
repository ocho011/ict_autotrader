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
