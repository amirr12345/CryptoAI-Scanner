import pandas as pd
import pytest

from models.detector_result import DetectorResult
from signals.detector_engine import DetectorEngine


class FakeDetector:
    def detect(self, df: pd.DataFrame) -> DetectorResult:
        return DetectorResult(
            detector="FAKE",
            signal="BUY",
            score=25,
            confidence=0.9,
            description="Fake detector result",
        )


class InvalidDetector:
    def detect(self, df: pd.DataFrame):
        return "INVALID"


def test_detector_engine_runs_detector():

    df = pd.DataFrame({"close": [100, 101, 102]})

    engine = DetectorEngine([FakeDetector()])

    results = engine.run(df)

    assert len(results) == 1
    assert isinstance(results[0], DetectorResult)
    assert results[0].detector == "FAKE"
    assert results[0].signal == "BUY"
    assert results[0].score == 25


def test_detector_engine_supports_multiple_detectors():

    df = pd.DataFrame({"close": [100, 101, 102]})

    engine = DetectorEngine([
        FakeDetector(),
        FakeDetector(),
    ])

    results = engine.run(df)

    assert len(results) == 2


def test_detector_engine_with_no_detectors():

    df = pd.DataFrame({"close": [100, 101, 102]})

    engine = DetectorEngine([])

    results = engine.run(df)

    assert results == []


def test_detector_engine_rejects_invalid_result():

    df = pd.DataFrame({"close": [100, 101, 102]})

    engine = DetectorEngine([InvalidDetector()])

    with pytest.raises(TypeError, match="must return DetectorResult"):
        engine.run(df)