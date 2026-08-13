from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class HistoricalContext:
    """
    Market context reconstructed strictly from information
    available at a historical timestamp.
    """

    symbol: str
    timestamp: int

    trade_count: int
    lookback_seconds: int

    cvd_direction: str
    cvd_strength: float
    cvd_divergence: str
    cvd_delta: float
    cvd_change: float

    vwap: float | None
    previous_vwap: float | None
    vwap_position: str
    vwap_distance_pct: float
    vwap_slope: float

    poc: float | None
    vah: float | None
    val: float | None
    profile_position: str

    historical: bool = True