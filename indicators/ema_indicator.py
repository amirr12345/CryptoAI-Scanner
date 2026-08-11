from __future__ import annotations

import pandas as pd

from indicators.base_indicator import BaseIndicator


class EMAIndicator(BaseIndicator):
    """
    Exponential Moving Average indicator.
    """

    def __init__(self, period: int):
        if period <= 0:
            raise ValueError("EMA period must be greater than zero.")

        self.period = period

    @property
    def column_name(self) -> str:
        return f"ema{self.period}"

    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        if "close" not in data.columns:
            raise ValueError("Missing required column: close")

        ema = data["close"].ewm(
            span=self.period,
            adjust=False,
        ).mean()

        return pd.DataFrame(
            {
                self.column_name: ema,
            },
            index=data.index,
        )