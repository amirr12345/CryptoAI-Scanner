import pandas as pd

from signals.detectors.volume_confirmation import VolumeConfirmationDetector


def test_high_volume():

    detector = VolumeConfirmationDetector()

    df = pd.DataFrame({
        "volume": [100] * 19 + [200]
    })

    result = detector.detect(df)

    assert result.signal == "HIGH_VOLUME"


def test_low_volume():

    detector = VolumeConfirmationDetector()

    df = pd.DataFrame({
        "volume": [100] * 19 + [50]
    })

    result = detector.detect(df)

    assert result.signal == "LOW_VOLUME"