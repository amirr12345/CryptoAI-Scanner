from __future__ import annotations

import pandas as pd

from indicators.base_indicator import BaseIndicator


class MACDIndicator(BaseIndicator):
    """
    Moving Average Convergence Divergence indicator.
    """

    def __init__(
        self,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
    ):
        if fast <= 0:
            raise ValueError("MACD fast period must be greater than zero.")

        if slow <= 0:
            raise ValueError("MACD slow period must be greater than zero.")

        if signal <= 0:
            raise ValueError(
                "MACD signal period must be greater than zero."
            )

        if fast >= slow:
            raise ValueError(
                "MACD fast period must be smaller than slow period."
            )

        self.fast = fast
        self.slow = slow
        self.signal = signal

    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        if "close" not in data.columns:
            raise ValueError("Missing required column: close")

        close = data["close"]

        ema_fast = close.ewm(
            span=self.fast,
            adjust=False,
        ).mean()

        ema_slow = close.ewm(
            span=self.slow,
            adjust=False,
        ).mean()

        macd = ema_fast - ema_slow

        signal = macd.ewm(
            span=self.signal,
            adjust=False,
        ).mean()

        histogram = macd - signal

        return pd.DataFrame(
            {
                "macd": macd,
                "signal": signal,
                "histogram": histogram,
            },
            index=data.index,
        )