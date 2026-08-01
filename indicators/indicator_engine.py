from indicators.ema import EMAIndicator
from models.analysis_result import AnalysisResult


class IndicatorEngine:

    def calculate(self, df, symbol: str) -> AnalysisResult:

        ema20 = EMAIndicator(20).calculate(df)
        ema50 = EMAIndicator(50).calculate(df)

        return AnalysisResult(
            symbol=symbol,
            price=float(df["close"].iloc[-1]),
            ema20=float(ema20.iloc[-1]),
            ema50=float(ema50.iloc[-1]),
        )