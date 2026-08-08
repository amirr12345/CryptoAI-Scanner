import pandas as pd

from models.detector_result import DetectorResult
from signals.detector_engine import DetectorEngine
from signals.detectors.ema_cross import EMACrossDetector
from signals.detectors.macd_cross import MACDCrossDetector
from signals.detectors.volume_confirmation import VolumeConfirmationDetector


def test_detector_engine_with_real_detectors():

    df = pd.DataFrame(
        {
            "ema20": [10] * 19 + [15],
            "ema50": [12] * 19 + [14],
            "macd": [1.0] * 19 + [2.0],
            "signal": [1.5] * 19 + [1.8],
            "volume": [100] * 19 + [150],
            "volume_sma20": [100] * 20,
            "volume_ratio": [1.0] * 19 + [1.5],
        }
    )

    engine = DetectorEngine(
        [
            EMACrossDetector(),
            MACDCrossDetector(),
            VolumeConfirmationDetector(),
        ]
    )

    results = engine.run(df)

    assert len(results) == 3

    assert all(
        isinstance(result, DetectorResult)
        for result in results
    )

    assert results[0].detector == "EMA"
    assert results[0].signal == "GOLDEN_CROSS"

    assert results[1].detector == "MACD"
    assert results[1].signal == "BULLISH_CROSS"

    assert results[2].detector == "VOLUME"