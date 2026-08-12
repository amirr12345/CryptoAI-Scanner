from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Ticker:
    """
    Provider-agnostic ticker model.

    This model contains normalized market data and must not
    depend on a specific exchange/provider.
    """

    symbol: str
    last_price: float
    high: float
    low: float
    volume: float