from __future__ import annotations

import json

from core.candle_store import CandleStore
from core.market_registry import MarketRegistry
from models.candle import Candle
from tools.capture_public_candles import (
    MAX_CHANNELS,
    PublicCandleCapture,
    decode_public_candle,
    extract_usdt_market_symbols,
    normalize_market_symbol,
    project_symbol,
)


def make_message(
    symbol: str = "BTCUSDT",
    resolution: str = "60",
    timestamp: int = 1000,
    close: float = 63000.0,
    volume: float = 20.0,
) -> str:
    return json.dumps(
        {
            "push": {
                "channel": (
                    f"public:candle-"
                    f"{symbol}-"
                    f"{resolution}"
                ),
                "pub": {
                    "data": {
                        "t": timestamp,
                        "o": 62000.0,
                        "h": 64000.0,
                        "l": 61000.0,
                        "c": close,
                        "v": volume,
                    }
                },
            }
        }
    )


def make_candle(
    timestamp: int = 1000,
) -> Candle:
    return Candle(
        timestamp=timestamp,
        open=62000.0,
        high=64000.0,
        low=61000.0,
        close=63000.0,
        volume=20.0,
    )


def test_normalize_market_symbol():
    assert (
        normalize_market_symbol("BTCUSDT")
        == "BTCUSDT"
    )

    assert (
        normalize_market_symbol("btcusdt")
        == "BTCUSDT"
    )

    assert (
        normalize_market_symbol("ETHUSDT")
        == "ETHUSDT"
    )


def test_normalize_market_symbol_rejects_empty():
    try:
        normalize_market_symbol("")
    except ValueError as exc:
        assert "empty" in str(exc).lower()
    else:
        raise AssertionError(
            "Expected ValueError."
        )


def test_project_symbol():
    assert (
        project_symbol("BTCUSDT")
        == "BTC"
    )

    assert (
        project_symbol("ETHUSDT")
        == "ETH"
    )

    assert (
        project_symbol("USDTIRT")
        == "USDT"
    )

    assert (
        project_symbol("BTCIRT")
        == "BTC"
    )


def test_extract_usdt_market_symbols():
    result = (
        extract_usdt_market_symbols(
            {
                "stats": {
                    "btc-usdt": {},
                    "eth-usdt": {},
                    "usdt-irt": {},
                    "btc-rls": {},
                    "eth-rls": {},
                    "INVALID": {},
                }
            }
        )
    )

    assert result == [
        "BTCUSDT",
        "ETHUSDT",
    ]


def test_extract_usdt_market_symbols_is_unique():
    result = (
        extract_usdt_market_symbols(
            {
                "stats": {
                    "btc-usdt": {},
                    "btc-usdt-copy": {},
                    "eth-usdt": {},
                    "btc-rls": {},
                }
            }
        )
    )

    assert result == [
        "BTCUSDT",
        "ETHUSDT",
    ]


def test_extract_usdt_market_symbols_case_insensitive():
    result = (
        extract_usdt_market_symbols(
            {
                "stats": {
                    "btc-usdt": {},
                    "ETH-USDT": {},
                    "Sol-Usdt": {},
                }
            }
        )
    )

    assert result == [
        "BTCUSDT",
        "ETHUSDT",
        "SOLUSDT",
    ]


def test_extract_usdt_market_symbols_excludes_irt():
    result = (
        extract_usdt_market_symbols(
            {
                "stats": {
                    "btc-rls": {},
                    "eth-rls": {},
                    "usdt-rls": {},
                }
            }
        )
    )

    assert result == []


def test_decode_valid_usdt_candle():
    result = decode_public_candle(
        make_message(
            symbol="BTCUSDT"
        )
    )

    assert result is not None

    assert (
        result["market_symbol"]
        == "BTCUSDT"
    )

    assert (
        result["symbol"]
        == "BTC"
    )

    assert (
        result["resolution"]
        == "60"
    )

    candle = result["candle"]

    assert candle.timestamp == 1000
    assert candle.open == 62000.0
    assert candle.high == 64000.0
    assert candle.low == 61000.0
    assert candle.close == 63000.0
    assert candle.volume == 20.0


def test_decode_rejects_irt_market():
    result = decode_public_candle(
        make_message(
            symbol="BTCIRT"
        )
    )

    assert result is None


def test_decode_valid_eth_usdt_candle():
    result = decode_public_candle(
        make_message(
            symbol="ETHUSDT",
            close=3500.0,
        )
    )

    assert result is not None

    assert (
        result["market_symbol"]
        == "ETHUSDT"
    )

    assert (
        result["symbol"]
        == "ETH"
    )

    assert (
        result["candle"].close
        == 3500.0
    )


def test_decode_invalid_json():
    assert (
        decode_public_candle(
            "not-json"
        )
        is None
    )


def test_decode_empty_message():
    assert (
        decode_public_candle("")
        is None
    )


def test_decode_ping_message():
    assert (
        decode_public_candle("{}")
        is None
    )


def test_decode_non_candle_channel():
    message = json.dumps(
        {
            "push": {
                "channel": (
                    "public:trades-BTCUSDT"
                ),
                "pub": {
                    "data": {}
                },
            }
        }
    )

    assert (
        decode_public_candle(
            message
        )
        is None
    )


def test_capture_saves_usdt_candle(
    tmp_path,
):
    store = CandleStore(
        tmp_path / "crypto.db"
    )

    registry = MarketRegistry()

    capture = PublicCandleCapture(
        symbols=["BTCUSDT"],
        resolution="60",
        candle_store=store,
        market_registry=registry,
    )

    capture.on_message(
        None,
        make_message(
            symbol="BTCUSDT",
            timestamp=1000,
            close=63000.0,
            volume=20.0,
        ),
    )

    assert (
        capture.received_count
        == 1
    )

    assert (
        capture.saved_count
        == 1
    )

    candle = store.get(
        symbol="BTCUSDT",
        timestamp=1000,
        timeframe="60",
    )

    assert candle is not None
    assert candle.close == 63000.0
    assert candle.volume == 20.0


def test_capture_registers_usdt_market(
    tmp_path,
):
    store = CandleStore(
        tmp_path / "crypto.db"
    )

    registry = MarketRegistry()

    capture = PublicCandleCapture(
        symbols=["BTCUSDT"],
        resolution="60",
        candle_store=store,
        market_registry=registry,
    )

    capture.on_message(
        None,
        make_message(
            symbol="BTCUSDT"
        ),
    )

    descriptor = registry.get(
        "BTCUSDT"
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

    assert (
        descriptor.execution_market
        == "BTCUSDT"
    )


def test_duplicate_updates_are_upserted(
    tmp_path,
):
    store = CandleStore(
        tmp_path / "crypto.db"
    )

    registry = MarketRegistry()

    capture = PublicCandleCapture(
        symbols=["BTCUSDT"],
        resolution="60",
        candle_store=store,
        market_registry=registry,
    )

    capture.on_message(
        None,
        make_message(
            timestamp=1000,
            close=63000.0,
            volume=20.0,
        ),
    )

    capture.on_message(
        None,
        make_message(
            timestamp=1000,
            close=63500.0,
            volume=35.0,
        ),
    )

    assert (
        capture.received_count
        == 2
    )

    assert (
        capture.saved_count
        == 2
    )

    assert (
        store.count("BTCUSDT")
        == 1
    )

    candle = store.get(
        symbol="BTCUSDT",
        timestamp=1000,
        timeframe="60",
    )

    assert candle is not None

    assert candle.close == 63500.0
    assert candle.volume == 35.0


def test_multiple_timestamps(
    tmp_path,
):
    store = CandleStore(
        tmp_path / "crypto.db"
    )

    capture = PublicCandleCapture(
        symbols=["BTCUSDT"],
        resolution="60",
        candle_store=store,
    )

    for timestamp in (
        1000,
        1060,
        1120,
    ):
        capture.on_message(
            None,
            make_message(
                timestamp=timestamp,
                close=float(timestamp),
                volume=10.0,
            ),
        )

    assert (
        store.count("BTCUSDT")
        == 3
    )


def test_different_usdt_markets_are_stored_separately(
    tmp_path,
):
    store = CandleStore(
        tmp_path / "crypto.db"
    )

    registry = MarketRegistry()

    capture = PublicCandleCapture(
        symbols=[
            "BTCUSDT",
            "ETHUSDT",
            "SOLUSDT",
        ],
        resolution="60",
        candle_store=store,
        market_registry=registry,
    )

    capture.on_message(
        None,
        make_message(
            symbol="BTCUSDT",
            timestamp=1000,
            close=63000.0,
        ),
    )

    capture.on_message(
        None,
        make_message(
            symbol="ETHUSDT",
            timestamp=1000,
            close=3500.0,
        ),
    )

    capture.on_message(
        None,
        make_message(
            symbol="SOLUSDT",
            timestamp=1000,
            close=150.0,
        ),
    )

    assert (
        store.count("BTCUSDT")
        == 1
    )

    assert (
        store.count("ETHUSDT")
        == 1
    )

    assert (
        store.count("SOLUSDT")
        == 1
    )

    btc = store.get(
        symbol="BTCUSDT",
        timestamp=1000,
    )

    eth = store.get(
        symbol="ETHUSDT",
        timestamp=1000,
    )

    sol = store.get(
        symbol="SOLUSDT",
        timestamp=1000,
    )

    assert btc is not None
    assert eth is not None
    assert sol is not None

    assert btc.close == 63000.0
    assert eth.close == 3500.0
    assert sol.close == 150.0


def test_usdt_bridge_is_not_captured_as_analysis_market(
    tmp_path,
):
    store = CandleStore(
        tmp_path / "crypto.db"
    )

    registry = MarketRegistry()

    capture = PublicCandleCapture(
        symbols=["BTCUSDT"],
        resolution="60",
        candle_store=store,
        market_registry=registry,
    )

    assert (
        "USDTIRT"
        not in capture.symbols
    )

    descriptor = (
        registry.get("BTCUSDT")
    )

    assert descriptor is not None

    assert (
        descriptor.analysis_market
        == "BTCUSDT"
    )


def test_market_descriptors_are_registered():
    registry = MarketRegistry()

    capture = PublicCandleCapture(
        symbols=[
            "BTCUSDT",
            "ETHUSDT",
            "SOLUSDT",
        ],
        resolution="60",
        market_registry=registry,
    )

    assert (
        len(capture.market_descriptors)
        == 3
    )

    assert (
        registry.get("BTCUSDT")
        is not None
    )

    assert (
        registry.get("ETHUSDT")
        is not None
    )

    assert (
        registry.get("SOLUSDT")
        is not None
    )


def test_all_capture_symbols_must_be_usdt():
    try:
        PublicCandleCapture(
            symbols=[
                "BTCIRT"
            ],
            resolution="60",
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


def test_mixed_irt_and_usdt_symbols_are_rejected():
    try:
        PublicCandleCapture(
            symbols=[
                "BTCUSDT",
                "ETHIRT",
            ],
            resolution="60",
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
        PublicCandleCapture(
            symbols=symbols,
            resolution="60",
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


def test_capture_uses_usdt_only_market_discovery(
    tmp_path,
):
    markets = {
        "stats": {
            "BTC-usdt": {},
            "ETH-usdt": {},
            "SOL-usdt": {},
            "BTC-rls": {},
            "ETH-rls": {},
            "SOL-rls": {},
            "USDT-rls": {},
        }
    }

    symbols = extract_usdt_market_symbols(
        markets
    )

    assert symbols == [
        "BTCUSDT",
        "ETHUSDT",
        "SOLUSDT",
    ]


def test_candle_store_does_not_mix_irt_and_usdt(
    tmp_path,
):
    store = CandleStore(
        tmp_path / "crypto.db"
    )

    registry = MarketRegistry()

    capture = PublicCandleCapture(
        symbols=["BTCUSDT"],
        resolution="60",
        candle_store=store,
        market_registry=registry,
    )

    capture.on_message(
        None,
        make_message(
            symbol="BTCUSDT",
            timestamp=1000,
            close=63000.0,
        ),
    )

    assert (
        store.count("BTCUSDT")
        == 1
    )

    assert (
        store.count("BTCIRT")
        == 0
    )