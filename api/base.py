from abc import ABC, abstractmethod
from api.models import Ticker


class ExchangeBase(ABC):

    @abstractmethod
    def get_ticker(self, symbol: str) -> Ticker:
        pass

    @abstractmethod
    def get_markets(self):
        pass
