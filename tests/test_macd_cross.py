import pandas as pd

from signals.detectors.macd_cross import MACDCrossDetector


def test_bullish_cross():

    detector = MACDCrossDetector()

    df = pd.DataFrame(
        {
            "macd": [-2, 1],
            "signal": [-1, 0],
        }
    )

    result = detector.detect(df)

    assert result.detector == "MACD"
    assert result.signal == "BULLISH_CROSS"
    assert result.score == 20


def test_bearish_cross():

    detector = MACDCrossDetector()

    df = pd.DataFrame(
        {
            "macd": [2, -1],
            "signal": [1, 0],
        }
    )

    result = detector.detect(df)

    assert result.detector == "MACD"
    assert result.signal == "BEARISH_CROSS"
    assert result.score == -20


def test_no_cross():

    detector = MACDCrossDetector()

    df = pd.DataFrame(
        {
            "macd": [2, 3],
            "signal": [1, 2],
        }
    )

    result = detector.detect(df)

    assert result.detector == "MACD"
    assert result.signal == "NO_CROSS"
    assert result.score == 0