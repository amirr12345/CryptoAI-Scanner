from __future__ import annotations

from dataclasses import dataclass, field

from models.liquidity_sweep import LiquiditySweep


@dataclass(slots=True, frozen=True)
class LiquiditySweepResult:
    """
    Liquidity sweep analysis result.
    """

    events: list[LiquiditySweep] = field(
        default_factory=list
    )

    latest_event: str = "NONE"
    latest_direction: str = "NEUTRAL"

    bullish_sweep_count: int = 0
    bearish_sweep_count: int = 0