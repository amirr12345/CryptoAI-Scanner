from models.candle import Candle
from services.analysis_service import AnalysisService


class FakeMarketService:
    def __init__(self, candles):
        self.candles = candles

    def history(
        self,
        symbol: str,
        resolution: str = "60",
        countback: int = 200,
    ):
        return self.candles


def make_candles(
    closes: list[float],
    volume: float = 1000.0,
) -> list[Candle]:
    candles = []

    for index, close in enumerate(closes):
        candles.append(
            Candle(
                timestamp=1_700_000_000 + index * 3600,
                open=close - 1,
                high=close + 2,
                low=close - 2,
                close=close,
                volume=volume,
            )
        )

    return candles


def test_analysis_service_neutral_scenario():
    closes = [
        100.0,
        100.2,
        99.8,
        100.1,
        99.9,
    ] * 16

    service = AnalysisService(
        market_service=FakeMarketService(
            make_candles(closes)
        )
    )

    result = service.analyze(
        symbol="BTCIRT",
        resolution="60",
        countback=len(closes),
    )

    assert result.symbol == "BTCIRT"
    assert result.price == closes[-1]

    assert result.signal in {
        "STRONG_BUY",
        "BUY",
        "HOLD",
        "SELL",
        "STRONG_SELL",
    }


def test_analysis_service_bullish_scenario():
    closes = (
        [100.0] * 40
        + [90.0, 91.0, 92.0, 94.0, 96.0]
        + list(range(97, 127))
    )

    service = AnalysisService(
        market_service=FakeMarketService(
            make_candles(
                closes,
                volume=2000.0,
            )
        )
    )

    result = service.analyze(
        symbol="BTCIRT",
        resolution="60",
        countback=len(closes),
    )

    assert result.symbol == "BTCIRT"
    assert result.price == closes[-1]
    assert result.total_score >= 0

    assert result.signal in {
        "STRONG_BUY",
        "BUY",
        "HOLD",
    }


def test_analysis_service_bearish_scenario():
    closes = (
        [130.0] * 40
        + [129.0, 128.0, 126.0, 124.0, 122.0]
        + list(range(121, 91, -1))
    )

    service = AnalysisService(
        market_service=FakeMarketService(
            make_candles(
                closes,
                volume=2000.0,
            )
        )
    )

    result = service.analyze(
        symbol="BTCIRT",
        resolution="60",
        countback=len(closes),
    )

    assert result.symbol == "BTCIRT"
    assert result.price == closes[-1]
    assert result.total_score <= 0

    assert result.signal in {
        "STRONG_SELL",
        "SELL",
        "HOLD",
    }


def test_analysis_service_rejects_empty_candle_history():
    service = AnalysisService(
        market_service=FakeMarketService([])
    )

    try:
        service.analyze(
            symbol="BTCIRT",
            resolution="60",
            countback=200,
        )
    except ValueError as exc:
        assert "No candles available" in str(exc)
    else:
        raise AssertionError(
            "Expected ValueError for empty candle history."
        )