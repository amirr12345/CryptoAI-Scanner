import pandas as pd

from indicators.indicator_engine import IndicatorEngine
from services.history_service import HistoryService
from signals.signal_engine import SignalEngine

from models.analysis_result import AnalysisResult


class AnalysisService:

    def __init__(self):

        self.history_service = HistoryService()
        self.indicator_engine = IndicatorEngine()
        self.signal_engine = SignalEngine()

    def run(
        self,
        symbol: str = "BTCIRT",
        resolution: str = "60",
        bars: int = 200,
    ) -> AnalysisResult:

        data = self.history_service.get_history(
            symbol=symbol,
            resolution=resolution,
            bars=bars,
        )

        df = pd.DataFrame(
            {
                "time": data["t"],
                "open": data["o"],
                "high": data["h"],
                "low": data["l"],
                "close": data["c"],
                "volume": data["v"],
            }
        )

        # Calculate Indicators
        result = self.indicator_engine.calculate(
            df=df,
            symbol=symbol,
        )

        # Generate Trading Signal
        result = self.signal_engine.generate(result)

        return result
