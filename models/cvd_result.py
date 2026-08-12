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
class SwingPoint:
    """
    Local swing point detected from a sequence of CVD points.

    kind:
        HIGH or LOW

    index:
        Position of the point inside the CVD point sequence.
    """

    index: int
    timestamp: int
    price: float
    cumulative_delta: float
    kind: str


@dataclass(slots=True, frozen=True)
class SwingDivergence:
    """
    Price/CVD swing-based divergence.
    """

    signal: str
    price_change: float
    cvd_change: float
    previous_index: int
    current_index: int


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
    swing_points: list[SwingPoint]
    swing_divergences: list[SwingDivergence]