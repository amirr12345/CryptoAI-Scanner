from types import SimpleNamespace

from microstructure.confluence_engine import (
    ConfluenceEngine,
)


class Setup:
    direction = "BULLISH"


def make_order_book(
    imbalance: float,
):
    return SimpleNamespace(
        imbalance=imbalance,
    )


def make_session(
    quality: float,
):
    return SimpleNamespace(
        session_name="LONDON",
        session_quality=quality,
    )


def make_context():
    return {
        "cvd": SimpleNamespace(
            direction="BULLISH",
            strength=80.0,
        ),
        "profile": SimpleNamespace(
            location="BELOW_VALUE_AREA",
        ),
        "vwap": SimpleNamespace(
            direction="BULLISH",
        ),
        "order_flow": SimpleNamespace(
            buy_volume=700.0,
            sell_volume=300.0,
            delta=400.0,
            delta_pct=40.0,
            trade_count=1000,
            aggression="BULLISH",
            aggression_strength=80.0,
        ),
    }


def evaluate(
    session_quality: float,
    imbalance: float = 0.0,
):
    engine = ConfluenceEngine()

    context = make_context()

    return engine.evaluate(
        setup=Setup(),
        cvd=context["cvd"],
        profile=context["profile"],
        vwap=context["vwap"],
        order_flow=context["order_flow"],
        order_book=make_order_book(
            imbalance
        ),
        session=make_session(
            session_quality
        ),
        live_mode=True,
    )


def test_live_session_below_5_blocks():
    result = evaluate(
        session_quality=4.9,
        imbalance=0.5,
    )

    assert result.execution_status == "BLOCK"
    assert result.actionable is False


def test_live_session_5_to_8_waits():
    result = evaluate(
        session_quality=6.5,
        imbalance=0.5,
    )

    assert result.execution_status == "WAIT"
    assert result.actionable is False


def test_live_session_8_or_more_can_execute():
    result = evaluate(
        session_quality=8.0,
        imbalance=0.05,
    )

    assert result.execution_status == "EXECUTE"
    assert result.actionable is True


def test_live_strong_session_with_supporting_order_book_executes():
    result = evaluate(
        session_quality=9.5,
        imbalance=0.40,
    )

    assert result.execution_status == "EXECUTE"
    assert result.actionable is True


def test_live_strong_session_with_extreme_opposing_order_book_blocks():
    result = evaluate(
        session_quality=9.5,
        imbalance=-0.50,
    )

    assert result.execution_status == "BLOCK"
    assert result.actionable is False


def test_live_strong_session_without_order_book_waits():
    engine = ConfluenceEngine()

    context = make_context()

    result = engine.evaluate(
        setup=Setup(),
        cvd=context["cvd"],
        profile=context["profile"],
        vwap=context["vwap"],
        order_flow=context["order_flow"],
        order_book=None,
        session=make_session(
            9.0
        ),
        live_mode=True,
    )

    assert result.execution_status == "WAIT"
    assert result.actionable is False