from abc import ABC, abstractmethod
from typing import Dict, List


class ExchangeBase(ABC):
    """کلاس پایه برای همه صرافی‌ها"""

    @abstractmethod
    def get_markets(self) -> List[Dict]:
        pass

    @abstractmethod
    def get_ticker(self, symbol: str) -> Dict:
        pass

    @abstractmethod
    def get_orderbook(self, symbol: str) -> Dict:
        pass