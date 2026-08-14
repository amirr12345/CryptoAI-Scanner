from dataclasses import replace

import pytest

from microstructure.historical_confluence import (
    HistoricalConfluenceEngine,
)
from models.historical_context import (
    HistoricalContext,
)
from models.structure_setup import StructureSetup


def make_setup(
    direction: str = "BULLISH",
    timestamp: int = 1000,
) -> StructureSetup:
    return StructureSetup(
        index=20,
        timestamp=timestamp,
        direction=direction,
        setup=(
            "BULLISH_STRUCTURE_SETUP"
            if direction == "BULLISH"
            else "BEARISH_STRUCTURE_SETUP"
        ),
        sweep_index=18,
        sweep_event="LIQUIDITY_SWEEP",
        mss_index=20,
        mss_event="MSS",
        level_price=100.0,
        sweep_excursion_pct=0.8,
        mss_displacement_pct=1.2,
        bars_between=2,
    )


def make_context(
    timestamp: int = 1000,
    cvd_direction: str = "BULLISH",
    cvd_strength: float = 80.0,
    profile_position: str = "BELOW_VALUE_AREA",
    vwap_slope: float = 2.0,
) -> HistoricalContext:
    return HistoricalContext(
        symbol="BTC",
        timestamp=timestamp,
        trade_count=100,
        lookback_seconds=3600,
        cvd_direction=cvd_direction,
        cvd_strength=cvd_strength,
        cvd_divergence="NONE",
        cvd_delta=50.0,
        cvd_change=60.0,
        vwap=101.0,
        previous_vwap=99.0,
        vwap_position="ABOVE_VWAP",
        vwap_distance_pct=1.0,
        vwap_slope=vwap_slope,
        poc=100.0,
        vah=102.0,
        val=98.0,
        profile_position=profile_position,
        historical=True,
    )


def test_bullish_aligned_context_produces_a_plus():
    engine = HistoricalConfluenceEngine()

    result = engine.evaluate(
        setup=make_setup(
            "BULLISH",
            1000,
        ),
        context=make_context(
            1000,
            cvd_direction="BULLISH",
            cvd_strength=80.0,
            profile_position="BELOW_VALUE_AREA",
            vwap_slope=2.0,
        ),
    )

    assert result.direction == "BULLISH"
    assert result.score == 100.0
    assert result.grade == "A+"
    assert result.actionable is True
    assert not result.conflicts


def test_bearish_aligned_context_produces_a_plus():
    engine = HistoricalConfluenceEngine()

    result = engine.evaluate(
        setup=make_setup(
            "BEARISH",
            1000,
        ),
        context=make_context(
            1000,
            cvd_direction="BEARISH",
            cvd_strength=80.0,
            profile_position="ABOVE_VALUE_AREA",
            vwap_slope=-2.0,
        ),
    )

    assert result.direction == "BEARISH"
    assert result.score == 100.0
    assert result.grade == "A+"
    assert result.actionable is True


def test_opposing_cvd_creates_conflict():
    engine = HistoricalConfluenceEngine()

    result = engine.evaluate(
        setup=make_setup(
            "BULLISH",
            1000,
        ),
        context=make_context(
            1000,
            cvd_direction="BEARISH",
            cvd_strength=90.0,
            profile_position="BELOW_VALUE_AREA",
            vwap_slope=2.0,
        ),
    )

    assert result.cvd_points == 0.0
    assert (
        "CVD opposing structure setup"
        in result.conflicts
    )
    assert result.grade == "CONFLICT"
    assert result.actionable is False


def test_opposing_profile_creates_conflict():
    engine = HistoricalConfluenceEngine()

    result = engine.evaluate(
        setup=make_setup(
            "BULLISH",
            1000,
        ),
        context=make_context(
            1000,
            cvd_direction="BULLISH",
            cvd_strength=80.0,
            profile_position="ABOVE_VALUE_AREA",
            vwap_slope=2.0,
        ),
    )

    assert result.profile_points == 0.0
    assert (
        "Volume Profile location opposing setup"
        in result.conflicts
    )
    assert result.actionable is False


def test_opposing_vwap_creates_conflict():
    engine = HistoricalConfluenceEngine()

    result = engine.evaluate(
        setup=make_setup(
            "BULLISH",
            1000,
        ),
        context=make_context(
            1000,
            cvd_direction="BULLISH",
            cvd_strength=80.0,
            profile_position="BELOW_VALUE_AREA",
            vwap_slope=-2.0,
        ),
    )

    assert result.vwap_points == 0.0
    assert (
        "VWAP opposing structure setup"
        in result.conflicts
    )
    assert result.actionable is False


def test_timestamp_mismatch_is_rejected():
    engine = HistoricalConfluenceEngine()

    with pytest.raises(
        ValueError,
        match=(
            "timestamp and historical context "
            "timestamp must match"
        ),
    ):
        engine.evaluate(
            setup=make_setup(
                "BULLISH",
                1000,
            ),
            context=make_context(
                1001,
            ),
        )


def test_non_historical_context_is_rejected():
    engine = HistoricalConfluenceEngine()

    context = replace(
        make_context(
            1000,
        ),
        historical=False,
    )

    with pytest.raises(
        ValueError,
        match="Historical context is not marked historical",
    ):
        engine.evaluate(
            setup=make_setup(
                "BULLISH",
                1000,
            ),
            context=context,
        )


def test_flat_vwap_is_neutral():
    engine = HistoricalConfluenceEngine()

    context = make_context(
        1000,
        cvd_direction="BULLISH",
        cvd_strength=80.0,
        profile_position="BELOW_VALUE_AREA",
        vwap_slope=0.0,
    )

    result = engine.evaluate(
        setup=make_setup(
            "BULLISH",
            1000,
        ),
        context=context,
    )

    # 40 Structure + 25 CVD + 20 Profile + 7 VWAP = 92
    # Therefore the correct grade is A+.
    assert result.vwap_points == 7.0
    assert result.score == 92.0
    assert result.grade == "A+"
    assert result.actionable is True


def test_partial_cvd_alignment_gets_partial_score():
    engine = HistoricalConfluenceEngine()

    context = make_context(
        1000,
        cvd_direction="BULLISH",
        cvd_strength=40.0,
        profile_position="BELOW_VALUE_AREA",
        vwap_slope=2.0,
    )

    result = engine.evaluate(
        setup=make_setup(
            "BULLISH",
            1000,
        ),
        context=context,
    )

    # 40 Structure + 8 CVD + 20 Profile + 15 VWAP = 83
    assert result.cvd_points == 8.0
    assert result.score == 83.0
    assert result.grade == "A"
    assert result.actionable is True