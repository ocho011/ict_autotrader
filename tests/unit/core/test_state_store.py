"""
Unit tests for StateStore class.

Tests cover:
- Initialization and empty collections
- Candle storage with deque maxlen behavior
- OrderBlock addition and retrieval
- FVG addition and retrieval
- Type filtering for patterns
- Validity filtering for patterns
- Edge cases (empty lists, all invalid patterns)
"""

import pytest
from datetime import datetime
from src.core.state_store import StateStore
from src.core.models import OrderBlock, FVG


class TestStateStoreInitialization:
    """Test StateStore initialization and configuration."""

    def test_init_creates_empty_collections(self):
        """Test that initialization creates empty collections."""
        store = StateStore()

        assert len(store.candles) == 0
        assert len(store.order_blocks) == 0
        assert len(store.fvgs) == 0

    def test_init_with_custom_candle_history_size(self):
        """Test initialization with custom candle history size."""
        store = StateStore(candle_history_size=1000)

        assert store.candles.maxlen == 1000

    def test_init_with_default_candle_history_size(self):
        """Test default candle history size is 500."""
        store = StateStore()

        assert store.candles.maxlen == 500

    def test_init_with_invalid_candle_history_size(self):
        """Test that invalid candle history size raises ValueError."""
        with pytest.raises(ValueError, match="candle_history_size must be positive"):
            StateStore(candle_history_size=0)

        with pytest.raises(ValueError, match="candle_history_size must be positive"):
            StateStore(candle_history_size=-100)


class TestCandleStorage:
    """Test candle addition and deque behavior."""

    def test_add_candle_appends_to_deque(self):
        """Test that add_candle appends candle dict to deque."""
        store = StateStore()
        candle = {
            "open": 45000.0,
            "high": 45100.0,
            "low": 44900.0,
            "close": 45050.0,
            "volume": 123.45
        }

        store.add_candle(candle)

        assert len(store.candles) == 1
        assert store.candles[0] == candle

    def test_add_multiple_candles(self):
        """Test adding multiple candles maintains order."""
        store = StateStore()
        candles = [
            {"close": 45000.0},
            {"close": 45100.0},
            {"close": 45200.0}
        ]

        for candle in candles:
            store.add_candle(candle)

        assert len(store.candles) == 3
        assert store.candles[0]["close"] == 45000.0
        assert store.candles[1]["close"] == 45100.0
        assert store.candles[2]["close"] == 45200.0

    def test_candle_deque_respects_maxlen(self):
        """Test that candle deque removes oldest when maxlen is reached."""
        store = StateStore(candle_history_size=3)

        # Add 4 candles to a deque with maxlen=3
        for i in range(4):
            store.add_candle({"id": i})

        # Should only have last 3 candles
        assert len(store.candles) == 3
        assert store.candles[0]["id"] == 1  # First candle removed
        assert store.candles[1]["id"] == 2
        assert store.candles[2]["id"] == 3


class TestOrderBlockStorage:
    """Test OrderBlock addition and retrieval."""

    def test_add_order_block_valid_instance(self):
        """Test adding valid OrderBlock instance."""
        store = StateStore()
        ob = OrderBlock(
            type="bullish",
            top=45000.0,
            bottom=44500.0,
            timestamp=datetime(2024, 1, 1, 12, 0, 0)
        )

        store.add_order_block(ob)

        assert len(store.order_blocks) == 1
        assert store.order_blocks[0] == ob

    def test_add_multiple_order_blocks(self):
        """Test adding multiple OrderBlocks."""
        store = StateStore()
        ob1 = OrderBlock(
            type="bullish",
            top=45000.0,
            bottom=44500.0,
            timestamp=datetime(2024, 1, 1, 12, 0, 0)
        )
        ob2 = OrderBlock(
            type="bearish",
            top=45500.0,
            bottom=45000.0,
            timestamp=datetime(2024, 1, 1, 13, 0, 0)
        )

        store.add_order_block(ob1)
        store.add_order_block(ob2)

        assert len(store.order_blocks) == 2
        assert store.order_blocks[0] == ob1
        assert store.order_blocks[1] == ob2


class TestFVGStorage:
    """Test FVG addition and retrieval."""

    def test_add_fvg_valid_instance(self):
        """Test adding valid FVG instance."""
        store = StateStore()
        fvg = FVG(
            type="bullish",
            top=45000.0,
            bottom=44800.0,
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            filled_percent=25.0
        )

        store.add_fvg(fvg)

        assert len(store.fvgs) == 1
        assert store.fvgs[0] == fvg

    def test_add_multiple_fvgs(self):
        """Test adding multiple FVGs."""
        store = StateStore()
        fvg1 = FVG(
            type="bullish",
            top=45000.0,
            bottom=44800.0,
            timestamp=datetime(2024, 1, 1, 12, 0, 0)
        )
        fvg2 = FVG(
            type="bearish",
            top=45500.0,
            bottom=45300.0,
            timestamp=datetime(2024, 1, 1, 13, 0, 0)
        )

        store.add_fvg(fvg1)
        store.add_fvg(fvg2)

        assert len(store.fvgs) == 2
        assert store.fvgs[0] == fvg1
        assert store.fvgs[1] == fvg2


class TestGetValidOrderBlocks:
    """Test get_valid_order_blocks method with filtering."""

    def test_get_valid_order_blocks_no_filter(self):
        """Test retrieving all valid order blocks without type filter."""
        store = StateStore()
        ob1 = OrderBlock(
            type="bullish",
            top=45000.0,
            bottom=44500.0,
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            is_valid=True
        )
        ob2 = OrderBlock(
            type="bearish",
            top=45500.0,
            bottom=45000.0,
            timestamp=datetime(2024, 1, 1, 13, 0, 0),
            is_valid=True
        )

        store.add_order_block(ob1)
        store.add_order_block(ob2)

        valid_obs = store.get_valid_order_blocks()

        assert len(valid_obs) == 2
        assert ob1 in valid_obs
        assert ob2 in valid_obs

    def test_get_valid_order_blocks_filter_bullish(self):
        """Test retrieving only bullish order blocks."""
        store = StateStore()
        ob1 = OrderBlock(
            type="bullish",
            top=45000.0,
            bottom=44500.0,
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            is_valid=True
        )
        ob2 = OrderBlock(
            type="bearish",
            top=45500.0,
            bottom=45000.0,
            timestamp=datetime(2024, 1, 1, 13, 0, 0),
            is_valid=True
        )
        ob3 = OrderBlock(
            type="bullish",
            top=44000.0,
            bottom=43500.0,
            timestamp=datetime(2024, 1, 1, 14, 0, 0),
            is_valid=True
        )

        store.add_order_block(ob1)
        store.add_order_block(ob2)
        store.add_order_block(ob3)

        bullish_obs = store.get_valid_order_blocks(ob_type="bullish")

        assert len(bullish_obs) == 2
        assert all(ob.type == "bullish" for ob in bullish_obs)
        assert ob1 in bullish_obs
        assert ob3 in bullish_obs
        assert ob2 not in bullish_obs

    def test_get_valid_order_blocks_filter_bearish(self):
        """Test retrieving only bearish order blocks."""
        store = StateStore()
        ob1 = OrderBlock(
            type="bullish",
            top=45000.0,
            bottom=44500.0,
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            is_valid=True
        )
        ob2 = OrderBlock(
            type="bearish",
            top=45500.0,
            bottom=45000.0,
            timestamp=datetime(2024, 1, 1, 13, 0, 0),
            is_valid=True
        )

        store.add_order_block(ob1)
        store.add_order_block(ob2)

        bearish_obs = store.get_valid_order_blocks(ob_type="bearish")

        assert len(bearish_obs) == 1
        assert bearish_obs[0] == ob2
        assert bearish_obs[0].type == "bearish"

    def test_get_valid_order_blocks_excludes_invalid(self):
        """Test that invalid order blocks are excluded."""
        store = StateStore()
        ob1 = OrderBlock(
            type="bullish",
            top=45000.0,
            bottom=44500.0,
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            is_valid=True
        )
        ob2 = OrderBlock(
            type="bullish",
            top=44000.0,
            bottom=43500.0,
            timestamp=datetime(2024, 1, 1, 13, 0, 0),
            is_valid=False  # Invalid
        )
        ob3 = OrderBlock(
            type="bearish",
            top=45500.0,
            bottom=45000.0,
            timestamp=datetime(2024, 1, 1, 14, 0, 0),
            is_valid=False  # Invalid
        )

        store.add_order_block(ob1)
        store.add_order_block(ob2)
        store.add_order_block(ob3)

        valid_obs = store.get_valid_order_blocks()

        assert len(valid_obs) == 1
        assert valid_obs[0] == ob1
        assert all(ob.is_valid for ob in valid_obs)

    def test_get_valid_order_blocks_empty_list(self):
        """Test that empty list is returned when no valid patterns exist."""
        store = StateStore()

        # Empty store
        assert store.get_valid_order_blocks() == []

        # Store with only invalid patterns
        ob = OrderBlock(
            type="bullish",
            top=45000.0,
            bottom=44500.0,
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            is_valid=False
        )
        store.add_order_block(ob)

        assert store.get_valid_order_blocks() == []
        assert store.get_valid_order_blocks(ob_type="bullish") == []

    def test_get_valid_order_blocks_type_filter_with_invalid(self):
        """Test type filtering excludes invalid patterns."""
        store = StateStore()
        ob1 = OrderBlock(
            type="bullish",
            top=45000.0,
            bottom=44500.0,
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            is_valid=True
        )
        ob2 = OrderBlock(
            type="bullish",
            top=44000.0,
            bottom=43500.0,
            timestamp=datetime(2024, 1, 1, 13, 0, 0),
            is_valid=False
        )

        store.add_order_block(ob1)
        store.add_order_block(ob2)

        bullish_obs = store.get_valid_order_blocks(ob_type="bullish")

        assert len(bullish_obs) == 1
        assert bullish_obs[0] == ob1


class TestGetValidFVGs:
    """Test get_valid_fvgs method with filtering."""

    def test_get_valid_fvgs_no_filter(self):
        """Test retrieving all valid FVGs without type filter."""
        store = StateStore()
        fvg1 = FVG(
            type="bullish",
            top=45000.0,
            bottom=44800.0,
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            is_valid=True
        )
        fvg2 = FVG(
            type="bearish",
            top=45500.0,
            bottom=45300.0,
            timestamp=datetime(2024, 1, 1, 13, 0, 0),
            is_valid=True
        )

        store.add_fvg(fvg1)
        store.add_fvg(fvg2)

        valid_fvgs = store.get_valid_fvgs()

        assert len(valid_fvgs) == 2
        assert fvg1 in valid_fvgs
        assert fvg2 in valid_fvgs

    def test_get_valid_fvgs_filter_bullish(self):
        """Test retrieving only bullish FVGs."""
        store = StateStore()
        fvg1 = FVG(
            type="bullish",
            top=45000.0,
            bottom=44800.0,
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            is_valid=True
        )
        fvg2 = FVG(
            type="bearish",
            top=45500.0,
            bottom=45300.0,
            timestamp=datetime(2024, 1, 1, 13, 0, 0),
            is_valid=True
        )
        fvg3 = FVG(
            type="bullish",
            top=44000.0,
            bottom=43800.0,
            timestamp=datetime(2024, 1, 1, 14, 0, 0),
            is_valid=True
        )

        store.add_fvg(fvg1)
        store.add_fvg(fvg2)
        store.add_fvg(fvg3)

        bullish_fvgs = store.get_valid_fvgs(fvg_type="bullish")

        assert len(bullish_fvgs) == 2
        assert all(fvg.type == "bullish" for fvg in bullish_fvgs)
        assert fvg1 in bullish_fvgs
        assert fvg3 in bullish_fvgs
        assert fvg2 not in bullish_fvgs

    def test_get_valid_fvgs_filter_bearish(self):
        """Test retrieving only bearish FVGs."""
        store = StateStore()
        fvg1 = FVG(
            type="bullish",
            top=45000.0,
            bottom=44800.0,
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            is_valid=True
        )
        fvg2 = FVG(
            type="bearish",
            top=45500.0,
            bottom=45300.0,
            timestamp=datetime(2024, 1, 1, 13, 0, 0),
            is_valid=True
        )

        store.add_fvg(fvg1)
        store.add_fvg(fvg2)

        bearish_fvgs = store.get_valid_fvgs(fvg_type="bearish")

        assert len(bearish_fvgs) == 1
        assert bearish_fvgs[0] == fvg2
        assert bearish_fvgs[0].type == "bearish"

    def test_get_valid_fvgs_excludes_invalid(self):
        """Test that invalid FVGs are excluded."""
        store = StateStore()
        fvg1 = FVG(
            type="bullish",
            top=45000.0,
            bottom=44800.0,
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            is_valid=True
        )
        fvg2 = FVG(
            type="bullish",
            top=44000.0,
            bottom=43800.0,
            timestamp=datetime(2024, 1, 1, 13, 0, 0),
            is_valid=False  # Invalid
        )
        fvg3 = FVG(
            type="bearish",
            top=45500.0,
            bottom=45300.0,
            timestamp=datetime(2024, 1, 1, 14, 0, 0),
            is_valid=False  # Invalid
        )

        store.add_fvg(fvg1)
        store.add_fvg(fvg2)
        store.add_fvg(fvg3)

        valid_fvgs = store.get_valid_fvgs()

        assert len(valid_fvgs) == 1
        assert valid_fvgs[0] == fvg1
        assert all(fvg.is_valid for fvg in valid_fvgs)

    def test_get_valid_fvgs_empty_list(self):
        """Test that empty list is returned when no valid patterns exist."""
        store = StateStore()

        # Empty store
        assert store.get_valid_fvgs() == []

        # Store with only invalid patterns
        fvg = FVG(
            type="bullish",
            top=45000.0,
            bottom=44800.0,
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            is_valid=False
        )
        store.add_fvg(fvg)

        assert store.get_valid_fvgs() == []
        assert store.get_valid_fvgs(fvg_type="bullish") == []

    def test_get_valid_fvgs_type_filter_with_invalid(self):
        """Test type filtering excludes invalid patterns."""
        store = StateStore()
        fvg1 = FVG(
            type="bullish",
            top=45000.0,
            bottom=44800.0,
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            is_valid=True
        )
        fvg2 = FVG(
            type="bullish",
            top=44000.0,
            bottom=43800.0,
            timestamp=datetime(2024, 1, 1, 13, 0, 0),
            is_valid=False
        )

        store.add_fvg(fvg1)
        store.add_fvg(fvg2)

        bullish_fvgs = store.get_valid_fvgs(fvg_type="bullish")

        assert len(bullish_fvgs) == 1
        assert bullish_fvgs[0] == fvg1
