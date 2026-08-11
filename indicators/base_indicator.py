from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class BaseIndicator(ABC):
    """
    Base class for all indicators.

    Every indicator receives a candle DataFrame and returns
    a DataFrame containing its calculated columns.
    """

    @abstractmethod
    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate indicator values.

        Parameters
        ----------
        data:
            Input OHLCV DataFrame.

        Returns
        -------
        pd.DataFrame
            DataFrame containing the indicator output columns.
        """
        raise NotImplementedError