from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class OrderBookLevel:
    """
    One price level in an order book.
    """

    price: float
    volume: float

    def __post_init__(self):
        if self.price < 0:
            raise ValueError(
                "Order book price cannot be negative."
            )

        if self.volume < 0:
            raise ValueError(
                "Order book volume cannot be negative."
            )