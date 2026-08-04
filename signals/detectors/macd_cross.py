from enum import Enum

import pandas as pd

from signals.detectors.base_detector import BaseDetector


class MACDCrossType(Enum):
    BULLISH_CROSS = "BULLISH_CROSS"
    BEARISH_CROSS = "BEARISH_CROSS"
    NO_CROSS = "NO_CROSS"


class MACDCrossDetector(BaseDetector):
    """
    Detect MACD signal line crossovers.
    """

    def detect(self, df: pd.DataFrame) -> MACDCrossType:

        if len(df) < 2:
            return MACDCrossType.NO_CROSS

        macd = df["macd"]
        signal = df["signal"]

        previous_macd = macd.iloc[-2]
        previous_signal = signal.iloc[-2]

        current_macd = macd.iloc[-1]
        current_signal = signal.iloc[-1]

        if previous_macd < previous_signal and current_macd > current_signal:
            return MACDCrossType.BULLISH_CROSS

        if previous_macd > previous_signal and current_macd < current_signal:
            return MACDCrossType.BEARISH_CROSS

        return MACDCrossType.NO_CROSS