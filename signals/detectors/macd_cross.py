from __future__ import annotations

import pandas as pd

from models.detector_result import DetectorResult
from signals.constants import (
    BEARISH_CROSS,
    BULLISH_CROSS,
    MACD,
    MACD_BEARISH_SCORE,
    MACD_BULLISH_SCORE,
    NO_CROSS,
)
from signals.detectors.base_detector import BaseDetector


class MACDCrossDetector(BaseDetector):
    """
    Detect MACD signal line crossovers.
    """

    def detect(self, df: pd.DataFrame) -> DetectorResult:

        if len(df) < 2:
            return DetectorResult(
                detector=MACD,
                signal=NO_CROSS,
                score=0,
                confidence=0.0,
                description="Not enough data.",
            )

        required_columns = {"macd", "signal"}
        missing = required_columns - set(df.columns)

        if missing:
            raise ValueError(
                f"Missing required columns: {', '.join(sorted(missing))}"
            )

        previous_macd = df["macd"].iloc[-2]
        previous_signal = df["signal"].iloc[-2]

        current_macd = df["macd"].iloc[-1]
        current_signal = df["signal"].iloc[-1]

        # Bullish Cross
        if previous_macd < previous_signal and current_macd > current_signal:
            return DetectorResult(
                detector=MACD,
                signal=BULLISH_CROSS,
                score=MACD_BULLISH_SCORE,
                confidence=0.90,
                description="MACD crossed above Signal line.",
            )

        # Bearish Cross
        if previous_macd > previous_signal and current_macd < current_signal:
            return DetectorResult(
                detector=MACD,
                signal=BEARISH_CROSS,
                score=MACD_BEARISH_SCORE,
                confidence=0.90,
                description="MACD crossed below Signal line.",
            )

        return DetectorResult(
            detector=MACD,
            signal=NO_CROSS,
            score=0,
            confidence=0.0,
            description="No MACD crossover detected.",
        )