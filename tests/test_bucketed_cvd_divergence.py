from microstructure.bucketed_cvd_divergence import (
    BucketedCVDAnalyzer,
)
from models.cvd_bucket import CVDBucket


def make_bucket(
    index: int,
    close_price: float,
    cumulative_delta: float,
) -> CVDBucket:
    return CVDBucket(
        start_timestamp=index * 60,
        end_timestamp=(index + 1) * 60,
        open_price=close_price,
        close_price=close_price,
        buy_volume=1.0,
        sell_volume=1.0,
        delta=0.0,
        cumulative_delta=cumulative_delta,
        trade_count=2,
    )


def test_bucketed_cvd_requires_positive_swing_window():
    analyzer = BucketedCVDAnalyzer()

    try:
        analyzer.analyze(
            [],
            swing_window=0,
        )
    except ValueError as exc:
        assert (
            "Swing window must be greater than zero"
            in str(exc)
        )
    else:
        raise AssertionError(
            "Expected ValueError for invalid swing window."
        )


def test_bucketed_cvd_empty_input():
    result = BucketedCVDAnalyzer().analyze([])

    assert result.swing_points == []
    assert result.divergences == []
    assert result.latest_signal == "NONE"


def test_bucketed_cvd_detects_swing_highs():
    buckets = [
        make_bucket(0, 100.0, 0.0),
        make_bucket(1, 105.0, 5.0),
        make_bucket(2, 101.0, 2.0),
        make_bucket(3, 108.0, 4.0),
        make_bucket(4, 100.0, 1.0),
    ]

    result = BucketedCVDAnalyzer().analyze(
        buckets,
        swing_window=1,
    )

    highs = [
        point
        for point in result.swing_points
        if point.kind == "HIGH"
    ]

    assert len(highs) == 2
    assert highs[0].price == 105.0
    assert highs[1].price == 108.0


def test_bucketed_cvd_detects_swing_lows():
    buckets = [
        make_bucket(0, 100.0, 0.0),
        make_bucket(1, 95.0, 2.0),
        make_bucket(2, 99.0, 1.0),
        make_bucket(3, 92.0, 5.0),
        make_bucket(4, 100.0, 3.0),
    ]

    result = BucketedCVDAnalyzer().analyze(
        buckets,
        swing_window=1,
    )

    lows = [
        point
        for point in result.swing_points
        if point.kind == "LOW"
    ]

    assert len(lows) == 2
    assert lows[0].price == 95.0
    assert lows[1].price == 92.0


def test_bucketed_cvd_detects_bullish_divergence():
    buckets = [
        make_bucket(0, 100.0, 0.0),
        make_bucket(1, 95.0, 10.0),
        make_bucket(2, 99.0, 5.0),
        make_bucket(3, 92.0, 20.0),
        make_bucket(4, 101.0, 15.0),
    ]

    result = BucketedCVDAnalyzer().analyze(
        buckets,
        swing_window=1,
    )

    bullish = [
        item
        for item in result.divergences
        if item.signal == "BULLISH_DIVERGENCE"
    ]

    assert len(bullish) == 1

    divergence = bullish[0]

    assert divergence.previous_price == 95.0
    assert divergence.current_price == 92.0
    assert divergence.price_change_pct < 0
    assert divergence.cvd_change > 0
    assert result.latest_signal == "BULLISH_DIVERGENCE"


def test_bucketed_cvd_detects_bearish_divergence():
    buckets = [
        make_bucket(0, 90.0, 0.0),
        make_bucket(1, 100.0, 10.0),
        make_bucket(2, 95.0, 15.0),
        make_bucket(3, 105.0, 5.0),
        make_bucket(4, 98.0, 8.0),
    ]

    result = BucketedCVDAnalyzer().analyze(
        buckets,
        swing_window=1,
    )

    bearish = [
        item
        for item in result.divergences
        if item.signal == "BEARISH_DIVERGENCE"
    ]

    assert len(bearish) == 1

    divergence = bearish[0]

    assert divergence.previous_price == 100.0
    assert divergence.current_price == 105.0
    assert divergence.price_change_pct > 0
    assert divergence.cvd_change < 0
    assert result.latest_signal == "BEARISH_DIVERGENCE"


def test_bucketed_cvd_keeps_only_real_divergences():
    buckets = [
        make_bucket(0, 100.0, 0.0),
        make_bucket(1, 95.0, -10.0),
        make_bucket(2, 99.0, -20.0),
        make_bucket(3, 93.0, -30.0),
        make_bucket(4, 101.0, -40.0),
    ]

    result = BucketedCVDAnalyzer().analyze(
        buckets,
        swing_window=1,
    )

    assert result.divergences == []
    assert result.latest_signal == "NONE"