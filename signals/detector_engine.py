from collections.abc import Sequence

import pandas as pd

from models.detector_result import DetectorResult
from signals.detectors.base_detector import BaseDetector


class DetectorEngine:
    """
    Executes registered detectors and collects their results.
    """

    def __init__(self, detectors: Sequence[BaseDetector]):
        self.detectors = list(detectors)

    def run(self, df: pd.DataFrame) -> list[DetectorResult]:
        results: list[DetectorResult] = []

        for detector in self.detectors:
            result = detector.detect(df)

            if not isinstance(result, DetectorResult):
                raise TypeError(
                    f"{detector.__class__.__name__}.detect() "
                    "must return DetectorResult"
                )

            results.append(result)

        return results