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
    return [
        Candle(
            timestamp=1_700_000_000 + index * 3600,
            open=close - 1,
            high=close + 2,
            low=close - 2,
            close=close,
            volume=volume,
        )
        for index, close in enumerate(closes)
    ]


def test_analysis_service_returns_analysis_result():
    closes = list(range(100, 180))

    service = AnalysisService(
        market_service=FakeMarketService(
            make_candles(closes)
        )
    )

    result = service.analyze(
        symbol="BTCIRT",
        resolution="60",
        countback=80,
    )

    assert result.symbol == "BTCIRT"
    assert result.price == closes[-1]

    assert isinstance(result.total_score, int)
    assert 0.0 <= result.confidence <= 1.0

    assert result.signal in {
        "STRONG_BUY",
        "BUY",
        "HOLD",
        "SELL",
        "STRONG_SELL",
    }

    assert isinstance(result.reasons, list)
    assert isinstance(result.indicators, dict)

    assert "ema20" in result.indicators
    assert "ema50" in result.indicators
    assert "macd" in result.indicators
    assert "rsi" in result.indicators
    assert "atr" in result.indicators


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


def test_analysis_service_rejects_insufficient_candles():
    closes = list(range(100, 130))

    service = AnalysisService(
        market_service=FakeMarketService(
            make_candles(closes)
        )
    )

    try:
        service.analyze(
            symbol="TESTIRT",
            resolution="60",
            countback=30,
        )
    except ValueError as exc:
        assert "insufficient candles" in str(exc)
    else:
        raise AssertionError(
            "Expected ValueError for insufficient candles."
        )


def test_analysis_service_rejects_flat_market():
    closes = [100.0] * 80

    service = AnalysisService(
        market_service=FakeMarketService(
            make_candles(closes, volume=1000.0)
        )
    )

    try:
        service.analyze(
            symbol="SLVON",
            resolution="60",
            countback=80,
        )
    except ValueError as exc:
        assert "flat price" in str(exc)
    else:
        raise AssertionError(
            "Expected ValueError for flat market."
        )


def test_analysis_service_rejects_zero_volume_market():
    closes = list(range(100, 180))

    service = AnalysisService(
        market_service=FakeMarketService(
            make_candles(closes, volume=0.0)
        )
    )

    try:
        service.analyze(
            symbol="NOVOLUME",
            resolution="60",
            countback=80,
        )
    except ValueError as exc:
        assert "zero trading volume" in str(exc)
    else:
        raise AssertionError(
            "Expected ValueError for zero volume."
        )