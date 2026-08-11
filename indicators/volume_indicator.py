from __future__ import annotations

import pandas as pd

from indicators.base_indicator import BaseIndicator


class VolumeIndicator(BaseIndicator):
    """
    Volume moving average and volume ratio indicator.
    """

    def __init__(self, period: int = 20):
        if period <= 0:
            raise ValueError(
                "Volume period must be greater than zero."
            )

        self.period = period

    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        if "volume" not in data.columns:
            raise ValueError("Missing required column: volume")

        volume = data["volume"]

        volume_sma = volume.rolling(
            window=self.period,
            min_periods=self.period,
        ).mean()

        volume_ratio = volume / volume_sma.replace(0, pd.NA)

        return pd.DataFrame(
            {
                "volume_sma20": volume_sma,
                "volume_ratio": volume_ratio,
            },
            index=data.index,
        )