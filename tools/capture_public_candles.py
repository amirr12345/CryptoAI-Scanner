from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import websocket

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.candle_store import CandleStore
from core.market_registry import MarketRegistry
from models.candle import Candle
from services.market_service import MarketService


WS_URL = (
    "wss://ws.nobitex.ir/"
    "connection/websocket"
)

MAX_CHANNELS = 300

INITIAL_RECONNECT_DELAY = 2
MAX_RECONNECT_DELAY = 60

PING_INTERVAL = 20
PING_TIMEOUT = 10


def normalize_market_symbol(
    symbol: str,
) -> str:
    value = symbol.strip().upper()

    if not value:
        raise ValueError(
            "Symbol cannot be empty."
        )

    return value


def project_symbol(
    market_symbol: str,
) -> str:
    value = market_symbol.strip().upper()

    for quote in (
        "USDT",
        "USDC",
        "IRT",
    ):
        if value.endswith(quote):
            base = value[:-len(quote)]

            if base:
                return base

    return value


def extract_usdt_market_symbols(
    markets: dict,
) -> list[str]:
    """
    Extract BASE/USDT markets from Nobitex.

    Examples:

        btc-usdt  -> BTCUSDT
        eth-usdt  -> ETHUSDT
        sol-usdt  -> SOLUSDT

    USDT is the primary analysis quote.
    """

    stats = markets.get(
        "stats",
        {},
    )

    symbols: set[str] = set()

    for market_key in stats:
        key = (
            str(market_key)
            .strip()
            .upper()
        )

        if not key.endswith(
            "-USDT"
        ):
            continue

        base = key[:-5].strip()

        if not base:
            continue

        symbols.add(
            f"{base}USDT"
        )

    return sorted(symbols)


def decode_public_candle(
    message: str,
) -> dict | None:
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
        push.get(
            "channel",
            "",
        )
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

        market_symbol = (
            parts[1].strip().upper()
        )

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

    if not market_symbol.endswith(
        "USDT"
    ):
        return None

    return {
        "market_symbol": market_symbol,
        "symbol": project_symbol(
            market_symbol
        ),
        "resolution": resolution,
        "candle": candle,
    }


class PublicCandleCapture:
    """
    Continuous USDT candle capture.

    USDT is the primary analysis quote.

    IRT is intentionally not subscribed here because:
        247 USDT channels + 248 IRT channels > 300
        channels per connection.

    IRT remains the execution market and will be
    handled by a separate execution-data path.
    """

    def __init__(
        self,
        symbols: list[str],
        resolution: str = "60",
        candle_store: CandleStore | None = None,
        market_registry: MarketRegistry | None = None,
        reconnect_initial_delay: int = (
            INITIAL_RECONNECT_DELAY
        ),
        reconnect_max_delay: int = (
            MAX_RECONNECT_DELAY
        ),
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
                normalize_market_symbol(
                    symbol
                )
                for symbol in symbols
                if symbol.strip()
            }
        )

        for symbol in unique_symbols:
            if not symbol.endswith("USDT"):
                raise ValueError(
                    "All capture symbols must be "
                    "BASEUSDT markets."
                )

        if len(unique_symbols) > MAX_CHANNELS:
            raise ValueError(
                f"Maximum supported channels "
                f"per connection is "
                f"{MAX_CHANNELS}."
            )

        if reconnect_initial_delay <= 0:
            raise ValueError(
                "reconnect_initial_delay must "
                "be greater than zero."
            )

        if reconnect_max_delay <= 0:
            raise ValueError(
                "reconnect_max_delay must "
                "be greater than zero."
            )

        if (
            reconnect_initial_delay
            > reconnect_max_delay
        ):
            raise ValueError(
                "reconnect_initial_delay cannot "
                "exceed reconnect_max_delay."
            )

        self.symbols = unique_symbols

        self.resolution = str(
            resolution
        )

        self.candle_store = (
            candle_store
            if candle_store is not None
            else CandleStore()
        )

        self.market_registry = (
            market_registry
            if market_registry is not None
            else MarketRegistry()
        )

        self.market_descriptors = [
            self.market_registry.register_symbol(
                symbol
            )
            for symbol in self.symbols
        ]

        self.reconnect_initial_delay = int(
            reconnect_initial_delay
        )

        self.reconnect_max_delay = int(
            reconnect_max_delay
        )

        self.ws: websocket.WebSocketApp | None = None

        self.running = True

        self.received_count = 0
        self.saved_count = 0
        self.error_count = 0

        self.connection_count = 0
        self.reconnect_count = 0

        self.last_message_at: float | None = None
        self.last_candle_timestamp: int | None = None

    def on_open(
        self,
        ws,
    ) -> None:
        self.connection_count += 1

        print(
            f"[WS OPEN] connection="
            f"{self.connection_count}"
        )

        self._send_connect(ws)
        self._subscribe_all(ws)

        print(
            f"[WS READY] subscribed="
            f"{len(self.symbols)}"
        )

    @staticmethod
    def _send_connect(
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

    def _subscribe_all(
        self,
        ws,
    ) -> None:
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

    def on_message(
        self,
        ws,
        message: str,
    ) -> None:
        self.last_message_at = time.time()

        if message == "{}":
            try:
                ws.send("{}")
            except Exception as exc:
                self.error_count += 1

                print(
                    f"[PONG ERROR] {exc}"
                )

            return

        candle_data = decode_public_candle(
            message
        )

        if candle_data is None:
            return

        self.received_count += 1

        market_symbol = (
            candle_data["market_symbol"]
        )

        resolution = (
            candle_data["resolution"]
        )

        candle = candle_data["candle"]

        try:
            descriptor = (
                self.market_registry.require(
                    market_symbol
                )
            )

        except Exception as exc:
            self.error_count += 1

            print(
                f"[REGISTRY ERROR] "
                f"{market_symbol}: {exc}"
            )

            return

        try:
            self.candle_store.save(
                symbol=market_symbol,
                candle=candle,
                timeframe=resolution,
            )

            self.saved_count += 1

            self.last_candle_timestamp = (
                int(candle.timestamp)
            )

        except Exception as exc:
            self.error_count += 1

            print(
                f"[STORE ERROR] "
                f"{market_symbol}: {exc}"
            )

            return

        print(
            f"{market_symbol:<14} "
            f"BASE={descriptor.base_asset:<8} "
            f"QUOTE={descriptor.quote_asset:<5} "
            f"ANALYSIS={descriptor.analysis_market:<12} "
            f"EXECUTION={descriptor.execution_market:<12} "
            f"TF={resolution:<4} "
            f"TS={candle.timestamp} "
            f"C={candle.close:.8f} "
            f"V={candle.volume:.8f}"
        )

    def on_error(
        self,
        ws,
        error,
    ) -> None:
        self.error_count += 1

        print(
            f"[WS ERROR] {error}"
        )

    def on_close(
        self,
        ws,
        close_status_code,
        close_message,
    ) -> None:
        print(
            f"[WS CLOSED] code="
            f"{close_status_code} "
            f"message="
            f"{close_message}"
        )

    def _create_websocket(
        self,
    ) -> websocket.WebSocketApp:
        return websocket.WebSocketApp(
            WS_URL,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
        )

    def _run_once(
        self,
    ) -> None:
        self.ws = (
            self._create_websocket()
        )

        self.ws.run_forever(
            ping_interval=PING_INTERVAL,
            ping_timeout=PING_TIMEOUT,
        )

    def stop(
        self,
    ) -> None:
        self.running = False

        if self.ws is not None:
            try:
                self.ws.close()
            except Exception:
                pass

    def run_forever(
        self,
    ) -> None:
        reconnect_delay = (
            self.reconnect_initial_delay
        )

        print(
            "[START] Nobitex USDT candle capture"
        )

        print(
            f"[MARKETS] {len(self.symbols)}"
        )

        print(
            f"[TIMEFRAME] {self.resolution}"
        )

        print(
            f"[RECONNECT] initial="
            f"{self.reconnect_initial_delay}s "
            f"max="
            f"{self.reconnect_max_delay}s"
        )

        while self.running:
            try:
                self._run_once()

                reconnect_delay = (
                    self.reconnect_initial_delay
                )

            except KeyboardInterrupt:
                print(
                    "[STOP] KeyboardInterrupt"
                )

                self.stop()
                break

            except Exception as exc:
                self.error_count += 1

                print(
                    f"[RUN ERROR] {exc}"
                )

            if not self.running:
                break

            self.reconnect_count += 1

            print(
                f"[RECONNECT] attempt="
                f"{self.reconnect_count} "
                f"delay="
                f"{reconnect_delay}s"
            )

            try:
                time.sleep(
                    reconnect_delay
                )
            except KeyboardInterrupt:
                self.stop()
                break

            reconnect_delay = min(
                reconnect_delay * 2,
                self.reconnect_max_delay,
            )

        print("[STOPPED]")

        print(
            f"connections="
            f"{self.connection_count}"
        )

        print(
            f"reconnects="
            f"{self.reconnect_count}"
        )

        print(
            f"received="
            f"{self.received_count}"
        )

        print(
            f"saved="
            f"{self.saved_count}"
        )

        print(
            f"errors="
            f"{self.error_count}"
        )


def build_capture_from_nobitex(
    resolution: str = "60",
    candle_store: CandleStore | None = None,
    market_registry: MarketRegistry | None = None,
) -> PublicCandleCapture:
    market_service = MarketService()

    markets = market_service.markets()

    symbols = extract_usdt_market_symbols(
        markets
    )

    if not symbols:
        raise RuntimeError(
            "No USDT Nobitex markets were returned."
        )

    if len(symbols) > MAX_CHANNELS:
        raise RuntimeError(
            f"Nobitex returned "
            f"{len(symbols)} USDT markets, "
            f"but one WebSocket connection "
            f"supports at most "
            f"{MAX_CHANNELS} channels."
        )

    print(
        f"[USDT MARKETS DISCOVERED] "
        f"{len(symbols)}"
    )

    registry = (
        market_registry
        if market_registry is not None
        else MarketRegistry()
    )

    for symbol in symbols:
        descriptor = (
            registry.register_symbol(
                symbol
            )
        )

        print(
            f"[MARKET] "
            f"{descriptor.market_symbol} "
            f"BASE={descriptor.base_asset} "
            f"QUOTE={descriptor.quote_asset} "
            f"ANALYSIS={descriptor.analysis_market} "
            f"EXECUTION={descriptor.execution_market}"
        )

    return PublicCandleCapture(
        symbols=symbols,
        resolution=resolution,
        candle_store=candle_store,
        market_registry=registry,
    )


def main() -> None:
    capture = (
        build_capture_from_nobitex(
            resolution="60"
        )
    )

    capture.run_forever()


if __name__ == "__main__":
    main()