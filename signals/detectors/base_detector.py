from abc import ABC, abstractmethod

import pandas as pd

from models.detector_result import DetectorResult


class BaseDetector(ABC):
    """
    Base class for all signal detectors.
    """

    @abstractmethod
    def detect(self, df: pd.DataFrame) -> DetectorResult:
        """
        Execute detector and return DetectorResult.
        """
        raise NotImplementedError