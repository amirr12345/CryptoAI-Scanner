from __future__ import annotations

import numpy as np
import pandas as pd

from indicators.base_indicator import BaseIndicator


class VWAPIndicator(BaseIndicator):
    """
    Volume Weighted Average Price indicator.

    Uses candle-based typical price:

        typical_price = (high + low + close) / 3

    Then calculates cumulative:

        VWAP =
            sum(typical_price * volume)
            /
            sum(volume)

    Required columns:
        high
        low
        close
        volume

    The calculation is cumulative over the supplied DataFrame.
    """

    OUTPUT_COLUMN = "vwap"

    REQUIRED_COLUMNS = {
        "high",
        "low",
        "close",
        "volume",
    }

    def calculate(
        self,
        data: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Calculate VWAP and return a single-column DataFrame.
        """

        if data.empty:
            return pd.DataFrame(
                index=data.index,
                columns=[self.OUTPUT_COLUMN],
            )

        missing = (
            self.REQUIRED_COLUMNS
            - set(data.columns)
        )

        if missing:
            raise ValueError(
                "Missing required columns: "
                + ", ".join(sorted(missing))
            )

        high = pd.to_numeric(
            data["high"],
            errors="coerce",
        )

        low = pd.to_numeric(
            data["low"],
            errors="coerce",
        )

        close = pd.to_numeric(
            data["close"],
            errors="coerce",
        )

        volume = pd.to_numeric(
            data["volume"],
            errors="coerce",
        )

        if (
            high.isna().any()
            or low.isna().any()
            or close.isna().any()
            or volume.isna().any()
        ):
            raise ValueError(
                "VWAP input contains non-numeric values."
            )

        if (
            not np.isfinite(high.to_numpy()).all()
            or not np.isfinite(low.to_numpy()).all()
            or not np.isfinite(close.to_numpy()).all()
            or not np.isfinite(volume.to_numpy()).all()
        ):
            raise ValueError(
                "VWAP input contains non-finite values."
            )

        if (volume < 0).any():
            raise ValueError(
                "VWAP volume cannot be negative."
            )

        typical_price = (
            high + low + close
        ) / 3.0

        weighted_price = (
            typical_price * volume
        )

        cumulative_volume = volume.cumsum()

        cumulative_weighted_price = (
            weighted_price.cumsum()
        )

        vwap = pd.Series(
            np.nan,
            index=data.index,
            dtype=float,
        )

        nonzero_volume = cumulative_volume > 0

        vwap.loc[nonzero_volume] = (
            cumulative_weighted_price.loc[
                nonzero_volume
            ]
            / cumulative_volume.loc[
                nonzero_volume
            ]
        )

        return pd.DataFrame(
            {
                self.OUTPUT_COLUMN: vwap,
            },
            index=data.index,
        )