import pandas as pd

from indicators.indicator_engine import IndicatorEngine
from services.history_service import HistoryService
from models.analysis_result import AnalysisResult


class AnalysisService:

    def __init__(self):

        self.history_service = HistoryService()
        self.engine = IndicatorEngine()

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

        return self.engine.calculate(
            df=df,
            symbol=symbol,
        )