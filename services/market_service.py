from __future__ import annotations

from api.nobitex import NobitexExchange
from models.candle import Candle


class MarketService:
    """
    Service layer for market data access.
    """

    def __init__(self, exchange: NobitexExchange | None = None):
        self.exchange = exchange or NobitexExchange()

    def btc(self):
        """
        Backward-compatible BTC ticker helper.
        """
        return self.exchange.get_ticker("btc")

    def history(
        self,
        symbol: str,
        resolution: str = "60",
        countback: int = 200,
    ) -> list[Candle]:
        """
        Return OHLCV candles for a market.
        """

        return self.exchange.get_history(
            symbol=symbol,
            resolution=resolution,
            countback=countback,
        )