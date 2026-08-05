from __future__ import annotations

from typing import Sequence

import pandas as pd

from models.detector_result import DetectorResult
from signals.detectors.base_detector import BaseDetector


class DetectorEngine:
    """
    Executes all registered detectors and collects their results.
    """

    def __init__(self, detectors: Sequence[BaseDetector]) -> None:
        self._detectors = list(detectors)

    @property
    def detectors(self) -> tuple[BaseDetector, ...]:
        return tuple(self._detectors)

    def run(self, df: pd.DataFrame) -> list[DetectorResult]:
        """
        Execute every detector.

        Returns
        -------
        list[DetectorResult]
        """

        results: list[DetectorResult] = []

        for detector in self._detectors:
            result = detector.detect(df)
            results.append(result)

        return results