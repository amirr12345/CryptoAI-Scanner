import pandas as pd

from services.history_service import HistoryService
from indicators.indicator_engine import IndicatorEngine


class AnalysisService:

    def __init__(self):
        self.history_service = HistoryService()
        self.engine = IndicatorEngine()

    def run(
        self,
        symbol: str = "BTCIRT",
        resolution: str = "60",
        bars: int = 200,
    ):

        data = self.history_service.get_history(
            symbol=symbol,
            resolution=resolution,
            bars=bars,
        )

        df = pd.DataFrame({
            "time": data["t"],
            "open": data["o"],
            "high": data["h"],
            "low": data["l"],
            "close": data["c"],
            "volume": data["v"],
        })

        result = self.engine.calculate(df)

        return result