from __future__ import annotations

import json

from core.market_registry import MarketRegistry
from core.trade_store import TradeStore
from tools.capture_public_trades import (
    MAX_CHANNELS,
    PublicTradeCapture,
    decode_public_trades,
    extract_usdt_market_symbols,
    normalize_market_symbol,
    project_symbol,
)


def make_message(
    symbol: str = "BTCUSDT",
    timestamp: int = 1786728600123,
    price: float = 63000.0,
    volume: float = 0.25,
    side: str = "buy",
) -> str:
    return json.dumps(
        {
            "push": {
                "channel": (
                    f"public:trades-"
                    f"{symbol}"
                ),
                "pub": {
                    "data": [
                        {
                            "t": timestamp,
                            "p": price,
                            "a": volume,
                            "s": side,
                        }
                    ]
                },
            }
        }
    )


def test_normalize_market_symbol():
    assert (
        normalize_market_symbol(
            "btcusdt"
        )
        == "BTCUSDT"
    )


def test_normalize_market_symbol_rejects_irt():
    try:
        normalize_market_symbol(
            "BTCIRT"
        )
    except ValueError as exc:
        assert "BASEUSDT" in str(exc)
    else:
        raise AssertionError(
            "Expected ValueError."
        )


def test_project_symbol():
    assert (
        project_symbol("BTCUSDT")
        == "BTC"
    )


def test_extract_usdt_market_symbols():
    result = (
        extract_usdt_market_symbols(
            {
                "stats": {
                    "btc-usdt": {},
                    "eth-usdt": {},
                    "btc-rls": {},
                    "usdt-rls": {},
                }
            }
        )
    )

    assert result == [
        "BTCUSDT",
        "ETHUSDT",
    ]


def test_decode_public_trade():
    trades = decode_public_trades(
        make_message()
    )

    assert len(trades) == 1

    trade = trades[0]

    assert trade.symbol == "BTCUSDT"
    assert trade.timestamp == 1786728600123
    assert trade.price == 63000.0
    assert trade.volume == 0.25
    assert trade.side == "buy"


def test_decode_sell_trade():
    trades = decode_public_trades(
        make_message(
            side="sell"
        )
    )

    assert len(trades) == 1

    assert (
        trades[0].side
        == "sell"
    )


def test_decode_invalid_json():
    assert (
        decode_public_trades(
            "not-json"
        )
        == []
    )


def test_decode_empty_message():
    assert (
        decode_public_trades("")
        == []
    )


def test_decode_ping():
    assert (
        decode_public_trades("{}")
        == []
    )


def test_decode_non_trade_channel():
    message = json.dumps(
        {
            "push": {
                "channel": (
                    "public:candle-BTCUSDT-60"
                ),
                "pub": {
                    "data": {}
                },
            }
        }
    )

    assert (
        decode_public_trades(
            message
        )
        == []
    )


def test_decode_multiple_trades():
    message = json.dumps(
        {
            "push": {
                "channel": (
                    "public:trades-BTCUSDT"
                ),
                "pub": {
                    "data": [
                        {
                            "t": 1000,
                            "p": 63000,
                            "a": 0.1,
                            "s": "buy",
                        },
                        {
                            "t": 1100,
                            "p": 63100,
                            "a": 0.2,
                            "s": "sell",
                        },
                    ]
                },
            }
        }
    )

    trades = decode_public_trades(
        message
    )

    assert len(trades) == 2

    assert trades[0].timestamp == 1000
    assert trades[0].side == "buy"

    assert trades[1].timestamp == 1100
    assert trades[1].side == "sell"


def test_decode_rejects_irt_trade_channel():
    message = make_message(
        symbol="BTCIRT"
    )

    assert (
        decode_public_trades(
            message
        )
        == []
    )


def test_capture_saves_trade(
    tmp_path,
):
    store = TradeStore(
        tmp_path / "crypto.db"
    )

    registry = MarketRegistry()

    capture = PublicTradeCapture(
        symbols=["BTCUSDT"],
        trade_store=store,
        market_registry=registry,
    )

    capture.on_message(
        None,
        make_message(
            timestamp=1786728600123
        ),
    )

    assert (
        capture.received_message_count
        == 1
    )

    assert (
        capture.received_trade_count
        == 1
    )

    assert (
        capture.saved_trade_count
        == 1
    )

    assert (
        store.count("BTCUSDT")
        == 1
    )

    trade = store.get_trades(
        symbol="BTCUSDT"
    )[0]

    assert (
        trade.timestamp
        == 1786728600123
    )

    assert trade.price == 63000.0
    assert trade.volume == 0.25
    assert trade.side == "buy"


def test_duplicate_trade_is_ignored(
    tmp_path,
):
    store = TradeStore(
        tmp_path / "crypto.db"
    )

    capture = PublicTradeCapture(
        symbols=["BTCUSDT"],
        trade_store=store,
    )

    message = make_message()

    capture.on_message(
        None,
        message,
    )

    capture.on_message(
        None,
        message,
    )

    assert (
        capture.received_trade_count
        == 2
    )

    assert (
        capture.saved_trade_count
        == 1
    )

    assert (
        capture.duplicate_trade_count
        == 1
    )

    assert (
        store.count("BTCUSDT")
        == 1
    )


def test_multiple_trades_are_saved(
    tmp_path,
):
    store = TradeStore(
        tmp_path / "crypto.db"
    )

    capture = PublicTradeCapture(
        symbols=["BTCUSDT"],
        trade_store=store,
    )

    message = json.dumps(
        {
            "push": {
                "channel": (
                    "public:trades-BTCUSDT"
                ),
                "pub": {
                    "data": [
                        {
                            "t": 1000,
                            "p": 63000,
                            "a": 0.1,
                            "s": "buy",
                        },
                        {
                            "t": 1100,
                            "p": 63100,
                            "a": 0.2,
                            "s": "sell",
                        },
                        {
                            "t": 1200,
                            "p": 63200,
                            "a": 0.3,
                            "s": "buy",
                        },
                    ]
                },
            }
        }
    )

    capture.on_message(
        None,
        message,
    )

    assert (
        capture.received_trade_count
        == 3
    )

    assert (
        capture.saved_trade_count
        == 3
    )

    assert (
        store.count("BTCUSDT")
        == 3
    )


def test_trade_timestamp_remains_in_milliseconds(
    tmp_path,
):
    store = TradeStore(
        tmp_path / "crypto.db"
    )

    capture = PublicTradeCapture(
        symbols=["BTCUSDT"],
        trade_store=store,
    )

    timestamp = 1786728600123

    capture.on_message(
        None,
        make_message(
            timestamp=timestamp
        ),
    )

    latest = (
        store.latest_timestamp(
            "BTCUSDT"
        )
    )

    assert latest == timestamp

    assert latest > 100_000_000_000


def test_market_registry_identity(
    tmp_path,
):
    store = TradeStore(
        tmp_path / "crypto.db"
    )

    registry = MarketRegistry()

    capture = PublicTradeCapture(
        symbols=["BTCUSDT"],
        trade_store=store,
        market_registry=registry,
    )

    descriptor = (
        registry.get("BTCUSDT")
    )

    assert descriptor is not None

    assert (
        descriptor.base_asset
        == "BTC"
    )

    assert (
        descriptor.quote_asset
        == "USDT"
    )

    assert (
        descriptor.analysis_market
        == "BTCUSDT"
    )


def test_only_usdt_markets_are_allowed():
    try:
        PublicTradeCapture(
            symbols=["BTCIRT"]
        )
    except ValueError as exc:
        assert (
            "BASEUSDT"
            in str(exc)
        )
    else:
        raise AssertionError(
            "Expected ValueError."
        )


def test_mixed_markets_are_rejected():
    try:
        PublicTradeCapture(
            symbols=[
                "BTCUSDT",
                "ETHIRT",
            ]
        )
    except ValueError as exc:
        assert (
            "BASEUSDT"
            in str(exc)
        )
    else:
        raise AssertionError(
            "Expected ValueError."
        )


def test_max_channel_limit():
    symbols = [
        f"TOKEN{i}USDT"
        for i in range(
            MAX_CHANNELS + 1
        )
    ]

    try:
        PublicTradeCapture(
            symbols=symbols
        )
    except ValueError as exc:
        assert (
            "Maximum supported channels"
            in str(exc)
        )
    else:
        raise AssertionError(
            "Expected ValueError."
        )