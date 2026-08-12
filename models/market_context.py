from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class MarketContextFusion:
    """
    Combined market context from CVD, VWAP and Volume Profile.

    This model does not represent a trading signal.
    It describes directional agreement and market location.
    """

    cvd_direction: str
    vwap_trend: str

    profile_position: str
    profile_alignment: str

    alignment: str
    direction: str

    cvd_strength: float
    effective_strength: float

    vwap_position: str
    vwap_distance_pct: float
    vwap_slope: float

    poc: float | None
    vah: float | None
    val: float | None
    current_price: float | None