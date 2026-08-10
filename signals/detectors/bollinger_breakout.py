from __future__ import annotations

import pandas as pd

from models.detector_result import DetectorResult
from signals.constants import (
    BOLLINGER,
    BOLLINGER_BREAKOUT_SCORE,
    BREAKOUT_DOWN,
    BREAKOUT_UP,
    NO_SIGNAL,
)
from signals.detectors.base_detector import BaseDetector


class BollingerBreakoutDetector(BaseDetector):
    """
    Detect Bollinger Band breakouts.

    Required columns:
        upper_band
        lower_band
        close
    """

    def detect(self, df: pd.DataFrame) -> DetectorResult:

        if len(df) < 1:
            return DetectorResult(
                detector=BOLLINGER,
                signal=NO_SIGNAL,
                score=0,
                confidence=0.0,
                description="Not enough candles.",
            )

        required_columns = {
            "close",
            "upper_band",
            "lower_band",
        }

        missing = required_columns - set(df.columns)

        if missing:
            raise ValueError(
                f"Missing required columns: {', '.join(sorted(missing))}"
            )

        close = float(df["close"].iloc[-1])
        upper = float(df["upper_band"].iloc[-1])
        lower = float(df["lower_band"].iloc[-1])

        # Bullish breakout
        if close > upper:
            return DetectorResult(
                detector=BOLLINGER,
                signal=BREAKOUT_UP,
                score=BOLLINGER_BREAKOUT_SCORE,
                confidence=0.85,
                description="Price closed above upper Bollinger Band.",
            )

        # Bearish breakout
        if close < lower:
            return DetectorResult(
                detector=BOLLINGER,
                signal=BREAKOUT_DOWN,
                score=-BOLLINGER_BREAKOUT_SCORE,
                confidence=0.85,
                description="Price closed below lower Bollinger Band.",
            )

        return DetectorResult(
            detector=BOLLINGER,
            signal=NO_SIGNAL,
            score=0,
            confidence=0.0,
            description="Price inside Bollinger Bands.",
        )