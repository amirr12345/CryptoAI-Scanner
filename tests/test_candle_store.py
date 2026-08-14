from core.candle_store import CandleStore
from models.candle import Candle


def make_candle(
    timestamp: int,
    close: float,
    volume: float,
) -> Candle:
    return Candle(
        timestamp=timestamp,
        open=100.0,
        high=110.0,
        low=95.0,
        close=close,
        volume=volume,
    )


def test_save_and_get(tmp_path):
    store = CandleStore(
        tmp_path / "crypto.db"
    )

    candle = make_candle(
        1000,
        close=105.0,
        volume=20.0,
    )

    assert store.save(
        symbol="BTC",
        candle=candle,
        timeframe="60",
    ) is True

    result = store.get(
        symbol="BTC",
        timestamp=1000,
        timeframe="60",
    )

    assert result is not None
    assert result.timestamp == 1000
    assert result.close == 105.0
    assert result.volume == 20.0


def test_same_candle_is_updated_not_duplicated(
    tmp_path,
):
    store = CandleStore(
        tmp_path / "crypto.db"
    )

    first = make_candle(
        1000,
        close=105.0,
        volume=20.0,
    )

    second = make_candle(
        1000,
        close=108.0,
        volume=35.0,
    )

    store.save(
        symbol="BTC",
        candle=first,
    )

    store.save(
        symbol="BTC",
        candle=second,
    )

    assert store.count("BTC") == 1

    result = store.get(
        symbol="BTC",
        timestamp=1000,
    )

    assert result is not None
    assert result.close == 108.0
    assert result.volume == 35.0


def test_multiple_candles_are_stored(
    tmp_path,
):
    store = CandleStore(
        tmp_path / "crypto.db"
    )

    store.save(
        symbol="BTC",
        candle=make_candle(
            1000,
            close=101.0,
            volume=10.0,
        ),
    )

    store.save(
        symbol="BTC",
        candle=make_candle(
            1060,
            close=102.0,
            volume=11.0,
        ),
    )

    store.save(
        symbol="BTC",
        candle=make_candle(
            1120,
            close=103.0,
            volume=12.0,
        ),
    )

    assert store.count("BTC") == 3


def test_latest_returns_newest_candle(
    tmp_path,
):
    store = CandleStore(
        tmp_path / "crypto.db"
    )

    store.save(
        symbol="BTC",
        candle=make_candle(
            1000,
            close=101.0,
            volume=10.0,
        ),
    )

    store.save(
        symbol="BTC",
        candle=make_candle(
            1120,
            close=103.0,
            volume=12.0,
        ),
    )

    latest = store.latest("BTC")

    assert latest is not None
    assert latest.timestamp == 1120
    assert latest.close == 103.0


def test_recent_is_chronological(
    tmp_path,
):
    store = CandleStore(
        tmp_path / "crypto.db"
    )

    for timestamp in (
        1000,
        1060,
        1120,
        1180,
    ):
        store.save(
            symbol="BTC",
            candle=make_candle(
                timestamp,
                close=float(timestamp),
                volume=10.0,
            ),
        )

    candles = store.get_recent(
        symbol="BTC",
        timeframe="60",
        limit=3,
    )

    assert [
        candle.timestamp
        for candle in candles
    ] == [
        1060,
        1120,
        1180,
    ]


def test_latest_timestamp(
    tmp_path,
):
    store = CandleStore(
        tmp_path / "crypto.db"
    )

    assert (
        store.latest_timestamp("BTC")
        is None
    )

    store.save(
        symbol="BTC",
        candle=make_candle(
            1000,
            close=101.0,
            volume=10.0,
        ),
    )

    store.save(
        symbol="BTC",
        candle=make_candle(
            1120,
            close=103.0,
            volume=12.0,
        ),
    )

    assert (
        store.latest_timestamp("BTC")
        == 1120
    )


def test_symbol_is_case_insensitive(
    tmp_path,
):
    store = CandleStore(
        tmp_path / "crypto.db"
    )

    store.save(
        symbol="btc",
        candle=make_candle(
            1000,
            close=105.0,
            volume=20.0,
        ),
    )

    assert store.count("BTC") == 1

    result = store.get(
        symbol="BTC",
        timestamp=1000,
    )

    assert result is not None
    assert result.close == 105.0


def test_timeframe_is_part_of_unique_key(
    tmp_path,
):
    store = CandleStore(
        tmp_path / "crypto.db"
    )

    candle = make_candle(
        1000,
        close=105.0,
        volume=20.0,
    )

    store.save(
        symbol="BTC",
        candle=candle,
        timeframe="60",
    )

    store.save(
        symbol="BTC",
        candle=candle,
        timeframe="300",
    )

    assert store.count(
        "BTC",
        timeframe="60",
    ) == 1

    assert store.count(
        "BTC",
        timeframe="300",
    ) == 1

def test_exchange_market_symbol_and_project_symbol_are_equivalent(
    tmp_path,
):
    store = CandleStore(
        tmp_path / "crypto.db"
    )

    candle = make_candle(
        1000,
        close=105.0,
        volume=20.0,
    )

    store.save(
        symbol="BTCIRT",
        candle=candle,
        timeframe="60",
    )

    assert store.count(
        "BTC"
    ) == 1

    assert store.count(
        "BTCIRT"
    ) == 1

    assert (
        store.latest_timestamp(
            "BTC"
        )
        == 1000
    )

    assert (
        store.latest_timestamp(
            "BTCIRT"
        )
        == 1000
    )

    assert (
        store.get(
            symbol="BTC",
            timestamp=1000,
        )
        is not None
    )

    assert (
        store.get(
            symbol="BTCIRT",
            timestamp=1000,
        )
        is not None
    )