from __future__ import annotations

import json

from core.candle_store import CandleStore
from tools.capture_public_candles import (
    PublicCandleCapture,
    decode_public_candle,
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


def test_decode_valid_candle():
    result = decode_public_candle(
        make_message()
    )

    assert result is not None
    assert result["symbol"] == "BTCIRT"
    assert result["resolution"] == "60"

    candle = result["candle"]

    assert candle.timestamp == 1000
    assert candle.open == 100.0
    assert candle.high == 110.0
    assert candle.low == 95.0
    assert candle.close == 105.0
    assert candle.volume == 20.0


def test_decode_invalid_json_returns_none():
    assert (
        decode_public_candle(
            "not-json"
        )
        is None
    )


def test_decode_empty_message_returns_none():
    assert (
        decode_public_candle("")
        is None
    )


def test_decode_ping_message_returns_none():
    assert (
        decode_public_candle("{}")
        is None
    )


def test_decode_non_candle_channel_returns_none():
    message = json.dumps(
        {
            "push": {
                "channel": "public:trades-BTCIRT",
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

    capture = PublicCandleCapture(
        symbols=["BTC"],
        resolution="60",
        candle_store=store,
    )

    capture.on_message(
        None,
        make_message(
            timestamp=1000,
            close=105.0,
            volume=20.0,
        ),
    )

    assert capture.received_count == 1
    assert capture.saved_count == 1

    candle = store.get(
        symbol="BTCIRT",
        timestamp=1000,
        timeframe="60",
    )

    assert candle is not None
    assert candle.close == 105.0
    assert candle.volume == 20.0


def test_duplicate_updates_are_upserted(
    tmp_path,
):
    store = CandleStore(
        tmp_path / "crypto.db"
    )

    capture = PublicCandleCapture(
        symbols=["BTC"],
        resolution="60",
        candle_store=store,
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

    assert capture.received_count == 2
    assert capture.saved_count == 2

    assert store.count(
        symbol="BTCIRT",
        timeframe="60",
    ) == 1

    candle = store.get(
        symbol="BTCIRT",
        timestamp=1000,
        timeframe="60",
    )

    assert candle is not None
    assert candle.close == 108.0
    assert candle.volume == 35.0


def test_multiple_timestamps_are_stored(
    tmp_path,
):
    store = CandleStore(
        tmp_path / "crypto.db"
    )

    capture = PublicCandleCapture(
        symbols=["BTC"],
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

    assert store.count(
        symbol="BTCIRT",
        timeframe="60",
    ) == 3