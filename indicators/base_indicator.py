from __future__ import annotations

from abc import ABC, abstractmethod
import pandas as pd


class BaseIndicator(ABC):
    """
    Base class for all indicators.
    """

    @abstractmethod
    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate indicator values and return a DataFrame.
        """
        raise NotImplementedError