import pandas as pd

from signals.detectors.bollinger_breakout import (
    BollingerBreakoutDetector,
)


def test_breakout_up():

    df = pd.DataFrame(
        {
            "close": [120],
            "upper_band": [110],
            "lower_band": [90],
        }
    )

    detector = BollingerBreakoutDetector()

    result = detector.detect(df)

    assert result.detector == "BOLLINGER"

    assert result.signal == "BREAKOUT_UP"

    assert result.score == 20


def test_breakout_down():

    df = pd.DataFrame(
        {
            "close": [80],
            "upper_band": [110],
            "lower_band": [90],
        }
    )

    detector = BollingerBreakoutDetector()

    result = detector.detect(df)

    assert result.detector == "BOLLINGER"

    assert result.signal == "BREAKOUT_DOWN"

    assert result.score == -20


def test_no_breakout():

    df = pd.DataFrame(
        {
            "close": [100],
            "upper_band": [110],
            "lower_band": [90],
        }
    )

    detector = BollingerBreakoutDetector()

    result = detector.detect(df)

    assert result.detector == "BOLLINGER"

    assert result.signal == "NO_SIGNAL"

    assert result.score == 0