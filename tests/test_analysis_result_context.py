from indicators.vwap_context import VWAPContext
from models.analysis_result import AnalysisResult
from models.cvd_strength import CVDStrengthResult
from models.market_context import MarketContextFusion
from models.market_context_snapshot import (
    MarketContextSnapshot,
)
from models.volume_profile import (
    VolumeProfileResult,
)


def test_analysis_result_supports_optional_market_context():
    cvd = CVDStrengthResult(
        flow_strength=80.0,
        momentum_strength=70.0,
        divergence_strength=0.0,
        participation_strength=100.0,
        overall_strength=75.0,
        direction="BULLISH",
        divergence="NONE",
        recent_delta=10.0,
        recent_cvd_change=10.0,
        recent_volume=100.0,
        recent_trade_count=20,
    )

    vwap = VWAPContext(
        position="ABOVE_VWAP",
        distance_pct=1.0,
        slope=1.0,
        trend="BULLISH",
    )

    profile = VolumeProfileResult(
        levels=[],
        poc=100.0,
        vah=105.0,
        val=95.0,
        total_volume=100.0,
        hvn=[],
        lvn=[],
        current_price=101.0,
        position="INSIDE_VALUE_AREA",
    )

    fusion = MarketContextFusion(
        cvd_direction="BULLISH",
        vwap_trend="BULLISH",
        profile_position="INSIDE_VALUE_AREA",
        profile_alignment="NEUTRAL",
        alignment="CONFIRMED",
        direction="BULLISH",
        cvd_strength=75.0,
        effective_strength=75.0,
        vwap_position="ABOVE_VWAP",
        vwap_distance_pct=1.0,
        vwap_slope=1.0,
        poc=100.0,
        vah=105.0,
        val=95.0,
        current_price=101.0,
    )

    snapshot = MarketContextSnapshot(
        cvd=cvd,
        vwap=vwap,
        volume_profile=profile,
        fusion=fusion,
    )

    result = AnalysisResult(
        symbol="BTC",
        timestamp=1_700_000_000,
        price=101.0,
        total_score=40,
        confidence=0.9,
        signal="BUY",
        market_context=snapshot,
    )

    assert result.market_context is not None
    assert (
        result.market_context.fusion.alignment
        == "CONFIRMED"
    )
    assert (
        result.market_context.fusion.direction
        == "BULLISH"
    )