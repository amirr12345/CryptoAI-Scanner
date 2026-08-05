from models.detector_result import DetectorResult
from signals.score_engine import ScoreEngine


def test_score_engine():

    results = [

        DetectorResult(
            detector="EMA",
            signal="GOLDEN_CROSS",
            score=25,
            confidence=0.9,
        ),

        DetectorResult(
            detector="MACD",
            signal="BULLISH_CROSS",
            score=20,
            confidence=0.8,
        ),

        DetectorResult(
            detector="BOLLINGER",
            signal="INSIDE_BANDS",
            score=0,
            confidence=0.5,
        ),

    ]

    engine = ScoreEngine()

    score = engine.calculate(results)

    assert score.total_score == 45

    assert score.detector_count == 3

    assert score.confidence == 0.73

    assert len(score.reasons) == 3