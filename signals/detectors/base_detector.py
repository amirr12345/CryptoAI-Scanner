from abc import ABC, abstractmethod
import pandas as pd


class BaseDetector(ABC):
    """
    Base class for all signal detectors.
    """

    @abstractmethod
    def detect(self, df: pd.DataFrame):
        """Detect trading signal."""
        raise NotImplementedError
