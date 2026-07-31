from indicators.ema import EMAIndicator


class IndicatorEngine:

    def calculate(self, dataframe):

        ema20 = EMAIndicator(20).calculate(dataframe)
        ema50 = EMAIndicator(50).calculate(dataframe)

        return {
            "ema20": float(ema20.iloc[-1]),
            "ema50": float(ema50.iloc[-1])
        }