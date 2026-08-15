from __future__ import annotations

from api.base import MarketDataProvider
from api.gateio import GateIOExchange
from models.candle import Candle
from models.order_book import OrderBook
from models.ticker import Ticker
from models.trade import Trade


class MarketService:
    """
    Provider-agnostic market-data service.

    Primary provider:
        Gate.io

    Primary analysis universe:
        BASEUSDT

    Backward-compatible provider injection remains supported.
    """

    def __init__(
        self,
        provider: MarketDataProvider | None = None,
        exchange: MarketDataProvider | None = None,
    ):
        if provider is not None:
            self.provider = provider

        elif exchange is not None:
            self.provider = exchange

        else:
            self.provider = GateIOExchange()

    @property
    def exchange(
        self,
    ) -> MarketDataProvider:
        return self.provider

    def btc(self) -> Ticker:
        """
        Backward-compatible BTC ticker helper.

        Gate.io uses BTCUSDT internally, but the legacy helper
        continues exposing BTC as the returned model symbol.
        """

        ticker = self.provider.get_ticker(
            "BTCUSDT"
        )

        if ticker.symbol == "BTC":
            return ticker

        return Ticker(
            symbol="BTC",
            last_price=ticker.last_price,
            high=ticker.high,
            low=ticker.low,
            volume=ticker.volume,
        )

    def markets(self) -> dict:
        return self.provider.get_markets()

    def history(
        self,
        symbol: str,
        resolution: str = "60",
        countback: int = 200,
    ) -> list[Candle]:
        return self.provider.get_history(
            symbol=symbol,
            resolution=resolution,
            countback=countback,
        )

    def trades(
        self,
        symbol: str,
        limit: int = 100,
    ) -> list[Trade]:
        return self.provider.get_trades(
            symbol=symbol,
            limit=limit,
        )

    def historical_trades(
        self,
        symbol: str,
        end_timestamp_ms: int | None = None,
        lookback_seconds: int = 3600,
        max_pages: int = 20,
    ) -> list[Trade]:
        """
        Provider-specific historical trade support.

        Gate.io implements this method.
        """

        method = getattr(
            self.provider,
            "get_historical_trades",
            None,
        )

        if method is None:
            raise NotImplementedError(
                "Configured provider does not implement "
                "get_historical_trades()."
            )

        return method(
            symbol=symbol,
            end_timestamp_ms=end_timestamp_ms,
            lookback_seconds=lookback_seconds,
            max_pages=max_pages,
        )

    def orderbook(
        self,
        symbol: str,
        depth: int = 20,
    ) -> OrderBook:
        return self.provider.get_orderbook(
            symbol=symbol,
            depth=depth,
        )