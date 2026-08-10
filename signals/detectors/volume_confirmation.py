from __future__ import annotations

import pandas as pd

from models.detector_result import DetectorResult
from signals.constants import (
    NO_CONFIRMATION,
    STRONG_CONFIRMATION,
    WEAK_CONFIRMATION,
    VOLUME,
)
from signals.detector_config import DetectorConfig
from signals.detectors.base_detector import BaseDetector


class VolumeConfirmationDetector(BaseDetector):
    """
    Confirm trading signals using trading volume.

    Required columns:
        volume
        volume_sma20
        volume_ratio
    """

    def detect(self, df: pd.DataFrame) -> DetectorResult:

        if len(df) < 20:
            return DetectorResult(
                detector=VOLUME,
                signal=NO_CONFIRMATION,
                score=0,
                confidence=0.0,
                description="Not enough candles.",
            )

        required_columns = {
            "volume",
            "volume_sma20",
            "volume_ratio",
        }

        missing = required_columns - set(df.columns)

        if missing:
            raise ValueError(
                f"Missing required columns: {', '.join(sorted(missing))}"
            )

        ratio = float(df["volume_ratio"].iloc[-1])

        # Strong confirmation
        if ratio >= DetectorConfig.VOLUME_STRONG_RATIO:
            return DetectorResult(
                detector=VOLUME,
                signal=STRONG_CONFIRMATION,
                score=DetectorConfig.VOLUME_WEIGHT,
                confidence=0.95,
                description="Trading volume is much higher than average.",
            )

        # Weak confirmation
        if ratio >= DetectorConfig.VOLUME_WEAK_RATIO:
            return DetectorResult(
                detector=VOLUME,
                signal=WEAK_CONFIRMATION,
                score=max(
                    1,
                    (DetectorConfig.VOLUME_WEIGHT + 1) // 2,
                ),
                confidence=0.75,
                description="Trading volume is slightly above average.",
            )

        return DetectorResult(
            detector=VOLUME,
            signal=NO_CONFIRMATION,
            score=0,
            confidence=0.0,
            description="Volume does not confirm the signal.",
        )