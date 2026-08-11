from __future__ import annotations

import pandas as pd

from indicators.base_indicator import BaseIndicator


class BollingerIndicator(BaseIndicator):
    """
    Bollinger Bands indicator.
    """

    def __init__(
        self,
        period: int = 20,
        std_dev: float = 2.0,
    ):
        if period <= 0:
            raise ValueError(
                "Bollinger period must be greater than zero."
            )

        if std_dev <= 0:
            raise ValueError(
                "Bollinger standard deviation must be greater than zero."
            )

        self.period = period
        self.std_dev = std_dev

    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        if "close" not in data.columns:
            raise ValueError("Missing required column: close")

        close = data["close"]

        middle = close.rolling(
            window=self.period,
            min_periods=self.period,
        ).mean()

        std = close.rolling(
            window=self.period,
            min_periods=self.period,
        ).std()

        upper = middle + (std * self.std_dev)
        lower = middle - (std * self.std_dev)

        bandwidth = (upper - lower) / middle.where(middle != 0)

        return pd.DataFrame(
            {
                "middle_band": middle,
                "upper_band": upper,
                "lower_band": lower,
                "bandwidth": bandwidth,
            },
            index=data.index,
        )