from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class StructureSetup:
    """
    Structure-based trading setup.

    A setup is valid only when a liquidity sweep is followed
    by an MSS in the same directional bias within a bounded
    number of candles.
    """

    index: int
    timestamp: int

    direction: str
    setup: str

    sweep_index: int
    sweep_event: str

    mss_index: int
    mss_event: str

    level_price: float
    sweep_excursion_pct: float
    mss_displacement_pct: float

    bars_between: int