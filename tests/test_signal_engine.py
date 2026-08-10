from models.score_result import ScoreResult
from models.signal_result import SignalResult
from signals.signal_engine import SignalEngine


def test_strong_buy():

    score = ScoreResult(
        total_score=50,
        detector_count=3,
        confidence=0.90,
        reasons=[
            "EMA: GOLDEN_CROSS",
            "MACD: BULLISH_CROSS",
        ],
    )

    result = SignalEngine().generate(score)

    assert isinstance(result, SignalResult)
    assert result.signal == "STRONG_BUY"
    assert result.score == 50
    assert result.confidence == 0.90


def test_buy():

    score = ScoreResult(
        total_score=25,
        detector_count=2,
        confidence=0.85,
        reasons=["EMA: GOLDEN_CROSS"],
    )

    result = SignalEngine().generate(score)

    assert result.signal == "BUY"
    assert result.score == 25


def test_hold():

    score = ScoreResult(
        total_score=10,
        detector_count=2,
        confidence=0.70,
        reasons=["VOLUME: CONFIRMATION"],
    )

    result = SignalEngine().generate(score)

    assert result.signal == "HOLD"
    assert result.score == 10


def test_sell():

    score = ScoreResult(
        total_score=-25,
        detector_count=2,
        confidence=0.85,
        reasons=["EMA: DEATH_CROSS"],
    )

    result = SignalEngine().generate(score)

    assert result.signal == "SELL"
    assert result.score == -25


def test_strong_sell():

    score = ScoreResult(
        total_score=-50,
        detector_count=3,
        confidence=0.90,
        reasons=[
            "EMA: DEATH_CROSS",
            "MACD: BEARISH_CROSS",
        ],
    )

    result = SignalEngine().generate(score)

    assert result.signal == "STRONG_SELL"
    assert result.score == -50
    assert result.confidence == 0.90


def test_signal_engine_preserves_reasons():

    reasons = [
        "EMA: GOLDEN_CROSS",
        "MACD: BULLISH_CROSS",
        "VOLUME: CONFIRMATION",
    ]

    score = ScoreResult(
        total_score=55,
        detector_count=3,
        confidence=0.92,
        reasons=reasons,
    )

    result = SignalEngine().generate(score)

    assert result.reasons == reasons