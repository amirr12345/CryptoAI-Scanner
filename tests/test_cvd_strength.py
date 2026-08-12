import pytest

from microstructure.cvd_strength import CVDStrengthAnalyzer
from models.cvd_bucket import CVDBucket
from models.cvd_bucket_analysis import (
    BucketDivergence,
    BucketedCVDAnalysis,
)


def make_bucket(
    index: int,
    delta: float,
    cumulative_delta: float,
    trades: int = 10,
) -> CVDBucket:
    buy = max(delta, 0.0)
    sell = max(-delta, 0.0)

    return CVDBucket(
        start_timestamp=index * 60,
        end_timestamp=(index + 1) * 60,
        open_price=100.0 + index,
        close_price=100.0 + index,
        buy_volume=buy,
        sell_volume=sell,
        delta=delta,
        cumulative_delta=cumulative_delta,
        trade_count=trades,
    )


def test_cvd_strength_empty_input():
    result = CVDStrengthAnalyzer().analyze([])

    assert result.flow_strength == 0.0
    assert result.momentum_strength == 0.0
    assert result.divergence_strength == 0.0
    assert result.participation_strength == 0.0
    assert result.overall_strength == 0.0
    assert result.direction == "NEUTRAL"
    assert result.divergence == "NONE"
    assert result.recent_delta == 0.0
    assert result.recent_cvd_change == 0.0
    assert result.recent_volume == 0.0
    assert result.recent_trade_count == 0


def test_cvd_strength_rejects_invalid_lookback():
    with pytest.raises(
        ValueError,
        match="Lookback must be greater than zero",
    ):
        CVDStrengthAnalyzer().analyze(
            [],
            lookback=0,
        )


def test_cvd_strength_bullish_direction():
    buckets = [
        make_bucket(0, 5.0, 5.0),
        make_bucket(1, 4.0, 9.0),
        make_bucket(2, 6.0, 15.0),
    ]

    result = CVDStrengthAnalyzer().analyze(
        buckets,
        lookback=3,
    )

    assert result.direction == "BULLISH"
    assert result.recent_delta == pytest.approx(
        15.0
    )
    assert result.recent_cvd_change == pytest.approx(
        15.0
    )
    assert result.recent_volume == pytest.approx(
        15.0
    )


def test_cvd_strength_bearish_direction():
    buckets = [
        make_bucket(0, -5.0, -5.0),
        make_bucket(1, -4.0, -9.0),
        make_bucket(2, -6.0, -15.0),
    ]

    result = CVDStrengthAnalyzer().analyze(
        buckets,
        lookback=3,
    )

    assert result.direction == "BEARISH"
    assert result.recent_delta == pytest.approx(
        -15.0
    )
    assert result.recent_cvd_change == pytest.approx(
        -15.0
    )


def test_flow_strength_is_zero_when_balanced():
    buckets = [
        CVDBucket(
            start_timestamp=0,
            end_timestamp=60,
            open_price=100.0,
            close_price=101.0,
            buy_volume=5.0,
            sell_volume=5.0,
            delta=0.0,
            cumulative_delta=0.0,
            trade_count=10,
        )
    ]

    result = CVDStrengthAnalyzer().analyze(
        buckets
    )

    assert result.flow_strength == 0.0


def test_flow_strength_is_maximum_when_one_side_dominates():
    buckets = [
        make_bucket(
            0,
            delta=10.0,
            cumulative_delta=10.0,
        )
    ]

    result = CVDStrengthAnalyzer().analyze(
        buckets
    )

    assert result.flow_strength == 100.0


def test_participation_strength_is_full_when_all_buckets_active():
    buckets = [
        make_bucket(0, 1.0, 1.0, trades=5),
        make_bucket(1, 2.0, 3.0, trades=6),
        make_bucket(2, 3.0, 6.0, trades=7),
    ]

    result = CVDStrengthAnalyzer().analyze(
        buckets
    )

    assert result.participation_strength == 100.0


def test_participation_strength_falls_for_empty_buckets():
    buckets = [
        make_bucket(0, 1.0, 1.0, trades=5),
        make_bucket(1, 0.0, 1.0, trades=0),
        make_bucket(2, 2.0, 3.0, trades=6),
        make_bucket(3, 0.0, 3.0, trades=0),
    ]

    result = CVDStrengthAnalyzer().analyze(
        buckets
    )

    assert result.participation_strength == 50.0


def test_momentum_strength_is_high_for_consistent_direction():
    buckets = [
        make_bucket(0, 2.0, 2.0),
        make_bucket(1, 3.0, 5.0),
        make_bucket(2, 4.0, 9.0),
    ]

    result = CVDStrengthAnalyzer().analyze(
        buckets
    )

    assert result.momentum_strength == 100.0


def test_momentum_strength_is_lower_when_delta_reverses():
    buckets = [
        make_bucket(0, 10.0, 10.0),
        make_bucket(1, -8.0, 2.0),
        make_bucket(2, 2.0, 4.0),
    ]

    result = CVDStrengthAnalyzer().analyze(
        buckets
    )

    assert 0.0 < result.momentum_strength < 100.0


def test_divergence_strength_is_zero_without_divergence():
    buckets = [
        make_bucket(0, 1.0, 1.0),
    ]

    analysis = BucketedCVDAnalysis(
        swing_points=[],
        divergences=[],
        latest_signal="NONE",
    )

    result = CVDStrengthAnalyzer().analyze(
        buckets,
        analysis=analysis,
    )

    assert result.divergence_strength == 0.0
    assert result.divergence == "NONE"


def test_divergence_strength_detects_latest_divergence():
    buckets = [
        make_bucket(0, 5.0, 5.0),
    ]

    analysis = BucketedCVDAnalysis(
        swing_points=[],
        divergences=[
            BucketDivergence(
                signal="BULLISH_DIVERGENCE",
                previous_index=1,
                current_index=2,
                previous_price=100.0,
                current_price=98.0,
                previous_cvd=10.0,
                current_cvd=30.0,
                price_change_pct=-2.0,
                cvd_change=20.0,
            )
        ],
        latest_signal="BULLISH_DIVERGENCE",
    )

    result = CVDStrengthAnalyzer().analyze(
        buckets,
        analysis=analysis,
    )

    assert result.divergence == "BULLISH_DIVERGENCE"
    assert result.divergence_strength > 0.0
    assert result.divergence_strength <= 100.0


def test_overall_strength_is_equal_weight_average():
    buckets = [
        make_bucket(0, 10.0, 10.0),
    ]

    result = CVDStrengthAnalyzer().analyze(
        buckets
    )

    expected = (
        result.flow_strength
        + result.momentum_strength
        + result.divergence_strength
        + result.participation_strength
    ) / 4.0

    assert result.overall_strength == pytest.approx(
        expected
    )


def test_lookback_uses_only_recent_buckets():
    buckets = [
        make_bucket(0, -100.0, -100.0),
        make_bucket(1, 5.0, -95.0),
        make_bucket(2, 6.0, -89.0),
        make_bucket(3, 7.0, -82.0),
    ]

    result = CVDStrengthAnalyzer().analyze(
        buckets,
        lookback=3,
    )

    assert result.recent_delta == pytest.approx(
        18.0
    )
    assert result.recent_cvd_change == pytest.approx(
        18.0
    )