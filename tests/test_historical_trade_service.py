from models.trade import Trade
from core.trade_store import TradeStore
from services.historical_trade_service import (
    HistoricalTradeService,
)


def trade(
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


def test_save_and_get_trades(tmp_path):
    store = TradeStore(
        tmp_path / "crypto.db"
    )

    service = HistoricalTradeService(
        store=store
    )

    trades = [
        trade(
            100,
            100.0,
            1.0,
            "buy",
        ),
        trade(
            101,
            101.0,
            2.0,
            "sell",
        ),
    ]

    inserted = service.save(trades)

    assert inserted == 2

    result = service.get(
        symbol="BTC"
    )

    assert len(result) == 2
    assert result[0].timestamp == 100
    assert result[1].timestamp == 101


def test_duplicate_trade_is_not_inserted_twice(
    tmp_path,
):
    store = TradeStore(
        tmp_path / "crypto.db"
    )

    service = HistoricalTradeService(
        store=store
    )

    item = trade(
        100,
        100.0,
        1.0,
        "buy",
    )

    assert service.save(
        [item]
    ) == 1

    assert service.save(
        [item]
    ) == 0

    assert service.count("BTC") == 1


def test_get_as_of_excludes_future_trades(
    tmp_path,
):
    store = TradeStore(
        tmp_path / "crypto.db"
    )

    service = HistoricalTradeService(
        store=store
    )

    service.save(
        [
            trade(
                100,
                100.0,
                1.0,
                "buy",
            ),
            trade(
                101,
                101.0,
                1.0,
                "sell",
            ),
            trade(
                102,
                102.0,
                1.0,
                "buy",
            ),
        ]
    )

    result = service.get_as_of(
        symbol="BTC",
        end_timestamp=101,
    )

    assert [
        item.timestamp
        for item in result
    ] == [100, 101]


def test_get_as_of_respects_lookback(
    tmp_path,
):
    store = TradeStore(
        tmp_path / "crypto.db"
    )

    service = HistoricalTradeService(
        store=store
    )

    service.save(
        [
            trade(
                100,
                100.0,
                1.0,
                "buy",
            ),
            trade(
                105,
                105.0,
                1.0,
                "buy",
            ),
            trade(
                110,
                110.0,
                1.0,
                "sell",
            ),
        ]
    )

    result = service.get_as_of(
        symbol="BTC",
        end_timestamp=110,
        lookback_seconds=5,
    )

    assert [
        item.timestamp
        for item in result
    ] == [105, 110]


def test_symbol_is_case_insensitive(
    tmp_path,
):
    store = TradeStore(
        tmp_path / "crypto.db"
    )

    service = HistoricalTradeService(
        store=store
    )

    service.save(
        [
            trade(
                100,
                100.0,
                1.0,
                "buy",
                symbol="btc",
            )
        ]
    )

    result = service.get(
        symbol="btc"
    )

    assert len(result) == 1
    assert result[0].symbol == "BTC"


def test_latest_timestamp(
    tmp_path,
):
    store = TradeStore(
        tmp_path / "crypto.db"
    )

    service = HistoricalTradeService(
        store=store
    )

    assert (
        service.latest_timestamp("BTC")
        is None
    )

    service.save(
        [
            trade(
                100,
                100.0,
                1.0,
                "buy",
            ),
            trade(
                150,
                105.0,
                2.0,
                "sell",
            ),
        ]
    )

    assert (
        service.latest_timestamp("BTC")
        == 150
    )