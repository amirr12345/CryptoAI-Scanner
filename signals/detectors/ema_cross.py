import pandas as pd

from models.detector_result import DetectorResult
from signals.detectors.base_detector import BaseDetector


class EMACrossDetector(BaseDetector):
    """
    Detect EMA20 / EMA50 crossover.
    """

    def detect(self, df: pd.DataFrame) -> DetectorResult:

        ema20 = df["ema20"]
        ema50 = df["ema50"]

        if len(df) < 2:
            return DetectorResult(
                detector="EMA",
                signal="NO_CROSS",
                score=0,
                confidence=0.0,
                description="Not enough data.",
            )

        previous20 = ema20.iloc[-2]
        previous50 = ema50.iloc[-2]

        current20 = ema20.iloc[-1]
        current50 = ema50.iloc[-1]

        # Golden Cross
        if previous20 < previous50 and current20 > current50:
            return DetectorResult(
                detector="EMA",
                signal="GOLDEN_CROSS",
                score=25,
                confidence=0.90,
                description="EMA20 crossed above EMA50.",
            )

        # Death Cross
        if previous20 > previous50 and current20 < current50:
            return DetectorResult(
                detector="EMA",
                signal="DEATH_CROSS",
                score=-25,
                confidence=0.90,
                description="EMA20 crossed below EMA50.",
            )

        # No Cross
        return DetectorResult(
            detector="EMA",
            signal="NO_CROSS",
            score=0,
            confidence=0.0,
            description="No EMA crossover detected.",
        )