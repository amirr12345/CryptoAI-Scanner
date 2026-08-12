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
    """

    BASE_URL = "https://apiv2.nobitex.ir"

    def get_ticker(self, symbol: str) -> Ticker:
        """
        Get current market ticker.
        """

        if not symbol:
            raise ValueError("Symbol cannot be empty.")

        symbol = symbol.strip().lower()

        response = requests.get(
            self.BASE_URL + "/market/stats",
            params={
                "srcCurrency": symbol,
                "dstCurrency": "rls",
            },
            timeout=10,
        )

        response.raise_for_status()

        data = response.json()

        if data.get("status") != "ok":
            raise ValueError(
                f"Nobitex market stats failed: {data}"
            )

        market_key = f"{symbol}-rls"

        try:
            market = data["stats"][market_key]
        except KeyError as exc:
            raise ValueError(
                f"Market not found in Nobitex response: "
                f"{market_key}"
            ) from exc

        return Ticker(
            symbol=symbol.upper(),
            last_price=float(market["latest"]),
            high=float(market["dayHigh"]),
            low=float(market["dayLow"]),
            volume=float(market["volumeSrc"]),
        )

    def get_markets(self) -> dict:
        """
        Get all Nobitex market statistics.
        """

        response = requests.get(
            self.BASE_URL + "/market/stats",
            timeout=10,
        )

        response.raise_for_status()

        data = response.json()

        if data.get("status") != "ok":
            raise ValueError(
                f"Nobitex market stats failed: {data}"
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
        """

        if not symbol:
            raise ValueError("Symbol cannot be empty.")

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

        normalized_symbol = symbol.strip().upper()

        if normalized_symbol.endswith("IRT"):
            udf_symbol = normalized_symbol
        else:
            udf_symbol = f"{normalized_symbol}IRT"

        to_timestamp = int(time.time())

        params = {
            "symbol": udf_symbol,
            "resolution": resolution,
            "to": to_timestamp,
            "countback": countback,
        }

        response = requests.get(
            self.BASE_URL + "/market/udf/history",
            params=params,
            timeout=10,
        )

        response.raise_for_status()

        data = response.json()

        if data.get("s") != "ok":
            raise ValueError(
                f"Nobitex history request failed: {data}"
            )

        timestamps = data.get("t", [])
        opens = data.get("o", [])
        highs = data.get("h", [])
        lows = data.get("l", [])
        closes = data.get("c", [])
        volumes = data.get("v", [])

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
                timestamp=int(timestamps[index]),
                open=float(opens[index]),
                high=float(highs[index]),
                low=float(lows[index]),
                close=float(closes[index]),
                volume=float(volumes[index]),
            )
            for index in range(len(timestamps))
        ]

    def get_trades(
        self,
        symbol: str,
        limit: int = 100,
    ) -> list[Trade]:
        """
        Get recent public executed trades from Nobitex.

        The provider normalizes the exchange response into the
        provider-agnostic Trade model.
        """

        if not symbol:
            raise ValueError("Symbol cannot be empty.")

        if limit <= 0:
            raise ValueError(
                "Limit must be greater than zero."
            )

        normalized_symbol = symbol.strip().upper()

        if normalized_symbol.endswith("IRT"):
            market_symbol = normalized_symbol
            source_symbol = normalized_symbol[:-3]
        else:
            market_symbol = f"{normalized_symbol}IRT"
            source_symbol = normalized_symbol

        response = requests.get(
            self.BASE_URL
            + f"/v2/trades/{market_symbol}",
            timeout=10,
        )

        response.raise_for_status()

        data = response.json()

        if data.get("status") != "ok":
            raise ValueError(
                f"Nobitex trades request failed: {data}"
            )

        raw_trades = data.get("trades", [])

        trades: list[Trade] = []

        for item in raw_trades:
            trades.append(
                Trade(
                    timestamp=int(item["time"]),
                    price=float(item["price"]),
                    volume=float(item["volume"]),
                    side=str(item["type"])
                    .strip()
                    .lower(),
                    symbol=source_symbol,
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
        Get a Level 2 order book snapshot from Nobitex.
        """

        if not symbol:
            raise ValueError("Symbol cannot be empty.")

        if depth <= 0:
            raise ValueError(
                "Depth must be greater than zero."
            )

        normalized_symbol = symbol.strip().upper()

        if normalized_symbol.endswith("IRT"):
            market_symbol = normalized_symbol
            source_symbol = normalized_symbol[:-3]
        else:
            market_symbol = f"{normalized_symbol}IRT"
            source_symbol = normalized_symbol

        response = requests.get(
            self.BASE_URL
            + f"/v3/orderbook/{market_symbol}",
            timeout=10,
        )

        response.raise_for_status()

        data = response.json()

        if data.get("status") != "ok":
            raise ValueError(
                f"Nobitex orderbook request failed: {data}"
            )

        raw_bids = data.get("bids", [])
        raw_asks = data.get("asks", [])

        bids = [
            OrderBookLevel(
                price=float(level[0]),
                volume=float(level[1]),
            )
            for level in raw_bids[:depth]
        ]

        asks = [
            OrderBookLevel(
                price=float(level[0]),
                volume=float(level[1]),
            )
            for level in raw_asks[:depth]
        ]

        return OrderBook(
            symbol=source_symbol,
            timestamp=int(data.get("lastUpdate", 0)),
            bids=bids,
            asks=asks,
        )