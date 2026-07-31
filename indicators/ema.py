import pandas as pd
from indicators.base_indicator import BaseIndicator


class EMAIndicator(BaseIndicator):

    def __init__(self, period: int):
        self.period = period

    def calculate(self, data: pd.DataFrame):

        return (
            data["close"]
            .ewm(span=self.period, adjust=False)
            .mean()
        )