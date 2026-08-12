from api.base import MarketDataProvider
from api.models import Ticker
from models.candle import Candle
from services.market_service import MarketService


class FakeMarketDataProvider(MarketDataProvider):
    def get_ticker(self, symbol: str) -> Ticker:
        return Ticker(
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


def test_market_service_uses_generic_provider():
    provider = FakeMarketDataProvider()

    service = MarketService(provider=provider)

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