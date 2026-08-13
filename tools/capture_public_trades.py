from __future__ import annotations

import json
import sys
from pathlib import Path

import websocket

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from models.trade import Trade
from services.historical_trade_service import (
    HistoricalTradeService,
)


WS_URL = (
    "wss://ws.nobitex.ir/"
    "connection/websocket"
)

MAX_CHANNELS = 300


def normalize_symbol(
    market_symbol: str,
) -> str:
    value = market_symbol.strip().upper()

    if value.endswith("IRT"):
        return value[:-3]

    return value


def extract_public_trade(
    message: str,
):
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
        "public:trades-"
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

    market_symbol = channel.split(
        "public:trades-",
        1,
    )[-1]

    symbol = normalize_symbol(
        market_symbol
    )

    try:
        timestamp = int(
            data["time"]
        )

        price = float(
            data["price"]
        )

        volume = float(
            data["volume"]
        )

        side = str(
            data["type"]
        ).strip().lower()

    except (
        KeyError,
        TypeError,
        ValueError,
    ):
        return None

    if side not in {
        "buy",
        "sell",
    }:
        return None

    return Trade(
        timestamp=timestamp,
        price=price,
        volume=volume,
        side=side,
        symbol=symbol,
    )


class PublicTradeCapture:
    """
    Capture all public trades for the configured symbols.

    Nobitex currently documents a maximum of 300
    public channels per WebSocket connection.
    """

    def __init__(
        self,
        symbols: list[str],
    ) -> None:

        if not symbols:
            raise ValueError(
                "At least one symbol is required."
            )

        unique_symbols = sorted(
            {
                symbol.strip().upper()
                for symbol in symbols
                if symbol.strip()
            }
        )

        if (
            len(unique_symbols)
            > MAX_CHANNELS
        ):
            raise ValueError(
                f"Maximum supported channels "
                f"per connection is {MAX_CHANNELS}."
            )

        self.symbols = unique_symbols

        self.service = (
            HistoricalTradeService()
        )

        self.ws = None

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

        for symbol in self.symbols:
            channel = (
                "public:trades-"
                f"{symbol}IRT"
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
            f"{len(self.symbols)} trade channels."
        )

    def on_message(
        self,
        ws,
        message: str,
    ) -> None:

        # Handle the application-level empty
        # ping/pong mechanism documented by Nobitex.
        if message == "{}":
            ws.send("{}")
            return

        trade = extract_public_trade(
            message
        )

        if trade is None:
            return

        try:
            inserted = self.service.save(
                [trade]
            )

        except Exception as exc:
            print(
                f"Storage error for "
                f"{trade.symbol}: {exc}"
            )
            return

        self.saved_count += inserted

        if inserted:
            print(
                f"{trade.symbol:<10} "
                f"{trade.side:<4} "
                f"price={trade.price:.8f} "
                f"volume={trade.volume:.8f} "
                f"ts={trade.timestamp}"
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
            f"Saved trades: "
            f"{self.saved_count}"
        )

    def run(self) -> None:

        print(
            "Starting Nobitex public trade capture..."
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


def get_symbols() -> list[str]:
    """
    Read symbols directly from market stats.
    """

    from services.market_service import (
        MarketService,
    )

    service = MarketService()

    data = service.markets()

    stats = data.get(
        "stats",
        {},
    )

    symbols = sorted(
        {
            key[:-4].upper()
            for key in stats
            if key.endswith("-rls")
        }
    )

    return symbols


def main() -> None:

    symbols = get_symbols()

    print(
        f"Markets found: {len(symbols)}"
    )

    capture = PublicTradeCapture(
        symbols=symbols
    )

    capture.run()


if __name__ == "__main__":
    main()