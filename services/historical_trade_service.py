from __future__ import annotations

from core.trade_store import TradeStore
from models.trade import Trade


class HistoricalTradeService:
    """
    Service layer for storing and retrieving historical
    public market trades.
    """

    def __init__(
        self,
        store: TradeStore | None = None,
    ) -> None:
        self.store = (
            store
            if store is not None
            else TradeStore()
        )

    def save(
        self,
        trades: list[Trade],
    ) -> int:
        """
        Persist normalized trades.
        """

        return self.store.save_trades(
            trades
        )

    def get(
        self,
        symbol: str,
        start_timestamp: int | None = None,
        end_timestamp: int | None = None,
    ) -> list[Trade]:
        """
        Retrieve trades in a time range.
        """

        return self.store.get_trades(
            symbol=symbol,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
        )

    def get_as_of(
        self,
        symbol: str,
        end_timestamp: int,
        lookback_seconds: int | None = None,
    ) -> list[Trade]:
        """
        Retrieve only information available at a
        historical point in time.
        """

        return self.store.get_trades_as_of(
            symbol=symbol,
            end_timestamp=end_timestamp,
            lookback_seconds=lookback_seconds,
        )

    def count(
        self,
        symbol: str | None = None,
    ) -> int:
        return self.store.count(
            symbol=symbol
        )

    def latest_timestamp(
        self,
        symbol: str,
    ) -> int | None:
        return self.store.latest_timestamp(
            symbol
        )