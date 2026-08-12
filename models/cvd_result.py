from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class CVDPoint:
    """
    Cumulative Volume Delta point for one executed trade.
    """

    timestamp: int
    price: float
    delta: float
    cumulative_delta: float


@dataclass(slots=True, frozen=True)
class CVDResult:
    """
    Aggregated Cumulative Volume Delta analysis.
    """

    buy_volume: float
    sell_volume: float
    delta: float
    starting_cvd: float
    cumulative_delta: float
    price_change: float
    cvd_change: float
    trend: str
    divergence: str
    points: list[CVDPoint]