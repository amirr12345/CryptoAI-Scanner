import pandas as pd

from models.detector_result import DetectorResult
from signals.detector_engine import DetectorEngine
from signals.detectors.base_detector import BaseDetector


class DummyDetector(BaseDetector):

    def detect(self, df):

        return DetectorResult(
            detector="Dummy",
            signal="TEST",
            score=10,
            confidence=1.0,
            description="Dummy detector",
        )


def test_detector_engine():

    df = pd.DataFrame({"close": [1, 2, 3]})

    engine = DetectorEngine([
        DummyDetector(),
    ])

    results = engine.run(df)

    assert len(results) == 1

    assert results[0].detector == "Dummy"

    assert results[0].signal == "TEST"

    assert results[0].score == 10