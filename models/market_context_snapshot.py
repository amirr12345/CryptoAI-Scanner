from __future__ import annotations

from dataclasses import dataclass

from models.cvd_strength import CVDStrengthResult
from models.market_context import MarketContextFusion
from models.volume_profile import VolumeProfileResult
from indicators.vwap_context import VWAPContext


@dataclass(slots=True, frozen=True)
class MarketContextSnapshot:
    """
    Complete market-context snapshot for one symbol.

    This model combines:
        - CVD strength
        - VWAP context
        - Volume Profile
        - Final context fusion

    It does not represent a trading signal.
    """

    cvd: CVDStrengthResult
    vwap: VWAPContext
    volume_profile: VolumeProfileResult
    fusion: MarketContextFusion