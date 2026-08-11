from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Candle:
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float