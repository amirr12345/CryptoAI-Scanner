import pandas as pd


class EMAIndicator:

    @staticmethod
    def calculate(close_prices, period=20):

        df = pd.DataFrame(close_prices, columns=["close"])

        ema = df["close"].ewm(span=period, adjust=False).mean()

        return ema