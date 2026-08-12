from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class CVDStrengthResult:
    """
    Normalized CVD strength and market-flow context.

    All strength values are normalized to the range 0..100.
    """

    flow_strength: float
    momentum_strength: float
    divergence_strength: float
    participation_strength: float
    overall_strength: float

    direction: str
    divergence: str

    recent_delta: float
    recent_cvd_change: float
    recent_volume: float
    recent_trade_count: int