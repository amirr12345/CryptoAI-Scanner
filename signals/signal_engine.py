from models.analysis_result import AnalysisResult


class SignalEngine:

    def generate(self, result: AnalysisResult) -> AnalysisResult:

        # Trend
        if result.ema20 > result.ema50:
            result.trend = "BULLISH"
        elif result.ema20 < result.ema50:
            result.trend = "BEARISH"
        else:
            result.trend = "NEUTRAL"

        # Signal
        if result.trend == "BULLISH" and result.rsi < 30:
            result.signal = "BUY"

        elif result.trend == "BEARISH" and result.rsi > 70:
            result.signal = "SELL"

        else:
            result.signal = "HOLD"

        return result
