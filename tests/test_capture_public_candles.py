from __future__ import annotations

import json

from core.candle_store import CandleStore
from core.market_registry import (
    MarketRegistry,
)
from models.candle import Candle
from tools.capture_public_candles import (
    MAX_CHANNELS,
    PublicCandleCapture,
    decode_public_candle,
    extract_market_symbols,
    normalize_market_symbol,
    project_symbol,
)


def make_message(
    symbol: str = "BTCIRT",
    resolution: str = "60",
    timestamp: int = 1000,
    close: float = 105.0,
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
                        "o": 100.0,
                        "h": 110.0,
                        "l": 95.0,
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
        open=100.0,
        high=110.0,
        low=95.0,
        close=105.0,
        volume=20.0,
    )


def test_normalize_market_symbol():
    assert (
        normalize_market_symbol("BTC")
        == "BTCIRT"
    )

    assert (
        normalize_market_symbol("btCirt")
        == "BTCIRT"
    )

    assert (
        normalize_market_symbol("ETHIRT")
        == "ETHIRT"
    )


def test_project_symbol():
    assert (
        project_symbol("BTCIRT")
        == "BTC"
    )

    assert (
        project_symbol("ETHIRT")
        == "ETH"
    )

    assert (
        project_symbol("BTCUSDT")
        == "BTC"
    )

    assert (
        project_symbol("USDTIRT")
        == "USDT"
    )


def test_extract_market_symbols():
    result = extract_market_symbols(
        {
            "stats": {
                "BTC-rls": {},
                "ETH-rls": {},
                "USDT-rls": {},
                "INVALID": {},
                "BTC-usdt": {},
            }
        }
    )

    assert result == [
        "BTCIRT",
        "ETHIRT",
        "USDTIRT",
    ]


def test_extract_market_symbols_is_unique():
    result = extract_market_symbols(
        {
            "stats": {
                "BTC-rls": {},
                "BTC-rls-copy": {},
                "ETH-rls": {},
            }
        }
    )

    assert result == [
        "BTCIRT",
        "ETHIRT",
    ]


def test_decode_valid_candle():
    result = decode_public_candle(
        make_message()
    )

    assert result is not None

    assert (
        result["market_symbol"]
        == "BTCIRT"
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
    assert candle.open == 100.0
    assert candle.high == 110.0
    assert candle.low == 95.0
    assert candle.close == 105.0
    assert candle.volume == 20.0


def test_decode_valid_usdt_market():
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


def test_decode_valid_usdt_irt_bridge():
    result = decode_public_candle(
        make_message(
            symbol="USDTIRT"
        )
    )

    assert result is not None

    assert (
        result["market_symbol"]
        == "USDTIRT"
    )

    assert (
        result["symbol"]
        == "USDT"
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
                    "public:trades-BTCIRT"
                ),
                "pub": {
                    "data": {}
                },
            }
        }
    )

    assert (
        decode_public_candle(message)
        is None
    )


def test_capture_saves_candle(
    tmp_path,
):
    store = CandleStore(
        tmp_path / "crypto.db"
    )

    registry = MarketRegistry()

    capture = PublicCandleCapture(
        symbols=["BTCIRT"],
        resolution="60",
        candle_store=store,
        market_registry=registry,
    )

    capture.on_message(
        None,
        make_message(
            timestamp=1000,
            close=105.0,
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
        symbol="BTCIRT",
        timestamp=1000,
        timeframe="60",
    )

    assert candle is not None
    assert candle.close == 105.0
    assert candle.volume == 20.0

    descriptor = registry.get(
        "BTCIRT"
    )

    assert descriptor is not None
    assert (
        descriptor.base_asset
        == "BTC"
    )
    assert (
        descriptor.quote_asset
        == "IRT"
    )
    assert (
        descriptor.analysis_market
        == "BTCUSDT"
    )
    assert (
        descriptor.execution_market
        == "BTCIRT"
    )


def test_duplicate_updates_are_upserted(
    tmp_path,
):
    store = CandleStore(
        tmp_path / "crypto.db"
    )

    registry = MarketRegistry()

    capture = PublicCandleCapture(
        symbols=["BTCIRT"],
        resolution="60",
        candle_store=store,
        market_registry=registry,
    )

    capture.on_message(
        None,
        make_message(
            timestamp=1000,
            close=105.0,
            volume=20.0,
        ),
    )

    capture.on_message(
        None,
        make_message(
            timestamp=1000,
            close=108.0,
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
        store.count("BTCIRT")
        == 1
    )

    candle = store.get(
        symbol="BTCIRT",
        timestamp=1000,
        timeframe="60",
    )

    assert candle is not None
    assert candle.close == 108.0
    assert candle.volume == 35.0


def test_multiple_timestamps(
    tmp_path,
):
    store = CandleStore(
        tmp_path / "crypto.db"
    )

    capture = PublicCandleCapture(
        symbols=["BTCIRT"],
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
        store.count("BTCIRT")
        == 3
    )


def test_different_markets_have_separate_registry_identity(
    tmp_path,
):
    store = CandleStore(
        tmp_path / "crypto.db"
    )

    registry = MarketRegistry()

    capture = PublicCandleCapture(
        symbols=[
            "BTCIRT",
            "BTCUSDT",
            "USDTIRT",
        ],
        resolution="60",
        candle_store=store,
        market_registry=registry,
    )

    capture.on_message(
        None,
        make_message(
            symbol="BTCIRT",
            timestamp=1000,
            close=11_830_000_000,
        ),
    )

    capture.on_message(
        None,
        make_message(
            symbol="BTCUSDT",
            timestamp=1000,
            close=63_000,
        ),
    )

    capture.on_message(
        None,
        make_message(
            symbol="USDTIRT",
            timestamp=1000,
            close=187_000,
        ),
    )

    assert (
        store.count("BTCIRT")
        == 1
    )

    assert (
        store.count("BTCUSDT")
        == 1
    )

    assert (
        store.count("USDTIRT")
        == 1
    )

    btc_irt = registry.require(
        "BTCIRT"
    )

    btc_usdt = registry.require(
        "BTCUSDT"
    )

    bridge = registry.require(
        "USDTIRT"
    )

    assert btc_irt.analysis_market == (
        "BTCUSDT"
    )

    assert btc_irt.execution_market == (
        "BTCIRT"
    )

    assert btc_usdt.analysis_market == (
        "BTCUSDT"
    )

    assert btc_usdt.execution_market == (
        "BTCUSDT"
    )

    assert bridge.analysis_market == (
        "USDTIRT"
    )

    assert bridge.execution_market == (
        "USDTIRT"
    )


def test_max_channel_limit():
    symbols = [
        f"TOKEN{i}"
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


def test_market_descriptors_are_registered():
    registry = MarketRegistry()

    capture = PublicCandleCapture(
        symbols=[
            "BTCIRT",
            "ETHIRT",
            "USDTIRT",
        ],
        resolution="60",
        market_registry=registry,
    )

    assert len(
        capture.market_descriptors
    ) == 3

    assert (
        registry.get("BTCIRT")
        is not None
    )

    assert (
        registry.get("ETHIRT")
        is not None
    )

    assert (
        registry.get("USDTIRT")
        is not None
    )