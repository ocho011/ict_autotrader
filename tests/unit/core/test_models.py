"""
Unit tests for trading dataclasses (OrderBlock, FVG, Position).

Tests cover:
- Valid dataclass instantiation
- Field validation (ranges, types, constraints)
- Immutability for frozen dataclasses
- Business logic validation (risk/reward, stop loss positioning)
- Error message quality
"""

import pytest
from datetime import datetime
from pydantic import ValidationError
from src.core.models import OrderBlock, FVG, Position


class TestOrderBlock:
    """Test OrderBlock dataclass validation and behavior."""

    def test_valid_bullish_order_block(self):
        """Test creation of valid bullish order block."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        ob = OrderBlock(
            type="bullish",
            top=45000.0,
            bottom=44500.0,
            timestamp=timestamp
        )

        assert ob.type == "bullish"
        assert ob.top == 45000.0
        assert ob.bottom == 44500.0
        assert ob.timestamp == timestamp
        assert ob.touches == 0  # Default value
        assert ob.is_valid is True  # Default value

    def test_valid_bearish_order_block(self):
        """Test creation of valid bearish order block."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        ob = OrderBlock(
            type="bearish",
            top=45000.0,
            bottom=44500.0,
            timestamp=timestamp,
            touches=3,
            is_valid=False
        )

        assert ob.type == "bearish"
        assert ob.touches == 3
        assert ob.is_valid is False

    def test_invalid_price_range_top_less_than_bottom(self):
        """Test validation fails when top <= bottom."""
        with pytest.raises(ValueError, match="top .* must be greater than bottom"):
            OrderBlock(
                type="bullish",
                top=44500.0,  # Invalid: top < bottom
                bottom=45000.0,
                timestamp=datetime.utcnow()
            )

    def test_invalid_price_range_top_equals_bottom(self):
        """Test validation fails when top == bottom."""
        with pytest.raises(ValueError, match="top .* must be greater than bottom"):
            OrderBlock(
                type="bullish",
                top=45000.0,
                bottom=45000.0,  # Invalid: top == bottom
                timestamp=datetime.utcnow()
            )

    def test_negative_top_price(self):
        """Test validation fails for negative top price."""
        with pytest.raises(ValidationError):
            OrderBlock(
                type="bullish",
                top=-100.0,  # Invalid: negative price
                bottom=44500.0,
                timestamp=datetime.utcnow()
            )

    def test_negative_bottom_price(self):
        """Test validation fails for negative bottom price."""
        with pytest.raises(ValidationError):
            OrderBlock(
                type="bullish",
                top=45000.0,
                bottom=-100.0,  # Invalid: negative price
                timestamp=datetime.utcnow()
            )

    def test_negative_touches(self):
        """Test validation fails for negative touches."""
        with pytest.raises(ValidationError):
            OrderBlock(
                type="bullish",
                top=45000.0,
                bottom=44500.0,
                timestamp=datetime.utcnow(),
                touches=-1  # Invalid: negative touches
            )

    def test_invalid_type(self):
        """Test validation fails for invalid type."""
        with pytest.raises(ValidationError):
            OrderBlock(
                type="neutral",  # Invalid: only 'bullish' or 'bearish' allowed
                top=45000.0,
                bottom=44500.0,
                timestamp=datetime.utcnow()
            )

    def test_immutability(self):
        """Test OrderBlock is frozen/immutable."""
        ob = OrderBlock(
            type="bullish",
            top=45000.0,
            bottom=44500.0,
            timestamp=datetime.utcnow()
        )

        # Attempt to modify should raise ValidationError
        with pytest.raises(ValidationError, match="Instance is frozen"):
            ob.touches = 5

    def test_zero_top_price(self):
        """Test validation fails for zero top price."""
        with pytest.raises(ValidationError):
            OrderBlock(
                type="bullish",
                top=0.0,  # Invalid: must be > 0
                bottom=44500.0,
                timestamp=datetime.utcnow()
            )


class TestFVG:
    """Test FVG (Fair Value Gap) dataclass validation and behavior."""

    def test_valid_bullish_fvg(self):
        """Test creation of valid bullish FVG."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        fvg = FVG(
            type="bullish",
            top=45000.0,
            bottom=44800.0,
            timestamp=timestamp
        )

        assert fvg.type == "bullish"
        assert fvg.top == 45000.0
        assert fvg.bottom == 44800.0
        assert fvg.timestamp == timestamp
        assert fvg.filled_percent == 0.0  # Default value
        assert fvg.is_valid is True  # Default value

    def test_valid_bearish_fvg_with_fill(self):
        """Test creation of valid bearish FVG with partial fill."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        fvg = FVG(
            type="bearish",
            top=45000.0,
            bottom=44800.0,
            timestamp=timestamp,
            filled_percent=25.5,
            is_valid=False
        )

        assert fvg.type == "bearish"
        assert fvg.filled_percent == 25.5
        assert fvg.is_valid is False

    def test_filled_percent_exceeds_100(self):
        """Test validation fails when filled_percent > 100."""
        with pytest.raises(ValidationError):
            FVG(
                type="bullish",
                top=45000.0,
                bottom=44800.0,
                timestamp=datetime.utcnow(),
                filled_percent=150.0  # Invalid: > 100
            )

    def test_filled_percent_negative(self):
        """Test validation fails when filled_percent < 0."""
        with pytest.raises(ValidationError):
            FVG(
                type="bullish",
                top=45000.0,
                bottom=44800.0,
                timestamp=datetime.utcnow(),
                filled_percent=-10.0  # Invalid: < 0
            )

    def test_filled_percent_precision_normalization(self):
        """Test filled_percent is normalized to 2 decimal places."""
        fvg = FVG(
            type="bullish",
            top=45000.0,
            bottom=44800.0,
            timestamp=datetime.utcnow(),
            filled_percent=25.567  # Should be rounded to 25.57
        )

        assert fvg.filled_percent == 25.57

    def test_filled_percent_boundary_values(self):
        """Test filled_percent accepts boundary values 0 and 100."""
        # Test 0%
        fvg_empty = FVG(
            type="bullish",
            top=45000.0,
            bottom=44800.0,
            timestamp=datetime.utcnow(),
            filled_percent=0.0
        )
        assert fvg_empty.filled_percent == 0.0

        # Test 100%
        fvg_full = FVG(
            type="bullish",
            top=45000.0,
            bottom=44800.0,
            timestamp=datetime.utcnow(),
            filled_percent=100.0
        )
        assert fvg_full.filled_percent == 100.0

    def test_invalid_price_range(self):
        """Test validation fails when top <= bottom."""
        with pytest.raises(ValueError, match="top .* must exceed bottom"):
            FVG(
                type="bullish",
                top=44800.0,
                bottom=45000.0,  # Invalid: bottom > top
                timestamp=datetime.utcnow()
            )

    def test_immutability(self):
        """Test FVG is frozen/immutable."""
        fvg = FVG(
            type="bullish",
            top=45000.0,
            bottom=44800.0,
            timestamp=datetime.utcnow()
        )

        # Attempt to modify should raise ValidationError
        with pytest.raises(ValidationError, match="Instance is frozen"):
            fvg.filled_percent = 50.0


class TestPosition:
    """Test Position dataclass validation and behavior."""

    def test_valid_long_position(self):
        """Test creation of valid long position."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        pos = Position(
            symbol="BTCUSDT",
            side="long",
            entry_price=45000.0,
            size=0.1,
            stop_loss=44500.0,
            take_profit=46000.0,
            timestamp=timestamp
        )

        assert pos.symbol == "BTCUSDT"
        assert pos.side == "long"
        assert pos.entry_price == 45000.0
        assert pos.size == 0.1
        assert pos.stop_loss == 44500.0
        assert pos.take_profit == 46000.0
        assert pos.timestamp == timestamp

    def test_valid_short_position(self):
        """Test creation of valid short position."""
        pos = Position(
            symbol="ETHUSDT",
            side="short",
            entry_price=3000.0,
            size=1.0,
            stop_loss=3100.0,  # Above entry for short
            take_profit=2900.0  # Below entry for short
        )

        assert pos.side == "short"
        assert pos.stop_loss == 3100.0
        assert pos.take_profit == 2900.0

    def test_long_position_invalid_stop_loss_above_entry(self):
        """Test long position rejects stop loss above entry price."""
        with pytest.raises(ValueError, match="stop loss .* must be below entry"):
            Position(
                symbol="BTCUSDT",
                side="long",
                entry_price=45000.0,
                size=0.1,
                stop_loss=46000.0,  # Invalid: SL above entry for long
                take_profit=47000.0
            )

    def test_long_position_invalid_take_profit_below_entry(self):
        """Test long position rejects take profit below entry price."""
        with pytest.raises(ValueError, match="take profit .* must be above entry"):
            Position(
                symbol="BTCUSDT",
                side="long",
                entry_price=45000.0,
                size=0.1,
                stop_loss=44000.0,
                take_profit=44500.0  # Invalid: TP below entry for long
            )

    def test_short_position_invalid_stop_loss_below_entry(self):
        """Test short position rejects stop loss below entry price."""
        with pytest.raises(ValueError, match="stop loss .* must be above entry"):
            Position(
                symbol="BTCUSDT",
                side="short",
                entry_price=45000.0,
                size=0.1,
                stop_loss=44000.0,  # Invalid: SL below entry for short
                take_profit=43000.0
            )

    def test_short_position_invalid_take_profit_above_entry(self):
        """Test short position rejects take profit above entry price."""
        with pytest.raises(ValueError, match="take profit .* must be below entry"):
            Position(
                symbol="BTCUSDT",
                side="short",
                entry_price=45000.0,
                size=0.1,
                stop_loss=46000.0,
                take_profit=46500.0  # Invalid: TP above entry for short
            )

    def test_invalid_symbol_lowercase(self):
        """Test validation fails for lowercase symbol."""
        with pytest.raises(ValidationError):
            Position(
                symbol="btcusdt",  # Invalid: must be uppercase
                side="long",
                entry_price=45000.0,
                size=0.1,
                stop_loss=44500.0,
                take_profit=46000.0
            )

    def test_invalid_symbol_empty(self):
        """Test validation fails for empty symbol."""
        with pytest.raises(ValidationError):
            Position(
                symbol="",  # Invalid: must be non-empty
                side="long",
                entry_price=45000.0,
                size=0.1,
                stop_loss=44500.0,
                take_profit=46000.0
            )

    def test_negative_size(self):
        """Test validation fails for negative position size."""
        with pytest.raises(ValidationError):
            Position(
                symbol="BTCUSDT",
                side="long",
                entry_price=45000.0,
                size=-0.1,  # Invalid: must be > 0
                stop_loss=44500.0,
                take_profit=46000.0
            )

    def test_zero_size(self):
        """Test validation fails for zero position size."""
        with pytest.raises(ValidationError):
            Position(
                symbol="BTCUSDT",
                side="long",
                entry_price=45000.0,
                size=0.0,  # Invalid: must be > 0
                stop_loss=44500.0,
                take_profit=46000.0
            )

    def test_position_mutability(self):
        """Test Position is mutable (not frozen)."""
        pos = Position(
            symbol="BTCUSDT",
            side="long",
            entry_price=45000.0,
            size=0.1,
            stop_loss=44500.0,
            take_profit=46000.0
        )

        # Should allow modification (e.g., trailing stop)
        pos.stop_loss = 45200.0
        assert pos.stop_loss == 45200.0

    def test_risk_reward_ratio_calculation(self):
        """Test risk/reward ratio calculation."""
        pos = Position(
            symbol="BTCUSDT",
            side="long",
            entry_price=45000.0,
            size=0.1,
            stop_loss=44500.0,  # Risk: 500
            take_profit=46000.0  # Reward: 1000
        )

        assert pos.risk_reward_ratio() == 2.0  # 1000 / 500

    def test_risk_reward_ratio_short_position(self):
        """Test risk/reward ratio calculation for short position."""
        pos = Position(
            symbol="BTCUSDT",
            side="short",
            entry_price=45000.0,
            size=0.1,
            stop_loss=45600.0,  # Risk: 600
            take_profit=43800.0  # Reward: 1200
        )

        assert pos.risk_reward_ratio() == 2.0  # 1200 / 600

    def test_timestamp_default_factory(self):
        """Test timestamp is auto-generated if not provided."""
        before = datetime.utcnow()
        pos = Position(
            symbol="BTCUSDT",
            side="long",
            entry_price=45000.0,
            size=0.1,
            stop_loss=44500.0,
            take_profit=46000.0
        )
        after = datetime.utcnow()

        # Timestamp should be between before and after
        assert before <= pos.timestamp <= after

    def test_invalid_side(self):
        """Test validation fails for invalid position side."""
        with pytest.raises(ValidationError):
            Position(
                symbol="BTCUSDT",
                side="neutral",  # Invalid: only 'long' or 'short' allowed
                entry_price=45000.0,
                size=0.1,
                stop_loss=44500.0,
                take_profit=46000.0
            )
