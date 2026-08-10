from models.detector_result import DetectorResult
from signals.score_engine import ScoreEngine


def test_score_engine_combines_detector_scores():

    results = [
        DetectorResult(
            detector="EMA",
            signal="GOLDEN_CROSS",
            score=25,
            confidence=0.95,
        ),
        DetectorResult(
            detector="MACD",
            signal="BULLISH_CROSS",
            score=20,
            confidence=0.90,
        ),
        DetectorResult(
            detector="VOLUME",
            signal="CONFIRMATION",
            score=10,
            confidence=0.80,
        ),
    ]

    engine = ScoreEngine()

    result = engine.calculate(results)

    assert result.total_score == 55
    assert result.detector_count == 3
    assert result.confidence == 0.88

    assert result.reasons == [
        "EMA: GOLDEN_CROSS",
        "MACD: BULLISH_CROSS",
        "VOLUME: CONFIRMATION",
    ]


def test_score_engine_with_empty_results():

    engine = ScoreEngine()

    result = engine.calculate([])

    assert result.total_score == 0
    assert result.detector_count == 0
    assert result.confidence == 0.0
    assert result.reasons == []


def test_score_engine_handles_negative_scores():

    results = [
        DetectorResult(
            detector="EMA",
            signal="DEATH_CROSS",
            score=-25,
            confidence=0.95,
        ),
        DetectorResult(
            detector="MACD",
            signal="BEARISH_CROSS",
            score=-20,
            confidence=0.90,
        ),
    ]

    engine = ScoreEngine()

    result = engine.calculate(results)

    assert result.total_score == -45
    assert result.detector_count == 2
    assert result.confidence == 0.93