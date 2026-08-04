import pandas as pd

from signals.detectors.macd_cross import (
    MACDCrossDetector,
    MACDCrossType,
)


def test_bullish_cross():

    detector = MACDCrossDetector()

    df = pd.DataFrame({
        "macd": [-2, 1],
        "signal": [-1, 0],
    })

    result = detector.detect(df)

    assert result == MACDCrossType.BULLISH_CROSS

def test_bearish_cross():

    detector = MACDCrossDetector()

    df = pd.DataFrame({
        "macd": [2, -1],
        "signal": [1, 0],
    })

    result = detector.detect(df)

    assert result == MACDCrossType.BEARISH_CROSS


def test_no_cross():

    detector = MACDCrossDetector()

    df = pd.DataFrame({
        "macd": [2, 3],
        "signal": [1, 2],
    })

    result = detector.detect(df)

    assert result == MACDCrossType.NO_CROSS    