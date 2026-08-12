from __future__ import annotations

from api.base import MarketDataProvider
from api.nobitex import NobitexExchange
from models.candle import Candle


class MarketService:
    """
    Provider-agnostic service layer for market data access.

    The service depends on the generic MarketDataProvider interface,
    not on a specific exchange implementation.

    Nobitex remains the default provider for backward compatibility.
    """

    def __init__(
        self,
        provider: MarketDataProvider | None = None,
        exchange: MarketDataProvider | None = None,
    ):
        """
        Initialize MarketService.

        Parameters
        ----------
        provider:
            Generic market data provider.

        exchange:
            Backward-compatible alias for older code/tests.

        Notes
        -----
        If both provider and exchange are supplied, provider takes
        precedence.
        """

        if provider is not None:
            self.provider = provider

        elif exchange is not None:
            self.provider = exchange

        else:
            self.provider = NobitexExchange()

    @property
    def exchange(self) -> MarketDataProvider:
        """
        Backward-compatible alias for the configured provider.

        New code should use `provider`.
        """
        return self.provider

    def btc(self):
        """
        Backward-compatible BTC ticker helper.
        """
        return self.provider.get_ticker("btc")

    def markets(self) -> dict:
        """
        Return available market statistics.
        """
        return self.provider.get_markets()

    def history(
        self,
        symbol: str,
        resolution: str = "60",
        countback: int = 200,
    ) -> list[Candle]:
        """
        Return OHLCV candles for a market.
        """
        return self.provider.get_history(
            symbol=symbol,
            resolution=resolution,
            countback=countback,
        )