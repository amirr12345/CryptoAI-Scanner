from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class LiquiditySweep:
    """
    Confirmed liquidity sweep.

    BULLISH:
        Sell-side liquidity swept below a confirmed swing low,
        followed by a close back above that level.

    BEARISH:
        Buy-side liquidity swept above a confirmed swing high,
        followed by a close back below that level.
    """

    index: int
    timestamp: int

    event: str
    direction: str

    level_index: int
    level_price: float
    level_kind: str

    candle_high: float
    candle_low: float
    candle_close: float

    excursion: float
    excursion_pct: float

    rejection: float
    rejection_pct: float