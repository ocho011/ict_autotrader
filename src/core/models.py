"""
Trading dataclasses with comprehensive validation.

This module defines core trading entities for ICT (Inner Circle Trader) methodology:
- OrderBlock: Institutional order zones (support/resistance)
- FVG: Fair Value Gaps (price inefficiencies)
- Position: Active trading positions with risk parameters
"""

from pydantic import BaseModel, Field, model_validator
from typing import Literal
from datetime import datetime


class OrderBlock(BaseModel):
    """
    Immutable Order Block representation.

    Order Blocks represent institutional activity zones where smart money
    likely placed orders. These are key support/resistance levels in ICT methodology.

    Attributes:
        type: Direction of the order block ('bullish' or 'bearish')
        top: Upper price boundary (must be > bottom)
        bottom: Lower price boundary
        timestamp: When the order block was identified
        touches: Number of times price has tested this level
        is_valid: Whether the order block is still considered valid

    Examples:
        >>> from datetime import datetime
        >>> ob = OrderBlock(
        ...     type="bullish",
        ...     top=45000.0,
        ...     bottom=44500.0,
        ...     timestamp=datetime.utcnow()
        ... )
        >>> ob.touches
        0
        >>> ob.type
        'bullish'
    """

    model_config = {"frozen": True}

    type: Literal["bullish", "bearish"] = Field(
        description="Direction of the order block"
    )
    top: float = Field(
        gt=0,
        description="Upper price boundary"
    )
    bottom: float = Field(
        gt=0,
        description="Lower price boundary"
    )
    timestamp: datetime = Field(
        description="When the order block was identified"
    )
    touches: int = Field(
        default=0,
        ge=0,
        description="Number of times price tested this level"
    )
    is_valid: bool = Field(
        default=True,
        description="Whether order block is still valid"
    )

    @model_validator(mode="after")
    def validate_price_range(self) -> "OrderBlock":
        """Ensure top > bottom for valid price range."""
        if self.top <= self.bottom:
            raise ValueError(
                f"Invalid OrderBlock: top ({self.top:.2f}) must be greater than "
                f"bottom ({self.bottom:.2f}). Check price data integrity."
            )
        return self


class FVG(BaseModel):
    """
    Immutable Fair Value Gap representation.

    FVGs are inefficiencies in price action where the market moved too quickly,
    creating gaps that price tends to fill later. Critical for ICT entry timing.

    Attributes:
        type: Direction of the gap ('bullish' or 'bearish')
        top: Upper boundary of the gap
        bottom: Lower boundary of the gap
        timestamp: When the FVG was created
        filled_percent: How much of the gap has been filled (0-100)
        is_valid: Whether the FVG is still tradeable

    Examples:
        >>> from datetime import datetime
        >>> fvg = FVG(
        ...     type="bullish",
        ...     top=45000.0,
        ...     bottom=44800.0,
        ...     timestamp=datetime.utcnow(),
        ...     filled_percent=25.5
        ... )
        >>> fvg.filled_percent
        25.5
        >>> fvg.is_valid
        True
    """

    model_config = {"frozen": True}

    type: Literal["bullish", "bearish"] = Field(
        description="Direction of the gap"
    )
    top: float = Field(
        gt=0,
        description="Upper boundary of the gap"
    )
    bottom: float = Field(
        gt=0,
        description="Lower boundary of the gap"
    )
    timestamp: datetime = Field(
        description="When the FVG was created"
    )
    filled_percent: float = Field(
        default=0.0,
        ge=0,
        le=100,
        description="Percentage of gap filled (0-100)"
    )
    is_valid: bool = Field(
        default=True,
        description="Whether FVG is still tradeable"
    )

    @model_validator(mode="after")
    def validate_fvg_integrity(self) -> "FVG":
        """Validate price range and normalize fill percentage precision."""
        if self.top <= self.bottom:
            raise ValueError(
                f"Invalid FVG: top ({self.top:.2f}) must exceed "
                f"bottom ({self.bottom:.2f}). Verify gap calculation."
            )

        # Normalize filled_percent to 2 decimals for consistency
        object.__setattr__(self, "filled_percent", round(self.filled_percent, 2))

        return self


class Position(BaseModel):
    """
    Mutable trading position representation.

    Tracks an active trading position with entry, exit levels, and sizing.
    Not frozen to allow updates for trailing stops or partial exits.

    Attributes:
        symbol: Trading pair (e.g., 'BTCUSDT')
        side: Position direction ('long' or 'short')
        entry_price: Price where position was entered
        size: Position size in base currency
        stop_loss: Stop loss price level
        take_profit: Take profit price level
        timestamp: When position was opened

    Examples:
        >>> from datetime import datetime
        >>> pos = Position(
        ...     symbol="BTCUSDT",
        ...     side="long",
        ...     entry_price=45000.0,
        ...     size=0.1,
        ...     stop_loss=44500.0,
        ...     take_profit=46000.0,
        ...     timestamp=datetime.utcnow()
        ... )
        >>> pos.risk_reward_ratio()
        2.0
    """

    # NOT frozen - positions may need updates (trailing stops, etc.)

    symbol: str = Field(
        min_length=1,
        pattern=r"^[A-Z]+$",
        description="Trading pair symbol"
    )
    side: Literal["long", "short"] = Field(
        description="Position direction"
    )
    entry_price: float = Field(
        gt=0,
        description="Entry price"
    )
    size: float = Field(
        gt=0,
        description="Position size in base currency"
    )
    stop_loss: float = Field(
        gt=0,
        description="Stop loss price level"
    )
    take_profit: float = Field(
        gt=0,
        description="Take profit price level"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When position was opened"
    )

    @model_validator(mode="after")
    def validate_risk_parameters(self) -> "Position":
        """Ensure stop loss and take profit make sense for position side."""
        if self.side == "long":
            if self.stop_loss >= self.entry_price:
                raise ValueError(
                    f"Long position stop loss ({self.stop_loss:.2f}) must be below "
                    f"entry price ({self.entry_price:.2f}). "
                    f"Current setting would trigger immediate loss."
                )
            if self.take_profit <= self.entry_price:
                raise ValueError(
                    f"Long position take profit ({self.take_profit:.2f}) must be above "
                    f"entry price ({self.entry_price:.2f}). "
                    f"Current setting prevents profit."
                )

        elif self.side == "short":
            if self.stop_loss <= self.entry_price:
                raise ValueError(
                    f"Short position stop loss ({self.stop_loss:.2f}) must be above "
                    f"entry price ({self.entry_price:.2f}). "
                    f"Current setting would trigger immediate loss."
                )
            if self.take_profit >= self.entry_price:
                raise ValueError(
                    f"Short position take profit ({self.take_profit:.2f}) must be below "
                    f"entry price ({self.entry_price:.2f}). "
                    f"Current setting prevents profit."
                )

        return self

    def risk_reward_ratio(self) -> float:
        """
        Calculate risk/reward ratio for the position.

        Returns:
            Risk/reward ratio (reward / risk). Higher is better.
            Returns 0.0 if risk is zero (invalid position).

        Examples:
            >>> pos = Position(
            ...     symbol="BTCUSDT",
            ...     side="long",
            ...     entry_price=45000.0,
            ...     size=0.1,
            ...     stop_loss=44500.0,
            ...     take_profit=46000.0,
            ...     timestamp=datetime.utcnow()
            ... )
            >>> pos.risk_reward_ratio()
            2.0
        """
        risk = abs(self.entry_price - self.stop_loss)
        reward = abs(self.take_profit - self.entry_price)
        return reward / risk if risk > 0 else 0.0
