import pandas as pd

from signals.detectors.volume_confirmation import (
    VolumeConfirmationDetector,
)


def test_strong_confirmation():

    df = pd.DataFrame(
        {
            "volume": [100] * 19 + [300],
            "volume_sma20": [100] * 20,
            "volume_ratio": [1.0] * 19 + [3.0],
        }
    )

    detector = VolumeConfirmationDetector()

    result = detector.detect(df)

    assert result.detector == "VOLUME"
    assert result.signal == "STRONG_CONFIRMATION"
    assert result.score == 15


def test_weak_confirmation():

    df = pd.DataFrame(
        {
            "volume": [100] * 19 + [120],
            "volume_sma20": [100] * 20,
            "volume_ratio": [1.0] * 19 + [1.20],
        }
    )

    detector = VolumeConfirmationDetector()

    result = detector.detect(df)

    assert result.signal == "WEAK_CONFIRMATION"
    assert result.score == 8


def test_no_confirmation():

    df = pd.DataFrame(
        {
            "volume": [100] * 20,
            "volume_sma20": [100] * 20,
            "volume_ratio": [1.0] * 20,
        }
    )

    detector = VolumeConfirmationDetector()

    result = detector.detect(df)

    assert result.signal == "NO_CONFIRMATION"
    assert result.score == 0