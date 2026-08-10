from __future__ import annotations

import pandas as pd

from models.detector_result import DetectorResult
from signals.constants import (
    DEATH_CROSS,
    EMA,
    EMA_DEATH_SCORE,
    EMA_GOLDEN_SCORE,
    GOLDEN_CROSS,
    NO_CROSS,
)
from signals.detectors.base_detector import BaseDetector


class EMACrossDetector(BaseDetector):
    """
    Detect EMA20 / EMA50 crossover.
    """

    def detect(self, df: pd.DataFrame) -> DetectorResult:

        if len(df) < 2:
            return DetectorResult(
                detector=EMA,
                signal=NO_CROSS,
                score=0,
                confidence=0.0,
                description="Not enough candles.",
            )

        required_columns = {"ema20", "ema50"}
        missing = required_columns - set(df.columns)

        if missing:
            raise ValueError(
                f"Missing required columns: {', '.join(sorted(missing))}"
            )

        previous20 = df["ema20"].iloc[-2]
        previous50 = df["ema50"].iloc[-2]

        current20 = df["ema20"].iloc[-1]
        current50 = df["ema50"].iloc[-1]

        # Golden Cross
        if previous20 < previous50 and current20 > current50:
            return DetectorResult(
                detector=EMA,
                signal=GOLDEN_CROSS,
                score=EMA_GOLDEN_SCORE,
                confidence=0.95,
                description="EMA20 crossed above EMA50.",
            )

        # Death Cross
        if previous20 > previous50 and current20 < current50:
            return DetectorResult(
                detector=EMA,
                signal=DEATH_CROSS,
                score=EMA_DEATH_SCORE,
                confidence=0.95,
                description="EMA20 crossed below EMA50.",
            )

        return DetectorResult(
            detector=EMA,
            signal=NO_CROSS,
            score=0,
            confidence=0.0,
            description="No EMA crossover detected.",
        )