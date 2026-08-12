from api.base import MarketDataProvider
from api.models import Ticker
from models.candle import Candle
from models.order_book import OrderBook
from models.order_book_level import OrderBookLevel
from models.ticker import Ticker as ModelTicker
from models.trade import Trade
from services.market_service import MarketService


class FakeMarketDataProvider(MarketDataProvider):
    def get_ticker(self, symbol: str) -> Ticker:
        return ModelTicker(
            symbol=symbol.upper(),
            last_price=100.0,
            high=110.0,
            low=90.0,
            volume=1000.0,
        )

    def get_markets(self) -> dict:
        return {
            "status": "ok",
            "stats": {
                "btc-rls": {},
                "eth-rls": {},
            },
        }

    def get_history(
        self,
        symbol: str,
        resolution: str = "60",
        countback: int = 200,
    ) -> list[Candle]:
        return [
            Candle(
                timestamp=1_700_000_000,
                open=99.0,
                high=101.0,
                low=98.0,
                close=100.0,
                volume=1000.0,
            )
        ]

    def get_trades(
        self,
        symbol: str,
        limit: int = 100,
    ) -> list[Trade]:
        return [
            Trade(
                timestamp=1_700_000_000,
                price=100.0,
                volume=1.5,
                side="buy",
                symbol=symbol.upper(),
            ),
            Trade(
                timestamp=1_700_000_001,
                price=101.0,
                volume=0.5,
                side="sell",
                symbol=symbol.upper(),
            ),
        ][:limit]

    def get_orderbook(
        self,
        symbol: str,
        depth: int = 20,
    ) -> OrderBook:
        bids = [
            OrderBookLevel(
                price=100.0,
                volume=5.0,
            ),
            OrderBookLevel(
                price=99.0,
                volume=3.0,
            ),
        ]

        asks = [
            OrderBookLevel(
                price=101.0,
                volume=4.0,
            ),
            OrderBookLevel(
                price=102.0,
                volume=2.0,
            ),
        ]

        return OrderBook(
            symbol=symbol.upper(),
            timestamp=1_700_000_000,
            bids=bids[:depth],
            asks=asks[:depth],
        )


def test_market_service_uses_generic_provider():
    provider = FakeMarketDataProvider()

    service = MarketService(
        provider=provider
    )

    assert service.provider is provider
    assert service.exchange is provider


def test_market_service_get_ticker():
    service = MarketService(
        provider=FakeMarketDataProvider()
    )

    ticker = service.btc()

    assert ticker.symbol == "BTC"
    assert ticker.last_price == 100.0
    assert ticker.high == 110.0
    assert ticker.low == 90.0
    assert ticker.volume == 1000.0


def test_market_service_get_markets():
    service = MarketService(
        provider=FakeMarketDataProvider()
    )

    markets = service.markets()

    assert markets["status"] == "ok"
    assert "btc-rls" in markets["stats"]
    assert "eth-rls" in markets["stats"]


def test_market_service_get_history():
    service = MarketService(
        provider=FakeMarketDataProvider()
    )

    candles = service.history(
        symbol="BTC",
        resolution="60",
        countback=1,
    )

    assert len(candles) == 1
    assert isinstance(candles[0], Candle)
    assert candles[0].close == 100.0
    assert candles[0].volume == 1000.0


def test_market_service_supports_exchange_backward_compatibility():
    provider = FakeMarketDataProvider()

    service = MarketService(
        exchange=provider
    )

    assert service.provider is provider
    assert service.exchange is provider


def test_market_service_returns_generic_ticker_model():
    service = MarketService(
        provider=FakeMarketDataProvider()
    )

    ticker = service.btc()

    assert isinstance(ticker, ModelTicker)


def test_market_service_get_trades():
    service = MarketService(
        provider=FakeMarketDataProvider()
    )

    trades = service.trades(
        symbol="BTC",
        limit=100,
    )

    assert len(trades) == 2

    assert all(
        isinstance(trade, Trade)
        for trade in trades
    )

    assert trades[0].symbol == "BTC"
    assert trades[0].side == "buy"
    assert trades[0].price == 100.0
    assert trades[0].volume == 1.5

    assert trades[1].side == "sell"
    assert trades[1].price == 101.0
    assert trades[1].volume == 0.5


def test_market_service_get_orderbook():
    service = MarketService(
        provider=FakeMarketDataProvider()
    )

    orderbook = service.orderbook(
        symbol="BTC",
        depth=20,
    )

    assert isinstance(orderbook, OrderBook)
    assert orderbook.symbol == "BTC"

    assert len(orderbook.bids) == 2
    assert len(orderbook.asks) == 2

    assert orderbook.best_bid() is not None
    assert orderbook.best_ask() is not None

    assert orderbook.best_bid().price == 100.0
    assert orderbook.best_ask().price == 101.0


def test_market_service_trades_respect_limit():
    service = MarketService(
        provider=FakeMarketDataProvider()
    )

    trades = service.trades(
        symbol="BTC",
        limit=1,
    )

    assert len(trades) == 1
    assert trades[0].side == "buy"


def test_market_service_orderbook_respects_depth():
    service = MarketService(
        provider=FakeMarketDataProvider()
    )

    orderbook = service.orderbook(
        symbol="BTC",
        depth=1,
    )

    assert len(orderbook.bids) == 1
    assert len(orderbook.asks) == 1