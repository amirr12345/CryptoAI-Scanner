from __future__ import annotations

import pandas as pd

from indicators.base_indicator import BaseIndicator


class ATRIndicator(BaseIndicator):
    """
    Average True Range indicator.

    This implementation uses a rolling arithmetic mean of True Range.
    """

    def __init__(self, period: int = 14):
        if period <= 0:
            raise ValueError("ATR period must be greater than zero.")

        self.period = period

    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        required_columns = {"high", "low", "close"}

        missing = required_columns - set(data.columns)

        if missing:
            raise ValueError(
                "Missing required columns: "
                f"{', '.join(sorted(missing))}"
            )

        high = data["high"]
        low = data["low"]
        close = data["close"]

        previous_close = close.shift(1)

        true_range = pd.concat(
            [
                high - low,
                (high - previous_close).abs(),
                (low - previous_close).abs(),
            ],
            axis=1,
        ).max(axis=1)

        atr = true_range.rolling(
            window=self.period,
            min_periods=self.period,
        ).mean()

        return pd.DataFrame(
            {
                "atr": atr,
            },
            index=data.index,
        )