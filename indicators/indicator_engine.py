from indicators.ema import EMAIndicator


class IndicatorEngine:

    def calculate(self, df):

        ema20 = EMAIndicator(20).calculate(df)
        ema50 = EMAIndicator(50).calculate(df)

        return {
            "price": float(df["close"].iloc[-1]),
            "ema20": float(ema20.iloc[-1]),
            "ema50": float(ema50.iloc[-1]),
        }