"""
Pytest configuration and shared fixtures for ICT Auto Trader tests.

This module provides:
- Async test configuration
- Common fixtures for EventBus, StateStore, AsyncClient mocks
- Test data generators
"""

import pytest
import asyncio
from typing import Generator

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_candle():
    """Provide a sample candle data structure for testing."""
    return {
        'timestamp': 1700000000000,
        'open': 35000.0,
        'high': 35100.0,
        'low': 34900.0,
        'close': 35050.0,
        'volume': 100.5
    }


@pytest.fixture
def sample_candles():
    """Provide a sequence of sample candles for pattern testing."""
    base_price = 35000.0
    candles = []

    for i in range(20):
        candles.append({
            'timestamp': 1700000000000 + (i * 900000),  # 15-minute intervals
            'open': base_price + (i * 10),
            'high': base_price + (i * 10) + 50,
            'low': base_price + (i * 10) - 50,
            'close': base_price + (i * 10) + 25,
            'volume': 100.0 + (i * 5)
        })

    return candles
