from microstructure.time_bucketed_cvd import (
    TimeBucketedCVDEngine,
)
from models.trade import Trade


def make_trade(
    timestamp: int,
    price: float,
    volume: float,
    side: str,
) -> Trade:
    return Trade(
        timestamp=timestamp,
        price=price,
        volume=volume,
        side=side,
        symbol="BTC",
    )


def test_time_bucketed_cvd_groups_trades():
    trades = [
        make_trade(1000, 100.0, 2.0, "buy"),
        make_trade(1010, 101.0, 1.0, "sell"),
        make_trade(1060, 102.0, 3.0, "buy"),
        make_trade(1070, 103.0, 1.0, "sell"),
    ]

    result = TimeBucketedCVDEngine().calculate(
        trades,
        interval_seconds=60,
    )

    assert len(result) == 2

    assert result[0].buy_volume == 2.0
    assert result[0].sell_volume == 1.0
    assert result[0].delta == 1.0
    assert result[0].trade_count == 2

    assert result[1].buy_volume == 3.0
    assert result[1].sell_volume == 1.0
    assert result[1].delta == 2.0
    assert result[1].trade_count == 2

    assert result[0].cumulative_delta == 1.0
    assert result[1].cumulative_delta == 3.0


def test_time_bucketed_cvd_supports_starting_cvd():
    trades = [
        make_trade(1000, 100.0, 2.0, "buy"),
        make_trade(1010, 101.0, 1.0, "sell"),
    ]

    result = TimeBucketedCVDEngine().calculate(
        trades,
        interval_seconds=60,
        starting_cvd=-10.0,
    )

    assert result[0].delta == 1.0
    assert result[0].cumulative_delta == -9.0


def test_time_bucketed_cvd_sorts_unordered_trades():
    trades = [
        make_trade(1070, 103.0, 1.0, "sell"),
        make_trade(1000, 100.0, 2.0, "buy"),
        make_trade(1060, 102.0, 3.0, "buy"),
        make_trade(1010, 101.0, 1.0, "sell"),
    ]

    result = TimeBucketedCVDEngine().calculate(
        trades,
        interval_seconds=60,
    )

    assert result[0].open_price == 100.0
    assert result[0].close_price == 101.0

    assert result[1].open_price == 102.0
    assert result[1].close_price == 103.0


def test_time_bucketed_cvd_supports_millisecond_timestamps():
    trades = [
        make_trade(
            1_700_000_000_000,
            100.0,
            2.0,
            "buy",
        ),
        make_trade(
            1_700_000_010_000,
            101.0,
            1.0,
            "sell",
        ),
    ]

    result = TimeBucketedCVDEngine().calculate(
        trades,
        interval_seconds=60,
    )

    assert len(result) == 1
    assert result[0].delta == 1.0


def test_time_bucketed_cvd_empty_input():
    result = TimeBucketedCVDEngine().calculate([])

    assert result == []


def test_time_bucketed_cvd_rejects_invalid_interval():
    trades = [
        make_trade(
            1000,
            100.0,
            1.0,
            "buy",
        )
    ]

    try:
        TimeBucketedCVDEngine().calculate(
            trades,
            interval_seconds=0,
        )
    except ValueError as exc:
        assert (
            "Interval must be greater than zero"
            in str(exc)
        )
    else:
        raise AssertionError(
            "Expected ValueError for invalid interval."
        )


def test_time_bucketed_cvd_rejects_invalid_trade_side():
    class InvalidTrade:
        timestamp = 1000
        price = 100.0
        volume = 1.0
        side = "unknown"

    try:
        TimeBucketedCVDEngine().calculate(
            [InvalidTrade()]
        )
    except ValueError as exc:
        assert (
            "Trade side must be 'buy' or 'sell'"
            in str(exc)
        )
    else:
        raise AssertionError(
            "Expected ValueError for invalid trade side."
        )