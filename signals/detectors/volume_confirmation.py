import pandas as pd

from models.detector_result import DetectorResult
from signals.constants import (
    VOLUME,
    HIGH_VOLUME,
    LOW_VOLUME,
    VOLUME_HIGH_SCORE,
    VOLUME_LOW_SCORE,
)
from signals.detectors.base_detector import BaseDetector


class VolumeConfirmationDetector(BaseDetector):
    """
    Detect whether the latest volume confirms the move.
    """

    def detect(self, df: pd.DataFrame) -> DetectorResult:

        if len(df) < 20:
            return DetectorResult(
                detector=VOLUME,
                signal=LOW_VOLUME,
                score=0,
                confidence=0.0,
                description="Not enough volume history.",
            )

        avg_volume = df["volume"].tail(20).mean()
        current_volume = df["volume"].iloc[-1]

        if current_volume >= avg_volume:
            return DetectorResult(
                detector=VOLUME,
                signal=HIGH_VOLUME,
                score=VOLUME_HIGH_SCORE,
                confidence=0.80,
                description="Volume confirms the move.",
            )

        return DetectorResult(
            detector=VOLUME,
            signal=LOW_VOLUME,
            score=VOLUME_LOW_SCORE,
            confidence=0.60,
            description="Weak trading volume.",
        )