from models.score_result import ScoreResult
from signals.signal_engine import SignalEngine


def test_strong_buy():

    engine = SignalEngine()

    result = engine.generate(
        ScoreResult(
            total_score=50,
            detector_count=4,
            confidence=0.85,
            reasons=["EMA", "MACD"],
        )
    )

    assert result.signal == "STRONG_BUY"


def test_buy():

    engine = SignalEngine()

    result = engine.generate(
        ScoreResult(
            total_score=25,
            detector_count=4,
            confidence=0.70,
            reasons=[],
        )
    )

    assert result.signal == "BUY"


def test_hold():

    engine = SignalEngine()

    result = engine.generate(
        ScoreResult(
            total_score=5,
            detector_count=4,
            confidence=0.50,
            reasons=[],
        )
    )

    assert result.signal == "HOLD"


def test_sell():

    engine = SignalEngine()

    result = engine.generate(
        ScoreResult(
            total_score=-25,
            detector_count=4,
            confidence=0.70,
            reasons=[],
        )
    )

    assert result.signal == "SELL"


def test_strong_sell():

    engine = SignalEngine()

    result = engine.generate(
        ScoreResult(
            total_score=-50,
            detector_count=4,
            confidence=0.90,
            reasons=[],
        )
    )

    assert result.signal == "STRONG_SELL"