import pandas as pd

from signals.detectors.ema_cross import (
    EMACrossDetector,
    EMACrossType,
)


def test_golden_cross():

    df = pd.DataFrame({
        "ema20": [10, 15],
        "ema50": [12, 14],
    })

    detector = EMACrossDetector()

    result = detector.detect(df)

    assert result == EMACrossType.GOLDEN_CROSS


def test_death_cross():

    df = pd.DataFrame({
        "ema20": [15, 10],
        "ema50": [14, 12],
    })

    detector = EMACrossDetector()

    result = detector.detect(df)

    assert result == EMACrossType.DEATH_CROSS


def test_no_cross():

    df = pd.DataFrame({
        "ema20": [15, 16],
        "ema50": [10, 11],
    })

    detector = EMACrossDetector()

    result = detector.detect(df)

    assert result == EMACrossType.NO_CROSS