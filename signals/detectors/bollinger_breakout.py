from __future__ import annotations

import pandas as pd

from models.detector_result import DetectorResult
from signals.detectors.base_detector import BaseDetector


class BollingerBreakoutDetector(BaseDetector):
    """
    Detect Bollinger Band breakouts.

    Expected columns:

        upper_band
        lower_band
        close
    """

    def detect(self, df: pd.DataFrame) -> DetectorResult:

        if len(df) < 1:
            return DetectorResult(
                detector="BOLLINGER",
                signal="NO_SIGNAL",
                score=0,
                confidence=0.0,
                description="Not enough candles.",
            )

        close = df["close"].iloc[-1]
        upper = df["upper_band"].iloc[-1]
        lower = df["lower_band"].iloc[-1]

        # Bullish breakout

        if close > upper:

            return DetectorResult(
                detector="BOLLINGER",
                signal="BREAKOUT_UP",
                score=20,
                confidence=0.85,
                description="Price closed above upper Bollinger Band.",
            )

        # Bearish breakout

        if close < lower:

            return DetectorResult(
                detector="BOLLINGER",
                signal="BREAKOUT_DOWN",
                score=-20,
                confidence=0.85,
                description="Price closed below lower Bollinger Band.",
            )

        return DetectorResult(
            detector="BOLLINGER",
            signal="NO_SIGNAL",
            score=0,
            confidence=0.0,
            description="Price inside Bollinger Bands.",
        )