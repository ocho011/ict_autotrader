"""
Binance WebSocket Client for Real-Time Market Data

This module provides WebSocket connectivity to Binance for streaming real-time
market data. It handles connection lifecycle, credential management, and event
emission for market data updates.

Security Features:
    - Separate testnet/mainnet credential handling
    - Environment variable-based credential loading
    - Validation of required credentials before connection
    - Secure AsyncClient initialization with proper testnet flag

Architecture:
    - Event-driven design using EventBus for loose coupling
    - Async/await patterns for non-blocking I/O
    - Proper resource cleanup with context manager support
"""

import os
from typing import Optional
from pathlib import Path
import yaml
from loguru import logger
from binance import AsyncClient, BinanceSocketManager

from src.core.event_bus import EventBus


class WebSocketCredentialError(Exception):
    """
    Raised when WebSocket credentials are missing or invalid.

    This exception indicates a configuration error that must be resolved
    before the WebSocket client can connect to Binance.
    """
    pass


class WebSocketConfigError(Exception):
    """
    Raised when WebSocket configuration is missing or invalid.

    This exception indicates a problem with config.yaml that must be
    resolved before the client can determine testnet/mainnet mode.
    """
    pass


class BinanceWebSocket:
    """
    WebSocket client for Binance market data streaming.

    Manages connection lifecycle to Binance WebSocket API for real-time market
    data. Supports both testnet and mainnet environments with automatic
    credential selection based on configuration.

    The client integrates with the EventBus to emit market data events,
    enabling decoupled processing by other system components.

    Attributes:
        event_bus (EventBus): Event bus for publishing market data events
        symbol (str): Trading pair symbol (e.g., 'BTCUSDT')
        interval (str): Candlestick interval (e.g., '15m')
        client (AsyncClient): Binance async client instance
        bsm (BinanceSocketManager): Binance socket manager instance

    Security:
        Credentials are loaded from environment variables:
        - Testnet: BINANCE_TESTNET_API_KEY, BINANCE_TESTNET_API_SECRET
        - Mainnet: BINANCE_MAINNET_API_KEY, BINANCE_MAINNET_API_SECRET

    Examples:
        >>> event_bus = EventBus()
        >>> ws = BinanceWebSocket(event_bus, 'BTCUSDT', '15m')
        >>> await ws.connect()
        >>> # WebSocket is now connected and streaming data
        >>> await ws.disconnect()
    """

    def __init__(
        self,
        event_bus: EventBus,
        symbol: str,
        interval: str,
        config_path: Optional[str] = None
    ):
        """
        Initialize Binance WebSocket client.

        Args:
            event_bus (EventBus): Event bus for publishing market data events
            symbol (str): Trading pair symbol (e.g., 'BTCUSDT')
            interval (str): Candlestick interval (e.g., '1m', '5m', '15m', '1h')
            config_path (str, optional): Path to config.yaml. Defaults to 'config.yaml'
                                        in project root.

        Raises:
            TypeError: If event_bus is not an EventBus instance
            ValueError: If symbol or interval are empty strings
        """
        # Validate event_bus type
        if not isinstance(event_bus, EventBus):
            raise TypeError(
                f"event_bus must be EventBus instance, got {type(event_bus).__name__}"
            )

        # Validate symbol and interval
        if not symbol or not isinstance(symbol, str):
            raise ValueError("symbol must be non-empty string")
        if not interval or not isinstance(interval, str):
            raise ValueError("interval must be non-empty string")

        self.event_bus = event_bus
        self.symbol = symbol.upper()  # Normalize to uppercase
        self.interval = interval.lower()  # Normalize to lowercase

        # Set config path - default to project root config.yaml
        if config_path is None:
            # Assume we're in src/data/, go up two levels to project root
            project_root = Path(__file__).parent.parent.parent
            self.config_path = project_root / "config.yaml"
        else:
            self.config_path = Path(config_path)

        # Connection state - initialized on connect()
        self.client: Optional[AsyncClient] = None
        self.bsm: Optional[BinanceSocketManager] = None
        self._is_testnet: Optional[bool] = None

        logger.info(
            f"BinanceWebSocket initialized for {self.symbol} ({self.interval})"
        )

    def _load_config(self) -> dict:
        """
        Load configuration from config.yaml.

        Returns:
            dict: Configuration dictionary

        Raises:
            WebSocketConfigError: If config file is missing or invalid
        """
        if not self.config_path.exists():
            raise WebSocketConfigError(
                f"Configuration file not found: {self.config_path}"
            )

        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)

            if config is None:
                raise WebSocketConfigError("Configuration file is empty")

            return config

        except yaml.YAMLError as e:
            raise WebSocketConfigError(
                f"Failed to parse configuration file: {e}"
            )
        except Exception as e:
            raise WebSocketConfigError(
                f"Error reading configuration file: {e}"
            )

    def _load_credentials(self, use_testnet: bool) -> tuple[str, str]:
        """
        Load API credentials from environment variables.

        Selects appropriate credentials based on testnet flag:
        - Testnet: BINANCE_TESTNET_API_KEY, BINANCE_TESTNET_API_SECRET
        - Mainnet: BINANCE_MAINNET_API_KEY, BINANCE_MAINNET_API_SECRET

        Args:
            use_testnet (bool): Whether to use testnet credentials

        Returns:
            tuple[str, str]: API key and secret

        Raises:
            WebSocketCredentialError: If required credentials are missing

        Security:
            - Credentials are never logged or printed
            - Environment variables are validated before use
            - Clear error messages guide configuration
        """
        if use_testnet:
            api_key_var = "BINANCE_TESTNET_API_KEY"
            api_secret_var = "BINANCE_TESTNET_API_SECRET"
            env_name = "testnet"
        else:
            api_key_var = "BINANCE_MAINNET_API_KEY"
            api_secret_var = "BINANCE_MAINNET_API_SECRET"
            env_name = "mainnet"

        # Load credentials from environment
        api_key = os.getenv(api_key_var)
        api_secret = os.getenv(api_secret_var)

        # Validate both credentials are present
        missing_vars = []
        if not api_key:
            missing_vars.append(api_key_var)
        if not api_secret:
            missing_vars.append(api_secret_var)

        if missing_vars:
            raise WebSocketCredentialError(
                f"Missing required {env_name} credentials: {', '.join(missing_vars)}. "
                f"Please set these environment variables in your .env file or environment."
            )

        # Validate credentials are not placeholder values
        placeholder_texts = ["your_", "_here", "placeholder"]
        for var_name, value in [(api_key_var, api_key), (api_secret_var, api_secret)]:
            if any(placeholder in value.lower() for placeholder in placeholder_texts):
                raise WebSocketCredentialError(
                    f"{var_name} appears to be a placeholder value. "
                    f"Please set your actual {env_name} API credentials."
                )

        logger.debug(f"Loaded {env_name} credentials successfully")
        return api_key, api_secret

    async def connect(self) -> None:
        """
        Establish connection to Binance WebSocket API.

        This method performs the following steps:
        1. Loads configuration from config.yaml to determine testnet/mainnet mode
        2. Loads appropriate API credentials from environment variables
        3. Creates AsyncClient with testnet flag
        4. Initializes BinanceSocketManager

        After successful connection, the client is ready to start streaming
        market data via the start_stream() method.

        Raises:
            WebSocketConfigError: If configuration is missing or invalid
            WebSocketCredentialError: If credentials are missing or invalid
            Exception: If connection to Binance fails

        Examples:
            >>> ws = BinanceWebSocket(event_bus, 'BTCUSDT', '15m')
            >>> await ws.connect()
            >>> # Client is now connected
        """
        logger.info(f"Connecting to Binance WebSocket for {self.symbol}")

        try:
            # Step 1: Load configuration
            config = self._load_config()

            # Extract testnet flag with validation
            if 'use_testnet' not in config:
                raise WebSocketConfigError(
                    "Missing 'use_testnet' flag in configuration file. "
                    "Please add 'use_testnet: true' or 'use_testnet: false' to config.yaml"
                )

            use_testnet = config['use_testnet']
            if not isinstance(use_testnet, bool):
                raise WebSocketConfigError(
                    f"'use_testnet' must be boolean (true/false), got {type(use_testnet).__name__}"
                )

            self._is_testnet = use_testnet

            # Step 2: Load credentials
            api_key, api_secret = self._load_credentials(use_testnet)

            # Step 3: Create AsyncClient with testnet parameter
            self.client = await AsyncClient.create(
                api_key=api_key,
                api_secret=api_secret,
                testnet=use_testnet
            )

            # Step 4: Initialize BinanceSocketManager
            self.bsm = BinanceSocketManager(self.client)

            env_name = "testnet" if use_testnet else "mainnet"
            logger.info(
                f"Successfully connected to Binance {env_name} WebSocket for {self.symbol}"
            )

        except (WebSocketConfigError, WebSocketCredentialError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Wrap unexpected errors
            logger.error(f"Failed to connect to Binance WebSocket: {e}")
            raise Exception(f"WebSocket connection failed: {e}") from e

    async def disconnect(self) -> None:
        """
        Close connection to Binance WebSocket API and cleanup resources.

        Properly closes the AsyncClient and releases any held resources.
        Safe to call multiple times - subsequent calls are no-ops.

        Examples:
            >>> await ws.connect()
            >>> # ... use websocket ...
            >>> await ws.disconnect()
        """
        if self.client:
            await self.client.close_connection()
            logger.info(f"Disconnected from Binance WebSocket for {self.symbol}")
            self.client = None
            self.bsm = None

    @property
    def is_connected(self) -> bool:
        """
        Check if WebSocket is connected.

        Returns:
            bool: True if connected to Binance, False otherwise
        """
        return self.client is not None and self.bsm is not None

    @property
    def is_testnet(self) -> Optional[bool]:
        """
        Check if connected to testnet.

        Returns:
            bool: True if testnet, False if mainnet, None if not connected
        """
        return self._is_testnet

    async def start_kline_stream(self) -> None:
        """
        Start streaming kline (candlestick) data from Binance WebSocket.

        This method establishes a WebSocket connection and continuously receives
        kline data updates. It runs indefinitely until an error occurs or the
        connection is closed.

        The method uses BinanceSocketManager's kline_futures_socket as a context
        manager to ensure proper resource cleanup. Each received kline message
        is processed through _handle_kline().

        Prerequisites:
            - Must call connect() before calling this method
            - AsyncClient and BinanceSocketManager must be initialized

        Raises:
            RuntimeError: If client is not connected
            Exception: If stream initialization or message processing fails

        Examples:
            >>> ws = BinanceWebSocket(event_bus, 'BTCUSDT', '15m')
            >>> await ws.connect()
            >>> await ws.start_kline_stream()  # Runs indefinitely
        """
        # Validate connection state
        if not self.is_connected:
            raise RuntimeError(
                "WebSocket is not connected. Call connect() before start_kline_stream()"
            )

        logger.info(
            f"Starting kline stream for {self.symbol} ({self.interval})"
        )

        try:
            # Use BinanceSocketManager's kline futures socket as context manager
            async with self.bsm.kline_futures_socket(
                symbol=self.symbol,
                interval=self.interval
            ) as stream:
                logger.info(
                    f"Successfully connected to kline stream for {self.symbol} ({self.interval})"
                )

                # Infinite loop to receive messages
                while True:
                    # Receive message from stream
                    msg = await stream.recv()

                    # Process the kline message
                    await self._handle_kline(msg)

        except Exception as e:
            # Log connection/streaming errors
            logger.error(
                f"Error in kline stream for {self.symbol} ({self.interval}): {e}"
            )
            raise

    async def _handle_kline(self, msg: dict) -> None:
        """
        Process a kline message received from Binance WebSocket.

        This method extracts kline data from the WebSocket message and emits
        a CANDLE_CLOSED event when a candlestick period completes (is_closed=True).

        The kline message structure follows Binance WebSocket API format:
        {
            'e': 'kline',
            'E': event_time,
            'k': {
                't': kline_start_time,
                'T': kline_close_time,
                'o': open_price,
                'h': high_price,
                'l': low_price,
                'c': close_price,
                'v': volume,
                'x': is_closed,
                ...
            }
        }

        Args:
            msg (dict): Raw kline message from Binance WebSocket

        Examples:
            >>> msg = {
            ...     'e': 'kline',
            ...     'k': {
            ...         'o': '45000.0',
            ...         'h': '45100.0',
            ...         'l': '44900.0',
            ...         'c': '45050.0',
            ...         'v': '100.5',
            ...         'x': True
            ...     }
            ... }
            >>> await ws._handle_kline(msg)  # Emits CANDLE_CLOSED event
        """
        try:
            # Extract kline data from message
            kline = msg.get('k', {})

            # Only process closed candles (completed periods)
            is_closed = kline.get('x', False)

            if is_closed:
                # Extract OHLCV data
                open_price = float(kline.get('o', 0))
                high_price = float(kline.get('h', 0))
                low_price = float(kline.get('l', 0))
                close_price = float(kline.get('c', 0))
                volume = float(kline.get('v', 0))
                close_time = kline.get('T', 0)

                # Create event data payload
                event_data = {
                    'symbol': self.symbol,
                    'interval': self.interval,
                    'open': open_price,
                    'high': high_price,
                    'low': low_price,
                    'close': close_price,
                    'volume': volume,
                    'timestamp': datetime.fromtimestamp(close_time / 1000)
                }

                # Emit CANDLE_CLOSED event to EventBus
                from src.core.event_bus import Event, EventType
                event = Event(
                    event_type=EventType.CANDLE_CLOSED,
                    data=event_data,
                    source='BinanceWebSocket'
                )

                await self.event_bus.publish(event)

                logger.debug(
                    f"Candle closed for {self.symbol} ({self.interval}): "
                    f"O={open_price} H={high_price} L={low_price} C={close_price} V={volume}"
                )

        except Exception as e:
            logger.error(
                f"Error handling kline message for {self.symbol}: {e}"
            )
            # Don't re-raise - continue processing other messages

    def __repr__(self) -> str:
        """Return detailed representation of WebSocket client."""
        status = "connected" if self.is_connected else "disconnected"
        env = f" ({('testnet' if self._is_testnet else 'mainnet')})" if self._is_testnet is not None else ""
        return f"BinanceWebSocket({self.symbol}, {self.interval}, {status}{env})"
