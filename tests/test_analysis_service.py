import pandas as pd

from models.candle import Candle
from services.analysis_service import AnalysisService


class FakeMarketService:
    def history(
        self,
        symbol: str,
        resolution: str = "60",
        countback: int = 200,
    ):
        rows = 80

        return [
            Candle(
                timestamp=1_700_000_000 + i * 3600,
                open=float(100 + i),
                high=float(102 + i),
                low=float(98 + i),
                close=float(100 + i),
                volume=1000.0,
            )
            for i in range(rows)
        ]


def test_analysis_service_returns_analysis_result():

    service = AnalysisService(
        market_service=FakeMarketService(),
    )

    result = service.analyze(
        symbol="BTCIRT",
        resolution="60",
        countback=80,
    )

    assert result.symbol == "BTCIRT"
    assert result.price > 0

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