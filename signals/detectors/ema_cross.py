from enum import Enum

import pandas as pd

from signals.detectors.base_detector import BaseDetector


class EMACrossType(Enum):
    GOLDEN_CROSS = "GOLDEN_CROSS"
    DEATH_CROSS = "DEATH_CROSS"
    NO_CROSS = "NO_CROSS"


class EMACrossDetector(BaseDetector):

    def detect(self, df: pd.DataFrame) -> EMACrossType:

        ema20 = df["ema20"]
        ema50 = df["ema50"]

        if len(df) < 2:
            return EMACrossType.NO_CROSS

        previous20 = ema20.iloc[-2]
        previous50 = ema50.iloc[-2]

        current20 = ema20.iloc[-1]
        current50 = ema50.iloc[-1]

        if previous20 < previous50 and current20 > current50:
            return EMACrossType.GOLDEN_CROSS

        if previous20 > previous50 and current20 < current50:
            return EMACrossType.DEATH_CROSS

        return EMACrossType.NO_CROSS