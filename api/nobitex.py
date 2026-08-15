from __future__ import annotations

import time

import requests

from api.base import MarketDataProvider
from models.candle import Candle
from models.order_book import OrderBook
from models.order_book_level import OrderBookLevel
from models.ticker import Ticker
from models.trade import Trade


class NobitexExchange(MarketDataProvider):
    """
    Nobitex market data provider.

    Market symbol rules:

        BTC
            -> legacy/default market -> BTCIRT

        BTCIRT
            -> exact IRT market

        BTCUSDT
            -> exact USDT market

    Important distinction:

        API market symbol:
            BTCUSDT / BTCIRT

        Domain model base symbol:
            BTC

    This keeps backward compatibility while allowing
    USDT-qualified markets to be used directly.
    """

    BASE_URL = "https://apiv2.nobitex.ir"

    @staticmethod
    def _normalize_market_symbol(
        symbol: str,
        default_quote: str = "IRT",
    ) -> str:
        """
        Normalize a market symbol while preserving an
        explicitly supplied quote asset.

        Examples:

            BTC
                -> BTCIRT

            BTCIRT
                -> BTCIRT

            BTCUSDT
                -> BTCUSDT

            ETHUSDC
                -> ETHUSDC
        """

        if not symbol:
            raise ValueError(
                "Symbol cannot be empty."
            )

        value = (
            symbol.strip()
            .upper()
        )

        if not value:
            raise ValueError(
                "Symbol cannot be empty."
            )

        if value.endswith("USDT"):
            return value

        if value.endswith("USDC"):
            return value

        if value.endswith("IRT"):
            return value

        return (
            f"{value}"
            f"{default_quote}"
        )

    @staticmethod
    def _extract_base_symbol(
        market_symbol: str,
    ) -> str:
        """
        Extract the BASE asset from a qualified market.

        Examples:

            BTCUSDT
                -> BTC

            BTCIRT
                -> BTC

            ETHUSDC
                -> ETH

            USDTIRT
                -> USDT
        """

        value = (
            market_symbol
            .strip()
            .upper()
        )

        for quote in (
            "USDT",
            "USDC",
            "IRT",
        ):
            if value.endswith(quote):
                base = value[
                    : -len(quote)
                ]

                if base:
                    return base

        return value

    def get_ticker(
        self,
        symbol: str,
    ) -> Ticker:
        """
        Get current Nobitex IRT ticker.

        This remains backward-compatible with the
        historical ticker implementation.

        Example:

            BTC
                -> BTC-rls
        """

        if not symbol:
            raise ValueError(
                "Symbol cannot be empty."
            )

        source_symbol = (
            symbol.strip().lower()
        )

        response = requests.get(
            self.BASE_URL
            + "/market/stats",
            params={
                "srcCurrency": source_symbol,
                "dstCurrency": "rls",
            },
            timeout=10,
        )

        response.raise_for_status()

        data = response.json()

        if data.get("status") != "ok":
            raise ValueError(
                "Nobitex market stats failed: "
                f"{data}"
            )

        market_key = (
            f"{source_symbol}-rls"
        )

        try:
            market = (
                data["stats"]
                [market_key]
            )

        except KeyError as exc:
            raise ValueError(
                "Market not found in Nobitex response: "
                f"{market_key}"
            ) from exc

        return Ticker(
            symbol=source_symbol.upper(),
            last_price=float(
                market["latest"]
            ),
            high=float(
                market["dayHigh"]
            ),
            low=float(
                market["dayLow"]
            ),
            volume=float(
                market["volumeSrc"]
            ),
        )

    def get_markets(
        self,
    ) -> dict:
        """
        Get all Nobitex market statistics.
        """

        response = requests.get(
            self.BASE_URL
            + "/market/stats",
            timeout=10,
        )

        response.raise_for_status()

        data = response.json()

        if data.get("status") != "ok":
            raise ValueError(
                "Nobitex market stats failed: "
                f"{data}"
            )

        return data

    def get_history(
        self,
        symbol: str,
        resolution: str = "60",
        countback: int = 200,
    ) -> list[Candle]:
        """
        Get OHLCV historical candles from Nobitex UDF.

        Explicit market symbols are preserved.

        Examples:

            BTC
                -> request BTCIRT

            BTCIRT
                -> request BTCIRT

            BTCUSDT
                -> request BTCUSDT
        """

        if not symbol:
            raise ValueError(
                "Symbol cannot be empty."
            )

        if not resolution:
            raise ValueError(
                "Resolution cannot be empty."
            )

        if countback <= 0:
            raise ValueError(
                "Countback must be greater than zero."
            )

        if countback > 500:
            raise ValueError(
                "Countback cannot be greater than 500 "
                "per request."
            )

        normalized_symbol = (
            self._normalize_market_symbol(
                symbol
            )
        )

        to_timestamp = int(
            time.time()
        )

        params = {
            "symbol": normalized_symbol,
            "resolution": str(
                resolution
            ),
            "to": to_timestamp,
            "countback": int(
                countback
            ),
        }

        response = requests.get(
            self.BASE_URL
            + "/market/udf/history",
            params=params,
            timeout=10,
        )

        response.raise_for_status()

        data = response.json()

        if data.get("s") != "ok":
            raise ValueError(
                "Nobitex history request failed: "
                f"{data}"
            )

        timestamps = data.get(
            "t",
            [],
        )

        opens = data.get(
            "o",
            [],
        )

        highs = data.get(
            "h",
            [],
        )

        lows = data.get(
            "l",
            [],
        )

        closes = data.get(
            "c",
            [],
        )

        volumes = data.get(
            "v",
            [],
        )

        lengths = {
            len(timestamps),
            len(opens),
            len(highs),
            len(lows),
            len(closes),
            len(volumes),
        }

        if len(lengths) != 1:
            raise ValueError(
                "Invalid Nobitex OHLC response: "
                "array lengths are inconsistent."
            )

        return [
            Candle(
                timestamp=int(
                    timestamps[index]
                ),
                open=float(
                    opens[index]
                ),
                high=float(
                    highs[index]
                ),
                low=float(
                    lows[index]
                ),
                close=float(
                    closes[index]
                ),
                volume=float(
                    volumes[index]
                ),
            )
            for index in range(
                len(timestamps)
            )
        ]

    def get_trades(
        self,
        symbol: str,
        limit: int = 100,
    ) -> list[Trade]:
        """
        Get recent public executed trades from Nobitex.

        API request:

            BTC
                -> /v2/trades/BTCIRT

            BTCIRT
                -> /v2/trades/BTCIRT

            BTCUSDT
                -> /v2/trades/BTCUSDT

        Domain model:

            Trade.symbol
                -> BTC

        Keeping the model symbol as BASE preserves
        backward compatibility and avoids changing the
        existing Trade contract.
        """

        if not symbol:
            raise ValueError(
                "Symbol cannot be empty."
            )

        if limit <= 0:
            raise ValueError(
                "Limit must be greater than zero."
            )

        normalized_symbol = (
            self._normalize_market_symbol(
                symbol
            )
        )

        base_symbol = (
            self._extract_base_symbol(
                normalized_symbol
            )
        )

        response = requests.get(
            self.BASE_URL
            + f"/v2/trades/"
            f"{normalized_symbol}",
            timeout=10,
        )

        response.raise_for_status()

        data = response.json()

        if data.get("status") != "ok":
            raise ValueError(
                "Nobitex trades request failed: "
                f"{data}"
            )

        raw_trades = data.get(
            "trades",
            [],
        )

        trades: list[Trade] = []

        for item in raw_trades:
            trades.append(
                Trade(
                    timestamp=int(
                        item["time"]
                    ),
                    price=float(
                        item["price"]
                    ),
                    volume=float(
                        item["volume"]
                    ),
                    side=str(
                        item["type"]
                    )
                    .strip()
                    .lower(),
                    symbol=base_symbol,
                )
            )

            if len(trades) >= limit:
                break

        return trades

    def get_orderbook(
        self,
        symbol: str,
        depth: int = 20,
    ) -> OrderBook:
        """
        Get Level 2 order book from Nobitex.

        API request:

            BTC
                -> /v3/orderbook/BTCIRT

            BTCIRT
                -> /v3/orderbook/BTCIRT

            BTCUSDT
                -> /v3/orderbook/BTCUSDT

        Domain model:

            OrderBook.symbol
                -> BTC
        """

        if not symbol:
            raise ValueError(
                "Symbol cannot be empty."
            )

        if depth <= 0:
            raise ValueError(
                "Depth must be greater than zero."
            )

        normalized_symbol = (
            self._normalize_market_symbol(
                symbol
            )
        )

        base_symbol = (
            self._extract_base_symbol(
                normalized_symbol
            )
        )

        response = requests.get(
            self.BASE_URL
            + f"/v3/orderbook/"
            f"{normalized_symbol}",
            timeout=10,
        )

        response.raise_for_status()

        data = response.json()

        if data.get("status") != "ok":
            raise ValueError(
                "Nobitex orderbook request failed: "
                f"{data}"
            )

        raw_bids = data.get(
            "bids",
            [],
        )

        raw_asks = data.get(
            "asks",
            [],
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
            for level in raw_bids[:depth]
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
            for level in raw_asks[:depth]
        ]

        return OrderBook(
            symbol=base_symbol,
            timestamp=int(
                data.get(
                    "lastUpdate",
                    0,
                )
            ),
            bids=bids,
            asks=asks,
        )