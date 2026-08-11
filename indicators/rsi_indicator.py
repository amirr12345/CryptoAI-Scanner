from __future__ import annotations

import pandas as pd

from indicators.base_indicator import BaseIndicator


class RSIIndicator(BaseIndicator):
    """
    Relative Strength Index indicator.
    """

    def __init__(self, period: int = 14):
        if period <= 0:
            raise ValueError("RSI period must be greater than zero.")

        self.period = period

    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        if "close" not in data.columns:
            raise ValueError("Missing required column: close")

        close = data["close"]

        delta = close.diff()

        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        average_gain = gain.ewm(
            alpha=1 / self.period,
            adjust=False,
            min_periods=self.period,
        ).mean()

        average_loss = loss.ewm(
            alpha=1 / self.period,
            adjust=False,
            min_periods=self.period,
        ).mean()

        relative_strength = average_gain / average_loss.replace(0, pd.NA)

        rsi = 100 - (
            100 / (1 + relative_strength)
        )

        # When there is gain but zero loss, RSI should be 100.
        rsi = rsi.mask(
            (average_loss == 0) & (average_gain > 0),
            100.0,
        )

        # When neither gain nor loss exists, RSI is neutral.
        rsi = rsi.mask(
            (average_gain == 0) & (average_loss == 0),
            50.0,
        )

        return pd.DataFrame(
            {
                "rsi": rsi,
            },
            index=data.index,
        )