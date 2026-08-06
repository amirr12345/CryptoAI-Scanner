from __future__ import annotations

from typing import Iterable

import pandas as pd

from models.detector_result import DetectorResult
from signals.detectors.base_detector import BaseDetector


class DetectorEngine:
    """
    Executes all registered detectors and returns
    a list of DetectorResult objects.
    """

    def __init__(self, detectors: Iterable[BaseDetector]):
        self.detectors = list(detectors)

    def run(self, df: pd.DataFrame) -> list[DetectorResult]:
        results: list[DetectorResult] = []

        for detector in self.detectors:
            result = detector.detect(df)

            if result is not None:
                results.append(result)

        return results