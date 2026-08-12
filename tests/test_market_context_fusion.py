from indicators.vwap_context import VWAPContext
from microstructure.market_context_fusion import (
    MarketContextFusionEngine,
)
from models.cvd_strength import CVDStrengthResult
from models.volume_profile import VolumeProfileResult


def make_cvd(
    direction: str,
    strength: float,
) -> CVDStrengthResult:
    return CVDStrengthResult(
        flow_strength=strength,
        momentum_strength=strength,
        divergence_strength=0.0,
        participation_strength=100.0,
        overall_strength=strength,
        direction=direction,
        divergence="NONE",
        recent_delta=10.0,
        recent_cvd_change=10.0,
        recent_volume=100.0,
        recent_trade_count=20,
    )


def make_vwap(
    trend: str,
    position: str = "ABOVE_VWAP",
    distance_pct: float = 1.0,
    slope: float = 10.0,
) -> VWAPContext:
    return VWAPContext(
        position=position,
        distance_pct=distance_pct,
        slope=slope,
        trend=trend,
    )


def make_profile(
    position: str,
    current_price: float = 100.0,
) -> VolumeProfileResult:
    return VolumeProfileResult(
        levels=[],
        poc=100.0,
        vah=105.0,
        val=95.0,
        total_volume=1000.0,
        hvn=[],
        lvn=[],
        current_price=current_price,
        position=position,
    )


def test_bullish_cvd_and_bullish_vwap_are_confirmed():
    result = MarketContextFusionEngine().combine(
        cvd=make_cvd("BULLISH", 80.0),
        vwap=make_vwap("BULLISH"),
    )

    assert result.cvd_direction == "BULLISH"
    assert result.vwap_trend == "BULLISH"
    assert result.alignment == "CONFIRMED"
    assert result.direction == "BULLISH"
    assert result.effective_strength == 80.0


def test_bearish_cvd_and_bearish_vwap_are_confirmed():
    result = MarketContextFusionEngine().combine(
        cvd=make_cvd("BEARISH", 75.0),
        vwap=make_vwap(
            "BEARISH",
            position="BELOW_VWAP",
            distance_pct=-1.5,
            slope=-10.0,
        ),
    )

    assert result.alignment == "CONFIRMED"
    assert result.direction == "BEARISH"
    assert result.effective_strength == 75.0


def test_bullish_cvd_and_bearish_vwap_are_conflicting():
    result = MarketContextFusionEngine().combine(
        cvd=make_cvd("BULLISH", 90.0),
        vwap=make_vwap(
            "BEARISH",
            position="BELOW_VWAP",
            distance_pct=-1.0,
            slope=-10.0,
        ),
    )

    assert result.alignment == "CONFLICT"
    assert result.direction == "CONFLICT"
    assert result.effective_strength == 0.0


def test_bearish_cvd_and_bullish_vwap_are_conflicting():
    result = MarketContextFusionEngine().combine(
        cvd=make_cvd("BEARISH", 65.0),
        vwap=make_vwap("BULLISH"),
    )

    assert result.alignment == "CONFLICT"
    assert result.direction == "CONFLICT"
    assert result.effective_strength == 0.0


def test_bullish_cvd_with_neutral_vwap_is_neutral():
    result = MarketContextFusionEngine().combine(
        cvd=make_cvd("BULLISH", 80.0),
        vwap=make_vwap(
            "NEUTRAL",
            position="AT_VWAP",
            distance_pct=0.0,
            slope=0.0,
        ),
    )

    assert result.alignment == "NEUTRAL"
    assert result.direction == "NEUTRAL"
    assert result.effective_strength == 40.0


def test_neutral_cvd_with_bullish_vwap_is_neutral():
    result = MarketContextFusionEngine().combine(
        cvd=make_cvd("NEUTRAL", 80.0),
        vwap=make_vwap("BULLISH"),
    )

    assert result.alignment == "NEUTRAL"
    assert result.direction == "NEUTRAL"
    assert result.effective_strength == 40.0


def test_both_neutral_are_neutral():
    result = MarketContextFusionEngine().combine(
        cvd=make_cvd("NEUTRAL", 50.0),
        vwap=make_vwap(
            "NEUTRAL",
            position="AT_VWAP",
            distance_pct=0.0,
            slope=0.0,
        ),
    )

    assert result.alignment == "NEUTRAL"
    assert result.direction == "NEUTRAL"
    assert result.effective_strength == 25.0


def test_volume_profile_supports_bullish_context_below_val():
    result = MarketContextFusionEngine().combine(
        cvd=make_cvd("BULLISH", 80.0),
        vwap=make_vwap("BULLISH"),
        profile=make_profile(
            "BELOW_VALUE_AREA",
            current_price=90.0,
        ),
    )

    assert result.profile_position == "BELOW_VALUE_AREA"
    assert result.profile_alignment == "SUPPORTIVE"
    assert result.alignment == "CONFIRMED"
    assert result.direction == "BULLISH"
    assert result.effective_strength == 88.0


def test_volume_profile_supports_bearish_context_above_vah():
    result = MarketContextFusionEngine().combine(
        cvd=make_cvd("BEARISH", 70.0),
        vwap=make_vwap(
            "BEARISH",
            position="BELOW_VWAP",
            distance_pct=-1.0,
            slope=-5.0,
        ),
        profile=make_profile(
            "ABOVE_VALUE_AREA",
            current_price=110.0,
        ),
    )

    assert result.profile_alignment == "SUPPORTIVE"
    assert result.alignment == "CONFIRMED"
    assert result.direction == "BEARISH"
    assert result.effective_strength == 77.0


def test_volume_profile_is_neutral_inside_value_area():
    result = MarketContextFusionEngine().combine(
        cvd=make_cvd("BULLISH", 80.0),
        vwap=make_vwap("BULLISH"),
        profile=make_profile(
            "INSIDE_VALUE_AREA",
            current_price=100.0,
        ),
    )

    assert result.profile_alignment == "NEUTRAL"
    assert result.alignment == "CONFIRMED"
    assert result.direction == "BULLISH"
    assert result.effective_strength == 80.0


def test_volume_profile_opposes_bullish_context_above_vah():
    result = MarketContextFusionEngine().combine(
        cvd=make_cvd("BULLISH", 90.0),
        vwap=make_vwap("BULLISH"),
        profile=make_profile(
            "ABOVE_VALUE_AREA",
            current_price=110.0,
        ),
    )

    assert result.profile_alignment == "OPPOSING"
    assert result.alignment == "CONFLICT"
    assert result.direction == "CONFLICT"
    assert result.effective_strength == 0.0


def test_volume_profile_opposes_bearish_context_below_val():
    result = MarketContextFusionEngine().combine(
        cvd=make_cvd("BEARISH", 90.0),
        vwap=make_vwap("BEARISH"),
        profile=make_profile(
            "BELOW_VALUE_AREA",
            current_price=90.0,
        ),
    )

    assert result.profile_alignment == "OPPOSING"
    assert result.alignment == "CONFLICT"
    assert result.direction == "CONFLICT"
    assert result.effective_strength == 0.0


def test_volume_profile_context_is_optional():
    result = MarketContextFusionEngine().combine(
        cvd=make_cvd("BULLISH", 80.0),
        vwap=make_vwap("BULLISH"),
        profile=None,
    )

    assert result.profile_position == "UNKNOWN"
    assert result.profile_alignment == "UNKNOWN"
    assert result.alignment == "CONFIRMED"
    assert result.direction == "BULLISH"


def test_fusion_preserves_volume_profile_levels():
    profile = make_profile(
        "INSIDE_VALUE_AREA",
        current_price=100.0,
    )

    result = MarketContextFusionEngine().combine(
        cvd=make_cvd("BULLISH", 75.0),
        vwap=make_vwap("BULLISH"),
        profile=profile,
    )

    assert result.poc == 100.0
    assert result.vah == 105.0
    assert result.val == 95.0
    assert result.current_price == 100.0