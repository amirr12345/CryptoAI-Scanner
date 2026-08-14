from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import websocket

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.market_registry import MarketRegistry
from core.trade_store import TradeStore
from models.trade import Trade
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
            "Market symbol cannot be empty."
        )

    if not value.endswith("USDT"):
        raise ValueError(
            f"Trade capture requires BASEUSDT "
            f"market symbols: {symbol}"
        )

    return value


def project_symbol(
    market_symbol: str,
) -> str:
    value = market_symbol.strip().upper()

    if value.endswith("USDT"):
        base = value[:-4]

        if base:
            return base

    return value


def extract_usdt_market_symbols(
    markets: dict,
) -> list[str]:
    """
    Extract BASE/USDT markets.

    Example:
        btc-usdt -> BTCUSDT
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


def _normalize_side(
    value,
) -> str | None:
    """
    Normalize common side encodings.

    Supported:
        buy
        sell
        b
        s
        1 / 0
        true / false
    """

    if value is None:
        return None

    if isinstance(value, bool):
        return "buy" if value else "sell"

    text = str(value).strip().lower()

    if text in {
        "buy",
        "b",
        "bid",
        "1",
        "true",
    }:
        return "buy"

    if text in {
        "sell",
        "s",
        "ask",
        "0",
        "false",
    }:
        return "sell"

    return None


def _first_value(
    data: dict,
    keys: tuple[str, ...],
):
    for key in keys:
        if key in data:
            return data[key]

    return None


def _parse_trade_item(
    item,
    symbol: str,
) -> Trade | None:
    """
    Parse one trade object.

    The parser intentionally accepts several common
    payload key names because provider payloads can expose
    equivalent fields under abbreviated or descriptive keys.
    """

    if not isinstance(item, dict):
        return None

    timestamp = _first_value(
        item,
        (
            "t",
            "timestamp",
            "time",
            "ts",
        ),
    )

    price = _first_value(
        item,
        (
            "p",
            "price",
            "rate",
        ),
    )

    volume = _first_value(
        item,
        (
            "a",
            "amount",
            "volume",
            "v",
            "qty",
            "quantity",
        ),
    )

    side_value = _first_value(
        item,
        (
            "s",
            "side",
            "type",
            "direction",
        ),
    )

    side = _normalize_side(
        side_value
    )

    if (
        timestamp is None
        or price is None
        or volume is None
        or side is None
    ):
        return None

    try:
        timestamp_int = int(
            float(timestamp)
        )

        price_float = float(price)
        volume_float = float(volume)

        return Trade(
            timestamp=timestamp_int,
            price=price_float,
            volume=volume_float,
            side=side,
            symbol=symbol,
        )

    except (
        TypeError,
        ValueError,
    ):
        return None


def _extract_trade_container(
    data,
):
    """
    Normalize possible trade payload containers.

    Supported shapes:

        [...]
        {"trades": [...]}
        {"data": [...]}
        {"data": {"trades": [...]}}
        {"result": [...]}
    """

    if isinstance(data, list):
        return data

    if not isinstance(data, dict):
        return None

    for key in (
        "trades",
        "data",
        "result",
        "items",
    ):
        value = data.get(key)

        if isinstance(value, list):
            return value

        if isinstance(value, dict):
            nested = _extract_trade_container(
                value
            )

            if nested is not None:
                return nested

    # Some providers send one trade as one object.
    if any(
        key in data
        for key in (
            "t",
            "timestamp",
            "p",
            "price",
        )
    ):
        return [data]

    return None


def decode_public_trades(
    message: str,
) -> list[Trade]:
    """
    Decode one Nobitex public trades message.

    Returns a list because a WebSocket event may contain
    one or multiple trades.
    """

    if not message:
        return []

    if message == "{}":
        return []

    try:
        payload = json.loads(message)
    except json.JSONDecodeError:
        return []

    push = payload.get("push")

    if not isinstance(push, dict):
        return []

    channel = str(
        push.get(
            "channel",
            "",
        )
    )

    if not channel.startswith(
        "public:trades-"
    ):
        return []

    parts = channel.split("-")

    if len(parts) < 2:
        return []

    market_symbol = parts[1].strip().upper()

    try:
        market_symbol = normalize_market_symbol(
            market_symbol
        )
    except ValueError:
        return []

    publication = push.get(
        "pub",
        {},
    )

    if not isinstance(
        publication,
        dict,
    ):
        return []

    raw_data = publication.get(
        "data"
    )

    container = _extract_trade_container(
        raw_data
    )

    if container is None:
        container = _extract_trade_container(
            publication
        )

    if container is None:
        return []

    trades: list[Trade] = []

    for item in container:
        trade = _parse_trade_item(
            item=item,
            symbol=market_symbol,
        )

        if trade is not None:
            trades.append(trade)

    return trades


class PublicTradeCapture:
    """
    Continuous BASE/USDT public trade capture.

    Analysis market:
        BTCUSDT
        ETHUSDT
        ...

    IRT markets are intentionally excluded.

    TradeStore receives the actual BASEUSDT symbol so
    HistoricalContext can later query trades using the
    same analytical market identity.
    """

    def __init__(
        self,
        symbols: list[str],
        trade_store: TradeStore | None = None,
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

        unique_symbols = sorted(
            {
                normalize_market_symbol(
                    symbol
                )
                for symbol in symbols
                if symbol.strip()
            }
        )

        if not unique_symbols:
            raise ValueError(
                "No valid USDT symbols were provided."
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

        self.trade_store = (
            trade_store
            if trade_store is not None
            else TradeStore()
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

        self.received_message_count = 0
        self.received_trade_count = 0
        self.saved_trade_count = 0
        self.duplicate_trade_count = 0
        self.error_count = 0

        self.connection_count = 0
        self.reconnect_count = 0

        self.last_message_at: float | None = None
        self.last_trade_timestamp: int | None = None

    def on_open(
        self,
        ws,
    ) -> None:
        self.connection_count += 1

        print(
            f"[WS OPEN] connection="
            f"{self.connection_count}"
        )

        self._send_connect(
            ws
        )

        self._subscribe_all(
            ws
        )

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
                "public:trades-"
                f"{market_symbol}"
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

        self.received_message_count += 1

        trades = decode_public_trades(
            message
        )

        if not trades:
            return

        self.received_trade_count += (
            len(trades)
        )

        try:
            inserted = (
                self.trade_store.save_trades(
                    trades
                )
            )

            self.saved_trade_count += (
                inserted
            )

            self.duplicate_trade_count += (
                len(trades) - inserted
            )

            self.last_trade_timestamp = max(
                trade.timestamp
                for trade in trades
            )

        except Exception as exc:
            self.error_count += 1

            print(
                f"[STORE ERROR] {exc}"
            )

            return

        # Print a compact heartbeat rather than every trade.
        print(
            f"[TRADES] "
            f"received={len(trades)} "
            f"saved={inserted} "
            f"duplicates="
            f"{len(trades) - inserted} "
            f"latest="
            f"{self.last_trade_timestamp}"
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
            "[START] Nobitex USDT trade capture"
        )

        print(
            f"[MARKETS] {len(self.symbols)}"
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

        print(
            "[STOPPED]"
        )

        print(
            f"connections="
            f"{self.connection_count}"
        )

        print(
            f"reconnects="
            f"{self.reconnect_count}"
        )

        print(
            f"messages="
            f"{self.received_message_count}"
        )

        print(
            f"trades_received="
            f"{self.received_trade_count}"
        )

        print(
            f"trades_saved="
            f"{self.saved_trade_count}"
        )

        print(
            f"duplicates="
            f"{self.duplicate_trade_count}"
        )

        print(
            f"errors="
            f"{self.error_count}"
        )


def build_capture_from_nobitex(
    trade_store: TradeStore | None = None,
    market_registry: MarketRegistry | None = None,
) -> PublicTradeCapture:
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

    registry = (
        market_registry
        if market_registry is not None
        else MarketRegistry()
    )

    for symbol in symbols:
        registry.register_symbol(
            symbol
        )

    print(
        f"[USDT MARKETS DISCOVERED] "
        f"{len(symbols)}"
    )

    return PublicTradeCapture(
        symbols=symbols,
        trade_store=trade_store,
        market_registry=registry,
    )


def main() -> None:
    capture = (
        build_capture_from_nobitex()
    )

    capture.run_forever()


if __name__ == "__main__":
    main()