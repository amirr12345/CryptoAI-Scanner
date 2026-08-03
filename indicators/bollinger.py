import pandas as pd

from indicators.base_indicator import BaseIndicator


class BollingerIndicator(BaseIndicator):
    """
    Bollinger Bands Indicator
    """

    def __init__(self, period: int = 20, std_dev: float = 2.0):
        self.period = period
        self.std_dev = std_dev

    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:

        close = data["close"]

        middle = close.rolling(self.period).mean()

        std = close.rolling(self.period).std()

        upper = middle + (std * self.std_dev)

        lower = middle - (std * self.std_dev)

        bandwidth = (upper - lower) / middle

        return pd.DataFrame({
            "middle": middle,
            "upper": upper,
            "lower": lower,
            "bandwidth": bandwidth,
        })