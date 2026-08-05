import pandas as pd

from signals.detectors.bollinger_breakout import BollingerBreakoutDetector


def test_upper_breakout():

    detector = BollingerBreakoutDetector()

    df = pd.DataFrame(
        {
            "close": [110],
            "bb_upper": [100],
            "bb_lower": [80],
        }
    )

    result = detector.detect(df)

    assert result.detector == "BOLLINGER"
    assert result.signal == "UPPER_BREAKOUT"


def test_lower_breakout():

    detector = BollingerBreakoutDetector()

    df = pd.DataFrame(
        {
            "close": [70],
            "bb_upper": [100],
            "bb_lower": [80],
        }
    )

    result = detector.detect(df)

    assert result.detector == "BOLLINGER"
    assert result.signal == "LOWER_BREAKOUT"


def test_inside_bands():

    detector = BollingerBreakoutDetector()

    df = pd.DataFrame(
        {
            "close": [90],
            "bb_upper": [100],
            "bb_lower": [80],
        }
    )

    result = detector.detect(df)

    assert result.detector == "BOLLINGER"
    assert result.signal == "INSIDE_BANDS"