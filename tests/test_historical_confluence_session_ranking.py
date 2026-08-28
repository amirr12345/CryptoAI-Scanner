from __future__ import annotations

from types import SimpleNamespace

import pytest

from microstructure.historical_confluence import (
    HistoricalConfluenceEngine,
)
from microstructure.session_ranking import (
    SessionPerformance,
)
from models.historical_context import (
    HistoricalContext,
)
from models.structure_setup import (
    StructureSetup,
)


# =====================================================================
# HELPERS
# =====================================================================


def make_setup(
    direction: str = "BULLISH",
    timestamp: int = 1000,
) -> StructureSetup:
    """
    Build a valid StructureSetup using the real project model.

    The project StructureSetup requires all structural fields,
    so the test supplies deterministic representative values.
    """

    return StructureSetup(
        timestamp=int(timestamp),

        direction=direction,

        index=10,

        setup=(
            "BULLISH_STRUCTURE_SETUP"
            if direction == "BULLISH"
            else "BEARISH_STRUCTURE_SETUP"
        ),

        sweep_index=8,

        sweep_event=None,

        mss_index=10,

        mss_event=None,

        level_price=100.0,

        sweep_excursion_pct=0.50,

        mss_displacement_pct=0.30,

        bars_between=2,
    )


def make_context(
    timestamp: int = 1000,
) -> HistoricalContext:
    """
    Build a deterministic historical context.

    The values intentionally represent a strongly aligned
    bullish historical setup.
    """

    return HistoricalContext(
        symbol="BTCUSDT",

        timestamp=int(timestamp),

        trade_count=1000,

        lookback_seconds=3600,

        # ---------------------------------------------------------
        # CVD
        # ---------------------------------------------------------

        cvd_direction="BULLISH",

        cvd_strength=80.0,

        cvd_divergence="NONE",

        cvd_delta=400.0,

        cvd_change=400.0,

        # ---------------------------------------------------------
        # VWAP
        # ---------------------------------------------------------

        vwap=100.0,

        previous_vwap=98.0,

        vwap_position="ABOVE_VWAP",

        vwap_distance_pct=2.0,

        vwap_slope=2.0,

        # ---------------------------------------------------------
        # Volume Profile
        # ---------------------------------------------------------

        poc=100.0,

        vah=110.0,

        val=90.0,

        profile_position="BELOW_VALUE_AREA",

        # ---------------------------------------------------------
        # Order Flow
        # ---------------------------------------------------------

        buy_volume=700.0,

        sell_volume=300.0,

        delta=400.0,

        delta_pct=40.0,

        buy_ratio=0.70,

        sell_ratio=0.30,

        average_trade_size=1.0,

        large_trade_buy_volume=100.0,

        large_trade_sell_volume=20.0,

        large_trade_imbalance=0.6667,

        order_flow_aggression="BULLISH",

        order_flow_strength=80.0,

        # ---------------------------------------------------------
        # Session
        # ---------------------------------------------------------

        session_name="LONDON",

        session_quality=9.0,

        session_is_overlap=False,

        # ---------------------------------------------------------
        # Historical marker
        # ---------------------------------------------------------

        historical=True,
    )


def make_high_session_performance(
    session_name: str = "LONDON",
) -> SessionPerformance:
    """
    Strong, well-observed session performance.
    """

    return SessionPerformance(
        session_name=session_name,

        sample_count=30,

        average_quality=9.20,

        average_trade_count=1500.0,

        average_order_flow_strength=85.0,

        average_cvd_strength=85.0,

        average_liquidity=0.90,

        best_rate=80.0,

        good_rate=20.0,

        neutral_rate=0.0,

        avoid_rate=0.0,

        execute_rate=80.0,

        observed_score=9.20,

        confidence="HIGH",

        rank=1,
    )


def make_low_session_performance(
    session_name: str = "OFF_HOURS",
) -> SessionPerformance:
    """
    Poorly performing session.
    """

    return SessionPerformance(
        session_name=session_name,

        sample_count=30,

        average_quality=4.20,

        average_trade_count=100.0,

        average_order_flow_strength=10.0,

        average_cvd_strength=10.0,

        average_liquidity=0.20,

        best_rate=0.0,

        good_rate=0.0,

        neutral_rate=0.0,

        avoid_rate=100.0,

        execute_rate=0.0,

        observed_score=2.00,

        confidence="HIGH",

        rank=4,
    )


def make_live_session(
    name: str = "LONDON",
    quality: float = 9.0,
    overlap: bool = False,
):
    """
    Build a lightweight current-session object compatible
    with ConfluenceEngine.
    """

    return SimpleNamespace(
        session_name=name,

        name=name,

        session_quality=float(
            quality
        ),

        quality_score=float(
            quality
        ),

        session_is_overlap=bool(
            overlap
        ),

        is_overlap=bool(
            overlap
        ),
    )


def make_order_book(
    imbalance: float = 0.05,
):
    """
    Build a lightweight Order Book confirmation object.
    """

    return SimpleNamespace(
        symbol="BTCUSDT",

        imbalance=float(
            imbalance
        ),

        bid_volume=700.0,

        ask_volume=650.0,

        best_bid=100.0,

        best_ask=100.01,

        spread_pct=0.01,

        wall_bias="NEUTRAL",

        timestamp=2000,
    )


# =====================================================================
# TESTS
# =====================================================================


def test_historical_confluence_without_ranking_preserves_behavior():
    engine = HistoricalConfluenceEngine()

    result = engine.evaluate(
        setup=make_setup(),

        context=make_context(),

        live_mode=False,
    )

    assert result.score == pytest.approx(
        100.0,
        abs=0.01,
    )

    assert result.grade == "A+"

    assert result.execution_status in {
        "HISTORICAL_OK",
        "WAIT",
    }


def test_live_high_quality_ranked_session_can_execute():
    engine = HistoricalConfluenceEngine()

    result = engine.evaluate(
        setup=make_setup(),

        context=make_context(),

        order_book=make_order_book(
            imbalance=0.05
        ),

        live_mode=True,

        session=make_live_session(
            name="LONDON",
            quality=9.0,
            overlap=False,
        ),

        session_performance=(
            make_high_session_performance()
        ),
    )

    assert result.score == pytest.approx(
        100.0,
        abs=0.01,
    )

    assert result.grade == "A+"

    assert result.execution_status == "EXECUTE"

    assert result.actionable is True

    assert any(
        "Session Ranking" in reason
        for reason in result.reasons
    )


def test_live_low_quality_ranked_session_blocks():
    engine = HistoricalConfluenceEngine()

    result = engine.evaluate(
        setup=make_setup(),

        context=make_context(),

        order_book=make_order_book(
            imbalance=0.05
        ),

        live_mode=True,

        session=make_live_session(
            name="OFF_HOURS",
            quality=4.5,
            overlap=False,
        ),

        session_performance=(
            make_low_session_performance()
        ),
    )

    assert result.score == pytest.approx(
        100.0,
        abs=0.01,
    )

    assert result.grade == "A+"

    assert result.execution_status == "BLOCK"

    assert result.actionable is False


def test_session_ranking_does_not_change_primary_score():
    engine = HistoricalConfluenceEngine()

    result_without_ranking = (
        engine.evaluate(
            setup=make_setup(),

            context=make_context(),

            order_book=make_order_book(
                imbalance=0.05
            ),

            live_mode=True,

            session=make_live_session(
                name="LONDON",
                quality=9.0,
                overlap=False,
            ),
        )
    )

    result_with_ranking = (
        engine.evaluate(
            setup=make_setup(),

            context=make_context(),

            order_book=make_order_book(
                imbalance=0.05
            ),

            live_mode=True,

            session=make_live_session(
                name="LONDON",
                quality=9.0,
                overlap=False,
            ),

            session_performance=(
                make_high_session_performance()
            ),
        )
    )

    assert result_with_ranking.score == pytest.approx(
        result_without_ranking.score,
        abs=0.01,
    )

    assert result_without_ranking.score == pytest.approx(
        100.0,
        abs=0.01,
    )

    assert result_with_ranking.score == pytest.approx(
        100.0,
        abs=0.01,
    )


def test_historical_mode_ignores_session_ranking():
    engine = HistoricalConfluenceEngine()

    result = engine.evaluate(
        setup=make_setup(),

        context=make_context(),

        live_mode=False,

        session_performance=(
            make_low_session_performance()
        ),
    )

    assert result.score == pytest.approx(
        100.0,
        abs=0.01,
    )

    assert result.grade == "A+"

    # Session Ranking belongs to the live execution layer.
    assert (
        "Session Ranking"
        not in
        " ".join(
            result.reasons
        )
    )


def test_timestamp_mismatch_is_rejected():
    engine = HistoricalConfluenceEngine()

    with pytest.raises(
        ValueError,
        match=(
            "timestamp"
        ),
    ):

        engine.evaluate(
            setup=make_setup(
                timestamp=1000
            ),

            context=make_context(
                timestamp=1001
            ),
        )


def test_non_historical_context_is_rejected():
    engine = HistoricalConfluenceEngine()

    context = make_context()

    # HistoricalContext is frozen, so create a replacement object.
    context = HistoricalContext(
        symbol=context.symbol,

        timestamp=context.timestamp,

        trade_count=context.trade_count,

        lookback_seconds=context.lookback_seconds,

        cvd_direction=context.cvd_direction,

        cvd_strength=context.cvd_strength,

        cvd_divergence=context.cvd_divergence,

        cvd_delta=context.cvd_delta,

        cvd_change=context.cvd_change,

        vwap=context.vwap,

        previous_vwap=context.previous_vwap,

        vwap_position=context.vwap_position,

        vwap_distance_pct=context.vwap_distance_pct,

        vwap_slope=context.vwap_slope,

        poc=context.poc,

        vah=context.vah,

        val=context.val,

        profile_position=context.profile_position,

        buy_volume=context.buy_volume,

        sell_volume=context.sell_volume,

        delta=context.delta,

        delta_pct=context.delta_pct,

        buy_ratio=context.buy_ratio,

        sell_ratio=context.sell_ratio,

        average_trade_size=context.average_trade_size,

        large_trade_buy_volume=(
            context.large_trade_buy_volume
        ),

        large_trade_sell_volume=(
            context.large_trade_sell_volume
        ),

        large_trade_imbalance=(
            context.large_trade_imbalance
        ),

        order_flow_aggression=(
            context.order_flow_aggression
        ),

        order_flow_strength=(
            context.order_flow_strength
        ),

        session_name=context.session_name,

        session_quality=context.session_quality,

        session_is_overlap=(
            context.session_is_overlap
        ),

        historical=False,
    )

    with pytest.raises(
        ValueError,
        match=(
            "not marked historical"
        ),
    ):

        engine.evaluate(
            setup=make_setup(),

            context=context,
        )


def test_live_without_order_book_does_not_execute():
    engine = HistoricalConfluenceEngine()

    result = engine.evaluate(
        setup=make_setup(),

        context=make_context(),

        order_book=None,

        live_mode=True,

        session=make_live_session(
            name="LONDON",
            quality=9.0,
            overlap=False,
        ),

        session_performance=(
            make_high_session_performance()
        ),
    )

    assert result.score == pytest.approx(
        100.0,
        abs=0.01,
    )

    assert result.execution_status == "WAIT"

    assert result.actionable is False


def test_opposing_order_book_blocks_even_with_strong_rank():
    engine = HistoricalConfluenceEngine()

    result = engine.evaluate(
        setup=make_setup(),

        context=make_context(),

        order_book=make_order_book(
            imbalance=-0.50
        ),

        live_mode=True,

        session=make_live_session(
            name="LONDON",
            quality=9.0,
            overlap=False,
        ),

        session_performance=(
            make_high_session_performance()
        ),
    )

    assert result.score == pytest.approx(
        100.0,
        abs=0.01,
    )

    assert result.execution_status == "BLOCK"

    assert result.actionable is False


def test_low_confidence_ranked_session_waits():
    engine = HistoricalConfluenceEngine()

    medium = SessionPerformance(
        session_name="LONDON",

        sample_count=15,

        average_quality=9.0,

        average_trade_count=1200.0,

        average_order_flow_strength=80.0,

        average_cvd_strength=80.0,

        average_liquidity=0.90,

        best_rate=80.0,

        good_rate=20.0,

        neutral_rate=0.0,

        avoid_rate=0.0,

        execute_rate=80.0,

        observed_score=9.0,

        confidence="MEDIUM",

        rank=1,
    )

    result = engine.evaluate(
        setup=make_setup(),

        context=make_context(),

        order_book=make_order_book(
            imbalance=0.05
        ),

        live_mode=True,

        session=make_live_session(
            name="LONDON",
            quality=9.0,
        ),

        session_performance=medium,
    )

    assert result.score == pytest.approx(
        100.0,
        abs=0.01,
    )

    assert result.execution_status == "WAIT"

    assert result.actionable is False