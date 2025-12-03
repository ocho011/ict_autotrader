"""
Integration tests for WebSocket graceful shutdown and cleanup.

This module tests the graceful shutdown mechanism of the BinanceWebSocket client,
including:
- stop() method for controlled shutdown
- Async context manager cleanup
- Resource leak prevention
- Shutdown during active streaming
"""

import asyncio
import pytest
import os
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.event_bus import EventBus
from src.data.websocket_client import BinanceWebSocket


@pytest.fixture
def event_bus():
    """Create EventBus instance for testing."""
    return EventBus()


@pytest.fixture
def mock_env(monkeypatch):
    """Set up mock environment variables."""
    monkeypatch.setenv('BINANCE_TESTNET_API_KEY', 'test_key')
    monkeypatch.setenv('BINANCE_TESTNET_API_SECRET', 'test_secret')


@pytest.fixture
def websocket_client(event_bus, mock_env):
    """Create BinanceWebSocket instance for testing."""
    return BinanceWebSocket(
        event_bus=event_bus,
        symbol='BTCUSDT',
        interval='15m'
    )


class TestGracefulShutdown:
    """Test graceful shutdown functionality."""

    @pytest.mark.asyncio
    async def test_stop_method_sets_running_flag(self, websocket_client):
        """
        Test that stop() method sets _running flag to False.

        Verifies:
        - stop() can be called without connection
        - _running flag is properly managed
        - Method is idempotent
        """
        # Initially not running
        assert websocket_client._running is False

        # Manually set running
        websocket_client._running = True

        # Call stop
        await websocket_client.stop()

        # Verify flag is False
        assert websocket_client._running is False

    @pytest.mark.asyncio
    async def test_stop_called_multiple_times(self, websocket_client):
        """
        Test that stop() can be called multiple times safely.

        Verifies:
        - Multiple stop() calls don't cause errors
        - Idempotent behavior
        """
        # Set running flag manually
        websocket_client._running = True

        # Call stop multiple times
        await websocket_client.stop()
        await websocket_client.stop()
        await websocket_client.stop()

        # Should be safe and result in False
        assert websocket_client._running is False

    @pytest.mark.asyncio
    async def test_context_manager_entry_connects(self, event_bus, mock_env):
        """
        Test that async context manager calls connect() on entry.

        Verifies:
        - __aenter__ establishes connection
        - Connection is ready for use
        """
        with patch('src.data.websocket_client.AsyncClient') as mock_client_cls, \
             patch('src.data.websocket_client.BinanceSocketManager'):

            mock_client = AsyncMock()
            mock_client_cls.create = AsyncMock(return_value=mock_client)

            # Use context manager
            async with BinanceWebSocket(event_bus, 'BTCUSDT', '15m') as ws:
                # Inside context - should be connected
                assert ws.is_connected is True

    @pytest.mark.asyncio
    async def test_context_manager_exit_disconnects(self, event_bus, mock_env):
        """
        Test that async context manager calls disconnect() on exit.

        Verifies:
        - __aexit__ closes connection
        - AsyncClient.close_connection() is called
        - Resources are properly released
        """
        with patch('src.data.websocket_client.AsyncClient') as mock_client_cls, \
             patch('src.data.websocket_client.BinanceSocketManager'):

            mock_client = AsyncMock()
            mock_client_cls.create = AsyncMock(return_value=mock_client)

            # Use context manager
            async with BinanceWebSocket(event_bus, 'BTCUSDT', '15m') as ws:
                pass  # Connection should happen here

            # Outside context - should be disconnected
            assert ws.is_connected is False
            mock_client.close_connection.assert_called_once()

    @pytest.mark.asyncio
    async def test_stream_loop_checks_running_flag(self, websocket_client):
        """
        Test that stream loop exits when _running becomes False.

        Verifies:
        - Loop checks _running flag on each iteration
        - Graceful exit when flag is set to False
        """
        message_count = 0
        max_messages = 5

        async def mock_recv():
            nonlocal message_count
            message_count += 1

            # Stop after a few messages
            if message_count >= max_messages:
                websocket_client._running = False

            return {
                'k': {
                    'o': '45000.0',
                    'h': '45100.0',
                    'l': '44900.0',
                    'c': '45050.0',
                    'v': '100.5',
                    'x': True,
                    'T': 1234567890000
                }
            }

        with patch('src.data.websocket_client.AsyncClient') as mock_client_cls, \
             patch('src.data.websocket_client.BinanceSocketManager') as mock_bsm_cls:

            mock_client = AsyncMock()
            mock_client_cls.create = AsyncMock(return_value=mock_client)

            mock_stream = AsyncMock()
            mock_stream.recv = mock_recv

            mock_bsm = MagicMock()
            mock_bsm.kline_futures_socket = MagicMock()
            mock_bsm.kline_futures_socket.return_value.__aenter__ = AsyncMock(
                return_value=mock_stream
            )
            mock_bsm.kline_futures_socket.return_value.__aexit__ = AsyncMock()
            mock_bsm_cls.return_value = mock_bsm

            # Connect
            await websocket_client.connect()

            # Start stream - should exit after max_messages
            await websocket_client.start_kline_stream(max_retries=1)

            # Verify loop exited after processing messages
            assert message_count == max_messages
            assert websocket_client._running is False

    @pytest.mark.asyncio
    async def test_no_resource_leak_after_disconnect(self, websocket_client):
        """
        Test that no resource leaks occur after disconnect.

        Verifies:
        - AsyncClient is properly closed
        - BinanceSocketManager is cleared
        - Connection state is clean
        """
        with patch('src.data.websocket_client.AsyncClient') as mock_client_cls, \
             patch('src.data.websocket_client.BinanceSocketManager'):

            mock_client = AsyncMock()
            mock_client_cls.create = AsyncMock(return_value=mock_client)

            # Connect and disconnect
            await websocket_client.connect()
            await websocket_client.disconnect()

            # Verify no resource leaks
            assert websocket_client.client is None
            assert websocket_client.bsm is None
            assert websocket_client._running is False

    @pytest.mark.asyncio
    async def test_context_manager_exception_propagation(self, event_bus, mock_env):
        """
        Test that __aexit__ doesn't suppress exceptions.

        Verifies:
        - Exceptions in context are propagated
        - Cleanup still happens
        """
        with patch('src.data.websocket_client.AsyncClient') as mock_client_cls, \
             patch('src.data.websocket_client.BinanceSocketManager'):

            mock_client = AsyncMock()
            mock_client_cls.create = AsyncMock(return_value=mock_client)

            # Exception should propagate
            with pytest.raises(ValueError):
                async with BinanceWebSocket(event_bus, 'BTCUSDT', '15m') as ws:
                    raise ValueError("Test exception")

            # Cleanup should still have happened
            mock_client.close_connection.assert_called_once()

