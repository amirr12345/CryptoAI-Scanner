import pandas as pd

from models.detector_result import DetectorResult
from signals.constants import (
    BOLLINGER,
    UPPER_BREAKOUT,
    LOWER_BREAKOUT,
    INSIDE_BANDS,
    BOLLINGER_BREAKOUT_SCORE,
)
from signals.detectors.base_detector import BaseDetector


class BollingerBreakoutDetector(BaseDetector):
    """
    Detect Bollinger Band breakouts.
    """

    def detect(self, df: pd.DataFrame) -> DetectorResult:

        if len(df) == 0:
            return DetectorResult(
                detector=BOLLINGER,
                signal=INSIDE_BANDS,
                score=0,
                confidence=0.0,
                description="No data.",
            )

        close = df["close"].iloc[-1]
        upper = df["bb_upper"].iloc[-1]
        lower = df["bb_lower"].iloc[-1]

        if close > upper:
            return DetectorResult(
                detector=BOLLINGER,
                signal=UPPER_BREAKOUT,
                score=-BOLLINGER_BREAKOUT_SCORE,
                confidence=0.85,
                description="Price closed above upper Bollinger Band.",
            )

        if close < lower:
            return DetectorResult(
                detector=BOLLINGER,
                signal=LOWER_BREAKOUT,
                score=BOLLINGER_BREAKOUT_SCORE,
                confidence=0.85,
                description="Price closed below lower Bollinger Band.",
            )

        return DetectorResult(
            detector=BOLLINGER,
            signal=INSIDE_BANDS,
            score=0,
            confidence=0.50,
            description="Price is inside Bollinger Bands.",
        )