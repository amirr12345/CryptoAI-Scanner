from __future__ import annotations

import pandas as pd

from indicators.base_indicator import BaseIndicator


class VolumeIndicator(BaseIndicator):
    """
    Calculate volume indicators.

    Output columns:

        volume_sma20
        volume_ratio
    """

    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:

        df = data.copy()

        if "volume" not in df.columns:
            raise ValueError("Column 'volume' not found.")

        # Average Volume (20)

        df["volume_sma20"] = (
            df["volume"]
            .rolling(window=20)
            .mean()
        )

        # Current Volume / Average Volume

        df["volume_ratio"] = (
            df["volume"] /
            df["volume_sma20"]
        )

        return df