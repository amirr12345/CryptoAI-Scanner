import pandas as pd

from signals.detectors.ema_cross import EMACrossDetector


def test_golden_cross():

    df = pd.DataFrame({
        "ema20": [10, 15],
        "ema50": [12, 14],
    })

    detector = EMACrossDetector()

    result = detector.detect(df)

    assert result.signal == "GOLDEN_CROSS"
    assert result.detector == "EMA"
    assert result.score == 25


def test_death_cross():

    df = pd.DataFrame({
        "ema20": [15, 10],
        "ema50": [14, 12],
    })

    detector = EMACrossDetector()

    result = detector.detect(df)

    assert result.signal == "DEATH_CROSS"
    assert result.detector == "EMA"
    assert result.score == -25


def test_no_cross():

    df = pd.DataFrame({
        "ema20": [15, 16],
        "ema50": [10, 11],
    })

    detector = EMACrossDetector()

    result = detector.detect(df)

    assert result.signal == "NO_CROSS"
    assert result.detector == "EMA"
    assert result.score == 0