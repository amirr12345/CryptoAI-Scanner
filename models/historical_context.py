from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class HistoricalContext:
    """
    Market context reconstructed strictly from information
    available at a historical timestamp.

    Historical-safe features:

        - CVD / Delta
        - VWAP
        - Volume Profile

    Optional live/derived enrichment:

        - Order Flow
        - Session Quality

    IMPORTANT:
        Current Order Book data must NOT be treated as historical
        context unless timestamped historical Level-2 data exists.
    """

    symbol: str
    timestamp: int

    trade_count: int
    lookback_seconds: int

    # ------------------------------------------------------------
    # CVD / Delta
    # ------------------------------------------------------------

    cvd_direction: str
    cvd_strength: float
    cvd_divergence: str
    cvd_delta: float
    cvd_change: float

    # ------------------------------------------------------------
    # Historical VWAP
    # ------------------------------------------------------------

    vwap: float | None
    previous_vwap: float | None
    vwap_position: str
    vwap_distance_pct: float
    vwap_slope: float

    # ------------------------------------------------------------
    # Historical Volume Profile
    # ------------------------------------------------------------

    poc: float | None
    vah: float | None
    val: float | None
    profile_position: str

    # ------------------------------------------------------------
    # Order Flow
    # ------------------------------------------------------------

    buy_volume: float = 0.0
    sell_volume: float = 0.0

    delta: float = 0.0
    delta_pct: float = 0.0

    buy_ratio: float = 0.0
    sell_ratio: float = 0.0

    average_trade_size: float = 0.0

    large_trade_buy_volume: float = 0.0
    large_trade_sell_volume: float = 0.0
    large_trade_imbalance: float = 0.0

    order_flow_aggression: str = "NEUTRAL"
    order_flow_strength: float = 0.0

    # ------------------------------------------------------------
    # Session Quality
    # ------------------------------------------------------------

    session_name: str = "UNKNOWN"
    session_quality: float = 0.0
    session_is_overlap: bool = False

    # ------------------------------------------------------------
    # Historical marker
    # ------------------------------------------------------------

    historical: bool = True