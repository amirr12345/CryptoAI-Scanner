from dataclasses import dataclass


@dataclass
class Ticker:
    symbol: str
    last_price: float
    high: float
    low: float
    volume: float