import pandas as pd

from indicators.indicator_engine import IndicatorEngine
from signals.detector_engine import DetectorEngine
from signals.detectors.bollinger_breakout import BollingerBreakoutDetector
from signals.detectors.ema_cross import EMACrossDetector
from signals.detectors.macd_cross import MACDCrossDetector
from signals.detectors.volume_confirmation import VolumeConfirmationDetector


def test_indicator_engine_to_detector_engine_pipeline():
    rows = 60

    df = pd.DataFrame(
        {
            "open": list(range(100, 100 + rows)),
            "high": list(range(102, 102 + rows)),
            "low": list(range(98, 98 + rows)),
            "close": list(range(100, 100 + rows)),
            "volume": [1000] * rows,
        }
    )

    indicator_engine = IndicatorEngine()
    enriched = indicator_engine.calculate(df)

    detector_engine = DetectorEngine(
        [
            EMACrossDetector(),
            MACDCrossDetector(),
            BollingerBreakoutDetector(),
            VolumeConfirmationDetector(),
        ]
    )

    results = detector_engine.run(enriched)

    assert len(results) == 4

    assert results[0].detector == "EMA"
    assert results[1].detector == "MACD"
    assert results[2].detector == "BOLLINGER"
    assert results[3].detector == "VOLUME"

    assert all(result.score is not None for result in results)
    assert all(0.0 <= result.confidence <= 1.0 for result in results)