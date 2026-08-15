from __future__ import annotations

import time

import requests

from api.base import MarketDataProvider
from models.candle import Candle
from models.order_book import OrderBook
from models.order_book_level import OrderBookLevel
from models.ticker import Ticker
from models.trade import Trade


class GateIOExchange(MarketDataProvider):
    """
    Gate.io public Spot market-data provider.

    Analysis universe:
        BASE/USDT only.

    Project symbol:
        BTCUSDT

    Gate.io symbol:
        BTC_USDT

    Timestamp conventions:
        Candle -> seconds
        Trade  -> milliseconds
    """

    BASE_URL = "https://api.gateio.ws"
    API_PREFIX = "/api/v4"

    MAX_CANDLE_LIMIT = 1000
    MAX_TRADE_LIMIT = 1000
    MAX_ORDERBOOK_DEPTH = 1000

    TIMEOUT = 15

    @staticmethod
    def normalize_symbol(
        symbol: str,
    ) -> str:
        """
        Normalize project symbol.

        Examples:
            btc-usdt -> BTCUSDT
            BTC_USDT -> BTCUSDT
            BTCUSDT  -> BTCUSDT
        """

        if not symbol:
            raise ValueError(
                "Symbol cannot be empty."
            )

        value = (
            str(symbol)
            .strip()
            .upper()
            .replace("-", "")
            .replace("_", "")
        )

        if not value:
            raise ValueError(
                "Symbol cannot be empty."
            )

        if not value.endswith(
            "USDT"
        ):
            raise ValueError(
                "Gate.io analysis requires BASEUSDT symbols."
            )

        base = value[:-4]

        if not base:
            raise ValueError(
                "Invalid BASEUSDT symbol."
            )

        return value

    @staticmethod
    def _gate_symbol(
        symbol: str,
    ) -> str:
        """
        Convert project symbol to Gate.io pair.

        BTCUSDT -> BTC_USDT
        ETHUSDT -> ETH_USDT
        """

        normalized = (
            GateIOExchange.normalize_symbol(
                symbol
            )
        )

        return (
            normalized[:-4]
            + "_USDT"
        )

    @staticmethod
    def _base_symbol(
        symbol: str,
    ) -> str:
        """
        Extract BASE asset.

        BTCUSDT -> BTC
        ETHUSDT -> ETH
        """

        normalized = (
            GateIOExchange.normalize_symbol(
                symbol
            )
        )

        return normalized[:-4]

    def _get(
        self,
        path: str,
        params: dict | None = None,
    ):
        """
        Execute a public GET request.
        """

        response = requests.get(
            self.BASE_URL
            + self.API_PREFIX
            + path,
            params=params or {},
            timeout=self.TIMEOUT,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )

        response.raise_for_status()

        return response.json()

    @staticmethod
    def _interval(
        resolution: str,
    ) -> str:
        """
        Convert project timeframe to Gate.io interval.
        """

        value = (
            str(resolution)
            .strip()
        )

        mapping = {
            "1": "1m",
            "3": "5m",
            "5": "5m",
            "15": "15m",
            "30": "30m",
            "60": "1h",
            "240": "4h",
            "D": "1d",
            "1D": "1d",
            "W": "7d",
            "1W": "7d",
        }

        if value not in mapping:
            raise ValueError(
                f"Unsupported Gate.io resolution: "
                f"{resolution}"
            )

        return mapping[value]

    def get_ticker(
        self,
        symbol: str,
    ) -> Ticker:
        """
        Return current Spot ticker.
        """

        normalized = (
            self.normalize_symbol(
                symbol
            )
        )

        pair = (
            self._gate_symbol(
                normalized
            )
        )

        data = self._get(
            "/spot/tickers",
            {
                "currency_pair": pair,
            },
        )

        if not data:
            raise ValueError(
                f"Gate.io ticker not found: {pair}"
            )

        item = data[0]

        return Ticker(
            symbol=normalized,
            last_price=float(
                item["last"]
            ),
            high=float(
                item["high_24h"]
            ),
            low=float(
                item["low_24h"]
            ),
            volume=float(
                item["base_volume"]
            ),
        )

    def get_markets(
        self,
    ) -> dict:
        """
        Return active USDT Spot markets.

        Tickers are used as the market-discovery source so
        this remains compatible with the existing service layer.
        """

        data = self._get(
            "/spot/tickers"
        )

        stats: dict = {}

        for item in data:
            pair = (
                str(
                    item.get(
                        "currency_pair",
                        "",
                    )
                )
                .strip()
                .upper()
            )

            if not pair.endswith(
                "_USDT"
            ):
                continue

            base = pair[:-5]

            if not base:
                continue

            stats[
                f"{base.lower()}-usdt"
            ] = item

        return {
            "stats": stats
        }

    def get_history(
        self,
        symbol: str,
        resolution: str = "60",
        countback: int = 200,
        start_timestamp: int | None = None,
        end_timestamp: int | None = None,
    ) -> list[Candle]:
        """
        Return Spot OHLCV candles.

        Without explicit timestamps:
            limit is used directly.

        With explicit timestamps:
            Gate.io's time-range mode is used.

        Candle timestamp:
            seconds.
        """

        normalized = (
            self.normalize_symbol(
                symbol
            )
        )

        if countback <= 0:
            raise ValueError(
                "Countback must be greater than zero."
            )

        if countback > self.MAX_CANDLE_LIMIT:
            raise ValueError(
                "Countback cannot exceed "
                f"{self.MAX_CANDLE_LIMIT}."
            )

        params = {
            "currency_pair": (
                self._gate_symbol(
                    normalized
                )
            ),
            "interval": (
                self._interval(
                    resolution
                )
            ),
        }

        if (
            start_timestamp is None
            and end_timestamp is None
        ):
            params["limit"] = int(
                countback
            )

        else:
            if (
                start_timestamp is None
                or end_timestamp is None
            ):
                raise ValueError(
                    "start_timestamp and "
                    "end_timestamp must be supplied together."
                )

            params["from"] = int(
                start_timestamp
            )

            params["to"] = int(
                end_timestamp
            )

        data = self._get(
            "/spot/candlesticks",
            params,
        )

        candles: list[Candle] = []

        for row in data:
            if len(row) < 7:
                continue

            candles.append(
                Candle(
                    timestamp=int(
                        row[0]
                    ),
                    open=float(
                        row[5]
                    ),
                    high=float(
                        row[3]
                    ),
                    low=float(
                        row[4]
                    ),
                    close=float(
                        row[2]
                    ),
                    volume=float(
                        row[6]
                    ),
                )
            )

        candles.sort(
            key=lambda item: int(
                item.timestamp
            )
        )

        if (
            start_timestamp is None
            and end_timestamp is None
        ):
            return candles[-countback:]

        return [
            candle
            for candle in candles
            if (
                int(candle.timestamp)
                >= int(start_timestamp)
                and int(candle.timestamp)
                <= int(end_timestamp)
            )
        ]

    def get_trades(
        self,
        symbol: str,
        limit: int = 100,
    ) -> list[Trade]:
        """
        Return recent Spot trades.

        Trade timestamps remain milliseconds.
        """

        normalized = (
            self.normalize_symbol(
                symbol
            )
        )

        if limit <= 0:
            raise ValueError(
                "Limit must be greater than zero."
            )

        if limit > self.MAX_TRADE_LIMIT:
            raise ValueError(
                "Trade limit cannot exceed "
                f"{self.MAX_TRADE_LIMIT}."
            )

        data = self._get(
            "/spot/trades",
            {
                "currency_pair": (
                    self._gate_symbol(
                        normalized
                    )
                ),
                "limit": int(
                    limit
                ),
            },
        )

        base = (
            self._base_symbol(
                normalized
            )
        )

        trades: list[Trade] = []

        for item in data:
            side = (
                str(
                    item.get(
                        "side",
                        "",
                    )
                )
                .strip()
                .lower()
            )

            if side not in {
                "buy",
                "sell",
            }:
                continue

            timestamp = (
                self._trade_timestamp_ms(
                    item
                )
            )

            trades.append(
                Trade(
                    timestamp=timestamp,
                    price=float(
                        item["price"]
                    ),
                    volume=float(
                        item["amount"]
                    ),
                    side=side,
                    symbol=base,
                )
            )

        trades.sort(
            key=lambda item: int(
                item.timestamp
            )
        )

        return trades

    def get_historical_trades(
        self,
        symbol: str,
        end_timestamp_ms: int | None = None,
        lookback_seconds: int = 3600,
        max_pages: int = 20,
    ) -> list[Trade]:
        """
        Retrieve historical Spot trades using Gate.io's
        last_id + reverse pagination.

        Algorithm:

            1. Fetch the newest page.
            2. Take the oldest trade ID from the page.
            3. Request the next page using:
                   last_id=<oldest_id>
                   reverse=true
            4. Continue until:
                   - historical boundary is reached
                   - page is empty
                   - cursor stops moving
                   - max_pages is reached

        All returned trades satisfy:

            timestamp <= end_timestamp_ms

        when an end timestamp is supplied.

        Trade timestamps:
            milliseconds.
        """

        normalized = (
            self.normalize_symbol(
                symbol
            )
        )

        if lookback_seconds <= 0:
            raise ValueError(
                "Lookback seconds must be greater than zero."
            )

        if max_pages <= 0:
            raise ValueError(
                "max_pages must be greater than zero."
            )

        if end_timestamp_ms is None:
            end_ms = int(
                time.time() * 1000
            )
        else:
            end_ms = int(
                end_timestamp_ms
            )

        start_ms = (
            end_ms
            - int(lookback_seconds) * 1000
        )

        start_sec = (
            start_ms // 1000
        )

        end_sec = (
            end_ms // 1000
        )

        base = (
            self._base_symbol(
                normalized
            )
        )

        collected: dict[
            str,
            Trade,
        ] = {}

        last_id: str | None = None

        for _ in range(
            max_pages
        ):
            params = {
                "currency_pair": (
                    self._gate_symbol(
                        normalized
                    )
                ),
                "limit": self.MAX_TRADE_LIMIT,
            }

            if last_id is not None:
                params["last_id"] = last_id
                params["reverse"] = "true"

            else:
                # Initial request uses the time upper boundary.
                params["to"] = end_sec

            data = self._get(
                "/spot/trades",
                params,
            )

            if not data:
                break

            oldest_id: str | None = None
            oldest_timestamp_ms: int | None = None

            for item in data:
                trade_id = str(
                    item.get(
                        "id",
                        item.get(
                            "sequence_id",
                            "",
                        ),
                    )
                )

                if not trade_id:
                    continue

                timestamp_ms = (
                    self._trade_timestamp_ms(
                        item
                    )
                )

                if (
                    timestamp_ms
                    > end_ms
                ):
                    continue

                if (
                    timestamp_ms
                    < start_ms
                ):
                    if (
                        oldest_timestamp_ms
                        is None
                        or timestamp_ms
                        < oldest_timestamp_ms
                    ):
                        oldest_timestamp_ms = (
                            timestamp_ms
                        )

                    oldest_id = (
                        trade_id
                    )
                    continue

                side = (
                    str(
                        item.get(
                            "side",
                            "",
                        )
                    )
                    .strip()
                    .lower()
                )

                if side not in {
                    "buy",
                    "sell",
                }:
                    continue

                trade = Trade(
                    timestamp=timestamp_ms,
                    price=float(
                        item["price"]
                    ),
                    volume=float(
                        item["amount"]
                    ),
                    side=side,
                    symbol=base,
                )

                collected[
                    trade_id
                ] = trade

                if (
                    oldest_timestamp_ms
                    is None
                    or timestamp_ms
                    < oldest_timestamp_ms
                ):
                    oldest_timestamp_ms = (
                        timestamp_ms
                    )

                oldest_id = trade_id

            if oldest_id is None:
                break

            if (
                oldest_timestamp_ms
                is not None
                and oldest_timestamp_ms
                <= start_ms
            ):
                break

            if (
                oldest_id
                == last_id
            ):
                break

            last_id = oldest_id

        trades = list(
            collected.values()
        )

        trades.sort(
            key=lambda item: int(
                item.timestamp
            )
        )

        return trades

    def get_orderbook(
        self,
        symbol: str,
        depth: int = 50,
    ) -> OrderBook:
        """
        Return current Spot order book.
        """

        normalized = (
            self.normalize_symbol(
                symbol
            )
        )

        if depth <= 0:
            raise ValueError(
                "Depth must be greater than zero."
            )

        if depth > self.MAX_ORDERBOOK_DEPTH:
            raise ValueError(
                "Orderbook depth cannot exceed "
                f"{self.MAX_ORDERBOOK_DEPTH}."
            )

        data = self._get(
            "/spot/order_book",
            {
                "currency_pair": (
                    self._gate_symbol(
                        normalized
                    )
                ),
                "limit": int(
                    depth
                ),
                "with_id": "true",
            },
        )

        bids = [
            OrderBookLevel(
                price=float(
                    level[0]
                ),
                volume=float(
                    level[1]
                ),
            )
            for level in data.get(
                "bids",
                [],
            )[:depth]
        ]

        asks = [
            OrderBookLevel(
                price=float(
                    level[0]
                ),
                volume=float(
                    level[1]
                ),
            )
            for level in data.get(
                "asks",
                [],
            )[:depth]
        ]

        timestamp = int(
            data.get(
                "current",
                data.get(
                    "update",
                    int(
                        time.time() * 1000
                    ),
                ),
            )
        )

        return OrderBook(
            symbol=self._base_symbol(
                normalized
            ),
            timestamp=timestamp,
            bids=bids,
            asks=asks,
        )

    @staticmethod
    def _trade_timestamp_ms(
        trade: dict,
    ) -> int:
        """
        Extract trade timestamp in milliseconds.

        Gate.io may provide create_time_ms with
        fractional precision. The project stores integer
        milliseconds.
        """

        value = trade.get(
            "create_time_ms"
        )

        if value is not None:
            return int(
                float(value)
            )

        create_time = trade.get(
            "create_time"
        )

        if create_time is None:
            raise ValueError(
                "Trade timestamp is missing."
            )

        return (
            int(float(create_time))
            * 1000
        )