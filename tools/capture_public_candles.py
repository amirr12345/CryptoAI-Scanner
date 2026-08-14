from __future__ import annotations

import json
import sys
from pathlib import Path

import websocket

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.candle_store import CandleStore
from models.candle import Candle


WS_URL = "wss://ws.nobitex.ir/connection/websocket"

MAX_CHANNELS = 300


def normalize_market_symbol(
    symbol: str,
) -> str:
    value = symbol.strip().upper()

    if not value:
        raise ValueError(
            "Symbol cannot be empty."
        )

    if value.endswith("IRT"):
        return value

    return f"{value}IRT"


def decode_public_candle(
    message: str,
) -> dict | None:
    """
    Decode one Nobitex public candle WebSocket message.
    """

    if not message:
        return None

    if message == "{}":
        return None

    try:
        payload = json.loads(message)
    except json.JSONDecodeError:
        return None

    push = payload.get("push")

    if not push:
        return None

    channel = str(
        push.get("channel", "")
    )

    if not channel.startswith(
        "public:candle-"
    ):
        return None

    publication = push.get(
        "pub",
        {},
    )

    data = publication.get(
        "data"
    )

    if data is None:
        return None

    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            return None

    try:
        parts = channel.split("-")

        market_symbol = parts[1]
        resolution = parts[2]

        candle = Candle(
            timestamp=int(data["t"]),
            open=float(data["o"]),
            high=float(data["h"]),
            low=float(data["l"]),
            close=float(data["c"]),
            volume=float(data["v"]),
        )

    except (
        IndexError,
        KeyError,
        TypeError,
        ValueError,
    ):
        return None

    return {
        "symbol": market_symbol,
        "resolution": resolution,
        "candle": candle,
    }


class PublicCandleCapture:
    """
    Capture public OHLCV candles from Nobitex WebSocket
    and persist them through CandleStore.

    Repeated updates for the same
    (symbol, timeframe, timestamp) are handled by
    CandleStore UPSERT logic.
    """

    def __init__(
        self,
        symbols: list[str],
        resolution: str = "60",
        candle_store: CandleStore | None = None,
    ) -> None:
        if not symbols:
            raise ValueError(
                "At least one symbol is required."
            )

        if not resolution:
            raise ValueError(
                "Resolution is required."
            )

        unique_symbols = sorted(
            {
                normalize_market_symbol(symbol)
                for symbol in symbols
                if symbol.strip()
            }
        )

        if not unique_symbols:
            raise ValueError(
                "No valid symbols were provided."
            )

        if len(unique_symbols) > MAX_CHANNELS:
            raise ValueError(
                f"Maximum supported channels "
                f"per connection is {MAX_CHANNELS}."
            )

        self.symbols = unique_symbols
        self.resolution = str(resolution)

        self.candle_store = (
            candle_store
            if candle_store is not None
            else CandleStore()
        )

        self.ws = None

        self.received_count = 0
        self.saved_count = 0

    def on_open(
        self,
        ws,
    ) -> None:
        ws.send(
            json.dumps(
                {
                    "connect": {},
                    "id": 1,
                }
            )
        )

        command_id = 2

        for market_symbol in self.symbols:
            channel = (
                "public:candle-"
                f"{market_symbol}-"
                f"{self.resolution}"
            )

            ws.send(
                json.dumps(
                    {
                        "id": command_id,
                        "subscribe": {
                            "channel": channel,
                        },
                    }
                )
            )

            command_id += 1

        print(
            f"Subscribed to "
            f"{len(self.symbols)} candle channels."
        )

    def on_message(
        self,
        ws,
        message: str,
    ) -> None:
        if message == "{}":
            try:
                ws.send("{}")
            except Exception:
                pass

            return

        candle_data = (
            decode_public_candle(message)
        )

        if candle_data is None:
            return

        self.received_count += 1

        symbol = candle_data["symbol"]
        resolution = candle_data["resolution"]
        candle = candle_data["candle"]

        try:
            self.candle_store.save(
                symbol=symbol,
                candle=candle,
                timeframe=resolution,
            )

            self.saved_count += 1

        except Exception as exc:
            print(
                f"CandleStore error for "
                f"{symbol}: {exc}"
            )

            return

        print(
            f"{symbol:<12} "
            f"TF={resolution:<4} "
            f"TS={candle.timestamp} "
            f"O={candle.open:.8f} "
            f"H={candle.high:.8f} "
            f"L={candle.low:.8f} "
            f"C={candle.close:.8f} "
            f"V={candle.volume:.8f}"
        )

    def on_error(
        self,
        ws,
        error,
    ) -> None:
        print(
            f"WebSocket error: {error}"
        )

    def on_close(
        self,
        ws,
        close_status_code,
        close_message,
    ) -> None:
        print(
            "WebSocket closed:",
            close_status_code,
            close_message,
        )

        print(
            f"Received candles: "
            f"{self.received_count}"
        )

        print(
            f"Saved candles: "
            f"{self.saved_count}"
        )

    def run(self) -> None:
        print(
            "Starting Nobitex public candle capture..."
        )

        self.ws = websocket.WebSocketApp(
            WS_URL,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
        )

        self.ws.run_forever(
            ping_interval=20,
            ping_timeout=10,
        )


def main() -> None:
    symbols = [
        "BTC",
        "ETH",
        "USDT",
        "BICO",
        "2Z",
    ]

    capture = PublicCandleCapture(
        symbols=symbols,
        resolution="60",
    )

    capture.run()


if __name__ == "__main__":
    main()