from indicators.ema import EMAIndicator
from indicators.rsi import RSIIndicator
from indicators.macd import MACDIndicator
from indicators.atr import ATRIndicator
from models.analysis_result import AnalysisResult
from indicators.bollinger import BollingerIndicator


class IndicatorEngine:

    def calculate(self, df, symbol: str) -> AnalysisResult:

        ema20 = EMAIndicator(20).calculate(df)
        ema50 = EMAIndicator(50).calculate(df)
        atr = ATRIndicator().calculate(df)  
        rsi = RSIIndicator().calculate(df)
        bb = BollingerIndicator().calculate(df)

        macd = MACDIndicator().calculate(df)

        return AnalysisResult(
            symbol=symbol,
            price=float(df["close"].iloc[-1]),
            ema20=float(ema20.iloc[-1]),
            ema50=float(ema50.iloc[-1]),
            rsi=float(rsi.iloc[-1]),
            macd=float(macd["macd"].iloc[-1]),
            atr=float(atr.iloc[-1]),
            bb_upper=float(bb["upper"].iloc[-1]),
            bb_middle=float(bb["middle"].iloc[-1]),
            bb_lower=float(bb["lower"].iloc[-1]),
            bb_width=float(bb["bandwidth"].iloc[-1]),
        )
