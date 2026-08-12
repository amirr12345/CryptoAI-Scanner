from dataclasses import dataclass, field

from models.order_book_level import OrderBookLevel


@dataclass(slots=True, frozen=True)
class OrderBook:
    """
    Provider-agnostic Level 2 order book snapshot.
    """

    symbol: str
    timestamp: int

    bids: list[OrderBookLevel] = field(
        default_factory=list
    )

    asks: list[OrderBookLevel] = field(
        default_factory=list
    )

    def best_bid(self) -> OrderBookLevel | None:
        """
        Return the highest bid price level.
        """

        if not self.bids:
            return None

        return max(
            self.bids,
            key=lambda level: level.price,
        )

    def best_ask(self) -> OrderBookLevel | None:
        """
        Return the lowest ask price level.
        """

        if not self.asks:
            return None

        return min(
            self.asks,
            key=lambda level: level.price,
        )

    def bid_volume(
        self,
        levels: int | None = None,
    ) -> float:
        """
        Sum bid volume.

        If levels is provided, only the first N bid
        levels are included.
        """

        source = (
            self.bids
            if levels is None
            else self.bids[:levels]
        )

        return sum(
            level.volume
            for level in source
        )

    def ask_volume(
        self,
        levels: int | None = None,
    ) -> float:
        """
        Sum ask volume.

        If levels is provided, only the first N ask
        levels are included.
        """

        source = (
            self.asks
            if levels is None
            else self.asks[:levels]
        )

        return sum(
            level.volume
            for level in source
        )

    def imbalance(
        self,
        levels: int | None = None,
    ) -> float:
        """
        Calculate bid/ask volume imbalance.

        Formula:

            (bid_volume - ask_volume)
            / (bid_volume + ask_volume)

        Returns a value between -1 and +1.

        Positive:
            More bid liquidity.

        Negative:
            More ask liquidity.

        Zero:
            Balanced liquidity.
        """

        bid = self.bid_volume(levels)
        ask = self.ask_volume(levels)

        total = bid + ask

        if total == 0:
            return 0.0

        return (
            (bid - ask) / total
        )