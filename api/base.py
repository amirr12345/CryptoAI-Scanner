from abc import ABC, abstractmethod

from models.candle import Candle
from models.order_book import OrderBook
from models.ticker import Ticker
from models.trade import Trade


class MarketDataProvider(ABC):
    """
    Provider-agnostic market data interface.

    Concrete providers such as Nobitex, Binance and Bybit
    implement this interface.
    """

    @abstractmethod
    def get_ticker(self, symbol: str) -> Ticker:
        raise NotImplementedError

    @abstractmethod
    def get_markets(self) -> dict:
        raise NotImplementedError

    @abstractmethod
    def get_history(
        self,
        symbol: str,
        resolution: str = "60",
        countback: int = 200,
    ) -> list[Candle]:
        raise NotImplementedError

    def get_trades(
        self,
        symbol: str,
        limit: int = 100,
    ) -> list[Trade]:
        """
        Return recent executed trades.

        Providers that support public trade data should override
        this method.

        The default implementation raises NotImplementedError
        so existing providers remain backward compatible.
        """

        raise NotImplementedError(
            "This provider does not implement get_trades()."
        )

    def get_orderbook(
        self,
        symbol: str,
        depth: int = 20,
    ) -> OrderBook:
        """
        Return a Level 2 order book snapshot.

        Providers that support public order book data should
        override this method.

        The default implementation raises NotImplementedError
        so existing providers remain backward compatible.
        """

        raise NotImplementedError(
            "This provider does not implement get_orderbook()."
        )


# Backward-compatible alias.
ExchangeBase = MarketDataProvider