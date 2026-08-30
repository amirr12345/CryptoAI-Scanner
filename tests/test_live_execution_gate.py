from types import SimpleNamespace

import pytest

from microstructure.confluence_engine import (
    ConfluenceEngine,
)


class Setup:
    direction = "BULLISH"


def make_order_book(
    imbalance: float,
):
    return SimpleNamespace(
        imbalance=float(imbalance),
    )


def make_session(
    quality: float,
):
    return SimpleNamespace(
        session_name="LONDON",
        session_quality=float(quality),
        name="LONDON",
        quality_score=float(quality),
        is_overlap=False,
    )


def make_context():
    return {
        "cvd": SimpleNamespace(
            direction="BULLISH",
            strength=80.0,
            cvd_direction="BULLISH",
            cvd_strength=80.0,
            cvd_delta=400.0,
            cvd_change=400.0,
            cvd_divergence="NONE",
            delta=400.0,
            delta_pct=40.0,
        ),
        "profile": SimpleNamespace(
            location="BELOW_VALUE_AREA",
            profile_position="BELOW_VALUE_AREA",
            position="BELOW_VALUE_AREA",
        ),
        "vwap": SimpleNamespace(
            direction="BULLISH",
            vwap_direction="BULLISH",
            vwap_position="ABOVE_VWAP",
            vwap_slope=1.0,
        ),
        "order_flow": SimpleNamespace(
            buy_volume=700.0,
            sell_volume=300.0,
            delta=400.0,
            delta_pct=40.0,
            trade_count=1000,
            aggression="BULLISH",
            aggression_strength=80.0,
            order_flow_aggression="BULLISH",
            order_flow_strength=80.0,
            buy_ratio=0.70,
            sell_ratio=0.30,
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
        order_book=make_order_book(imbalance),
        session=make_session(session_quality),
        live_mode=True,
    )


# =====================================================================
# SESSION EXECUTION GATE
# =====================================================================


def test_live_session_below_5_blocks():
    result = evaluate(
        session_quality=4.9,
        imbalance=0.50,
    )

    assert result.execution_status == "BLOCK"
    assert result.actionable is False


def test_live_session_5_to_below_8_waits():
    result = evaluate(
        session_quality=6.5,
        imbalance=0.50,
    )

    assert result.execution_status == "WAIT"
    assert result.actionable is False


def test_live_session_at_8_can_execute_with_neutral_order_book():
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


# =====================================================================
# ORDER BOOK EXECUTION GATE
# =====================================================================


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
        session=make_session(9.0),
        live_mode=True,
    )

    assert result.execution_status == "WAIT"
    assert result.actionable is False


# =====================================================================
# ORDER BOOK MUST NOT CHANGE PRIMARY SCORE
# =====================================================================


def test_supporting_order_book_does_not_change_primary_score():
    result = evaluate(
        session_quality=9.0,
        imbalance=0.40,
    )

    assert result.score == pytest.approx(
        100.0,
        abs=0.01,
    )


def test_extreme_opposing_order_book_does_not_change_primary_score():
    result = evaluate(
        session_quality=9.0,
        imbalance=-0.50,
    )

    assert result.score == pytest.approx(
        100.0,
        abs=0.01,
    )


def test_order_book_changes_execution_not_score():
    supporting = evaluate(
        session_quality=9.0,
        imbalance=0.40,
    )

    opposing = evaluate(
        session_quality=9.0,
        imbalance=-0.50,
    )

    assert supporting.score == pytest.approx(
        opposing.score,
        abs=0.01,
    )

    assert supporting.score == pytest.approx(
        100.0,
        abs=0.01,
    )

    assert opposing.score == pytest.approx(
        100.0,
        abs=0.01,
    )

    assert supporting.execution_status == "EXECUTE"
    assert opposing.execution_status == "BLOCK"


# =====================================================================
# SESSION INFORMATION
# =====================================================================


def test_session_quality_is_preserved_in_result():
    result = evaluate(
        session_quality=9.25,
        imbalance=0.05,
    )

    assert result.session_name == "LONDON"

    assert result.session_quality == pytest.approx(
        9.25,
        abs=0.01,
    )


# =====================================================================
# ORDER BOOK INFORMATION
# =====================================================================


def test_order_book_imbalance_is_preserved_in_result():
    result = evaluate(
        session_quality=9.0,
        imbalance=0.275,
    )

    assert result.order_book_imbalance == pytest.approx(
        0.275,
        abs=0.0001,
    )


# =====================================================================
# SAFETY RULES
# =====================================================================


def test_low_session_blocks_even_with_supporting_order_book():
    result = evaluate(
        session_quality=4.0,
        imbalance=0.50,
    )

    assert result.execution_status == "BLOCK"
    assert result.actionable is False


def test_medium_session_waits_even_with_supporting_order_book():
    result = evaluate(
        session_quality=7.0,
        imbalance=0.50,
    )

    assert result.execution_status == "WAIT"
    assert result.actionable is False


def test_strong_session_neutral_order_book_executes():
    result = evaluate(
        session_quality=9.0,
        imbalance=0.0,
    )

    assert result.execution_status == "EXECUTE"
    assert result.actionable is True


def test_strong_session_mild_opposing_order_book_waits():
    result = evaluate(
        session_quality=9.0,
        imbalance=-0.15,
    )

    assert result.execution_status == "WAIT"
    assert result.actionable is False


def test_strong_session_material_opposing_order_book_waits():
    result = evaluate(
        session_quality=9.0,
        imbalance=-0.25,
    )

    assert result.execution_status == "WAIT"
    assert result.actionable is False


def test_strong_session_extreme_opposing_order_book_blocks():
    result = evaluate(
        session_quality=9.0,
        imbalance=-0.35,
    )

    assert result.execution_status == "BLOCK"
    assert result.actionable is False
