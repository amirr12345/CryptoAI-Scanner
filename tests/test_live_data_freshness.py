from services.live_data_freshness import (
    LiveDataFreshness,
)


def test_fresh_candle():
    freshness = LiveDataFreshness(
        max_candle_lag_seconds=300,
    )

    result = freshness.check(
        latest_candle_timestamp=1000,
        latest_trade_timestamp=1300,
    )

    assert result.fresh is True
    assert result.status == "FRESH"
    assert result.candle_lag_seconds == 300


def test_stale_candle():
    freshness = LiveDataFreshness(
        max_candle_lag_seconds=300,
    )

    result = freshness.check(
        latest_candle_timestamp=1000,
        latest_trade_timestamp=1301,
    )

    assert result.fresh is False
    assert result.status == "STALE_CANDLES"
    assert result.candle_lag_seconds == 301


def test_millisecond_trade_timestamp_is_normalized():
    freshness = LiveDataFreshness(
        max_candle_lag_seconds=300,
    )

    candle_timestamp = 1_299_999_700
    trade_timestamp_ms = 1_300_000_000_000

    result = freshness.check(
        latest_candle_timestamp=candle_timestamp,
        latest_trade_timestamp=trade_timestamp_ms,
    )

    assert result.latest_trade_timestamp == (
        trade_timestamp_ms
    )
    assert result.candle_lag_seconds == 300
    assert result.status == "FRESH"


def test_second_trade_timestamp_is_supported():
    freshness = LiveDataFreshness(
        max_candle_lag_seconds=300,
    )

    result = freshness.check(
        latest_candle_timestamp=1000,
        latest_trade_timestamp=1300,
    )

    assert result.latest_trade_timestamp == 1300
    assert result.candle_lag_seconds == 300
    assert result.status == "FRESH"


def test_clock_is_used_without_trade_timestamp():
    freshness = LiveDataFreshness(
        max_candle_lag_seconds=300,
        clock=lambda: 1300,
    )

    result = freshness.check(
        latest_candle_timestamp=1000,
    )

    assert result.latest_trade_timestamp is None
    assert result.candle_lag_seconds == 300
    assert result.status == "FRESH"


def test_clock_can_detect_stale_candle():
    freshness = LiveDataFreshness(
        max_candle_lag_seconds=300,
        clock=lambda: 1301,
    )

    result = freshness.check(
        latest_candle_timestamp=1000,
    )

    assert result.latest_trade_timestamp is None
    assert result.candle_lag_seconds == 301
    assert result.status == "STALE_CANDLES"
    assert result.fresh is False


def test_invalid_candle_timestamp():
    freshness = LiveDataFreshness()

    try:
        freshness.check(
            latest_candle_timestamp=0,
            latest_trade_timestamp=1000,
        )
    except ValueError as exc:
        assert (
            "latest_candle_timestamp"
            in str(exc)
        )
    else:
        raise AssertionError(
            "Expected ValueError."
        )


def test_invalid_max_lag():
    try:
        LiveDataFreshness(
            max_candle_lag_seconds=0,
        )
    except ValueError as exc:
        assert (
            "max_candle_lag_seconds"
            in str(exc)
        )
    else:
        raise AssertionError(
            "Expected ValueError."
        )