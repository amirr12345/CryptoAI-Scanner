from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class CVDBucket:
    """
    Time-bucketed cumulative volume delta result.
    """

    start_timestamp: int
    end_timestamp: int

    open_price: float
    close_price: float

    buy_volume: float
    sell_volume: float
    delta: float
    cumulative_delta: float

    trade_count: int