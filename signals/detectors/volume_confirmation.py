from __future__ import annotations

import pandas as pd

from models.detector_result import DetectorResult
from signals.detectors.base_detector import BaseDetector


class VolumeConfirmationDetector(BaseDetector):
    """
    Confirm trading signals using trading volume.

    Required columns:

        volume
        volume_sma20
        volume_ratio
    """

    STRONG_RATIO = 1.50
    WEAK_RATIO = 1.10

    def detect(self, df: pd.DataFrame) -> DetectorResult:

        if len(df) < 20:
            return DetectorResult(
                detector="VOLUME",
                signal="NO_CONFIRMATION",
                score=0,
                confidence=0.0,
                description="Not enough candles.",
            )

        ratio = df["volume_ratio"].iloc[-1]

        if ratio >= self.STRONG_RATIO:

            return DetectorResult(
                detector="VOLUME",
                signal="STRONG_CONFIRMATION",
                score=15,
                confidence=0.95,
                description="Trading volume is much higher than average.",
            )

        if ratio >= self.WEAK_RATIO:

            return DetectorResult(
                detector="VOLUME",
                signal="WEAK_CONFIRMATION",
                score=8,
                confidence=0.75,
                description="Trading volume is slightly above average.",
            )

        return DetectorResult(
            detector="VOLUME",
            signal="NO_CONFIRMATION",
            score=0,
            confidence=0.0,
            description="Volume does not confirm the signal.",
        )