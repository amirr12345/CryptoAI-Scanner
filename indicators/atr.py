import pandas as pd

from indicators.base_indicator import BaseIndicator


class ATRIndicator(BaseIndicator):
    """
    Average True Range (ATR)
    """

    def __init__(self, period: int = 14):
        self.period = period

    def calculate(self, data: pd.DataFrame) -> pd.Series:

        high = data["high"]
        low = data["low"]
        close = data["close"]

        previous_close = close.shift(1)

        tr = pd.concat(
            [
                high - low,
                (high - previous_close).abs(),
                (low - previous_close).abs(),
            ],
            axis=1,
        ).max(axis=1)

        atr = tr.rolling(self.period).mean()

        return atr