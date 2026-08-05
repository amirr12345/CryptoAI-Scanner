import pandas as pd

from models.detector_result import DetectorResult
from signals.detectors.base_detector import BaseDetector


class MACDCrossDetector(BaseDetector):
    """
    Detect MACD signal line crossovers.
    """

    def detect(self, df: pd.DataFrame) -> DetectorResult:

        if len(df) < 2:
            return DetectorResult(
                detector="MACD",
                signal="NO_CROSS",
                score=0,
                confidence=0.0,
                description="Not enough data.",
            )

        macd = df["macd"]
        signal = df["signal"]

        previous_macd = macd.iloc[-2]
        previous_signal = signal.iloc[-2]

        current_macd = macd.iloc[-1]
        current_signal = signal.iloc[-1]

        # Bullish Cross
        if previous_macd < previous_signal and current_macd > current_signal:
            return DetectorResult(
                detector="MACD",
                signal="BULLISH_CROSS",
                score=20,
                confidence=0.90,
                description="MACD crossed above Signal line.",
            )

        # Bearish Cross
        if previous_macd > previous_signal and current_macd < current_signal:
            return DetectorResult(
                detector="MACD",
                signal="BEARISH_CROSS",
                score=-20,
                confidence=0.90,
                description="MACD crossed below Signal line.",
            )

        # No Cross
        return DetectorResult(
            detector="MACD",
            signal="NO_CROSS",
            score=0,
            confidence=0.0,
            description="No MACD crossover detected.",
        )