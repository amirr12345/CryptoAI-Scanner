from __future__ import annotations

import requests

from api.base import MarketDataProvider
from models.candle import Candle
from models.order_book import OrderBook
from models.order_book_level import OrderBookLevel
from models.ticker import Ticker
from models.trade import Trade


class OKXExchange(MarketDataProvider):
    """
    OKX public market-data provider.

    Analysis universe:
        Spot BASE-USDT markets.

    Project symbol:
        BTCUSDT

    OKX symbol:
        BTC-USDT
    """

    BASE_URL = "https://www.okx.com"

    INST_TYPE = "SPOT"

    MAX_CANDLE_LIMIT = 100
    MAX_TRADE_LIMIT = 100
    MAX_ORDERBOOK_DEPTH = 400

    TIMEOUT = 15

    @staticmethod
    def normalize_symbol(
        symbol: str,
    ) -> str:
        """
        Normalize project symbol.

        Examples:
            btc-usdt -> BTCUSDT
            BTCUSDT  -> BTCUSDT
        """

        if not symbol:
            raise ValueError(
                "Symbol cannot be empty."
            )

        value = (
            symbol.strip()
            .upper()
            .replace("-", "")
        )

        if not value:
            raise ValueError(
                "Symbol cannot be empty."
            )

        if not value.endswith("USDT"):
            raise ValueError(
                "OKX analysis requires BASEUSDT symbols."
            )

        base = value[:-4]

        if not base:
            raise ValueError(
                "Invalid BASEUSDT symbol."
            )

        return value

    @staticmethod
    def _okx_symbol(
        symbol: str,
    ) -> str:
        """
        Convert project symbol to OKX symbol.

        BTCUSDT -> BTC-USDT
        """

        normalized = (
            OKXExchange.normalize_symbol(
                symbol
            )
        )

        return (
            normalized[:-4]
            + "-USDT"
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
            OKXExchange.normalize_symbol(
                symbol
            )
        )

        return normalized[:-4]

    def _get(
        self,
        path: str,
        params: dict,
    ) -> dict:
        """
        Execute a public GET request against OKX.
        """

        response = requests.get(
            self.BASE_URL + path,
            params=params,
            timeout=self.TIMEOUT,
        )

        response.raise_for_status()

        data = response.json()

        if data.get("code") != "0":
            raise ValueError(
                "OKX request failed: "
                f"{data}"
            )

        return data

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

        okx_symbol = (
            self._okx_symbol(
                normalized
            )
        )

        data = self._get(
            "/api/v5/market/ticker",
            {
                "instId": okx_symbol,
            },
        )

        rows = data.get(
            "data",
            [],
        )

        if not rows:
            raise ValueError(
                f"OKX ticker not found: "
                f"{okx_symbol}"
            )

        item = rows[0]

        return Ticker(
            symbol=normalized,
            last_price=float(
                item["last"]
            ),
            high=float(
                item["high24h"]
            ),
            low=float(
                item["low24h"]
            ),
            volume=float(
                item["vol24h"]
            ),
        )

    def get_markets(
        self,
    ) -> dict:
        """
        Return active Spot USDT instruments.

        Output is kept compatible with the current
        MarketService market-discovery structure.
        """

        data = self._get(
            "/api/v5/public/instruments",
            {
                "instType": self.INST_TYPE,
            },
        )

        stats: dict = {}

        for item in data.get(
            "data",
            [],
        ):
            inst_id = (
                str(
                    item.get(
                        "instId",
                        "",
                    )
                )
                .strip()
                .upper()
            )

            state = (
                str(
                    item.get(
                        "state",
                        "",
                    )
                )
                .strip()
                .lower()
            )

            quote_ccy = (
                str(
                    item.get(
                        "quoteCcy",
                        "",
                    )
                )
                .strip()
                .upper()
            )

            if not inst_id.endswith(
                "-USDT"
            ):
                continue

            if quote_ccy != "USDT":
                continue

            if state != "live":
                continue

            base = inst_id[:-5]

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
        countback: int = 100,
        start_timestamp_ms: int | None = None,
        end_timestamp_ms: int | None = None,
    ) -> list[Candle]:
        """
        Get historical Spot candles.

        Project resolution:
            1   -> 1m
            3   -> 3m
            5   -> 5m
            15  -> 15m
            30  -> 30m
            60  -> 1H
            120 -> 2H
            240 -> 4H

        Candle timestamps are returned in seconds.
        """

        if countback <= 0:
            raise ValueError(
                "Countback must be greater than zero."
            )

        if countback > self.MAX_CANDLE_LIMIT:
            raise ValueError(
                "Countback cannot exceed "
                f"{self.MAX_CANDLE_LIMIT} per request."
            )

        bar_map = {
            "1": "1m",
            "3": "3m",
            "5": "5m",
            "15": "15m",
            "30": "30m",
            "60": "1H",
            "120": "2H",
            "240": "4H",
        }

        resolution_value = (
            str(resolution)
            .strip()
        )

        if (
            resolution_value
            not in bar_map
        ):
            raise ValueError(
                f"Unsupported OKX resolution: "
                f"{resolution}"
            )

        params = {
            "instId": self._okx_symbol(
                symbol
            ),
            "bar": bar_map[
                resolution_value
            ],
            "limit": str(
                countback
            ),
        }

        if end_timestamp_ms is not None:
            params["after"] = str(
                int(end_timestamp_ms)
            )

        if start_timestamp_ms is not None:
            params["before"] = str(
                int(start_timestamp_ms)
            )

        data = self._get(
            "/api/v5/market/history-candles",
            params,
        )

        candles: list[Candle] = []

        for row in data.get(
            "data",
            [],
        ):
            if len(row) < 6:
                continue

            candles.append(
                Candle(
                    timestamp=int(
                        int(row[0]) // 1000
                    ),
                    open=float(
                        row[1]
                    ),
                    high=float(
                        row[2]
                    ),
                    low=float(
                        row[3]
                    ),
                    close=float(
                        row[4]
                    ),
                    volume=float(
                        row[5]
                    ),
                )
            )

        candles.sort(
            key=lambda item: int(
                item.timestamp
            )
        )

        return candles

    def get_trades(
        self,
        symbol: str,
        limit: int = 100,
    ) -> list[Trade]:
        """
        Get recent public Spot trades.

        Maximum:
            100 trades/request.
        """

        if limit <= 0:
            raise ValueError(
                "Limit must be greater than zero."
            )

        if limit > self.MAX_TRADE_LIMIT:
            raise ValueError(
                "Trade limit cannot exceed "
                f"{self.MAX_TRADE_LIMIT}."
            )

        normalized = (
            self.normalize_symbol(
                symbol
            )
        )

        data = self._get(
            "/api/v5/market/trades",
            {
                "instId": self._okx_symbol(
                    normalized
                ),
                "limit": str(
                    limit
                ),
            },
        )

        base = self._base_symbol(
            normalized
        )

        trades: list[Trade] = []

        for item in data.get(
            "data",
            [],
        ):
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

            trades.append(
                Trade(
                    timestamp=int(
                        item["ts"]
                    ),
                    price=float(
                        item["px"]
                    ),
                    volume=float(
                        item["sz"]
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
        Retrieve historical public trades using the OKX
        history-trades endpoint and pagination.

        Only trades inside:

            [end_timestamp - lookback,
             end_timestamp]

        are returned.

        Timestamp unit:
            milliseconds.

        Pagination ends only when:

            - API returns an empty page
            - historical boundary is reached
            - cursor does not move
            - max_pages is reached

        The number of records in a page is NOT used as the
        stopping condition.
        """

        if lookback_seconds <= 0:
            raise ValueError(
                "Lookback seconds must be greater than zero."
            )

        if max_pages <= 0:
            raise ValueError(
                "max_pages must be greater than zero."
            )

        normalized = (
            self.normalize_symbol(
                symbol
            )
        )

        end_ms = (
            int(end_timestamp_ms)
            if end_timestamp_ms is not None
            else None
        )

        if end_ms is not None:
            start_ms = (
                end_ms
                - int(lookback_seconds)
                * 1000
            )
        else:
            start_ms = None

        collected: dict[
            str,
            Trade,
        ] = {}

        after: str | None = None

        for _ in range(
            max_pages
        ):
            params = {
                "instId": self._okx_symbol(
                    normalized
                ),
                "limit": "100",
            }

            if after is not None:
                params["after"] = after

            data = self._get(
                "/api/v5/market/history-trades",
                params,
            )

            rows = data.get(
                "data",
                [],
            )

            if not rows:
                break

            oldest_trade_id: str | None = None
            oldest_timestamp: int | None = None

            for item in rows:
                timestamp = int(
                    item["ts"]
                )

                trade_id = str(
                    item["tradeId"]
                )

                oldest_trade_id = (
                    trade_id
                )

                if (
                    oldest_timestamp is None
                    or timestamp < oldest_timestamp
                ):
                    oldest_timestamp = (
                        timestamp
                    )

                # Never allow future trades.
                if (
                    end_ms is not None
                    and timestamp > end_ms
                ):
                    continue

                # Ignore trades older than requested
                # historical window.
                if (
                    start_ms is not None
                    and timestamp < start_ms
                ):
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

                collected[
                    trade_id
                ] = Trade(
                    timestamp=timestamp,
                    price=float(
                        item["px"]
                    ),
                    volume=float(
                        item["sz"]
                    ),
                    side=side,
                    symbol=self._base_symbol(
                        normalized
                    ),
                )

            if oldest_trade_id is None:
                break

            # Requested historical boundary reached.
            if (
                start_ms is not None
                and oldest_timestamp is not None
                and oldest_timestamp <= start_ms
            ):
                break

            next_after = (
                oldest_trade_id
            )

            # Cursor did not move.
            if next_after == after:
                break

            after = next_after

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
        Get current Spot order book.
        """

        if depth <= 0:
            raise ValueError(
                "Depth must be greater than zero."
            )

        if depth > self.MAX_ORDERBOOK_DEPTH:
            raise ValueError(
                "Orderbook depth cannot exceed "
                f"{self.MAX_ORDERBOOK_DEPTH}."
            )

        normalized = (
            self.normalize_symbol(
                symbol
            )
        )

        data = self._get(
            "/api/v5/market/books",
            {
                "instId": self._okx_symbol(
                    normalized
                ),
                "sz": str(
                    depth
                ),
            },
        )

        rows = data.get(
            "data",
            [],
        )

        if not rows:
            raise ValueError(
                f"OKX orderbook not found: "
                f"{normalized}"
            )

        book = rows[0]

        bids = [
            OrderBookLevel(
                price=float(
                    level[0]
                ),
                volume=float(
                    level[1]
                ),
            )
            for level in book.get(
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
            for level in book.get(
                "asks",
                [],
            )[:depth]
        ]

        return OrderBook(
            symbol=self._base_symbol(
                normalized
            ),
            timestamp=int(
                book.get(
                    "ts",
                    0,
                )
            ),
            bids=bids,
            asks=asks,
        )