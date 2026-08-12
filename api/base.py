from abc import ABC, abstractmethod

from api.models import Ticker
from models.candle import Candle


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


# Backward-compatible alias.
#
# Existing code/tests that still import ExchangeBase
# will continue to work.
ExchangeBase = MarketDataProvider