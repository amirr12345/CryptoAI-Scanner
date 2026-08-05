import pandas as pd

from signals.detector_engine import DetectorEngine


class FakeDetector:

    def detect(self, df):
        return "OK"


def test_engine_runs_detector():

    engine = DetectorEngine([
        FakeDetector()
    ])

    df = pd.DataFrame()

    results = engine.run(df)

    assert len(results) == 1