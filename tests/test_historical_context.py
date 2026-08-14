from core.trade_store import TradeStore
from microstructure.historical_context import (
    HistoricalContextEngine,
)
from models.trade import Trade


def make_trade(
    timestamp: int,
    price: float,
    volume: float,
    side: str,
    symbol: str = "BTC",
) -> Trade:
    return Trade(
        timestamp=timestamp,
        price=price,
        volume=volume,
        side=side,
        symbol=symbol,
    )


def build_engine(
    tmp_path,
) -> HistoricalContextEngine:
    store = TradeStore(
        tmp_path / "crypto.db"
    )

    trades = [
        make_trade(
            100,
            100.0,
            2.0,
            "buy",
        ),
        make_trade(
            101,
            102.0,
            1.0,
            "buy",
        ),
        make_trade(
            102,
            101.0,
            3.0,
            "sell",
        ),
        make_trade(
            103,
            104.0,
            4.0,
            "buy",
        ),
        make_trade(
            104,
            103.0,
            2.0,
            "sell",
        ),
        # Future trade. It MUST NOT affect timestamp=104 context.
        make_trade(
            110,
            120.0,
            10.0,
            "buy",
        ),
    ]

    store.save_trades(trades)

    return HistoricalContextEngine(
        trade_store=store
    )


def test_uses_only_trades_up_to_timestamp(
    tmp_path,
):
    engine = build_engine(
        tmp_path
    )

    result = engine.calculate(
        symbol="BTC",
        timestamp=104,
        lookback_seconds=100,
    )

    assert result.trade_count == 5
    assert result.timestamp == 104


def test_future_trade_cannot_enter_result(
    tmp_path,
):
    engine = build_engine(
        tmp_path
    )

    result = engine.calculate(
        symbol="BTC",
        timestamp=104,
        lookback_seconds=100,
    )

    assert result.vwap is not None

    expected_vwap = (
        100.0 * 2.0
        + 102.0 * 1.0
        + 101.0 * 3.0
        + 104.0 * 4.0
        + 103.0 * 2.0
    ) / (
        2.0
        + 1.0
        + 3.0
        + 4.0
        + 2.0
    )

    assert result.vwap == expected_vwap


def test_vwap_position_is_historical(
    tmp_path,
):
    engine = build_engine(
        tmp_path
    )

    result = engine.calculate(
        symbol="BTC",
        timestamp=104,
        lookback_seconds=100,
    )

    # Last historical trade price = 103.
    # Historical VWAP is slightly below 103.
    assert result.vwap_position == "ABOVE_VWAP"
    assert result.vwap_distance_pct > 0


def test_cvd_is_directionally_calculated(
    tmp_path,
):
    engine = build_engine(
        tmp_path
    )

    result = engine.calculate(
        symbol="BTC",
        timestamp=104,
        lookback_seconds=100,
    )

    expected_delta = (
        2.0
        + 1.0
        - 3.0
        + 4.0
        - 2.0
    )

    assert result.cvd_delta == expected_delta


def test_volume_profile_has_historical_boundaries(
    tmp_path,
):
    engine = build_engine(
        tmp_path
    )

    result = engine.calculate(
        symbol="BTC",
        timestamp=104,
        lookback_seconds=100,
    )

    assert result.poc is not None
    assert result.vah is not None
    assert result.val is not None

    assert result.val <= result.poc
    assert result.poc <= result.vah


def test_result_is_marked_historical(
    tmp_path,
):
    engine = build_engine(
        tmp_path
    )

    result = engine.calculate(
        symbol="BTC",
        timestamp=104,
    )

    assert result.historical is True


def test_empty_historical_window_fails(
    tmp_path,
):
    engine = build_engine(
        tmp_path
    )

    try:
        engine.calculate(
            symbol="BTC",
            timestamp=50,
            lookback_seconds=10,
        )
    except ValueError as exc:
        assert (
            "No historical trades available"
            in str(exc)
        )
    else:
        raise AssertionError(
            "Expected ValueError."
        )


def test_invalid_timestamp_fails(
    tmp_path,
):
    engine = build_engine(
        tmp_path
    )

    try:
        engine.calculate(
            symbol="BTC",
            timestamp=0,
        )
    except ValueError as exc:
        assert (
            "Timestamp must be greater than zero"
            in str(exc)
        )
    else:
        raise AssertionError(
            "Expected ValueError."
        )


def test_invalid_lookback_fails(
    tmp_path,
):
    engine = build_engine(
        tmp_path
    )

    try:
        engine.calculate(
            symbol="BTC",
            timestamp=104,
            lookback_seconds=0,
        )
    except ValueError as exc:
        assert (
            "Lookback seconds must be greater than zero"
            in str(exc)
        )
    else:
        raise AssertionError(
            "Expected ValueError."
        )
def test_seconds_setup_timestamp_matches_millisecond_trades(
    tmp_path,
):
    store = TradeStore(
        tmp_path / "crypto.db"
    )

    store.save_trades(
        [
            make_trade(
                1786681800000,
                100.0,
                2.0,
                "buy",
            ),
            make_trade(
                1786681801000,
                101.0,
                1.0,
                "buy",
            ),
            make_trade(
                1786681802000,
                100.0,
                2.0,
                "sell",
            ),
        ]
    )

    engine = HistoricalContextEngine(
        trade_store=store
    )

    result = engine.calculate(
        symbol="BTC",
        timestamp=1786681802,
        lookback_seconds=3600,
    )

    assert result.timestamp == 1786681802
    assert result.trade_count == 3
    assert result.historical is True