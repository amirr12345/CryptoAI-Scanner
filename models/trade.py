from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Trade:
    """
    Provider-agnostic executed trade model.

    Represents one executed market trade.
    """

    timestamp: int
    price: float
    volume: float
    side: str
    symbol: str

    def __post_init__(self):
        if self.price < 0:
            raise ValueError(
                "Trade price cannot be negative."
            )

        if self.volume < 0:
            raise ValueError(
                "Trade volume cannot be negative."
            )

        normalized_side = self.side.strip().lower()

        if normalized_side not in {"buy", "sell"}:
            raise ValueError(
                "Trade side must be 'buy' or 'sell'."
            )