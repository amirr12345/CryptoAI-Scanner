from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class BucketSwingPoint:
    """
    Swing point detected on time-bucketed CVD data.
    """

    index: int
    timestamp: int
    price: float
    cumulative_delta: float
    kind: str


@dataclass(slots=True, frozen=True)
class BucketDivergence:
    """
    Price/CVD divergence detected between two bucket swings.
    """

    signal: str

    previous_index: int
    current_index: int

    previous_price: float
    current_price: float

    previous_cvd: float
    current_cvd: float

    price_change_pct: float
    cvd_change: float


@dataclass(slots=True, frozen=True)
class BucketedCVDAnalysis:
    """
    Swing/divergence analysis of time-bucketed CVD.
    """

    swing_points: list[BucketSwingPoint]
    divergences: list[BucketDivergence]
    latest_signal: str