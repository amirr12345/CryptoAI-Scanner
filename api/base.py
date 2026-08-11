from abc import ABC, abstractmethod

from api.models import Ticker
from models.candle import Candle


class ExchangeBase(ABC):

    @abstractmethod
    def get_ticker(self, symbol: str) -> Ticker:
        raise NotImplementedError

    @abstractmethod
    def get_markets(self):
        raise NotImplementedError

    @abstractmethod
    def get_history(
        self,
        symbol: str,
        resolution: str = "60",
        countback: int = 200,
    ) -> list[Candle]:
        raise NotImplementedError